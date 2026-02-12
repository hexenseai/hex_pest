"""
Bağımsız tespitler raporu PDF üretimi. Seçili kayıtların her biri ayrı blokta;
tarih, firma, tesis, yer açıklaması, gözlem açıklaması, öneriler, raporlandı bilgileri
ve her kaydın altında yan yana 3 görsel (varsa).
"""
import io
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from . import label_pdf as _label_pdf

_FONT = _label_pdf._FONT_NAME
_FONT_BOLD = _label_pdf._FONT_BOLD_NAME

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 14 * mm
LINE_HEIGHT = 4 * mm
SECTION_GAP = 4 * mm
RECORD_GAP = 8 * mm
FONT_SIZE = 8
FONT_SIZE_SMALL = 7
FONT_SIZE_TITLE = 12
FONT_SIZE_HEADER = 10
LOGO_SIZE = 12 * mm
# Görsel: 3 tane yan yana, her biri eşit genişlik
IMG_COL_PAD = 2 * mm
IMG_COL_WIDTH = (PAGE_WIDTH - 2 * MARGIN - 2 * IMG_COL_PAD) / 3
IMG_MAX_HEIGHT = 45 * mm


def _get_logo_path():
    try:
        from django.conf import settings

        base = getattr(settings, "BASE_DIR", None)
        if base is None:
            return None
        if hasattr(base, "__truediv__"):
            path = base / "statics" / "logo.png"
            if path.exists():
                return str(path)
        else:
            p = os.path.join(str(base), "statics", "logo.png")
            if os.path.exists(p):
                return p
    except Exception:
        pass
    return None


def _get_image_path(image_field):
    """ImageField'dan dosya yolu alır. Yoksa None."""
    if not image_field:
        return None
    try:
        path = getattr(image_field, "path", None)
        if path and os.path.isfile(path):
            return path
        # Django: file açıksa path var olabilir
        from django.conf import settings

        if hasattr(image_field, "name") and image_field.name:
            full = os.path.join(str(settings.MEDIA_ROOT), image_field.name)
            if os.path.isfile(full):
                return full
    except Exception:
        pass
    return None


def _draw_header(c, y):
    """Sol: logo + KALE İLAÇLAMA. Sağ üst: Bağımsız Tespitler Raporu."""
    logo_path = _get_logo_path()
    if logo_path:
        try:
            c.drawImage(
                ImageReader(logo_path),
                MARGIN,
                y - LOGO_SIZE,
                width=LOGO_SIZE,
                height=LOGO_SIZE,
            )
        except Exception:
            pass
    c.setFont(_FONT_BOLD, FONT_SIZE_HEADER)
    c.drawString(MARGIN + LOGO_SIZE + 2 * mm, y - LOGO_SIZE / 2 - 2 * mm, "KALE İLAÇLAMA")
    c.setFont(_FONT_BOLD, FONT_SIZE_TITLE)
    title = "Bağımsız Tespitler Raporu"
    tw = c.stringWidth(title, _FONT_BOLD, FONT_SIZE_TITLE)
    c.drawString(PAGE_WIDTH - MARGIN - tw, y - LOGO_SIZE / 2 - 2 * mm, title)
    y -= LOGO_SIZE + 3 * mm
    return y


def _format_date(d):
    if d is None:
        return "—"
    return d.strftime("%d.%m.%Y") if hasattr(d, "strftime") else str(d)


def _wrap_text(c, text, max_width, font, size):
    """Metni max_width'e göre satırlara böler."""
    if not text or not text.strip():
        return [""]
    lines = []
    for para in str(text).replace("\r", "").split("\n"):
        para = para.strip()
        if not para:
            lines.append("")
            continue
        words = para.split()
        current = ""
        for w in words:
            test = current + " " + w if current else w
            if c.stringWidth(test, font, size) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
    return lines if lines else [""]


