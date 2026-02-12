"""Admin rapor view'ları."""
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import render

from .istasyon_raporu import IstasyonRaporuForm, build_istasyon_raporu_excel, get_istasyon_raporu_data
from .models import WorkRecordIlac


@staff_member_required
def ilac_kullanımlari_raporu(request):
    """İlaç kullanımları raporu: iş kaydı ve talep bilgileri ile liste."""
    qs = (
        WorkRecordIlac.objects.select_related(
            "work_record",
            "work_record__customer",
            "work_record__facility",
            "work_record__personel",
            "work_record__ekip",
            "work_record__kapatilan_talep",
            "work_record__kapatilan_talep__customer",
            "work_record__kapatilan_talep__facility",
            "work_record__kapatilan_talep__tip",
            "ilac_tanim",
        )
        .order_by("-work_record__tarih", "ilac_tanim__ticari_ismi")
    )
    rows = []
    for wri in qs:
        wr = wri.work_record
        talep = getattr(wr, "kapatilan_talep", None)
        customer = wr.customer or (talep.customer if talep else None)
        facility = wr.facility or (talep.facility if talep else None)
        rows.append({
            "ilac_ticari_ismi": wri.ilac_tanim.ticari_ismi,
            "ilac_firma": wri.ilac_tanim.temin_edildigi_firma,
            "ilac_aktif_madde": wri.ilac_tanim.aktif_madde,
            "miktar": wri.miktar,
            "is_kaydi_tarih": wr.tarih,
            "is_kaydi_personel": wr.personel.get_username() if wr.personel_id else "",
            "is_kaydi_ekip": str(wr.ekip) if wr.ekip_id else "",
            "is_kaydi_form_no": wr.form_numarasi or "",
            "talep": str(talep) if talep else "—",
            "talep_musteri": customer.kod if customer else "—",
            "talep_tesis": str(facility) if facility else "—",
            "talep_tip": str(talep.tip) if talep and talep.tip_id else "—",
        })
    context = {
        **admin.site.each_context(request),
        "title": "İlaç Kullanımları",
        "rows": rows,
    }
    return render(request, "admin/core/rapor_ilac_kullanımlari.html", context)


@staff_member_required
def istasyon_raporu(request):
    """İstasyon raporu: tesis + tarih aralığı seç; Excel indir veya ekranda tablo göster."""
    form = IstasyonRaporuForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        facility_id = form.cleaned_data["tesis"].pk
        start = form.cleaned_data["baslangic_tarihi"]
        end = form.cleaned_data["bitis_tarihi"]
        if request.POST.get("ekran"):
            data = get_istasyon_raporu_data(facility_id, start, end)
            ratio_genel = data.get("ratio_genel", [])
            ratio_by_zone = data.get("ratio_by_zone", {})
            # Oranları % formatında (örn. "50.0%")
            ratio_genel_fmt = [f"{r * 100:.1f}%" if r is not None else "—" for r in ratio_genel]
            ratio_by_zone_fmt = {
                z: [f"{r * 100:.1f}%" if r is not None else "—" for r in ratios]
                for z, ratios in ratio_by_zone.items()
            }
            context = {
                **admin.site.each_context(request),
                "title": "İstasyon Raporu",
                "form": form,
                "rapor_musteri_tesis": data["musteri_tesis"],
                "rapor_adres": data["adres"],
                "rapor_date_headers": data["date_headers"],
                "rapor_rows": data["rows"],
                "rapor_ratio_genel": ratio_genel_fmt,
                "rapor_ratio_by_zone": sorted(ratio_by_zone_fmt.items()),
                "rapor_zone_stats": data.get("zone_stats", []),
            }
            return render(request, "admin/core/rapor_istasyon.html", context)
        excel_bytes = build_istasyon_raporu_excel(facility_id, start, end)
        facility = form.cleaned_data["tesis"]
        filename = f"istasyon_raporu_{facility.customer.kod}_{facility.kod}_{start:%Y%m%d}_{end:%Y%m%d}.xlsx"
        response = HttpResponse(excel_bytes, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    context = {
        **admin.site.each_context(request),
        "title": "İstasyon Raporu",
        "form": form,
    }
    return render(request, "admin/core/rapor_istasyon.html", context)
