from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib import messages
from django.db.models import Q, Count
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required

from .models import (
    BagimsizTespit,
    Customer,
    Facility,
    Zone,
    Station,
    WorkRecord,
    WorkRecordStationCount,
)
from .istasyon_raporu import get_istasyon_raporu_data_by_work_records
from .forms import CustomerForm, FacilityForm, ZoneForm, StationForm
from addressbook.forms import CustomerContactFormSet, FacilityContactFormSet


def _get_profile(user):
    """Kullanıcı profilini döndürür; yoksa None."""
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "profile", None)


def client_portal_required(view_func):
    """Sadece is_client=True kullanıcıların müşteri portalına erişmesine izin verir."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL + "?next=" + request.path)
        profile = _get_profile(request.user)
        if not profile or not profile.is_client:
            if request.user.is_staff:
                return redirect("admin:index")
            messages.error(
                request,
                "Müşteri portalına erişim yetkiniz bulunmuyor. "
                "Admin panelinde kullanıcı profilinde 'Müşteri tarafı kullanıcı' işaretlenmiş olmalıdır.",
            )
            logout(request)
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapper


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Giriş sayfası. is_client kullanıcılar portal'a, staff admin'e yönlendirilir."""
    if request.user.is_authenticated:
        profile = _get_profile(request.user)
        if profile and profile.is_client:
            return redirect("home")
        if request.user.is_staff:
            return redirect("admin:index")
        messages.error(
            request,
            "Müşteri portalına erişim yetkiniz bulunmuyor. "
            "Admin panelinde kullanıcı profilinde 'Müşteri tarafı kullanıcı' işaretlenmiş olmalıdır.",
        )
        logout(request)
        return redirect("login")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        profile = _get_profile(user)
        if profile and profile.is_client:
            next_url = request.GET.get("next") or "home"
            return redirect(next_url)
        if user.is_staff:
            return redirect("admin:index")
        messages.error(
            request,
            "Müşteri portalına erişim yetkiniz bulunmuyor. "
            "Admin panelinde kullanıcı profilinde 'Müşteri tarafı kullanıcı' işaretlenmiş olmalıdır.",
        )
        logout(request)
        return redirect("login")
    return render(request, "core/login.html", {"form": form})


def service_worker(request):
    """PWA service worker dosyasını sunar (root scope için)."""
    path = settings.BASE_DIR / "statics" / "service-worker.js"
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return HttpResponse("", status=404)
    return HttpResponse(content, content_type="application/javascript")


@require_http_methods(["POST"])
def logout_view(request):
    """Çıkış yap; login sayfasına yönlendir."""
    logout(request)
    return redirect("login")


def _dashboard_facility_zone_pie_data(facility_id):
    """
    Seçili tesis için son iş kaydına göre bölge bazlı tüketim var/yok sayıları.
    Dönüş: {"labels": ["Bölge A (Var)", "Bölge A (Yok)", ...], "var": [n, ...], "yok": [m, ...]}
    as lists for Chart.js pie (one segment per zone: var count + yok count).
    """
    latest_wr = (
        WorkRecord.objects.filter(
            Q(facility_id=facility_id) | Q(kapatilan_talep__facility_id=facility_id)
        )
        .order_by("-tarih", "-created_at")
        .first()
    )
    if not latest_wr:
        return None
    counts = list(
        WorkRecordStationCount.objects.filter(
            work_record_id=latest_wr.pk
        ).filter(station__zone__facility_id=facility_id).select_related(
            "station", "station__zone"
        ).values_list("station__zone__kod", "station__zone__ad", "tuketim_var")
    )
    from collections import defaultdict
    by_zone = defaultdict(lambda: {"var": 0, "yok": 0})
    for z_kod, z_ad, tuketim_var in counts:
        key = (z_kod or "", z_ad or "")
        if tuketim_var:
            by_zone[key]["var"] += 1
        else:
            by_zone[key]["yok"] += 1
    if not by_zone:
        return None
    labels_final = []
    data_final = []
    for (z_kod, z_ad), v in sorted(by_zone.items()):
        zone_label = f"{z_kod} {z_ad}".strip() or "Bölge"
        if v["var"]:
            labels_final.append(f"{zone_label} (Var)")
            data_final.append(v["var"])
        if v["yok"]:
            labels_final.append(f"{zone_label} (Yok)")
            data_final.append(v["yok"])
    return {"labels": labels_final, "data": data_final}