def _draw_record(c, y, record, record_num, min_y=MARGIN):
    """
    Tek bir Bağımsız Tespit kaydını çizer: bilgiler + 3 görsel yan yana.
    Gerekirse yeni sayfa açar.
    """
    x = MARGIN
    max_text_width = PAGE_WIDTH - 2 * MARGIN

    # Kayıt başlığı
    c.setFont(_FONT_BOLD, FONT_SIZE)
    baslik = f"Tespit #{record_num}"
    c.drawString(x, y, baslik)
    y -= LINE_HEIGHT

    # Tarih, Firma, Tesis
    c.setFont(_FONT, FONT_SIZE_SMALL)
    firma_str = str(record.firma) if record.firma_id else "—"
    tesis_str = str(record.tesis) if record.tesis_id else "—"
    raporlandi_str = "Evet" if record.raporlandi else "Hayır"

    infos = [
        f"Tarih: {_format_date(record.tarih)}",
        f"Firma: {firma_str}",
        f"Tesis: {tesis_str}",
        f"Raporlandı: {raporlandi_str}",
    ]
    for line in infos:
        if y < min_y + LINE_HEIGHT:
            c.showPage()
            y = PAGE_HEIGHT - MARGIN
            c.setFont(_FONT, FONT_SIZE_SMALL)
        c.drawString(x, y, (line or "—")[:95])
        y -= LINE_HEIGHT * 0.85

    # Yer açıklaması
    if record.yer_aciklamasi and record.yer_aciklamasi.strip():
        c.setFont(_FONT_BOLD, FONT_SIZE_SMALL)
        c.drawString(x, y, "Yer açıklaması:")
        y -= LINE_HEIGHT * 0.7
        c.setFont(_FONT, FONT_SIZE_SMALL)
        for line in _wrap_text(c, record.yer_aciklamasi, max_text_width, _FONT, FONT_SIZE_SMALL):
            if y < min_y + LINE_HEIGHT:
                c.showPage()
                y = PAGE_HEIGHT - MARGIN
                c.setFont(_FONT, FONT_SIZE_SMALL)
            c.drawString(x, y, (line or "")[:120])
            y -= LINE_HEIGHT * 0.8
        y -= LINE_HEIGHT * 0.3

    # Gözlem açıklaması
    if record.gozlem_aciklamasi and record.gozlem_aciklamasi.strip():
        c.setFont(_FONT_BOLD, FONT_SIZE_SMALL)
        c.drawString(x, y, "Gözlem açıklaması:")
        y -= LINE_HEIGHT * 0.7
        c.setFont(_FONT, FONT_SIZE_SMALL)
        for line in _wrap_text(c, record.gozlem_aciklamasi, max_text_width, _FONT, FONT_SIZE_SMALL):
            if y < min_y + LINE_HEIGHT:
                c.showPage()
                y = PAGE_HEIGHT - MARGIN
                c.setFont(_FONT, FONT_SIZE_SMALL)
            c.drawString(x, y, (line or "")[:120])
            y -= LINE_HEIGHT * 0.8
        y -= LINE_HEIGHT * 0.3

    # Öneriler
    if record.oneriler and record.oneriler.strip():
        c.setFont(_FONT_BOLD, FONT_SIZE_SMALL)
        c.drawString(x, y, "Öneriler:")
        y -= LINE_HEIGHT * 0.7
        c.setFont(_FONT, FONT_SIZE_SMALL)
        for line in _wrap_text(c, record.oneriler, max_text_width, _FONT, FONT_SIZE_SMALL):
            if y < min_y + LINE_HEIGHT:
                c.showPage()
                y = PAGE_HEIGHT - MARGIN
                c.setFont(_FONT, FONT_SIZE_SMALL)
            c.drawString(x, y, (line or "")[:120])
            y -= LINE_HEIGHT * 0.8
        y -= LINE_HEIGHT * 0.3

    y -= SECTION_GAP

    # Görseller: 3 tane yan yana
    gorseller = [record.gorsel1, record.gorsel2, record.gorsel3]
    paths = []
    for g in gorseller:
        p = _get_image_path(g)
        paths.append(p)

    if any(paths):
        # Görseller için alan ayır
        if y - IMG_MAX_HEIGHT - 2 * mm < min_y:
            c.showPage()
            y = PAGE_HEIGHT - MARGIN

        c.setFont(_FONT_BOLD, FONT_SIZE_SMALL)
        c.drawString(x, y, "Görseller:")
        y -= LINE_HEIGHT

        img_y_start = y - IMG_MAX_HEIGHT
        for i, img_path in enumerate(paths):
            col_x = MARGIN + i * (IMG_COL_WIDTH + IMG_COL_PAD)
            if img_path:
                try:
                    img = ImageReader(img_path)
                    iw, ih = img.getSize()
                    if iw and ih:
                        scale = min(
                            IMG_COL_WIDTH / iw,
                            IMG_MAX_HEIGHT / ih,
                            1.0,
                        )
                        dw = iw * scale
                        dh = ih * scale
                        c.drawImage(
                            img,
                            col_x,
                            img_y_start + (IMG_MAX_HEIGHT - dh) / 2,
                            width=dw,
                            height=dh,
                        )
                except Exception:
                    c.setFont(_FONT, FONT_SIZE_SMALL)
                    c.drawString(col_x, img_y_start + IMG_MAX_HEIGHT / 2 - 2 * mm, "(yüklenemedi)")
                    c.setFont(_FONT_BOLD, FONT_SIZE_SMALL)

        y = img_y_start - SECTION_GAP
    else:
        y -= 2 * mm

    return y


def generate_bagimsiz_tespit_raporu_pdf(queryset):
    """
    Seçili Bağımsız Tespit kayıtları için PDF raporu oluşturur.
    Her kayıt ayrı blokta; bilgiler + 3 görsel yan yana.
    """
    records = list(
        queryset.select_related("firma", "tesis").order_by("-tarih", "-created_at")
    )
    if not records:
        raise ValueError("Rapor oluşturmak için en az bir kayıt seçin.")

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = PAGE_HEIGHT - MARGIN

    # Üst başlık
    y = _draw_header(c, y)
    y -= RECORD_GAP

    for i, record in enumerate(records, 1):
        y = _draw_record(c, y, record, i)
        if i < len(records):
            y -= RECORD_GAP
            if y < MARGIN + 50 * mm:
                c.showPage()
                y = PAGE_HEIGHT - MARGIN

    c.save()
    buf.seek(0)
    return buf.getvalue()
