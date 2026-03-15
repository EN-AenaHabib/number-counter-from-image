import os, re, cv2, base64
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")

# ─────────────────────────────────────────────────────────────
#  PREPROCESSING  — tuned for handwritten marks on paper
# ─────────────────────────────────────────────────────────────

def preprocess_for_handwriting(img_array):
    """
    Returns a list of preprocessed variants.
    We try multiple approaches because handwriting varies a lot —
    some teachers write dark, some light, some with pen, some pencil.
    """
    variants = []

    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)

    # ── Variant 1: Upscale + CLAHE + Otsu ────────────────────
    # CLAHE = equalises brightness locally → handles shadows/uneven lighting
    up = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    eq = clahe.apply(up)
    blur = cv2.GaussianBlur(eq, (3, 3), 0)
    _, v1 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(v1)

    # ── Variant 2: Deskew + adaptive threshold ────────────────
    # Adaptive handles uneven backgrounds and shadows
    up2 = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    blur2 = cv2.bilateralFilter(up2, 9, 75, 75)
    v2 = cv2.adaptiveThreshold(
        blur2, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 15
    )
    variants.append(v2)

    # ── Variant 3: PIL-based enhancement ─────────────────────
    # Good for faded pencil marks
    pil = Image.fromarray(gray).resize(
        (gray.shape[1]*2, gray.shape[0]*2), Image.LANCZOS
    )
    pil = ImageEnhance.Contrast(pil).enhance(2.5)
    pil = ImageEnhance.Sharpness(pil).enhance(3.0)
    pil_gray = pil.convert("L")
    v3 = np.array(pil_gray)
    _, v3_thresh = cv2.threshold(v3, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(v3_thresh)

    # ── Variant 4: Invert (for dark background sheets) ────────
    variants.append(cv2.bitwise_not(v1))

    return variants


# ─────────────────────────────────────────────────────────────
#  OCR  — multiple configs for handwritten digits
# ─────────────────────────────────────────────────────────────

# Tesseract configs tuned for handwritten isolated digits
DIGIT_CONFIGS = [
    # psm 6 = uniform block of text (best for rows of marks)
    r'--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789',
    # psm 4 = single column (good for vertical lists)
    r'--psm 4 --oem 3 -c tessedit_char_whitelist=0123456789',
    # psm 11 = sparse text (picks up isolated numbers anywhere)
    r'--psm 11 --oem 3 -c tessedit_char_whitelist=0123456789',
    # psm 13 = raw line (good for a single row of marks)
    r'--psm 13 --oem 3 -c tessedit_char_whitelist=0123456789',
    # No whitelist — sometimes works better for handwriting
    r'--psm 6 --oem 3',
    r'--psm 11 --oem 3',
]


def parse_numbers(text):
    """Extract valid mark numbers (0-100) from OCR text."""
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
    """
    Tries every combination of preprocessing × OCR config.
    Returns the combination that found the most numbers.
    """
    variants = preprocess_for_handwriting(img_array)

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


# ─────────────────────────────────────────────────────────────
#  CALCULATIONS
# ─────────────────────────────────────────────────────────────

def calculate_results(numbers):
    if not numbers:
        return {}
    total   = sum(numbers)
    count   = len(numbers)
    avg     = round(total / count, 2)
    eq      = " + ".join(str(n) for n in numbers) + " = " + str(total)
    return {
        "numbers" : numbers,
        "equation": eq,
        "total"   : total,
        "count"   : count,
        "average" : avg,
        "maximum" : max(numbers),
        "minimum" : min(numbers),
    }


def do_recount(numbers, claimed_total):
    actual     = sum(numbers)
    claimed    = float(claimed_total)
    diff       = round(actual - claimed, 2)
    matches    = abs(diff) < 0.01
    eq         = " + ".join(str(n) for n in numbers) + " = " + str(actual)
    return {
        "numbers"       : numbers,
        "equation"      : eq,
        "actual_total"  : actual,
        "claimed_total" : claimed,
        "matches"       : matches,
        "difference"    : diff,
    }


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────

def decode_image(b64_string):
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    img_bytes = base64.b64decode(b64_string)
    arr       = np.frombuffer(img_bytes, np.uint8)
    img       = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img


# ─────────────────────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


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
                "tip"  : "Ensure good lighting, hold phone steady above the paper, numbers should be clearly written"
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
    os.makedirs("static", exist_ok=True)
    print("\n🎓  ExamScan  →  http://localhost:5000\n")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