def _dashboard_facility_consumption_rates(facility_ids):
    """
    Her tesis için son iş kaydındaki tüketim oranı (0-100).
    Dönüş: [{"facility_id", "facility_name", "rate": 0-100}, ...]
    """
    result = []
    for fid in facility_ids:
        latest_wr = (
            WorkRecord.objects.filter(
                Q(facility_id=fid) | Q(kapatilan_talep__facility_id=fid)
            )
            .order_by("-tarih", "-created_at")
            .first()
        )
        if not latest_wr:
            result.append({"facility_id": fid, "facility_name": "", "rate": 0})
            continue
        stations = list(Station.objects.filter(zone__facility_id=fid).values_list("pk", flat=True))
        if not stations:
            fac = Facility.objects.filter(pk=fid).select_related("customer").first()
            result.append({
                "facility_id": fid,
                "facility_name": f"{fac.customer.kod}-{fac.kod} {fac.ad}" if fac else "",
                "rate": 0,
            })
            continue
        var_count = WorkRecordStationCount.objects.filter(
            work_record_id=latest_wr.pk,
            station_id__in=stations,
            tuketim_var=True,
        ).count()
        rate = round(100 * var_count / len(stations), 1)
        fac = Facility.objects.filter(pk=fid).select_related("customer").first()
        result.append({
            "facility_id": fid,
            "facility_name": f"{fac.customer.kod}-{fac.kod} {fac.ad}" if fac else "",
            "rate": rate,
        })
    return result


@client_portal_required
def home(request):
    """Müşteri portalı ana sayfası (dashboard)."""
    profile = _get_profile(request.user)
    facilities = list(
        profile.get_visible_facilities().select_related("customer").prefetch_related(
            "bolgeler__istasyonlar"
        ).order_by("kod")
    )
    facility_ids = [f.pk for f in facilities]

    if not facility_ids:
        # Müşteri var ama tesis yoksa sadece tesis atanmamış tespitler
        if profile and profile.customer_id:
            unresolved_qs = (
                BagimsizTespit.objects.filter(firma_id=profile.customer_id, tesis__isnull=True)
                .filter(durum=BagimsizTespit.DURUM_TESPIT_EDILDI)
                .select_related("tesis")
            )
        else:
            unresolved_qs = BagimsizTespit.objects.none()
        unresolved_count = unresolved_qs.count()
        last_unresolved = list(unresolved_qs.order_by("-tarih", "-created_at")[:5])
        return render(
            request,
            "core/home.html",
            {
                "facilities": [],
                "last_3_work_records": [],
                "facility_count": 0,
                "work_record_count": 0,
                "station_count": 0,
                "facility_consumption_rates": [],
                "zone_pie_by_facility": {},
                "unresolved_bagimsiz_tespit_count": unresolved_count,
                "last_unresolved_bagimsiz_tespitler": last_unresolved,
            },
        )

    # Son 3 faaliyet (iş) kaydı
    work_record_qs = (
        WorkRecord.objects.filter(
            Q(facility_id__in=facility_ids) | Q(kapatilan_talep__facility_id__in=facility_ids)
        )
        .distinct()
        .select_related("customer", "facility", "personel", "ekip", "kapatilan_talep", "kapatilan_talep__customer", "kapatilan_talep__facility")
        .order_by("-tarih", "-created_at")[:3]
    )
    last_3 = []
    for wr in work_record_qs:
        cust = wr.customer or (wr.kapatilan_talep.customer if wr.kapatilan_talep_id else None)
        fac = wr.facility or (wr.kapatilan_talep.facility if wr.kapatilan_talep_id else None)
        last_3.append({
            "id": wr.pk,
            "tarih": wr.tarih.strftime("%d.%m.%Y"),
            "form_no": wr.form_numarasi or "—",
            "musteri": cust.firma_ismi if cust else "—",
            "tesis": fac.ad if fac else "—",
            "durum": wr.get_durum_display(),
        })

    work_record_count = WorkRecord.objects.filter(
        Q(facility_id__in=facility_ids) | Q(kapatilan_talep__facility_id__in=facility_ids)
    ).distinct().count()
    station_count = Station.objects.filter(zone__facility_id__in=facility_ids).count()

    facility_consumption_rates = _dashboard_facility_consumption_rates(facility_ids)

    # Tesis seçildiğinde pie chart için bölge var/yok verisi (her tesis için)
    zone_pie_by_facility = {}
    for f in facilities:
        pie = _dashboard_facility_zone_pie_data(f.pk)
        if pie:
            zone_pie_by_facility[str(f.pk)] = pie
        else:
            zone_pie_by_facility[str(f.pk)] = {"labels": [], "data": []}

    # Çözülmemiş bağımsız tespitler (durum = Tespit edildi)
    unresolved_qs = (
        BagimsizTespit.objects.filter(firma_id=profile.customer_id)
        .filter(Q(tesis_id__in=facility_ids) | Q(tesis__isnull=True))
        .filter(durum=BagimsizTespit.DURUM_TESPIT_EDILDI)
        .select_related("tesis")
    )
    unresolved_bagimsiz_tespit_count = unresolved_qs.count()
    last_unresolved_bagimsiz_tespitler = list(unresolved_qs.order_by("-tarih", "-created_at")[:5])

    return render(
        request,
        "core/home.html",
        {
            "facilities": facilities,
            "last_3_work_records": last_3,
            "facility_count": len(facilities),
            "work_record_count": work_record_count,
            "station_count": station_count,
            "facility_consumption_rates": facility_consumption_rates,
            "zone_pie_by_facility": zone_pie_by_facility,
            "unresolved_bagimsiz_tespit_count": unresolved_bagimsiz_tespit_count,
            "last_unresolved_bagimsiz_tespitler": last_unresolved_bagimsiz_tespitler,
        },
    )


