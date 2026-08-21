# BTK-USOM Sorgulama

> 🇬🇧 [Click here for English version](README.md)

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
  <strong>İkili GUI: BTK site sorgu (OCR) + USOM/SGB zararlı liste API</strong>
</p>

<p align="center">
  <a href="https://www.tampermonkey.net/">
    <img src="https://img.shields.io/badge/Kur-Tampermonkey-FF6900?style=for-the-badge&logo=tampermonkey&logoColor=white" alt="Tampermonkey Kur" />
  </a>
  &nbsp;
  <a href="https://raw.githubusercontent.com/nightsamuraisec/btk-usom-sorgulama/main/usom_link_plugin.user.js">
    <img src="https://img.shields.io/badge/Kur-USOM%20Userscript-111827?style=for-the-badge" alt="Userscript Kur" />
  </a>
</p>

<p align="center">
  <a href="#-proje-hakkında-about-the-project">Hakkında</a> ·
  <a href="#-ekran-görüntüleri-screenshots">Ekran Görüntüleri</a> ·
  <a href="#-tampermonkey-userscript">Userscript</a> ·
  <a href="#-özellikler-features">Özellikler</a> ·
  <a href="#-dosya-ağacı-folder-structure">Dosya Ağacı</a> ·
  <a href="#-kullanılan-teknolojiler-built-with">Teknolojiler</a> ·
  <a href="#-başlarken-getting-started">Başlarken</a> ·
  <a href="#-kullanım-usage">Kullanım</a>
</p>

---

## 📌 Proje Hakkında (About The Project)

PyQt5 ikili panel: BTK site sorgu (OCR captcha) ve USOM/SGB adres API’si. İsteğe bağlı Tampermonkey rozeti de var. Eğitim/portföy amaçlıdır; resmi API değildir.

---

## 🖼 Ekran Görüntüleri (Screenshots)

> Gerçek arayüz görüntüleri `screenshots/` klasöründe.

### GUI

![GUI](screenshots/gui.png)

*BTK-USOM ikili panel*

### USOM Rozeti

![USOM Rozeti](screenshots/usom-badge.png)

*USOM Rozeti*

---

## 🧩 Tampermonkey Userscript

1. **Tampermonkey** kur:
   - [Chrome / Edge](https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo)
   - [Firefox](https://addons.mozilla.org/firefox/addon/tampermonkey/)
2. Aşağıdaki linke tıkla (raw `.user.js` açılır — Tampermonkey kurulum sorar):

   **→ [usom_link_plugin.user.js kur](https://raw.githubusercontent.com/nightsamuraisec/btk-usom-sorgulama/main/usom_link_plugin.user.js)**

Doğrudan raw URL:

```text
https://raw.githubusercontent.com/nightsamuraisec/btk-usom-sorgulama/main/usom_link_plugin.user.js
```

---

## ✨ Özellikler (Features)

- 🔍 Domain sorgu otomasyonu
- 🖼 Captcha + Tesseract OCR
- 🛡 USOM durum rozeti userscript

- 📸 **Otomatik `screenshots/` medya klasörü** — Uygulama açılışında (veya ilk kayıtta) çalışma dizininde `screenshots/` klasörünü otomatik oluşturur. Ekran görüntüleri, yakalamalar ve dışa aktarımlar buraya düzenli kaydedilir. Manuel klasör oluşturmana gerek yoktur.

---

## 🗂 Dosya Ağacı (Folder Structure)

```text
btk-usom-sorgulama/
├── btk_query.py
├── usom_link_plugin.user.js
├── requirements.txt
├── screenshots/
│   ├── gui.png
│   └── usom-badge.png
├── README.md
└── README-tr.md
```

> `screenshots/` — medya çıktıları (ekran görüntüsü, kayıt, export). README görselleri buradan referanslanır.

---

## 🛠 Kullanılan Teknolojiler (Built With)

- Python + Requests / BeautifulSoup
- Tesseract OCR
- Tampermonkey

---

## 🚀 Başlarken (Getting Started)

### Ön şartlar (Prerequisites)

Python 3.10+, Tesseract OCR, Tampermonkey (userscript için).

### Kurulum (Installation)

```bash
git clone https://github.com/nightsamuraisec/btk-usom-sorgulama.git
cd btk-usom-sorgulama
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
python btk_query.py
```

### Çevre Değişkenleri (Environment Variables)

Gerektiğinde `.env.example` dosyasını `.env` olarak kopyala:

```env
# .env.example
SCREENSHOTS_DIR=screenshots
APP_DEBUG=false
```

---

## 📖 Kullanım (Usage)

```bash
python btk_query.py
```

Userscript (Tampermonkey kuruluysa tek tık):  
[usom_link_plugin.user.js kur](https://raw.githubusercontent.com/nightsamuraisec/btk-usom-sorgulama/main/usom_link_plugin.user.js)

### `screenshots/` klasörüne kayıt

1. Uygulamayı başlat — `screenshots/` yoksa otomatik oluşur.
2. Yakala / dışa aktar / QR kaydet gibi bir işlemi tetikle.
3. Dosyaları kontrol et:

```bash
dir screenshots          # Windows
ls screenshots           # Linux / macOS
```

---

## 📄 Lisans (License)

Bu proje **MIT License** ile lisanslanmıştır. Ayrıntılar: [`LICENSE`](LICENSE).

Katkı ve sorun bildirimleri GitHub Issues üzerinden yapılabilir. Geliştirici: **nightsamuraisec**.

---

<p align="center"><sub>BTK-USOM Sorgulama · by <a href="https://github.com/nightsamuraisec">nightsamuraisec</a> · MIT
