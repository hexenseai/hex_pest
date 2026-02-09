"""
İstasyon raporu: Tesis + tarih aralığı seçilir, Excel indirilir.
Bölüm (zone) bazında istasyonlar; her iş kaydı tarihi bir sütun, hücrede sayım değeri.
"""
from datetime import date
from io import BytesIO

from django import forms
from django.http import HttpResponse

from .models import Facility, WorkRecord, WorkRecordStationCount, Station


class IstasyonRaporuForm(forms.Form):
    """Tesis ve tarih aralığı seçimi."""
    tesis = forms.ModelChoiceField(
        label="Tesis",
        queryset=Facility.objects.none(),
        required=True,
    )
    baslangic_tarihi = forms.DateField(
        label="Başlangıç tarihi",
        required=True,
        widget=forms.DateInput(attrs={"type": "date", "class": "w-full rounded border border-base-300 dark:border-base-600 bg-white dark:bg-base-800 px-3 py-2"}),
    )
    bitis_tarihi = forms.DateField(
        label="Bitiş tarihi",
        required=True,
        widget=forms.DateInput(attrs={"type": "date", "class": "w-full rounded border border-base-300 dark:border-base-600 bg-white dark:bg-base-800 px-3 py-2"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tesis"].queryset = Facility.objects.select_related("customer").order_by("customer__kod", "kod")
        self.fields["tesis"].widget.attrs["class"] = "w-full rounded border border-base-300 dark:border-base-600 bg-white dark:bg-base-800 px-3 py-2"

    def clean(self):
        data = super().clean()
        if data.get("baslangic_tarihi") and data.get("bitis_tarihi"):
            if data["baslangic_tarihi"] > data["bitis_tarihi"]:
                raise forms.ValidationError("Bitiş tarihi başlangıçtan önce olamaz.")
        return data


def get_istasyon_raporu_data(facility_id, start_date, end_date):
    """
    Tesis ve tarih aralığına göre rapor verisini döndürür.
    Dönüş: musteri_tesis, adres, date_headers (tarih listesi), rows (her satır: zone, kod, ad, counts listesi).
    """
    facility = Facility.objects.select_related("customer").get(pk=facility_id)
    customer = facility.customer
    musteri_tesis = f"{customer.firma_ismi} - {facility.ad}"
    adres = (facility.adres or "").strip() or (customer.adres or "").strip() or "—"

    work_records = list(
        WorkRecord.objects.filter(
            kapatilan_talep__facility_id=facility_id,
            tarih__gte=start_date,
            tarih__lte=end_date,
        )
        .order_by("tarih")
        .values_list("id", "tarih")
    )
    wr_ids = [wr[0] for wr in work_records]
    stations = list(
        Station.objects.filter(zone__facility_id=facility_id)
        .select_related("zone")
        .order_by("zone__kod", "kod")
    )
    counts_qs = WorkRecordStationCount.objects.filter(
        work_record_id__in=wr_ids,
        station_id__in=[s.id for s in stations],
    ).values_list("work_record_id", "station_id", "sayim_degeri")
    count_map = {(wr_id, st_id): val for wr_id, st_id, val in counts_qs}

    date_headers = [wr[1].strftime("%d.%m.%Y") for wr in work_records]
    rows = []
    for station in stations:
        zone_name = str(station.zone) if station.zone else "—"
        counts = [count_map.get((wr[0], station.id)) for wr in work_records]
        rows.append({
            "zone": zone_name,
            "kod": station.kod,
            "ad": station.ad or "",
            "counts": counts,
        })
    return {
        "musteri_tesis": musteri_tesis,
        "adres": adres,
        "date_headers": date_headers,
        "rows": rows,
    }


def build_istasyon_raporu_excel(facility_id, start_date, end_date):
    """
    Tesis ve tarih aralığına göre Excel dosyası üretir.
    İlk iki satır: müşteri adı - tesis, alt satırda adres.
    Sonra satırlar: bölüm bazında istasyonlar (Bölge, İstasyon Kodu, Açıklama).
    Sütunlar: her iş kaydı tarihi için sayım değeri.
    """
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side

    data = get_istasyon_raporu_data(facility_id, start_date, end_date)
    musteri_tesis = data["musteri_tesis"]
    adres = data["adres"]
    date_headers = data["date_headers"]
    rows = data["rows"]
    ncols = 3 + len(date_headers)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "İstasyon Raporu"

    thin = Side(style="thin")
    header_font = Font(bold=True)

    # İlk iki satır: müşteri - tesis, adres
    ws.cell(row=1, column=1, value=musteri_tesis)
    ws.cell(row=1, column=1).font = Font(bold=True)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(3, ncols))
    ws.row_dimensions[1].height = 20
    ws.cell(row=2, column=1, value=adres)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max(3, ncols))
    ws.row_dimensions[2].height = 18

    # Başlık satırı (3): Bölge | İstasyon Kodu | Açıklama | Tarih1 | Tarih2 | ...
    header_row = 3
    headers = ["Bölge", "İstasyon Kodu", "Açıklama"] + date_headers
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col, value=h)
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
    ws.row_dimensions[header_row].height = 22

    for row_idx, row in enumerate(rows, header_row + 1):
        ws.cell(row=row_idx, column=1, value=row["zone"])
        ws.cell(row=row_idx, column=2, value=row["kod"])
        ws.cell(row=row_idx, column=3, value=row["ad"])
        for col_idx, val in enumerate(row["counts"], 4):
            cell = ws.cell(row=row_idx, column=col_idx, value=val if val is not None else "")
            cell.alignment = Alignment(horizontal="center" if val is not None else "left", vertical="center")
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        ws.row_dimensions[row_idx].height = 18

    # Sütun genişlikleri
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 22
    for col_idx in range(4, 4 + len(date_headers)):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 12

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