@client_portal_required
def client_facility_list(request):
    """Müşteri portalı: Tesisler listesi. Tesis seçiliyse tek tesis, değilse tüm tesisler."""
    profile = _get_profile(request.user)
    facilities = profile.get_visible_facilities().select_related("customer").prefetch_related(
        "bolgeler__istasyonlar"
    ).order_by("kod")
    return render(request, "core/client/facility_list.html", {"facilities": facilities})


@client_portal_required
def client_work_record_list(request):
    """Müşteri portalı: Faaliyet (iş) kayıtları. Tesis seçiliyse tek tesis, değilse tüm tesisler."""
    profile = _get_profile(request.user)
    facilities = list(profile.get_visible_facilities().select_related("customer").order_by("kod"))
    facility_ids = [f.pk for f in facilities]
    facility_filter = request.GET.get("facility", "").strip()

    if not facility_ids:
        work_records = []
        table_data = []
        detail_data = {}
        facilities = []
    else:
        qs = (
            WorkRecord.objects.filter(
                Q(facility_id__in=facility_ids) | Q(kapatilan_talep__facility_id__in=facility_ids)
            ).distinct()
            .select_related(
                "customer", "facility", "personel", "ekip", "kapatilan_talep", "kapatilan_talep__customer", "kapatilan_talep__facility"
            )
            .prefetch_related(
                "yapilan_uygulamalar__uygulama_tanim",
                "faaliyetler__faaliyet_tanim",
                "kullanilan_ilaclar__ilac_tanim",
                "tespitler__tespit_tanim",
            )
            .order_by("-tarih", "-created_at")
        )
        if facility_filter:
            try:
                fid = int(facility_filter)
                if fid in facility_ids:
                    qs = qs.filter(Q(facility_id=fid) | Q(kapatilan_talep__facility_id=fid))
            except ValueError:
                pass

        search = request.GET.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(form_numarasi__icontains=search)
                | Q(customer__firma_ismi__icontains=search)
                | Q(customer__kod__icontains=search)
                | Q(facility__ad__icontains=search)
                | Q(facility__kod__icontains=search)
                | Q(personel__username__icontains=search)
                | Q(ekip__kod__icontains=search)
                | Q(oneriler__icontains=search)
                | Q(not_alani__icontains=search)
            )

        items = []
        detail_data = {}
        for wr in qs:
            cust = wr.customer or (wr.kapatilan_talep.customer if wr.kapatilan_talep_id else None)
            fac = wr.facility or (wr.kapatilan_talep.facility if wr.kapatilan_talep_id else None)
            items.append({
                "wr": wr,
                "cust": cust,
                "fac": fac,
            })
            detail_data[str(wr.pk)] = _build_work_record_detail(wr, cust, fac)
        table_data = []
        for i in items:
            wr, cust, fac = i["wr"], i["cust"], i["fac"]
            table_data.append({
                "id": wr.pk,
                "tarih": wr.tarih.strftime("%d.%m.%Y"),
                "form_no": wr.form_numarasi or "—",
                "musteri": cust.firma_ismi if cust else "—",
                "tesis": fac.ad if fac else "—",
                "tesis_id": fac.pk if fac else None,
                "personel": wr.personel.get_full_name() or wr.personel.get_username(),
                "ekip": wr.ekip.kod if wr.ekip_id else "—",
                "durum": wr.get_durum_display(),
                "durum_key": wr.durum,
            })
        work_records = items

    return render(
        request,
        "core/client/work_record_list.html",
        {
            "work_records": work_records,
            "table_data": table_data,
            "detail_data": detail_data,
            "facilities": facilities,
            "facility_filter": facility_filter,
            "q": request.GET.get("q", "").strip(),
        },
    )


