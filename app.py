import os, re, cv2, base64
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance
from flask import Flask, request, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

# ─────────────────────────────────────────────────────────────
#  PREPROCESSING
# ─────────────────────────────────────────────────────────────

def preprocess_for_handwriting(img_array):
    variants = []
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)

    # Variant 1: CLAHE + Otsu
    up = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    eq = clahe.apply(up)
    blur = cv2.GaussianBlur(eq, (3, 3), 0)
    _, v1 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(v1)

    # Variant 2: adaptive threshold
    up2 = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    blur2 = cv2.bilateralFilter(up2, 9, 75, 75)
    v2 = cv2.adaptiveThreshold(blur2, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
    variants.append(v2)

    # Variant 3: PIL contrast boost
    pil = Image.fromarray(gray).resize((gray.shape[1]*2, gray.shape[0]*2), Image.LANCZOS)
    pil = ImageEnhance.Contrast(pil).enhance(2.5)
    pil = ImageEnhance.Sharpness(pil).enhance(3.0)
    v3 = np.array(pil.convert("L"))
    _, v3t = cv2.threshold(v3, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(v3t)

    # Variant 4: inverted
    variants.append(cv2.bitwise_not(v1))

    return variants


DIGIT_CONFIGS = [
    r'--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789',
    r'--psm 4 --oem 3 -c tessedit_char_whitelist=0123456789',
    r'--psm 11 --oem 3 -c tessedit_char_whitelist=0123456789',
    r'--psm 13 --oem 3 -c tessedit_char_whitelist=0123456789',
    r'--psm 6 --oem 3',
    r'--psm 11 --oem 3',
]


def parse_numbers(text):
    raw = re.findall(r'\b\d{1,3}\b', text)
    nums = []
    for n in raw:
        try:
            val = int(n)
            if 0 <= val <= 100:
                nums.append(val)
        except ValueError:
            pass
    return nums


def extract_numbers_from_image(img_array):
    variants     = preprocess_for_handwriting(img_array)
    best_numbers = []
    best_text    = ""
    for variant in variants:
        pil_img = Image.fromarray(variant)
        for cfg in DIGIT_CONFIGS:
            try:
                text = pytesseract.image_to_string(pil_img, config=cfg)
                nums = parse_numbers(text)
                if len(nums) > len(best_numbers):
                    best_numbers = nums
                    best_text    = text
            except Exception:
                pass
    return best_numbers, best_text.strip()


def calculate_results(numbers):
    if not numbers:
        return {}
    total = sum(numbers)
    count = len(numbers)
    return {
        "numbers" : numbers,
        "equation": " + ".join(str(n) for n in numbers) + " = " + str(total),
        "total"   : total,
        "count"   : count,
        "average" : round(total / count, 2),
        "maximum" : max(numbers),
        "minimum" : min(numbers),
    }


def do_recount(numbers, claimed_total):
    actual  = sum(numbers)
    claimed = float(claimed_total)
    diff    = round(actual - claimed, 2)
    return {
        "numbers"       : numbers,
        "equation"      : " + ".join(str(n) for n in numbers) + " = " + str(actual),
        "actual_total"  : actual,
        "claimed_total" : claimed,
        "matches"       : abs(diff) < 0.01,
        "difference"    : diff,
    }


def decode_image(b64_string):
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    img_bytes = base64.b64decode(b64_string)
    arr       = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


# ─────────────────────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    # index.html is in the root folder (same level as app.py)
    html_path = os.path.join(BASE_DIR, "index.html")
    if not os.path.exists(html_path):
        files = os.listdir(BASE_DIR)
        return f"<h2>index.html not found</h2><p>Files: {files}</p>", 500
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/scan", methods=["POST"])
def scan():
    try:
        data = request.get_json()
        img  = decode_image(data.get("image", ""))
        if img is None:
            return jsonify({"error": "Could not decode image"}), 400
        numbers, raw = extract_numbers_from_image(img)
        if not numbers:
            return jsonify({
                "error": "No numbers found",
                "tip"  : "Ensure good lighting and clear handwriting"
            }), 422
        res = calculate_results(numbers)
        res["raw_text"] = raw
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/recount", methods=["POST"])
def recount():
    try:
        data    = request.get_json()
        claimed = data.get("claimed_total")
        if claimed is None:
            return jsonify({"error": "No claimed total provided"}), 400
        img = decode_image(data.get("image", ""))
        if img is None:
            return jsonify({"error": "Could not decode image"}), 400
        numbers, raw = extract_numbers_from_image(img)
        if not numbers:
            return jsonify({
                "error": "No numbers found",
                "tip"  : "Ensure good lighting and clear handwriting"
            }), 422
        res = do_recount(numbers, claimed)
        res["raw_text"] = raw
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n🎓  ExamScan  →  http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port)
