import os, re, cv2, base64
import numpy as np
from PIL import Image, ImageEnhance
from flask import Flask, request, jsonify
import easyocr

app    = Flask(__name__)
reader = None   # lazy load — first request initialises it

def get_reader():
    global reader
    if reader is None:
        print("Loading EasyOCR model (first time only)...")
        reader = easyocr.Reader(['en'], gpu=False)
        print("EasyOCR ready.")
    return reader

# ─────────────────────────────────────────────────────────────
#  PREPROCESSING  — tuned for handwritten marks on paper
# ─────────────────────────────────────────────────────────────

def preprocess(img_array):
    """
    Returns multiple preprocessed variants of the image.
    EasyOCR picks the one that gives the most numbers.
    """
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    variants = [img_array]   # always try the original colour image too

    # Upscale + CLAHE (fixes uneven lighting, shadows)
    up = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    eq  = clahe.apply(up)
    variants.append(eq)

    # Sharpen
    kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]], np.float32)
    sharp  = cv2.filter2D(eq, -1, kernel)
    variants.append(sharp)

    # PIL contrast boost (great for faded pencil)
    pil = Image.fromarray(gray)
    pil = pil.resize((gray.shape[1]*2, gray.shape[0]*2), Image.LANCZOS)
    pil = ImageEnhance.Contrast(pil).enhance(2.5)
    pil = ImageEnhance.Sharpness(pil).enhance(2.0)
    variants.append(np.array(pil))

    return variants


# ─────────────────────────────────────────────────────────────
#  NUMBER PARSING
# ─────────────────────────────────────────────────────────────

def parse_numbers(results):
    """
    EasyOCR returns list of (bbox, text, confidence).
    We extract numbers and handle fractions like 8/10.
    Only keeps numbers between 0 and 100.
    """
    nums = []
    for (_, text, conf) in results:
        if conf < 0.2:   # skip very low confidence
            continue
        text = text.strip()

        # Handle fractions: 8/10 → take numerator (8)
        if '/' in text:
            parts = text.split('/')
            try:
                val = int(parts[0].strip())
                if 0 <= val <= 100:
                    nums.append(val)
                continue
            except ValueError:
                pass

        # Plain numbers
        found = re.findall(r'\b\d{1,3}\b', text)
        for n in found:
            try:
                val = int(n)
                if 0 <= val <= 100:
                    nums.append(val)
            except ValueError:
                pass

    return nums


def extract_numbers_from_image(img_array):
    r        = get_reader()
    variants = preprocess(img_array)

    best_numbers = []
    best_raw     = []

    for variant in variants:
        try:
            results = r.readtext(variant, detail=1, paragraph=False)
            nums    = parse_numbers(results)
            if len(nums) > len(best_numbers):
                best_numbers = nums
                best_raw     = results
        except Exception as e:
            print(f"EasyOCR error on variant: {e}")
            continue

    raw_text = " | ".join([text for (_, text, _) in best_raw])
    return best_numbers, raw_text


# ─────────────────────────────────────────────────────────────
#  CALCULATIONS
# ─────────────────────────────────────────────────────────────

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


def find_index_html():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"),
        os.path.join(os.getcwd(), "index.html"),
        "/app/index.html",
        "index.html",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


# ─────────────────────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    path = find_index_html()
    if path is None:
        return f"<pre>index.html not found\ncwd: {os.getcwd()}\nfiles: {os.listdir(os.getcwd())}</pre>", 500
    with open(path, "r", encoding="utf-8") as f:
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
                "tip"  : "Hold phone steady above the paper. Make sure marks are clearly visible and well lit."
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
                "tip"  : "Hold phone steady above the paper. Make sure marks are clearly visible and well lit."
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