@client_portal_required
def client_bagimsiz_tespit_list(request):
    """Müşteri portalı: Bağımsız tespitler listesi. Müşteriye ait ve görünür tesislere ait kayıtlar."""
    profile = _get_profile(request.user)
    if not profile or not profile.customer_id:
        tespitler = []
        facilities = []
    else:
        facilities = list(profile.get_visible_facilities().select_related("customer").order_by("kod"))
        facility_ids = [f.pk for f in facilities]
        qs = BagimsizTespit.objects.filter(firma_id=profile.customer_id).filter(
            Q(tesis_id__in=facility_ids) | Q(tesis__isnull=True)
        ).select_related("firma", "tesis").order_by("-tarih", "-created_at")
        tespitler = list(qs)
    return render(
        request,
        "core/client/bagimsiz_tespit_list.html",
        {"tespitler": tespitler, "facilities": facilities},
    )


def _build_work_record_detail(wr, cust, fac):
    """İş kaydı detayını JSON-serializable dict olarak döndürür."""
    equip = []
    if wr.skb:
        equip.append("SKB")
    if wr.atomizor:
        equip.append("Atomizör")
    if wr.pulverizator:
        equip.append("Pülverizatör")
    if wr.termal_sis:
        equip.append("Termal Sis")
    if wr.ar_uz_ulv:
        equip.append("Ar.Üz. ULV")
    if wr.elk_ulv:
        equip.append("Elk. ULV")
    if wr.civi_tabancasi:
        equip.append("Çivi Tabancası")

    return {
        "tarih": wr.tarih.strftime("%d.%m.%Y"),
        "form_numarasi": wr.form_numarasi or "—",
        "musteri": cust.firma_ismi if cust else "—",
        "tesis": fac.ad if fac else "—",
        "personel": wr.personel.get_full_name() or wr.personel.get_username(),
        "ekip": wr.ekip.kod if wr.ekip_id else "—",
        "durum": wr.get_durum_display(),
        "baslama_saati": wr.baslama_saati.strftime("%H:%M") if wr.baslama_saati else "—",
        "bitis_saati": wr.bitis_saati.strftime("%H:%M") if wr.bitis_saati else "—",
        "gozlem_ziyareti_yapilmali": wr.gozlem_ziyareti_yapilmali,
        "sozlesme_disi_islem_var": wr.sozlesme_disi_islem_var,
        "ekipman": ", ".join(equip) if equip else "—",
        "uygulamalar": [u.uygulama_tanim.ad for u in wr.yapilan_uygulamalar.all()],
        "faaliyetler": [
            f"{f.faaliyet_tanim.ad}: " + ", ".join([k for k, v in [("Kontrol", f.kontrol), ("Kuruldu", f.kuruldu), ("Eklendi", f.eklendi), ("Sabitlendi", f.sabitlendi), ("Yeri değiştirildi", f.yeri_degistirildi), ("Yenilendi", f.yenilendi)] if v])
            for f in wr.faaliyetler.all()
        ],
        "ilaclar": [f"{i.ilac_tanim.ticari_ismi}: {i.miktar}" for i in wr.kullanilan_ilaclar.all()],
        "tespitler": [f"{t.tespit_tanim.ad} ({t.get_yogunluk_display()}, {t.get_tespit_eden_display()})" for t in wr.tespitler.all()],
        "oneriler": wr.oneriler or "—",
        "not_alani": wr.not_alani or "—",
    }


