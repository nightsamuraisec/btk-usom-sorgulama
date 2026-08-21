"""
BTK-USOM Sorgulama — ikili GUI (BTK site sorgu + USOM/SGB liste)
Eğitim / portföy amaçlıdır; resmi API değildir.
"""

import os
import sys
import time
from shutil import which
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# --- SCREENSHOTS DIR AUTO ---
_SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
os.makedirs(_SCREENSHOTS_DIR, exist_ok=True)

# =======================================================================
# TESSERACT
# =======================================================================
OCR_AVAILABLE = False
try:
    import pytesseract
    from PIL import Image

    def find_tesseract_path():
        windows_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        t_path = which("tesseract")
        if t_path and os.path.exists(t_path):
            return t_path
        if sys.platform == "win32":
            for path in windows_paths:
                if os.path.exists(path):
                    return path
        return None

    tesseract_exe_path = find_tesseract_path()
    if tesseract_exe_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path
        OCR_AVAILABLE = True
except ImportError:
    pass

# =======================================================================
# SABİTLER
# =======================================================================
SORGULAMA_URL = "https://internet.btk.gov.tr/sitesorgu/"
USOM_API_FALLBACKS = (
    "https://siberguvenlik.gov.tr/api",
    "https://www.usom.gov.tr/api",
)
CAPTCHA_FILENAME = os.path.join(_SCREENSHOTS_DIR, "btk_captcha.png")
MAX_DENEME = 10
MAX_NET_RETRY = 4
BTK_TIMEOUT = (12, 75)  # (connect, read)
USOM_TIMEOUT = (10, 45)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_usom_maps_cache = None
_usom_maps_ts = 0
_USOM_MAP_TTL = 86400

DESC_FALLBACK = {
    "PH": "Oltalama (Phishing)",
    "BP": "Bankacılık - Oltalama",
    "MD": "Zararlı yazılım barındıran / yayan",
    "OA": "Zararlı yazılım komuta-kontrol",
}
SOURCE_FALLBACK = {
    "US": "USOM / TR-CERT",
    "SO": "SOME / CERT",
    "RS": "RSA",
    "IH": "İhbar",
    "SB": "SGB",
}
CONN_FALLBACK = {
    "AC": "APT C&C",
    "BC": "Botnet C&C",
    "EK": "Exploit Kit",
    "MC": "Mobil C&C",
    "MF": "Zararlı dosya indirme",
    "MM": "Mining zararlısı",
    "PH": "Oltalama",
    "OT": "Diğer",
}


def normalize_host(value: str) -> str:
    value = (value or "").strip().lower()
    if not value:
        return ""
    if "://" not in value:
        value = "http://" + value
    try:
        host = urlparse(value).hostname or ""
    except Exception:
        host = value.split("/")[0]
    return (host or "").replace("www.", "")


def _new_session(json_api=False):
    s = requests.Session()
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    if json_api:
        headers["Accept"] = "application/json"
    else:
        headers["Accept"] = (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        )
    s.headers.update(headers)
    return s


