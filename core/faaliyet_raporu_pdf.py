"""
İş kaydı faaliyet raporu PDF üretimi. Türkçe font için core.label_pdf fontları kullanılır.
Tasarım: Logo sol üst, Faaliyet Raporu sağ üst; ilk satır iki sütun (müşteri/tesis | iş bilgileri);
bölümler tablo formatında; istasyon sayımı 3 sütun (bölge başlık, altında istasyon no + sayı).
"""
import io
import os
from collections import OrderedDict

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
SECTION_GAP = 3 * mm
FONT_SIZE = 8
FONT_SIZE_SMALL = 7
FONT_SIZE_TITLE = 12
FONT_SIZE_HEADER = 10
LOGO_SIZE = 12 * mm
TABLE_HEADER_HEIGHT = 4.5 * mm
TABLE_ROW_HEIGHT = 4 * mm
# İstasyon: 3 sütun, A4'te yan yana
COL_WIDTH = (PAGE_WIDTH - 2 * MARGIN) / 3
ISTASYON_HEADER_H = 4 * mm
ISTASYON_ROW_H = 3.5 * mm
ISTASYON_FONT = 6


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


def _draw_header(c, y):
    """Sol: logo + KALE İLAÇLAMA. Sağ üst: Faaliyet Raporu."""
    logo_path = _get_logo_path()
    if logo_path:
        try:
            c.drawImage(ImageReader(logo_path), MARGIN, y - LOGO_SIZE, width=LOGO_SIZE, height=LOGO_SIZE)
        except Exception:
            pass
    c.setFont(_FONT_BOLD, FONT_SIZE_HEADER)
    c.drawString(MARGIN + LOGO_SIZE + 2 * mm, y - LOGO_SIZE / 2 - 2 * mm, "KALE İLAÇLAMA")
    # Sağ üst: Faaliyet Raporu
    c.setFont(_FONT_BOLD, FONT_SIZE_TITLE)
    title = "Faaliyet Raporu"
    tw = c.stringWidth(title, _FONT_BOLD, FONT_SIZE_TITLE)
    c.drawString(PAGE_WIDTH - MARGIN - tw, y - LOGO_SIZE / 2 - 2 * mm, title)
    y -= LOGO_SIZE + 3 * mm
    return y


def _draw_first_row(c, y, left_lines, right_lines):
    """İlk satır: sol sütun (müşteri, adres, tesis), sağ sütun (tarih, form no, başlama/bitiş...)."""
    col_width = (PAGE_WIDTH - 2 * MARGIN - 8 * mm) / 2
    x_left = MARGIN
    x_right = MARGIN + col_width + 8 * mm
    c.setFont(_FONT_BOLD, FONT_SIZE)
    c.drawString(x_left, y, "Müşteri / Tesis")
    c.drawString(x_right, y, "İş kaydı bilgileri")
    y -= LINE_HEIGHT * 0.8
    c.setFont(_FONT, FONT_SIZE)
    max_rows = max(len(left_lines), len(right_lines))
    for i in range(max_rows):
        if y < MARGIN + LINE_HEIGHT:
            c.showPage()
            y = PAGE_HEIGHT - MARGIN
            c.setFont(_FONT, FONT_SIZE)
        left = (left_lines[i] if i < len(left_lines) else "")[:55]
        right = (right_lines[i] if i < len(right_lines) else "")[:55]
        c.drawString(x_left, y, left)
        c.drawString(x_right, y, right)
        y -= LINE_HEIGHT * 0.9
    return y - SECTION_GAP


