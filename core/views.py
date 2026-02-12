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

from .models import Customer, Facility, Zone, Station
from .forms import CustomerForm, FacilityForm, ZoneForm, StationForm
from addressbook.forms import CustomerContactFormSet, FacilityContactFormSet


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Giriş sayfası. Kayıt yok; kullanıcılar admin'den tanımlanır."""
    if request.user.is_authenticated:
        return redirect("home")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        next_url = request.GET.get("next") or "home"
        return redirect(next_url)
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


@login_required
def home(request):
    """Ana sayfa (giriş gerekli)."""
    return render(request, "core/home.html")


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