def _request_with_retry(session, method, url, timeout, progress_cb=None, label="İstek", **kwargs):
    last_err = None
    for i in range(1, MAX_NET_RETRY + 1):
        try:
            if progress_cb and i > 1:
                progress_cb(f"{label} yeniden deneniyor ({i}/{MAX_NET_RETRY})…")
            resp = session.request(method, url, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_err = e
            time.sleep(1.2 * i)
    raise last_err


def recognize_captcha_code(image_path):
    try:
        img = Image.open(image_path).convert("L")
        img = img.point(lambda p: p > 140 and 255)
        config_params = (
            "--psm 7 -c tessedit_char_whitelist="
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        )
        text = pytesseract.image_to_string(img, config=config_params)
        return "".join(c for c in text if c.isalnum()).strip()
    except Exception:
        return None


def _extract_btk_extras(soup_result):
    """Sayfadaki ek tablo / metin bloklarını topla."""
    extras = []
    for table in soup_result.find_all("table"):
        tid = table.get("id") or ""
        if tid == "title_1":
            continue
        rows = []
        for row in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            cells = [c for c in cells if c]
            if cells:
                rows.append(" | ".join(cells))
        if rows:
            extras.append({"title": tid or "Tablo", "rows": rows})

    for div_id in ("sorgu_mahkeme", "sorgu_sonuc", "sorgu_ip"):
        div = soup_result.find("div", id=div_id)
        if not div:
            continue
        text = div.get_text("\n", strip=True)
        if text and len(text) < 4000:
            extras.append({"title": div_id, "rows": [text]})
    return extras


# =======================================================================
# BTK SORGULAMA
# =======================================================================
def btk_sorgulama_yap(domain_to_query, progress_cb=None):
    """
    Returns dict:
      ok, blocked, site_info, karar_tr, karar_en, extras, message, attempts, detail
    """
    result = {
        "ok": False,
        "blocked": None,
        "site_info": {},
        "karar_tr": "",
        "karar_en": "",
        "extras": [],
        "message": "",
        "attempts": 0,
        "detail": "",
        "query": domain_to_query,
    }

    if not OCR_AVAILABLE:
        result["message"] = "Tesseract OCR bulunamadı. BTK otomatik sorgu için gerekli."
        return result

    session = _new_session()
    deneme = 1
    while deneme <= MAX_DENEME:
        result["attempts"] = deneme
        if progress_cb:
            progress_cb(f"BTK deneme {deneme}/{MAX_DENEME}…")

        try:
            response = _request_with_retry(
                session, "GET", SORGULAMA_URL, BTK_TIMEOUT,
                progress_cb=progress_cb, label="BTK bağlantı",
            )
        except requests.RequestException as e:
            result["message"] = f"BTK sayfasına bağlanılamadı: {e}"
            result["detail"] = (
                "İpucu: BTK sitesi yavaş/kapalı olabilir. Birkaç sn sonra tekrar deneyin."
            )
            return result

        soup = BeautifulSoup(response.content, "html.parser")
        captcha_img_tag = soup.find(
            "img", src=lambda src: src and "captcha" in src.lower()
        )
        if not captcha_img_tag or "src" not in captcha_img_tag.attrs:
            result["message"] = "CAPTCHA resmi bulunamadı."
            return result

        captcha_full_url = urljoin(SORGULAMA_URL, captcha_img_tag["src"])
        try:
            captcha_response = _request_with_retry(
                session, "GET", captcha_full_url, BTK_TIMEOUT,
                progress_cb=progress_cb, label="CAPTCHA indirme",
            )
            with open(CAPTCHA_FILENAME, "wb") as f:
                f.write(captcha_response.content)
        except requests.RequestException as e:
            result["message"] = f"CAPTCHA indirilemedi: {e}"
            return result

        captcha_code = recognize_captcha_code(CAPTCHA_FILENAME)
        if not captcha_code:
            deneme += 1
            time.sleep(1)
            continue

        if progress_cb:
            progress_cb(f"OCR: {captcha_code} — form gönderiliyor…")

        form_data = {}
        for hidden_input in soup.find_all("input", {"type": "hidden"}):
            name = hidden_input.get("name")
            if name:
                form_data[name] = hidden_input.get("value", "")

        form_data["deger"] = domain_to_query
        form_data["security_code"] = captcha_code
        form_data["submit"] = "Sorgula"

        try:
            post_response = _request_with_retry(
                session, "POST", SORGULAMA_URL, BTK_TIMEOUT,
                progress_cb=progress_cb, label="BTK sorgu",
                data=form_data,
                headers={
                    "Referer": SORGULAMA_URL,
                    "Origin": "https://internet.btk.gov.tr",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
        except requests.RequestException as e:
            result["message"] = f"Sorgulama isteği başarısız: {e}"
            return result

        response_text = post_response.text
        if (
            "Güvenlik kodunu yanlış girdiniz" in response_text
            or "Güvenlik Kodu Hatası" in response_text
        ):
            deneme += 1
            time.sleep(1.5)
            continue

        soup_result = BeautifulSoup(response_text, "html.parser")
        table_1 = soup_result.find("table", id="title_1")
        if table_1:
            for row in table_1.find_all("tr"):
                th, td = row.find("th"), row.find("td")
                if th and td and th.text.strip():
                    val = td.get_text(separator=" | ", strip=True)
                    if val:
                        result["site_info"][th.text.strip()] = val

        result["extras"] = _extract_btk_extras(soup_result)

        if soup_result.find("div", id="sorgu_mahkeme"):
            result["blocked"] = True
            karar_span = soup_result.find("span", class_="yazi2_2")
            if karar_span:
                result["karar_tr"] = karar_span.text.strip()
            else:
                result["karar_tr"] = (
                    f"{domain_to_query} hakkında erişim engeli kararı bulunmaktadır."
                )
            karar_en = soup_result.find("span", class_="yazi3_1")
            if karar_en:
                result["karar_en"] = karar_en.text.strip()
            result["message"] = "ERİŞİM ENGELİ VAR"
        elif soup_result.find("div", id="sorgu_sonuc"):
            result["blocked"] = False
            result["message"] = "Erişim engelleme kararı bulunmamaktadır."
        else:
            result["message"] = "Beklenmeyen yanıt; sayfa çözümlenemedi."
            result["detail"] = response_text[:500]
            return result

        result["ok"] = True
        return result

    result["message"] = f"{MAX_DENEME} denemede CAPTCHA okunamadı."
    return result


# =======================================================================
# USOM / SGB API
# =======================================================================
def _fetch_usom_maps(session, base, progress_cb=None):
    global _usom_maps_cache, _usom_maps_ts
    now = time.time()
    if _usom_maps_cache and (now - _usom_maps_ts) < _USOM_MAP_TTL:
        return _usom_maps_cache

    maps = {
        "desc": dict(DESC_FALLBACK),
        "source": dict(SOURCE_FALLBACK),
        "conn": dict(CONN_FALLBACK),
    }
    endpoints = {
        "desc": "address-description/index",
        "source": "address-source/index",
        "conn": "address-connection-type/index",
    }
    for key, path in endpoints.items():
        try:
            if progress_cb:
                progress_cb(f"USOM sözlük: {key}…")
            r = session.get(f"{base}/{path}", timeout=USOM_TIMEOUT)
            if r.status_code != 200 or "application/json" not in (
                r.headers.get("content-type") or ""
            ):
                continue
            data = r.json()
            for m in data.get("models") or []:
                mid = str(m.get("id") or "").strip()
                title = (m.get("tr_title") or m.get("en_title") or "").strip()
                if mid and title:
                    maps[key][mid] = title
        except Exception:
            continue

    _usom_maps_cache = maps
    _usom_maps_ts = now
    return maps


def _label(maps, kind, code):
    code = (code or "").strip()
    if not code:
        return "—"
    return maps.get(kind, {}).get(code, code)


def _normalize_entry_host(url_value):
    return normalize_host(url_value or "")


def _entry_matches_host(entry_url, host):
    eh = _normalize_entry_host(entry_url)
    if not eh or not host:
        return False
    if eh == host:
        return True
    # alt alan: evil.facebook.com ↔ facebook.com listede ise
    return eh.endswith("." + host) or host.endswith("." + eh)


def usom_sorgulama_yap(domain_to_query, progress_cb=None):
    """
    Returns dict with detailed API matches (exact + related).
    """
    host = normalize_host(domain_to_query)
    result = {
        "ok": False,
        "listed": None,
        "host": host,
        "message": "",
        "total_hits": 0,
        "exact": [],
        "related": [],
        "api_base": "",
        "detail": "",
    }
    if not host:
        result["message"] = "Geçersiz alan adı."
        return result

    session = _new_session(json_api=True)
    data = None
    used_base = None
    last_err = None

    for base in USOM_API_FALLBACKS:
        try:
            if progress_cb:
                progress_cb(f"USOM API sorgulanıyor ({base})…")
            resp = _request_with_retry(
                session,
                "GET",
                f"{base}/address/index",
                USOM_TIMEOUT,
                progress_cb=progress_cb,
                label="USOM API",
                params={"q": host},
            )
            ctype = (resp.headers.get("content-type") or "").lower()
            if "json" not in ctype:
                last_err = f"{base} JSON dönmedi ({ctype or 'html'})"
                continue
            data = resp.json()
            used_base = base
            break
        except requests.RequestException as e:
            last_err = str(e)
            continue

    if data is None:
        result["message"] = f"USOM API erişilemedi: {last_err}"
        return result

    maps = _fetch_usom_maps(session, used_base, progress_cb=progress_cb)
    models = data.get("models") or []
    # İkinci sayfa varsa ilgili kayıtları da al (max 2 sayfa)
    page_count = int(data.get("pageCount") or 1)
    if page_count > 1:
        try:
            if progress_cb:
                progress_cb("USOM ek sayfa alınıyor…")
            resp2 = session.get(
                f"{used_base}/address/index",
                params={"q": host, "page": 1},
                timeout=USOM_TIMEOUT,
            )
            if "json" in (resp2.headers.get("content-type") or "").lower():
                models = models + (resp2.json().get("models") or [])
        except Exception:
            pass

    exact, related = [], []
    seen = set()
    for m in models:
        url_val = (m.get("url") or "").strip()
        key = (m.get("id"), url_val)
        if key in seen:
            continue
        seen.add(key)
        entry = {
            "id": m.get("id"),
            "url": url_val,
            "type": m.get("type") or "—",
            "desc_code": m.get("desc") or "",
            "desc": _label(maps, "desc", m.get("desc")),
            "source_code": m.get("source") or "",
            "source": _label(maps, "source", m.get("source")),
            "connection_code": m.get("connectiontype") or "",
            "connection": _label(maps, "conn", m.get("connectiontype")),
            "criticality": m.get("criticality_level"),
            "date": (m.get("date") or "")[:19],
        }
        if _entry_matches_host(url_val, host):
            exact.append(entry)
        else:
            related.append(entry)

    result["ok"] = True
    result["api_base"] = used_base
    result["total_hits"] = int(data.get("totalCount") or len(models))
    result["exact"] = exact
    result["related"] = related[:25]
    result["listed"] = len(exact) > 0

    if exact:
        result["message"] = (
            f"Tam eşleşme: {len(exact)} kayıt USOM/SGB zararlı listesinde."
        )
    elif related:
        result["message"] = (
            f"Tam eşleşme yok; '{host}' içeren {result['total_hits']} benzer kayıt var."
        )
    else:
        result["message"] = "USOM/SGB zararlı adres API’sinde kayıt bulunamadı."

    result["detail"] = (
        f"Kaynak: {used_base}/address/index?q={host}\n"
        f"API totalCount: {result['total_hits']}"
    )
    return result


def format_btk_report(btk):
    lines = [
        f"Sorgu     : {btk.get('query') or '—'}",
        f"Durum     : {btk.get('message') or '—'}",
        f"OCR deneme: {btk.get('attempts') or 0}",
        "",
    ]
    if btk.get("site_info"):
        lines.append("[ Site bilgileri ]")
        for k, v in btk["site_info"].items():
            lines.append(f"  {k}: {v}")
        lines.append("")
    if btk.get("karar_tr"):
        lines.append(f"Karar (TR): {btk['karar_tr']}")
    if btk.get("karar_en"):
        lines.append(f"Karar (EN): {btk['karar_en']}")
    if btk.get("extras"):
        lines.append("")
        lines.append("[ Ek ayrıntılar ]")
        for block in btk["extras"][:6]:
            lines.append(f"  · {block.get('title')}")
            for row in (block.get("rows") or [])[:8]:
                lines.append(f"    {row[:300]}")
    if btk.get("detail") and not btk.get("ok"):
        lines.append("")
        lines.append(btk["detail"])
    return "\n".join(lines).strip()


def format_usom_report(usom):
    lines = [
        f"Host        : {usom.get('host') or '—'}",
        f"API         : {usom.get('api_base') or '—'}",
        f"Toplam hit  : {usom.get('total_hits', 0)}",
        f"Tam eşleşme : {len(usom.get('exact') or [])}",
        f"Benzer kayıt: {len(usom.get('related') or [])}",
        "",
        usom.get("message") or "",
        "",
    ]

    def _dump(title, items):
        if not items:
            return
        lines.append(f"[ {title} ]")
        for i, e in enumerate(items, 1):
            lines.append(f"{i}. {e.get('url')}")
            lines.append(
                f"   ID:{e.get('id')}  Tip:{e.get('type')}  "
                f"Kritiklik:{e.get('criticality')}"
            )
            lines.append(f"   Kategori : {e.get('desc')} ({e.get('desc_code')})")
            lines.append(f"   Kaynak   : {e.get('source')} ({e.get('source_code')})")
            lines.append(
                f"   Bağlantı : {e.get('connection')} ({e.get('connection_code')})"
            )
            lines.append(f"   Tarih    : {e.get('date') or '—'}")
            lines.append("")

    _dump("Tam eşleşen kayıtlar", usom.get("exact") or [])
    _dump("Benzer / ilgili kayıtlar", usom.get("related") or [])
    if usom.get("detail"):
        lines.append(usom["detail"])
    return "\n".join(lines).strip()


# =======================================================================
# GUI
# =======================================================================
def run_gui():
    from PyQt5.QtCore import Qt, QThread, pyqtSignal
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import (
        QApplication,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    class BtkWorker(QThread):
        progress = pyqtSignal(str)
        finished = pyqtSignal(dict)

        def __init__(self, domain):
            super().__init__()
            self.domain = domain

        def run(self):
            self.finished.emit(
                btk_sorgulama_yap(self.domain, progress_cb=self.progress.emit)
            )

    class UsomWorker(QThread):
        progress = pyqtSignal(str)
        finished = pyqtSignal(dict)

        def __init__(self, domain):
            super().__init__()
            self.domain = domain

        def run(self):
            self.finished.emit(
                usom_sorgulama_yap(self.domain, progress_cb=self.progress.emit)
            )

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("BTK-USOM Sorgulama")
            self.setMinimumSize(820, 560)
            self.resize(920, 620)
            self._btk_worker = None
            self._usom_worker = None
            self._build_ui()
            self._apply_style()

        def _build_ui(self):
            root = QWidget()
            self.setCentralWidget(root)
            layout = QVBoxLayout(root)
            layout.setContentsMargins(20, 18, 20, 18)
            layout.setSpacing(14)

            title = QLabel("BTK-USOM")
            title.setObjectName("title")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)

            sub = QLabel("Alan adı / IP — her kaynak ayrı ayrı sorgulanır")
            sub.setObjectName("subtitle")
            sub.setAlignment(Qt.AlignCenter)
            layout.addWidget(sub)

            self.input = QLineEdit()
            self.input.setPlaceholderText("örnek: example.com")
            layout.addWidget(self.input)

            self.status = QLabel("Hazır — soldan BTK veya sağdan USOM seçin")
            self.status.setObjectName("status")
            layout.addWidget(self.status)

            panels = QHBoxLayout()
            panels.setSpacing(12)

            # BTK panel
            btk_frame = QFrame()
            btk_frame.setObjectName("panel")
            btk_l = QVBoxLayout(btk_frame)
            btk_head = QLabel("BTK Site Sorgu")
            btk_head.setObjectName("panelTitle")
            self.btn_btk = QPushButton("BTK Sorgula")
            self.btn_btk.clicked.connect(self.start_btk)
            self.btk_badge = QLabel("—")
            self.btk_badge.setObjectName("badgeNeutral")
            self.btk_badge.setAlignment(Qt.AlignCenter)
            self.btk_out = QTextEdit()
            self.btk_out.setReadOnly(True)
            btk_l.addWidget(btk_head)
            btk_l.addWidget(self.btn_btk)
            btk_l.addWidget(self.btk_badge)
            btk_l.addWidget(self.btk_out, 1)

            # USOM panel
            usom_frame = QFrame()
            usom_frame.setObjectName("panel")
            usom_l = QVBoxLayout(usom_frame)
            usom_head = QLabel("USOM Liste Kontrolü")
            usom_head.setObjectName("panelTitle")
            self.btn_usom = QPushButton("USOM Sorgula")
            self.btn_usom.setObjectName("btnUsom")
            self.btn_usom.clicked.connect(self.start_usom)
            self.usom_badge = QLabel("—")
            self.usom_badge.setObjectName("badgeNeutral")
            self.usom_badge.setAlignment(Qt.AlignCenter)
            self.usom_out = QTextEdit()
            self.usom_out.setReadOnly(True)
            usom_l.addWidget(usom_head)
            usom_l.addWidget(self.btn_usom)
            usom_l.addWidget(self.usom_badge)
            usom_l.addWidget(self.usom_out, 1)

            panels.addWidget(btk_frame, 1)
            panels.addWidget(usom_frame, 1)
            layout.addLayout(panels, 1)

            foot = QLabel(
                "Eğitim / portföy aracı · resmi BTK veya USOM API’si değildir"
            )
            foot.setObjectName("footer")
            foot.setAlignment(Qt.AlignCenter)
            layout.addWidget(foot)

        def _apply_style(self):
            self.setStyleSheet(
                """
                QMainWindow, QWidget {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 #0f1c24, stop:0.5 #132830, stop:1 #0c161c
                    );
                    color: #e7eef2;
                    font-family: 'Segoe UI', 'Candara', sans-serif;
                }
                #title {
                    font-size: 28px;
                    font-weight: 700;
                    letter-spacing: 3px;
                    color: #f0f7fa;
                }
                #subtitle {
                    font-size: 13px;
                    color: #8aa3b0;
                    margin-bottom: 4px;
                }
                QLineEdit {
                    background: #1a2e38;
                    border: 1px solid #2d4a56;
                    border-radius: 8px;
                    padding: 10px 14px;
                    font-size: 15px;
                    color: #f2f7f9;
                    selection-background-color: #1f6f7a;
                }
                QLineEdit:focus { border-color: #3d9aaa; }
                QPushButton {
                    background: #1f6f7a;
                    color: #ffffff;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 16px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover { background: #278a97; }
                QPushButton:disabled { background: #2a4048; color: #7a9098; }
                QPushButton#btnUsom { background: #3d5a6e; }
                QPushButton#btnUsom:hover { background: #4a6d85; }
                #status { color: #9bb4c0; font-size: 12px; }
                #panel {
                    background: rgba(20, 38, 46, 0.92);
                    border: 1px solid #2a4450;
                    border-radius: 12px;
                }
                #panelTitle {
                    font-size: 15px;
                    font-weight: 600;
                    color: #c5d8e0;
                    padding: 4px 2px;
                }
                QTextEdit {
                    background: #101c22;
                    border: 1px solid #243840;
                    border-radius: 8px;
                    padding: 8px;
                    font-family: 'Cascadia Mono', 'Consolas', monospace;
                    font-size: 12px;
                    color: #d5e4ea;
                }
                #badgeNeutral, #badgeOk, #badgeBad, #badgeWarn {
                    border-radius: 6px;
                    padding: 8px;
                    font-weight: 700;
                    font-size: 13px;
                }
                #badgeNeutral { background: #2a3d46; color: #a8bcc4; }
                #badgeOk { background: #1a4a36; color: #7ddea8; }
                #badgeBad { background: #5a1e1e; color: #ffb0b0; }
                #badgeWarn { background: #4a3a16; color: #f0d58a; }
                #footer { color: #6a828e; font-size: 11px; }
                """
            )

        def _domain(self):
            domain = self.input.text().strip()
            if not domain:
                QMessageBox.warning(self, "Eksik", "Alan adı veya IP girin.")
                return None
            return domain

        def start_btk(self):
            domain = self._domain()
            if not domain:
                return
            if self._btk_worker and self._btk_worker.isRunning():
                return

            self.btn_btk.setEnabled(False)
            self.status.setText("BTK sorgulanıyor…")
            self._set_badge(self.btk_badge, "Sorgulanıyor…", "badgeWarn")
            self.btk_out.setPlainText("")

            self._btk_worker = BtkWorker(domain)
            self._btk_worker.progress.connect(self._on_progress)
            self._btk_worker.finished.connect(self._on_btk_finished)
            self._btk_worker.start()

        def start_usom(self):
            domain = self._domain()
            if not domain:
                return
            if self._usom_worker and self._usom_worker.isRunning():
                return

            self.btn_usom.setEnabled(False)
            self.status.setText("USOM sorgulanıyor…")
            self._set_badge(self.usom_badge, "Sorgulanıyor…", "badgeWarn")
            self.usom_out.setPlainText("")

            self._usom_worker = UsomWorker(domain)
            self._usom_worker.progress.connect(self._on_progress)
            self._usom_worker.finished.connect(self._on_usom_finished)
            self._usom_worker.start()

        def _on_progress(self, msg):
            self.status.setText(msg)

        def _set_badge(self, label, text, obj_name):
            label.setText(text)
            label.setObjectName(obj_name)
            label.style().unpolish(label)
            label.style().polish(label)

        def _on_btk_finished(self, btk):
            self.btn_btk.setEnabled(True)
            self.status.setText("BTK tamamlandı")
            self.btk_out.setPlainText(format_btk_report(btk))

            if not btk.get("ok"):
                self._set_badge(self.btk_badge, "Hata / OCR", "badgeWarn")
            elif btk.get("blocked") is True:
                self._set_badge(self.btk_badge, "ERİŞİM ENGELİ VAR", "badgeBad")
            elif btk.get("blocked") is False:
                self._set_badge(self.btk_badge, "ENGEL YOK", "badgeOk")
            else:
                self._set_badge(self.btk_badge, "Bilinmiyor", "badgeNeutral")

            try:
                if os.path.exists(CAPTCHA_FILENAME):
                    os.remove(CAPTCHA_FILENAME)
            except Exception:
                pass

        def _on_usom_finished(self, usom):
            self.btn_usom.setEnabled(True)
            self.status.setText("USOM tamamlandı")
            self.usom_out.setPlainText(format_usom_report(usom))

            if not usom.get("ok"):
                self._set_badge(self.usom_badge, "Hata", "badgeWarn")
            elif usom.get("listed"):
                self._set_badge(self.usom_badge, "YASAKLI LİSTEDE", "badgeBad")
            elif usom.get("related"):
                self._set_badge(self.usom_badge, "BENZER KAYIT VAR", "badgeWarn")
            else:
                self._set_badge(self.usom_badge, "LİSTEDE YOK", "badgeOk")

    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


def run_cli():
    target = input("Lütfen sorgulamak istediğiniz IP/Domain'i girin: ").strip()
    if not target:
        print("Domain/IP girişi yapılmadı.")
        return

    print("\n--- USOM ---")
    usom = usom_sorgulama_yap(target, progress_cb=print)
    print(format_usom_report(usom))

    print("\n--- BTK ---")
    btk = btk_sorgulama_yap(target, progress_cb=print)
    print(format_btk_report(btk))

    try:
        if os.path.exists(CAPTCHA_FILENAME):
            os.remove(CAPTCHA_FILENAME)
    except Exception:
        pass


if __name__ == "__main__":
    if "--cli" in sys.argv:
        run_cli()
    else:
        try:
            run_gui()
        except ImportError:
            print("PyQt5 yok; CLI moduna geçiliyor. (pip install PyQt5)")
            print("GUI için: pip install PyQt5 && python btk_query.py")
            print("-" * 50)
            run_cli()