def _section_table(c, y, title, headers, rows, min_y=MARGIN):
    """Başlık + tablo (header row + data rows)."""
    if y < min_y + TABLE_HEADER_HEIGHT + 2 * TABLE_ROW_HEIGHT:
        c.showPage()
        y = PAGE_HEIGHT - MARGIN
    ncols = max(len(headers), 1)
    col_w = (PAGE_WIDTH - 2 * MARGIN - 4 * mm) / ncols
    c.setFont(_FONT_BOLD, FONT_SIZE)
    c.drawString(MARGIN, y, title)
    y -= LINE_HEIGHT * 0.7
    x_start = MARGIN
    c.setFont(_FONT_BOLD, FONT_SIZE_SMALL)
    for i in range(ncols):
        h = (headers[i] if i < len(headers) else "") or ""
        c.drawString(x_start + i * col_w, y, h[:25])
    y -= TABLE_ROW_HEIGHT * 0.9
    c.setFont(_FONT, FONT_SIZE_SMALL)
    for row in rows:
        if y < min_y:
            c.showPage()
            y = PAGE_HEIGHT - MARGIN
            c.setFont(_FONT, FONT_SIZE_SMALL)
        row_padded = list(row) + [""] * (ncols - len(row))
        for i in range(ncols):
            cell = row_padded[i] if i < len(row_padded) else ""
            c.drawString(x_start + i * col_w, y, (str(cell) if cell is not None else "—")[:28])
        y -= TABLE_ROW_HEIGHT * 0.85
    return y - SECTION_GAP


def _format_time(t):
    if t is None:
        return "—"
    return str(t)[:5] if hasattr(t, "strftime") else str(t)


def _format_date(d):
    if d is None:
        return "—"
    return d.strftime("%d.%m.%Y") if hasattr(d, "strftime") else str(d)


def _draw_istasyon_3_columns(c, y, sayimlar_by_zone, min_y=MARGIN):
    """İstasyon tüketim: 3 sütun yan yana. Her sütunda bölge başlığı, altında İstasyon No | Tüketim (Var/Yok) listesi."""
    if not sayimlar_by_zone:
        c.setFont(_FONT_BOLD, FONT_SIZE)
        c.drawString(MARGIN, y, "Bölge ve istasyon tüketim sonuçları")
        y -= LINE_HEIGHT
        c.setFont(_FONT, FONT_SIZE_SMALL)
        c.drawString(MARGIN, y, "—")
        return y - SECTION_GAP
    c.setFont(_FONT_BOLD, FONT_SIZE)
    c.drawString(MARGIN, y, "Bölge ve istasyon tüketim sonuçları")
    y -= ISTASYON_HEADER_H
    col_w = COL_WIDTH
    pad = 2 * mm
    zones = list(sayimlar_by_zone.keys())
    # 3'lü gruplar halinde (her satırda en fazla 3 bölge)
    for group_start in range(0, len(zones), 3):
        zone_group = zones[group_start : group_start + 3]
        max_rows = max(len(sayimlar_by_zone[z]) for z in zone_group)
        block_height = ISTASYON_HEADER_H + max_rows * ISTASYON_ROW_H
        if y - block_height < min_y:
            c.showPage()
            y = PAGE_HEIGHT - MARGIN
        for col_i, zone_name in enumerate(zone_group):
            x = MARGIN + col_i * (col_w + pad)
            c.setFont(_FONT_BOLD, ISTASYON_FONT)
            c.drawString(x, y, (zone_name or "—")[:22])
            yy = y - ISTASYON_ROW_H
            c.setFont(_FONT, ISTASYON_FONT)
            for st_kod, tuketim_str in sayimlar_by_zone[zone_name]:
                if yy < min_y:
                    break
                c.drawString(x, yy, (st_kod or "—")[:20])
                # Tüketim var/yok sütun içinde sağa yakın çiz
                c.drawRightString(x + col_w - 1 * mm, yy, tuketim_str)
                yy -= ISTASYON_ROW_H
        y -= block_height + 2 * mm
    return y - SECTION_GAP


