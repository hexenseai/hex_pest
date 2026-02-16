"""
80mm x 25mm rulo etiket PDF üretimi. Sol: QR (benzersiz_kod), sağ: bölge, istasyon adı, benzersiz_kod (kalın ve büyük).
Türkçe karakter desteği için TTF font kullanılır (DejaVu veya Windows Arial).
"""
import io
import os

import qrcode
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# Türkçe uyumlu font adları (kayıt sonrası kullanılacak)
_FONT_NAME = "Helvetica"
_FONT_BOLD_NAME = "Helvetica-Bold"


def _register_turkish_fonts():
    """Türkçe karakter destekleyen TTF font kaydeder.
    Öncelik: core/fonts/DejaVu → Linux sistem DejaVu → Windows Arial.
    Ubuntu/Linux'ta sistem DejaVu fontları kullanılır (fonts-dejavu-core paketi).
    """
    global _FONT_NAME, _FONT_BOLD_NAME
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    def _try_register_dejavu(regular_path, bold_path):
        if os.path.isfile(regular_path) and os.path.isfile(bold_path):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", regular_path))
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold_path))
                return True
            except Exception:
                pass
        return False

    # 1) Proje içi core/fonts: DejaVuSans.ttf, DejaVuSans-Bold.ttf
    core_dir = os.path.dirname(os.path.abspath(__file__))
    fonts_dir = os.path.join(core_dir, "fonts")
    dejavu_regular = os.path.join(fonts_dir, "DejaVuSans.ttf")
    dejavu_bold = os.path.join(fonts_dir, "DejaVuSans-Bold.ttf")
    if _try_register_dejavu(dejavu_regular, dejavu_bold):
        _FONT_NAME, _FONT_BOLD_NAME = "DejaVuSans", "DejaVuSans-Bold"
        return

    # 2) Linux/Ubuntu: Sistem DejaVu fontları (fonts-dejavu-core paketi)
    linux_dejavu_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    for regular in linux_dejavu_paths:
        bold = regular.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
        if _try_register_dejavu(regular, bold):
            _FONT_NAME, _FONT_BOLD_NAME = "DejaVuSans", "DejaVuSans-Bold"
            return

    # 3) Windows: Arial (Türkçe destekli)
    windir = os.environ.get("WINDIR", "")
    if windir:
        arial = os.path.join(windir, "Fonts", "arial.ttf")
        arial_bold = os.path.join(windir, "Fonts", "arialbd.ttf")
        if os.path.isfile(arial) and os.path.isfile(arial_bold):
            try:
                pdfmetrics.registerFont(TTFont("ArialTR", arial))
                pdfmetrics.registerFont(TTFont("ArialTR-Bold", arial_bold))
                _FONT_NAME, _FONT_BOLD_NAME = "ArialTR", "ArialTR-Bold"
                return
            except Exception:
                pass
    # Helvetica kalır (Türkçe karakterler boş/kutu çıkabilir)
    return


# Modül yüklendiğinde bir kez dene
_register_turkish_fonts()


LABEL_WIDTH_MM = 80
LABEL_HEIGHT_MM = 25
QR_SIZE_MM = 18  # kare QR, etiket yüksekliğine sığacak
TEXT_LEFT_MM = 23  # metin alanı başlangıcı
MARGIN_MM = 3  # kenarlardan boşluk
TEXT_RIGHT_MARGIN_MM = 3  # sağ kenar boşluğu
FONT_ZONE_STATION = 10  # bölge ve istasyon açıklaması (benzersiz_kod dışı)
FONT_BENZERSIZ = 14     # benzersiz kod (kalın)
LINE_HEIGHT_PT = 10     # satır aralığı


def _make_qr_image(benzersiz_kod, pixel_size=120):
    """Benzersiz kodu QR kod olarak PNG bytes döndürür (pixel_size x pixel_size)."""
    qr = qrcode.QRCode(version=1, box_size=4, border=1)
    qr.add_data(benzersiz_kod)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((pixel_size, pixel_size))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def generate_station_labels_pdf(stations):
    """
    Seçili Station queryset/iterable için 80x25mm etiket PDF'i oluşturur.
    Her etiket ayrı sayfada. Sol: QR (benzersiz_kod), sağ: bölge adı, istasyon adı, benzersiz_kod (bold, büyük).
    """
    width_pt = LABEL_WIDTH_MM * mm
    height_pt = LABEL_HEIGHT_MM * mm
    margin_pt = MARGIN_MM * mm
    text_right_pt = width_pt - (TEXT_RIGHT_MARGIN_MM * mm)
    qr_size_pt = QR_SIZE_MM * mm
    text_left_pt = TEXT_LEFT_MM * mm

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width_pt, height_pt))

    for station in stations:
        station = station  # select_related için döngüde tekrar kullanılabilir
        zone = getattr(station, "zone", None)
        benzersiz_kod = station.benzersiz_kod or f"ST-{station.pk}"
        zone_desc = ""
        if zone:
            zone_desc = (getattr(zone, "kod", "") or "") + " " + (getattr(zone, "ad", "") or "")
            zone_desc = zone_desc.strip() or "—"
        station_desc = (getattr(station, "ad", "") or getattr(station, "kod", "") or "").strip() or "—"

        # QR sol tarafa, kenardan margin_pt uzakta
        try:
            qr_buf = _make_qr_image(benzersiz_kod)
            c.drawImage(ImageReader(qr_buf), margin_pt, height_pt - margin_pt - qr_size_pt, width=qr_size_pt, height=qr_size_pt)
        except Exception:
            pass  # QR çizilemezse metin alanı yeterli

        # Metin: bölge, istasyon, benzersiz_kod (bold, büyük) — Türkçe uyumlu font
        top = height_pt - margin_pt
        c.setFont(_FONT_NAME, FONT_ZONE_STATION)
        c.drawString(text_left_pt, top - LINE_HEIGHT_PT, (zone_desc or "")[:50])
        c.drawString(text_left_pt, top - 2 * LINE_HEIGHT_PT, (station_desc or "")[:50])
        c.setFont(_FONT_BOLD_NAME, FONT_BENZERSIZ)
        c.drawString(text_left_pt, top - 3 * LINE_HEIGHT_PT - 8, (benzersiz_kod or "")[:40])

        c.showPage()

    c.save()
    buf.seek(0)
    return buf.getvalue()