@client_portal_required
def client_istasyon_raporu(request):
    """Müşteri portalı: Seçili iş kayıtlarına göre istasyon raporu (grafikler, istatistik)."""
    profile = _get_profile(request.user)
    facility_ids = set(profile.get_visible_facilities().values_list("pk", flat=True))
    ids_param = request.GET.get("ids", "").strip()
    if not ids_param:
        return render(request, "core/client/istasyon_raporu.html", {"reports": [], "error": "Lütfen faaliyet kayıtları sayfasından rapor görmek istediğiniz kayıtları seçin."})

    try:
        work_record_ids = [int(x) for x in ids_param.split(",") if x.strip()]
    except ValueError:
        return render(request, "core/client/istasyon_raporu.html", {"reports": [], "error": "Geçersiz kayıt seçimi."})

    if not work_record_ids:
        return render(request, "core/client/istasyon_raporu.html", {"reports": [], "error": "En az bir kayıt seçin."})

    reports = get_istasyon_raporu_data_by_work_records(work_record_ids, facility_ids_allowed=facility_ids)

    if not reports:
        wrs = WorkRecord.objects.filter(pk__in=work_record_ids).select_related("facility", "kapatilan_talep", "kapatilan_talep__facility")
        has_facility = any(wr.facility_id or (wr.kapatilan_talep and wr.kapatilan_talep.facility_id) for wr in wrs)
        fac_in_allowed = False
        if has_facility:
            for wr in wrs:
                fac = wr.facility or (wr.kapatilan_talep.facility if wr.kapatilan_talep_id else None)
                if fac and fac.id in facility_ids:
                    fac_in_allowed = True
                    break
        if not has_facility:
            error_msg = "Seçilen iş kayıtlarında tesis bilgisi bulunmuyor. Rapor için tesis atanmış iş kayıtları seçin."
        elif not fac_in_allowed:
            error_msg = "Seçilen iş kayıtlarının tesisi erişim yetkiniz dışında."
        else:
            error_msg = "Seçilen kayıtlara ait tesiste bölge veya istasyon tanımı bulunamadı."
        return render(request, "core/client/istasyon_raporu.html", {"reports": [], "error": error_msg})

    return render(request, "core/client/istasyon_raporu.html", {"reports": reports, "error": None})


# --- Müşteriler ---

SORT_FIELDS = {
    "kod": "Kod",
    "firma_ismi": "Firma ismi",
    "created_at": "Kayıt tarihi",
}


