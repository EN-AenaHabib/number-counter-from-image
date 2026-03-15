<div align="center">

<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white"/>
<img src="https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white"/>
<img src="https://img.shields.io/badge/Tesseract_OCR-2E8B57?style=for-the-badge&logoColor=white"/>

<br/><br/>

# 🎓 ExamScan

### *Scan handwritten exam mark sheets — count, total & recount in seconds*

<br/>

> Point your phone camera at any exam paper —  
> ExamScan reads the handwritten marks, sums them up, and shows the result instantly.  
> Built for teachers who want to save time on manual counting and recounting.

<br/>

[![Live Demo](https://img.shields.io/badge/Live_Demo-Render-46E3B7?style=flat-square&logo=render)](https://examscanner.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)]()

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 📷 **Live Camera** | Real-time camera feed — no photo capture needed |
| 🔢 **Count & Total** | Scans all handwritten marks and shows `6+7+0+9+5 = 27` |
| 🔍 **Recount Mode** | Enter claimed total → app tells you ✅ Correct or ❌ Mismatch |
| ✍️ **Handwriting OCR** | Multiple preprocessing passes tuned for handwritten digits |
| 📱 **Mobile First** | Works on any phone browser — no app install needed |
| 🌐 **Web Based** | Share a link, she opens it on her phone, done |

---

## 📱 How to Use

```
1. Open the app link on your phone browser
2. Allow camera permission
3. Point camera at the exam mark sheet
4. Align marks inside the scanning frame
5. Tap  ✨ Scan Marks
6. Result pops up instantly
```

**For Recount:**
```
1. Switch to Recount tab
2. Type the total written on the paper
3. Scan — app tells you if it matches or not
```

---

## ⚙️ How It Works

```
📷  Live Camera Feed
        │
        ▼
📸  Capture Frame (when Scan tapped)
        │
        ▼
🔧  Image Preprocessing  ──────── 4 variants in parallel:
    │                              • CLAHE equalisation (fixes shadows)
    │                              • Upscale ×2.5 + Otsu threshold
    │                              • PIL contrast + sharpness boost
    │                              • Inverted (dark background sheets)
        │
        ▼
🤖  Tesseract OCR  ─────────────  6 configs per variant
    │                              Best result = most numbers found
        │
        ▼
🔢  Parse numbers (0–100 range filter)
        │
        ├── Count mode  →  sum + average + highest
        │
        └── Recount mode  →  compare against claimed total
                              ✅ Match or ❌ Mismatch + difference
        │
        ▼
📊  Popup result with equation
    e.g.  6 + 7 + 0 + 9 + 5 = 27
```

---

## 🚀 Deploy Live (Render — Free)

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/examscanner.git
git push -u origin main
```

### Step 2 — Deploy on Render

1. Go to [render.com](https://render.com) → **Sign up free**
2. Click **New** → **Web Service**
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` → click **Deploy**
5. Wait ~3 minutes → get your live URL ✅

> **Note:** Free tier sleeps after 15 min of no use. First visit takes ~30s to wake up. After that it's fast.

---

## 💻 Run Locally

### Requirements

- Python 3.8+
- Tesseract OCR installed on your system

### Install Tesseract

```bash
# Ubuntu / Debian / Render
sudo apt-get install -y tesseract-ocr

# Mac
brew install tesseract

# Windows
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Run

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/examscanner.git
cd examscanner

# Install Python packages
pip install -r requirements.txt

# Start server
python app.py

# Open in browser
http://localhost:5000
```

---

## 🗂️ Project Structure

```
examscanner/
│
├── app.py                  ← Flask backend (OCR + calculations)
├── requirements.txt        ← Python dependencies
├── Procfile                ← For Render deployment
├── render.yaml             ← Render auto-config
├── .gitignore
├── README.md
│
└── static/
    └── index.html          ← Full mobile UI (camera + results)
```

---

## 📦 Tech Stack

```
Backend
├── Flask          — web server
├── OpenCV         — image preprocessing
├── Tesseract OCR  — handwriting recognition
├── Pillow         — image enhancement
└── NumPy          — array operations

Frontend
└── Vanilla HTML/CSS/JS  — no frameworks, works on any phone
```

---

## 📊 Tips for Best Scan Results

| Do this | Avoid this |
|---|---|
| Hold phone directly above the paper | Scanning at an angle |
| Flat surface with good lighting | Dark rooms or harsh shadows |
| Marks clearly inside the scan frame | Marks near the edges |
| Paper flat and still | Paper curled or crumpled |
| Numbers written large and clear | Very small or cramped writing |

---

## 🔭 Coming Soon

- [ ] Average & result sheet generation
- [ ] Export results to PDF
- [ ] Multiple student scan mode
- [ ] Grade calculator (A/B/C based on total)
- [ ] History — save and review past scans

---

## 🤝 Contributing

Pull requests are welcome!

1. Fork the repo
2. Create your branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m "Add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

<div align="center">

Built with Flask + OpenCV + Tesseract

⭐ Star this repo if it helped you!

</div>
