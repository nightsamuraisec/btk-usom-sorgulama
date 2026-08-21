# BTK-USOM Sorgulama

> 🇹🇷 [Türkçe sürüm için tıklayın](README-tr.md)

<p align="center">
  <img src="https://img.shields.io/badge/version-1.1.0-blue?style=for-the-badge" alt="Version" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/badge/author-nightsamuraisec-111827?style=for-the-badge" alt="Author" />
  <img src="https://img.shields.io/badge/status-ready-success?style=for-the-badge" alt="Status" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="python" />
  <img src="https://img.shields.io/badge/PyQt5-GUI-41CD52?style=flat-square" alt="pyqt5" />
  <img src="https://img.shields.io/badge/Tampermonkey-Userscript-FF6900?style=flat-square" alt="tampermonkey" />
</p>

<p align="center">
  <strong>Dual GUI: BTK site query (OCR) + USOM/SGB malicious list API</strong>
</p>

<p align="center">
  <a href="#-about-the-project">About</a> ·
  <a href="#-screenshots">Screenshots</a> ·
  <a href="#-features">Features</a> ·
  <a href="#-folder-structure">Structure</a> ·
  <a href="#-built-with">Built With</a> ·
  <a href="#-getting-started">Getting Started</a> ·
  <a href="#-usage">Usage</a>
</p>

---

## 📌 About The Project

PyQt5 dual-panel app: BTK public site-query (OCR captcha) and USOM/SGB address API. Optional Tampermonkey badge script included. Education/portfolio — not an official API.

---

## 🖼 Screenshots

> Real UI captures under `screenshots/`.

### GUI

![GUI](screenshots/gui.png)

*BTK-USOM dual panel*

### USOM Badge

![USOM Badge](screenshots/usom-badge.png)

*USOM Badge*

---

## ✨ Features

- 🔍 Domain query automation
- 🖼 Captcha + Tesseract OCR
- 🛡 USOM status badge userscript

- 📸 **Automatic `screenshots/` media folder** — On launch (or first save), the app creates a `screenshots/` directory in the working folder. Screenshots, captures, and exports are stored there in an organized way. No manual folder setup required.

---

## 🗂 Folder Structure

```text
btk-usom-sorgulama/
├── btk_query.py
├── usom_link_plugin.js
├── requirements.txt
├── screenshots/
│   ├── gui.png
│   └── usom-badge.png
├── README.md
└── README-tr.md
```

> `screenshots/` — media output (screenshots, captures, exports). README images are referenced from here.

---

## 🛠 Built With

- Python + Requests / BeautifulSoup
- Tesseract OCR
- Tampermonkey

---

## 🚀 Getting Started

### Prerequisites

Python 3.10+, Tesseract OCR, Tampermonkey (for the userscript).

### Installation

```bash
git clone https://github.com/nightsamuraisec/btk-usom-sorgulama.git
cd btk-usom-sorgulama
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
python btk_query.py
```

### Environment Variables

Copy `.env.example` to `.env` when needed:

```env
# .env.example
SCREENSHOTS_DIR=screenshots
APP_DEBUG=false
```

---

## 📖 Usage

```bash
python btk_query.py
```
Install `usom_link_plugin.js` in Tampermonkey.

### Saving into `screenshots/`

1. Start the app — `screenshots/` is created automatically if missing.
2. Trigger a capture / export / QR save action.
3. Check the files:

```bash
dir screenshots          # Windows
ls screenshots           # Linux / macOS
```

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE).

Issues and contributions are welcome via GitHub.

---

<p align="center"><sub>BTK-USOM Sorgulama · by <a href="https://github.com/nightsamuraisec">nightsamuraisec</a> · MIT