@login_required
def customer_list(request):
    """Müşteri listesi: arama ve sıralama."""
    qs = Customer.objects.annotate(
        contacts_count=Count("contacts"),
        tesis_count=Count("tesisler"),
    )
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(kod__icontains=q)
            | Q(firma_ismi__icontains=q)
        )
    sort = request.GET.get("sort", "kod")
    if sort not in SORT_FIELDS:
        sort = "kod"
    order = request.GET.get("order", "asc")
    if order == "desc":
        qs = qs.order_by(f"-{sort}")
    else:
        qs = qs.order_by(sort)
    table_data = [
        {
            "id": c.pk,
            "kod": c.kod,
            "firma_ismi": c.firma_ismi,
            "contacts_count": c.contacts_count,
            "tesis_count": c.tesis_count,
            "edit_url": reverse("customer_edit", args=[c.pk]),
        }
        for c in qs
    ]
    context = {
        "customer_list": qs,
        "table_data": table_data,
        "q": q,
        "sort": sort,
        "order": order,
        "sort_fields": SORT_FIELDS,
    }
    return render(request, "core/customer_list.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def customer_create(request):
    """Yeni müşteri ekleme."""
    form = CustomerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Müşteri kaydedildi.")
        return redirect("customer_list")
    return render(
        request,
        "core/customer_form.html",
        {"form": form, "is_edit": False},
    )


@login_required
@require_http_methods(["GET", "POST"])
def customer_edit(request, pk):
    """Müşteri düzenleme (form + müşteri iletişim listesi)."""
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    contact_formset = CustomerContactFormSet(
        request.POST or None,
        instance=customer,
        prefix="contacts",
    )
    if request.method == "POST":
        if form.is_valid() and contact_formset.is_valid():
            form.save()
            contact_formset.save()
            messages.success(request, "Müşteri güncellendi.")
            return redirect("customer_list")
    return render(
        request,
        "core/customer_form.html",
        {
            "form": form,
            "contact_formset": contact_formset,
            "customer": customer,
            "is_edit": True,
        },
    )


# --- Tesisler ---

@login_required
def facility_list(request):
    """Tesis listesi: müşteriye göre filtre, sıralama."""
    qs = (
        Facility.objects.select_related("customer")
        .annotate(contacts_count=Count("contacts"))
        .all()
    )
    customer_id = request.GET.get("customer", "").strip()
    if customer_id:
        qs = qs.filter(customer_id=customer_id)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(kod__icontains=q)
            | Q(ad__icontains=q)
            | Q(customer__firma_ismi__icontains=q)
            | Q(customer__kod__icontains=q)
        )
    qs = qs.order_by("customer__kod", "kod")
    table_data = [
        {
            "id": f.pk,
            "customer_name": f.customer.firma_ismi,
            "customer_id": f.customer_id,
            "customer_edit_url": reverse("customer_edit", args=[f.customer_id]),
            "kod": f.kod,
            "ad": f.ad,
            "contacts_count": f.contacts_count,
            "edit_url": reverse("facility_edit", args=[f.pk]),
            "contacts_url": reverse(
                "facility_contacts", args=[f.customer_id, f.pk]
            ),
        }
        for f in qs
    ]
    context = {
        "facility_list": qs,
        "table_data": table_data,
        "q": q,
        "customer_id": customer_id,
        "customers": Customer.objects.order_by("kod"),
    }
    return render(request, "core/facility_list.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def facility_create(request):
    """Yeni tesis ekleme."""
    form = FacilityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Tesis kaydedildi.")
        return redirect("facility_list")
    return render(request, "core/facility_form.html", {"form": form, "is_edit": False})


@login_required
@require_http_methods(["GET", "POST"])
def facility_edit(request, pk):
    """Tesis düzenleme."""
    facility = get_object_or_404(Facility, pk=pk)
    form = FacilityForm(request.POST or None, instance=facility)
    form.fields["customer"].disabled = True
    if request.method == "POST":
        if form.is_valid():
            form.instance.customer_id = facility.customer_id
            form.save()
            messages.success(request, "Tesis güncellendi.")
            return redirect("facility_list")
    zone_list = [(z, StationForm()) for z in facility.bolgeler.all()]
    return render(
        request,
        "core/facility_form.html",
        {
            "form": form,
            "facility": facility,
            "is_edit": True,
            "zone_list": zone_list,
            "zone_form": ZoneForm(),
        },
    )


@login_required
@require_http_methods(["POST"])
def facility_add_zone(request, facility_pk):
    """HTMX: Tesis altına bölge ekle; yeni bölge kartı HTML döner."""
    facility = get_object_or_404(Facility, pk=facility_pk)
    form = ZoneForm(request.POST or None)
    if form.is_valid():
        zone = form.save(commit=False)
        zone.facility = facility
        zone.save()
        return render(
            request,
            "core/partials/zone_block.html",
            {"zone": zone, "facility": facility, "station_form": StationForm()},
        )
    return render(
        request,
        "core/partials/zone_form.html",
        {"form": form, "facility": facility, "is_oob": True},
        status=422,
    )


@login_required
@require_http_methods(["POST"])
def zone_add_station(request, zone_pk):
    """HTMX: Bölge altına istasyon ekle; güncel istasyon listesi HTML döner."""
    zone = get_object_or_404(Zone, pk=zone_pk)
    form = StationForm(request.POST or None)
    if form.is_valid():
        station = form.save(commit=False)
        station.zone = zone
        station.save()
        form = StationForm()
    return render(
        request,
        "core/partials/station_list.html",
        {"zone": zone, "form": form},
    )


@login_required
@require_http_methods(["GET", "POST"])
def facility_contacts(request, customer_pk, facility_pk):
    """Tesis iletişim listesi: tesis bilgisi + iletişim formset."""
    customer = get_object_or_404(Customer, pk=customer_pk)
    facility = get_object_or_404(Facility, pk=facility_pk, customer=customer)
    formset = FacilityContactFormSet(
        request.POST or None,
        instance=facility,
        prefix="contacts",
    )
    if request.method == "POST":
        if formset.is_valid():
            formset.save()
            messages.success(request, "Tesis iletişimleri güncellendi.")
            return redirect("facility_edit", pk=facility.pk)
    return render(
        request,
        "core/facility_contacts.html",
        {"customer": customer, "facility": facility, "formset": formset},
    )