def generate_faaliyet_raporu_pdf(work_record):
    """
    Tek bir WorkRecord için Faaliyet Raporu PDF'i üretir.
    Müşteri ve tesis bilgisi iş kaydından; yoksa kapatılan talepten alınır.
    """
    wr = work_record
    talep = getattr(wr, "kapatilan_talep", None)
    # Önce iş kaydındaki müşteri/tesis, yoksa talepten
    customer = getattr(wr, "customer", None)
    facility = getattr(wr, "facility", None)
    if not customer and talep:
        customer = getattr(talep, "customer", None)
    if not facility and talep:
        facility = getattr(talep, "facility", None)
    ekip = getattr(wr, "ekip", None)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = PAGE_HEIGHT - MARGIN

    # Üst: logo + KALE İLAÇLAMA (sol), Faaliyet Raporu (sağ üst)
    y = _draw_header(c, y)

    # İlk satır: sol = müşteri/tesis, sağ = iş kaydı bilgileri
    left_lines = []
    if customer:
        left_lines.append(f"{customer.kod} - {customer.firma_ismi}")
        if customer.adres:
            addr = (customer.adres[:100] or "").replace("\n", " ").strip()
            if addr:
                left_lines.append(addr)
    if facility:
        left_lines.append(f"Tesis: {facility.kod} - {facility.ad}")
        if facility.adres:
            left_lines.append(facility.adres[:60].replace("\n", " "))
    if not left_lines:
        left_lines.append("—")

    right_lines = [
        f"Tarih: {_format_date(wr.tarih)}",
        f"Form no: {wr.form_numarasi or '—'}",
        f"Başlama: {_format_time(wr.baslama_saati)}  Bitiş: {_format_time(wr.bitis_saati)}",
        f"Ekip: {ekip.kod if ekip else '—'}",
    ]
    y = _draw_first_row(c, y, left_lines, right_lines)

    # Ekip detay (tablo)
    ekip_rows = []
    if ekip:
        lider = getattr(ekip, "ekip_lideri", None)
        lider_adi = (lider.get_full_name() or getattr(lider, "username", str(lider))) if lider else "—"
        ekip_rows = [[f"Çalışan sayısı: {ekip.kisi_sayisi}", f"Sorumlu: {lider_adi}"]]
    else:
        ekip_rows = [["—", "—"]]
    y = _section_table(c, y, "Ekip", ["", ""], ekip_rows if ekip_rows else [["—", "—"]])

    # Ziyaret şekli
    tip_ad = str(talep.tip) if (talep and getattr(talep, "tip", None)) else "—"
    y = _section_table(c, y, "Ziyaret şekli (Talep tipi)", ["Tip"], [[tip_ad]])

    # Tespitler (tablo)
    tespitler = list(wr.tespitler.select_related("tespit_tanim").all()) if hasattr(wr, "tespitler") else []
    tespit_rows = []
    for t in tespitler:
        tt = getattr(t, "tespit_tanim", None)
        yog = getattr(t, "get_yogunluk_display", lambda: "")() or getattr(t, "yogunluk", "")
        tespit_eden = getattr(t, "get_tespit_eden_display", lambda: "")() or getattr(t, "tespit_eden", "")
        tespit_rows.append([str(tt) if tt else "—", yog, tespit_eden])
    if not tespit_rows:
        tespit_rows = [["—", "—", "—"]]
    y = _section_table(c, y, "Tespitler", ["Tespit", "Yoğunluk", "Tespit eden"], tespit_rows)

    # Yapılan çalışmalar
    uygulamalar = list(wr.yapilan_uygulamalar.select_related("uygulama_tanim").all()) if hasattr(wr, "yapilan_uygulamalar") else []
    uyg_rows = [[str(getattr(u, "uygulama_tanim", u))] for u in uygulamalar]
    if not uyg_rows:
        uyg_rows = [["—"]]
    y = _section_table(c, y, "Yapılan çalışmalar (Faaliyetler)", ["Uygulama"], uyg_rows)

    # Makine ve ekipmanlar
    makine = []
    if getattr(wr, "skb", False):
        makine.append("SKB")
    if getattr(wr, "atomizor", False):
        makine.append("Atomizör")
    if getattr(wr, "pulverizator", False):
        makine.append("Pülverizatör")
    if getattr(wr, "termal_sis", False):
        makine.append("Termal Sis")
    if getattr(wr, "ar_uz_ulv", False):
        makine.append("Ar.Üz. ULV")
    if getattr(wr, "elk_ulv", False):
        makine.append("Elk. ULV")
    if getattr(wr, "civi_tabancasi", False):
        makine.append("Çivi Tabancası")
    makine_rows = [[", ".join(makine)] if makine else ["—"]]
    y = _section_table(c, y, "Makine ve ekipmanlar", ["Ekipman"], makine_rows)

    # Kutucuklar
    k1 = "Evet" if getattr(wr, "sozlesme_disi_islem_var", False) else "Hayır"
    k2 = "Evet" if getattr(wr, "gozlem_ziyareti_yapilmali", False) else "Hayır"
    y = _section_table(
        c, y, "Kutucuklar",
        ["Sözleşme dışı işlem", "Gözlem ziyareti yapılmalı"],
        [[k1, k2]],
    )

    # Düzeltici önleyici faaliyetler
    faaliyetler = list(wr.faaliyetler.select_related("faaliyet_tanim").all()) if hasattr(wr, "faaliyetler") else []
    df_rows = []
    for f in faaliyetler:
        ft = getattr(f, "faaliyet_tanim", None)
        flags = []
        if getattr(f, "kontrol", False):
            flags.append("Kontrol")
        if getattr(f, "kuruldu", False):
            flags.append("Kuruldu")
        if getattr(f, "eklendi", False):
            flags.append("Eklendi")
        if getattr(f, "sabitlendi", False):
            flags.append("Sabitlendi")
        if getattr(f, "yeri_degistirildi", False):
            flags.append("Yeri Değiştirildi")
        if getattr(f, "yenilendi", False):
            flags.append("Yenilendi")
        df_rows.append([str(ft) if ft else "—", ", ".join(flags) if flags else "—"])
    if not df_rows:
        df_rows = [["—", "—"]]
    y = _section_table(c, y, "Düzeltici önleyici faaliyetler", ["Faaliyet", "Durum"], df_rows)

    # Kullanılan ilaç ve fare yemi
    ilaclar = list(wr.kullanilan_ilaclar.select_related("ilac_tanim").all()) if hasattr(wr, "kullanilan_ilaclar") else []
    ilac_rows = [[str(getattr(i, "ilac_tanim", i)), str(getattr(i, "miktar", ""))] for i in ilaclar]
    if not ilac_rows:
        ilac_rows = [["—", "—"]]
    y = _section_table(c, y, "Kullanılan ilaç ve fare yemi", ["İlaç / Ürün", "Miktar"], ilac_rows)

    # İstasyon sayımı: bölgelere göre grupla, 3 sütun
    sayimlar = (
        wr.station_counts.select_related("station", "station__zone")
        .order_by("station__zone__kod", "station__kod")
    ) if hasattr(wr, "station_counts") else []
    sayimlar_by_zone = OrderedDict()
    for sc in sayimlar:
        st = getattr(sc, "station", None)
        zone = getattr(st, "zone", None) if st else None
        zone_name = str(zone) if zone else "—"
        st_kod = (getattr(st, "kod", None) or getattr(st, "benzersiz_kod", "")) if st else "—"
        if zone_name not in sayimlar_by_zone:
            sayimlar_by_zone[zone_name] = []
        tuketim = getattr(sc, "tuketim_var", False)
        sayimlar_by_zone[zone_name].append((st_kod, "Var" if tuketim else "Yok"))
    y = _draw_istasyon_3_columns(c, y, sayimlar_by_zone)

    c.save()
    buf.seek(0)
    return buf.getvalue()
