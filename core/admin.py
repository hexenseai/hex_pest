from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.db import models
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, TabularInline

from .forms import StationForm, ZoneForm, TalepAdminForm
from django.core.files.base import ContentFile

from .models import (
    BagimsizTespit,
    Customer,
    Facility,
    Zone,
    Station,
    UserProfile,
    Ekip,
    Periyod,
    UygulamaTanim,
    FaaliyetTanim,
    IlacTanim,
    TespitTanim,
    WorkRecord,
    WorkRecordUygulama,
    WorkRecordFaaliyet,
    WorkRecordIlac,
    WorkRecordTespit,
    WorkRecordStationCount,
    TalepTipi,
    Talep,
    FaaliyetRaporu,
)
from .faaliyet_raporu_pdf import generate_faaliyet_raporu_pdf
from .bagimsiz_tespit_raporu_pdf import generate_bagimsiz_tespit_raporu_pdf
from .label_pdf import generate_station_labels_pdf
from .widgets import ImageCropInput
from addressbook.models import Contact

User = get_user_model()


class FacilityInline(TabularInline):
    model = Facility
    extra = 0
    fields = ("kod", "ad", "adres")


class CustomerContactInline(TabularInline):
    """Müşteri düzenleme sayfasında iletişim kayıtları."""
    model = Contact
    fk_name = "customer"
    exclude = ("facility",)
    extra = 1
    can_delete = True
    autocomplete_fields = ["category"]
    fields = ("category", "ad_soyad", "telefon", "email", "not_alani")


class FacilityContactInline(TabularInline):
    """Tesis düzenleme sayfasında iletişim kayıtları."""
    model = Contact
    fk_name = "facility"
    exclude = ("customer",)
    extra = 1
    can_delete = True
    autocomplete_fields = ["category"]
    fields = ("category", "ad_soyad", "telefon", "email", "not_alani")


class ZoneInline(TabularInline):
    model = Zone
    extra = 0
    fields = ("kod", "ad")


class StationInline(TabularInline):
    model = Station
    extra = 0
    fields = ("kod", "ad",)
    readonly_fields = ("benzersiz_kod",)


class WorkRecordStationCountInline(TabularInline):
    model = WorkRecordStationCount
    extra = 0
    fields = ("station", "tuketim_var", "not_alani")
    autocomplete_fields = ["station"]


class WorkRecordUygulamaInline(TabularInline):
    model = WorkRecordUygulama
    extra = 0
    fields = ("uygulama_tanim",)
    autocomplete_fields = ["uygulama_tanim"]


class WorkRecordTespitInline(TabularInline):
    model = WorkRecordTespit
    extra = 0
    fields = ("tespit_tanim", "yogunluk", "tespit_eden")
    autocomplete_fields = ["tespit_tanim"]


class WorkRecordFaaliyetInline(TabularInline):
    model = WorkRecordFaaliyet
    extra = 0
    fields = (
        "faaliyet_tanim",
        "kontrol", "kuruldu", "eklendi", "sabitlendi", "yeri_degistirildi", "yenilendi",
    )
    autocomplete_fields = ["faaliyet_tanim"]
    verbose_name = "Düzeltici / Önleyici Faaliyet"
    verbose_name_plural = "Düzeltici / Önleyici Faaliyetler"


class WorkRecordIlacInline(TabularInline):
    model = WorkRecordIlac
    extra = 0
    fields = ("ilac_tanim", "miktar")
    autocomplete_fields = ["ilac_tanim"]


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    fk_name = "user"
    max_num = 1
    can_delete = True
    fields = ("customer", "avatar")
    autocomplete_fields = ["customer"]
    formfield_overrides = {models.ImageField: {"widget": ImageCropInput}}

    class Media:
        css = {"all": ("https://cdn.jsdelivr.net/npm/cropperjs@1.6.2/dist/cropper.min.css",)}
        js = (
            "https://cdn.jsdelivr.net/npm/cropperjs@1.6.2/dist/cropper.min.js",
            "core/js/image_crop.js",
        )


@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = ("kod", "firma_ismi", "logo_thumb", "created_at")
    list_filter = ("created_at",)
    search_fields = ("kod", "firma_ismi")
    inlines = [CustomerContactInline, FacilityInline]
    formfield_overrides = {models.ImageField: {"widget": ImageCropInput}}

    def logo_thumb(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" alt="" style="height:28px;width:28px;object-fit:cover;border-radius:4px;">',
                obj.logo.url,
            )
        return "—"

    logo_thumb.short_description = "Logo"

    class Media:
        css = {"all": ("https://cdn.jsdelivr.net/npm/cropperjs@1.6.2/dist/cropper.min.css",)}
        js = (
            "https://cdn.jsdelivr.net/npm/cropperjs@1.6.2/dist/cropper.min.js",
            "core/js/image_crop.js",
        )


@admin.register(Facility)
class FacilityAdmin(ModelAdmin):
    list_display = ("kod", "ad", "customer", "istasyonlar_link", "created_at")
    list_filter = ("customer", "created_at")
    search_fields = ("kod", "ad", "customer__kod")
    autocomplete_fields = ["customer"]
    inlines = [FacilityContactInline, ZoneInline]

    def istasyonlar_link(self, obj):
        if obj.pk:
            url = reverse("admin:core_facility_stations", args=[obj.pk])
            return format_html(
                '<a href="{}" class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md'
                ' bg-primary-600 text-white hover:bg-primary-700 focus:outline-none focus:ring-2'
                ' focus:ring-offset-2 focus:ring-primary-500 no-underline">İstasyonlar</a>',
                url,
            )
        return "-"

    istasyonlar_link.short_description = "İstasyonlar"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<path:object_id>/stations/",
                self.admin_site.admin_view(self.stations_view),
                name="core_facility_stations",
            ),
        ]
        return custom + urls

    def stations_view(self, request, object_id):
        facility = get_object_or_404(Facility, pk=object_id)
        if not self.has_change_permission(request, facility):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        zones = facility.bolgeler.prefetch_related("istasyonlar").order_by("kod")

        add_form_errors = None
        add_form_zone_id = None
        zone_form = ZoneForm()
        zone_form_errors = None

        if request.method == "POST":
            if request.POST.get("action") == "add_zone":
                zone_form = ZoneForm(request.POST)
                if zone_form.is_valid():
                    zone = zone_form.save(commit=False)
                    zone.facility = facility
                    zone.save()
                    messages.success(request, "Bölge eklendi.")
                    return redirect("admin:core_facility_stations", object_id=object_id)
                zone_form_errors = zone_form
            else:
                zone_id = request.POST.get("zone_id")
                zone = get_object_or_404(Zone, pk=zone_id, facility=facility)
                form = StationForm(request.POST)
                if form.is_valid():
                    station = form.save(commit=False)
                    station.zone = zone
                    station.save()
                    messages.success(request, "İstasyon eklendi.")
                    return redirect("admin:core_facility_stations", object_id=object_id)
                add_form_errors = form
                add_form_zone_id = zone.pk

        context = {
            **self.admin_site.each_context(request),
            "title": f"İstasyonlar — {facility}",
            "facility": facility,
            "zones": zones,
            "opts": self.model._meta,
            "station_form": StationForm(),
            "add_form_errors": add_form_errors,
            "add_form_zone_id": add_form_zone_id,
            "zone_form": zone_form_errors or ZoneForm(),
            "zone_form_errors": zone_form_errors,
        }
        return render(request, "admin/core/facility/stations.html", context)


@admin.register(Zone)
class ZoneAdmin(ModelAdmin):
    list_display = ("kod", "ad", "facility", "created_at")
    list_filter = ("facility__customer", "facility", "created_at")
    search_fields = ("kod", "ad", "facility__kod")
    autocomplete_fields = ["facility"]
    inlines = [StationInline]


class TesisListFilter(admin.SimpleListFilter):
    """İstasyon listesinde tesis bazlı filtre."""
    title = "Tesis"
    parameter_name = "tesis"

    def lookups(self, request, model_admin):
        for f in Facility.objects.select_related("customer").order_by("customer__kod", "kod"):
            yield (str(f.pk), str(f))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(zone__facility_id=self.value())
        return queryset


@admin.register(Station)
class StationAdmin(ModelAdmin):
    list_display = ("benzersiz_kod", "kod", "ad", "zone", "created_at")
    list_filter = (TesisListFilter, "zone__facility__customer", "zone", "created_at")
    search_fields = ("benzersiz_kod", "kod", "ad")
    readonly_fields = ("benzersiz_kod",)
    autocomplete_fields = ["zone"]
    actions = ["etiket_pdf_indir"]

    @admin.action(description="Seçili istasyonlar için etiket PDF indir (80x25mm)")
    def etiket_pdf_indir(self, request, queryset):
        stations = queryset.select_related("zone").order_by("zone__facility", "zone", "kod")
        if not stations:
            self.message_user(request, "En az bir istasyon seçin.", level=messages.WARNING)
            return
        try:
            pdf_bytes = generate_station_labels_pdf(stations)
        except Exception as e:
            self.message_user(request, f"PDF oluşturulamadı: {e}", level=messages.ERROR)
            return
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="istasyon-etiketleri.pdf"'
        return response


@admin.register(Ekip)
class EkipAdmin(ModelAdmin):
    list_display = ("kod", "ekip_lideri", "kisi_sayisi", "created_at")
    list_filter = ("ekip_lideri",)
    search_fields = ("kod", "uyeler")
    autocomplete_fields = ["ekip_lideri"]


@admin.register(Periyod)
class PeriyodAdmin(ModelAdmin):
    list_display = ("customer", "facility", "ad", "talep_tipi", "siklik", "aralik", "baslangic_tarihi", "bitis_tarihi", "aktif", "created_at")
    list_filter = ("siklik", "aktif", "talep_tipi", "customer", "created_at")
    search_fields = ("ad", "customer__kod", "facility__ad")
    autocomplete_fields = ["customer", "facility", "talep_tipi"]
    date_hierarchy = "baslangic_tarihi"


@admin.register(UygulamaTanim)
class UygulamaTanimAdmin(ModelAdmin):
    list_display = ("ad", "sira", "created_at")
    list_editable = ("sira",)
    ordering = ("sira", "ad")
    search_fields = ("ad",)


@admin.register(FaaliyetTanim)
class FaaliyetTanimAdmin(ModelAdmin):
    list_display = ("ad", "sira", "created_at")
    list_editable = ("sira",)
    ordering = ("sira", "ad")
    search_fields = ("ad",)


@admin.register(IlacTanim)
class IlacTanimAdmin(ModelAdmin):
    list_display = ("ticari_ismi", "temin_edildigi_firma", "aktif_madde", "ambalaj", "antidot", "aktif", "created_at")
    list_filter = ("aktif", "temin_edildigi_firma")
    search_fields = ("ticari_ismi", "temin_edildigi_firma", "aktif_madde", "antidot")
    ordering = ("ticari_ismi",)

    def get_search_results(self, request, queryset, search_term):
        """Autocomplete (iş kaydında ilaç seçerken) sadece aktif ilaçlar aranır; liste sayfasında tümü."""
        if "/autocomplete/" in request.path:
            queryset = queryset.filter(aktif=True)
        return super().get_search_results(request, queryset, search_term)


@admin.register(TespitTanim)
class TespitTanimAdmin(ModelAdmin):
    list_display = ("ad", "sira", "created_at")
    list_editable = ("sira",)
    ordering = ("sira", "ad")
    search_fields = ("ad",)


@admin.register(WorkRecord)
class WorkRecordAdmin(ModelAdmin):
    formfield_overrides = {
        models.TimeField: {
            "widget": forms.TimeInput(attrs={"type": "time", "class": "vTimeField"}),
        },
    }
    list_display = (
        "form_numarasi", "tarih", "durum", "customer", "facility", "personel", "ekip",
        "baslama_saati", "bitis_saati", "baslat_bitir_links",
        "faaliyet_raporu_durum", "kapatilan_talep_link", "istasyon_sayim_link", "created_at",
    )
    actions = ["faaliyet_raporu_olustur", "baslat_action", "bitir_action"]
    list_filter = (
        "tarih", "durum", "customer", "personel", "ekip", "gozlem_ziyareti_yapilmali", "sozlesme_disi_islem_var",
        "skb", "atomizor", "pulverizator", "termal_sis", "ar_uz_ulv", "elk_ulv", "civi_tabancasi",
        "created_at",
    )
    search_fields = ("personel__username", "oneriler", "form_numarasi", "customer__kod", "facility__kod")
    readonly_fields = ("form_numarasi",)
    autocomplete_fields = ["customer", "facility", "personel", "ekip", "kapatilan_talep"]
    inlines = [
        WorkRecordUygulamaInline,
        WorkRecordTespitInline,
        WorkRecordFaaliyetInline,
        WorkRecordIlacInline,
        WorkRecordStationCountInline,
    ]
    date_hierarchy = "tarih"
    fieldsets = (
        (None, {
            "fields": (
                "tarih", "durum", "customer", "facility", "personel", "ekip",
                "baslama_saati", "bitis_saati",
                "gozlem_ziyareti_yapilmali", "sozlesme_disi_islem_var",
                "oneriler", "not_alani", "kapatilan_talep", "form_numarasi",
            ),
        }),
        ("Makine ve Ekipmanlar", {
            "fields": ("skb", "atomizor", "pulverizator", "termal_sis", "ar_uz_ulv", "elk_ulv", "civi_tabancasi"),
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "ilac_tanim":
            object_id = getattr(request.resolver_match, "kwargs", {}).get("object_id")
            if object_id:
                used_ids = WorkRecordIlac.objects.filter(work_record_id=object_id).values_list("ilac_tanim_id", flat=True)
                kwargs["queryset"] = IlacTanim.objects.filter(Q(aktif=True) | Q(pk__in=used_ids)).distinct()
            else:
                kwargs["queryset"] = IlacTanim.objects.filter(aktif=True)
            return super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "facility":
            object_id = getattr(request.resolver_match, "kwargs", {}).get("object_id")
            if object_id:
                try:
                    obj = self.get_object(request, object_id)
                    if obj and obj.customer_id:
                        kwargs["queryset"] = Facility.objects.filter(customer_id=obj.customer_id).order_by("kod")
                except Exception:
                    pass
            return super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "kapatilan_talep":
            qs = kwargs.get("queryset") or Talep.objects.all()
            object_id = getattr(request.resolver_match, "kwargs", {}).get("object_id") if getattr(request, "resolver_match", None) else None
            if object_id:
                try:
                    obj = self.get_object(request, object_id)
                    if obj and obj.kapatilan_talep_id:
                        qs = Talep.objects.filter(~Q(durum="yapildi") | Q(pk=obj.kapatilan_talep_id))
                    else:
                        qs = qs.exclude(durum="yapildi")
                except Exception:
                    qs = qs.exclude(durum="yapildi")
            else:
                qs = qs.exclude(durum="yapildi")
            kwargs["queryset"] = qs
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    change_form_template = "admin/core/workrecord/change_form.html"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        try:
            obj = WorkRecord.objects.get(pk=object_id)
            extra_context["istasyon_sayim_url"] = reverse("admin:core_workrecord_istasyon_sayim", args=[obj.pk])
            extra_context["istasyon_sayim_toplu_url"] = reverse("admin:core_workrecord_istasyon_sayim_toplu", args=[obj.pk])
            extra_context["faaliyet_raporu_pdf_url"] = reverse("admin:core_workrecord_faaliyet_raporu_pdf", args=[obj.pk])
        except WorkRecord.DoesNotExist:
            extra_context["istasyon_sayim_url"] = None
            extra_context["istasyon_sayim_toplu_url"] = None
            extra_context["faaliyet_raporu_pdf_url"] = None
        return super().change_view(request, object_id, form_url, extra_context)

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        if obj is None:
            req = request
            class WorkRecordFormWithInitial(form_class):
                def __init__(self, *args, **kwargs):
                    kwargs.setdefault("initial", {})
                    if "personel" not in kwargs["initial"] and getattr(req, "user", None):
                        kwargs["initial"]["personel"] = req.user.pk
                    super().__init__(*args, **kwargs)
            return WorkRecordFormWithInitial
        return form_class

    @admin.action(description="Seçilenleri başlat")
    def baslat_action(self, request, queryset):
        from django.utils import timezone
        now = timezone.now().time()
        count = 0
        for wr in queryset.filter(durum=WorkRecord.DURUM_BASLANMADI):
            wr.durum = WorkRecord.DURUM_DEVAM_EDIYOR
            if not wr.baslama_saati:
                wr.baslama_saati = now
            wr.save(update_fields=["durum", "baslama_saati"])
            count += 1
        if count:
            self.message_user(request, f"{count} iş kaydı başlatıldı.", level=messages.SUCCESS)
        else:
            self.message_user(request, "Başlatılacak kayıt yok (zaten devam eden veya tamamlanmış).", level=messages.WARNING)

    @admin.action(description="Seçilenleri tamamla")
    def bitir_action(self, request, queryset):
        from django.utils import timezone
        now = timezone.now().time()
        count = 0
        for wr in queryset.filter(durum=WorkRecord.DURUM_DEVAM_EDIYOR):
            wr.durum = WorkRecord.DURUM_TAMAMLANDI
            if not wr.bitis_saati:
                wr.bitis_saati = now
            wr.save(update_fields=["durum", "bitis_saati"])
            count += 1
        if count:
            self.message_user(request, f"{count} iş kaydı tamamlandı.", level=messages.SUCCESS)
        else:
            self.message_user(request, "Tamamlanacak kayıt yok (başlanmamış veya zaten tamamlanmış).", level=messages.WARNING)

    @admin.action(description="Seçilen iş kayıtları için faaliyet raporu oluştur")
    def faaliyet_raporu_olustur(self, request, queryset):
        from .faaliyet_raporu_pdf import generate_faaliyet_raporu_pdf

        olusturulan = 0
        for wr in queryset.select_related(
            "customer", "facility", "ekip", "ekip__ekip_lideri",
            "kapatilan_talep", "kapatilan_talep__customer",
            "kapatilan_talep__facility", "kapatilan_talep__tip",
        ):
            try:
                pdf_bytes = generate_faaliyet_raporu_pdf(wr)
                musteri_kod = (wr.customer.kod if wr.customer_id else "") or (
                    wr.kapatilan_talep.customer.kod if wr.kapatilan_talep_id and wr.kapatilan_talep.customer_id else ""
                )
                is_kaydi_kod = wr.form_numarasi or f"WR-{wr.pk}"
                rapor, created = FaaliyetRaporu.objects.get_or_create(
                    work_record=wr,
                    defaults={
                        "musteri_kod": musteri_kod,
                        "is_kaydi_kod": is_kaydi_kod,
                        "rapor_tarihi": wr.tarih,
                    },
                )
                rapor.musteri_kod = musteri_kod
                rapor.is_kaydi_kod = is_kaydi_kod
                rapor.rapor_tarihi = wr.tarih
                rapor.rapor_olusturuldu = True
                dosya_adi = f"{is_kaydi_kod}_faaliyet.pdf"
                rapor.pdf.save(dosya_adi, ContentFile(pdf_bytes), save=True)
                rapor.save()
                olusturulan += 1
            except Exception as e:
                self.message_user(request, f"İş kaydı {wr.pk} için rapor oluşturulamadı: {e}", level=messages.ERROR)
        if olusturulan:
            self.message_user(request, f"{olusturulan} faaliyet raporu oluşturuldu.", level=messages.SUCCESS)

    def faaliyet_raporu_durum(self, obj):
        # Rapor silinmiş olabilir; her seferinde sorgu ile kontrol et
        rapor = FaaliyetRaporu.objects.filter(work_record=obj).first()
        if rapor is None:
            url = reverse("admin:core_workrecord_faaliyet_raporu_pdf", args=[obj.pk])
            return format_html(
                '<a href="{}" class="inline-flex items-center px-2 py-1 text-xs rounded bg-gray-200 hover:bg-gray-300" title="Rapor oluştur veya tekrar oluştur">Tekrar oluşturulacak</a>',
                url,
            )
        if not rapor.rapor_olusturuldu or not rapor.pdf:
            url = reverse("admin:core_workrecord_faaliyet_raporu_pdf", args=[obj.pk])
            return format_html('<a href="{}">Oluştur</a>', url)
        pdf_url = rapor.pdf.url if hasattr(rapor.pdf, "url") else ""
        if pdf_url:
            return format_html(
                '<span title="Rapor oluşturuldu">✓</span> <a href="{}" target="_blank">PDF</a>',
                pdf_url,
            )
        return format_html('<span title="Rapor oluşturuldu">✓</span>')

    faaliyet_raporu_durum.short_description = "Rapor"

    def kapatilan_talep_link(self, obj):
        talep = getattr(obj, "kapatilan_talep", None)
        if talep is None:
            return "—"
        url = reverse("admin:core_talep_change", args=[talep.pk])
        return format_html(
            '<a href="{}" class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md '
            'bg-primary-600 text-white hover:bg-primary-700 focus:outline-none focus:ring-2 '
            'focus:ring-offset-2 focus:ring-primary-500 no-underline">{}</a>',
            url, str(talep),
        )

    kapatilan_talep_link.short_description = "Kapatılan talep"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<path:object_id>/baslat/",
                self.admin_site.admin_view(self.baslat_view),
                name="core_workrecord_baslat",
            ),
            path(
                "<path:object_id>/bitir/",
                self.admin_site.admin_view(self.bitir_view),
                name="core_workrecord_bitir",
            ),
            path(
                "<path:object_id>/istasyon-sayim/",
                self.admin_site.admin_view(self.istasyon_sayim_view),
                name="core_workrecord_istasyon_sayim",
            ),
            path(
                "<path:object_id>/istasyon-sayim-toplu/",
                self.admin_site.admin_view(self.istasyon_sayim_toplu_view),
                name="core_workrecord_istasyon_sayim_toplu",
            ),
            path(
                "<path:object_id>/faaliyet-raporu-pdf/",
                self.admin_site.admin_view(self.faaliyet_raporu_pdf_view),
                name="core_workrecord_faaliyet_raporu_pdf",
            ),
        ]
        return custom + urls

    def _baslat_or_bitir(self, request, object_id, action):
        """Başlat veya Bitir işlemi."""
        from django.core.exceptions import PermissionDenied
        from django.utils import timezone

        work_record = get_object_or_404(WorkRecord, pk=object_id)
        if not self.has_change_permission(request, work_record):
            raise PermissionDenied
        now = timezone.now().time()
        if action == "baslat":
            work_record.durum = WorkRecord.DURUM_DEVAM_EDIYOR
            if not work_record.baslama_saati:
                work_record.baslama_saati = now
        else:  # bitir
            work_record.durum = WorkRecord.DURUM_TAMAMLANDI
            if not work_record.bitis_saati:
                work_record.bitis_saati = now
        work_record.save(update_fields=["durum", "baslama_saati", "bitis_saati"])
        return work_record

    def baslat_view(self, request, object_id):
        self._baslat_or_bitir(request, object_id, "baslat")
        messages.success(request, "İş kaydı başlatıldı.")
        return redirect("admin:core_workrecord_changelist")

    def bitir_view(self, request, object_id):
        self._baslat_or_bitir(request, object_id, "bitir")
        messages.success(request, "İş kaydı tamamlandı.")
        return redirect("admin:core_workrecord_changelist")

    def baslat_bitir_links(self, obj):
        if obj is None or not obj.pk:
            return "—"
        links = []
        if obj.durum == WorkRecord.DURUM_BASLANMADI:
            url = reverse("admin:core_workrecord_baslat", args=[obj.pk])
            links.append(
                f'<a href="{url}" class="inline-flex items-center px-2 py-1 text-xs rounded bg-green-600 text-white hover:bg-green-700 no-underline">Başlat</a>'
            )
        elif obj.durum == WorkRecord.DURUM_DEVAM_EDIYOR:
            url = reverse("admin:core_workrecord_bitir", args=[obj.pk])
            links.append(
                f'<a href="{url}" class="inline-flex items-center px-2 py-1 text-xs rounded bg-amber-600 text-white hover:bg-amber-700 no-underline">Bitir</a>'
            )
        else:
            links.append('<span class="text-green-600">✓</span>')
        return mark_safe(" ".join(links)) if links else "—"

    baslat_bitir_links.short_description = "İşlem"

    def faaliyet_raporu_pdf_view(self, request, object_id):
        from django.core.exceptions import PermissionDenied

        work_record = get_object_or_404(
            WorkRecord.objects.select_related(
                "customer", "facility", "ekip", "ekip__ekip_lideri",
                "kapatilan_talep", "kapatilan_talep__customer",
                "kapatilan_talep__facility", "kapatilan_talep__tip",
            ),
            pk=object_id,
        )
        if not self.has_view_permission(request, work_record):
            raise PermissionDenied
        pdf_bytes = generate_faaliyet_raporu_pdf(work_record)
        musteri_kod = (work_record.customer.kod if work_record.customer_id else "") or (
            work_record.kapatilan_talep.customer.kod if work_record.kapatilan_talep_id and work_record.kapatilan_talep.customer_id else ""
        )
        is_kaydi_kod = work_record.form_numarasi or f"WR-{work_record.pk}"
        rapor, created = FaaliyetRaporu.objects.get_or_create(
            work_record=work_record,
            defaults={
                "musteri_kod": musteri_kod,
                "is_kaydi_kod": is_kaydi_kod,
                "rapor_tarihi": work_record.tarih,
            },
        )
        rapor.musteri_kod = musteri_kod
        rapor.is_kaydi_kod = is_kaydi_kod
        rapor.rapor_tarihi = work_record.tarih
        rapor.rapor_olusturuldu = True
        dosya_adi = f"{is_kaydi_kod}_faaliyet.pdf"
        rapor.pdf.save(dosya_adi, ContentFile(pdf_bytes), save=True)
        rapor.save()
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{dosya_adi}"'
        return response

    def istasyon_sayim_view(self, request, object_id):
        from django.core.exceptions import PermissionDenied

        work_record = get_object_or_404(
            WorkRecord.objects.select_related("facility", "kapatilan_talep"),
            pk=object_id,
        )
        if not self.has_view_permission(request, work_record):
            raise PermissionDenied
        locked = work_record.bitis_saati is not None
        default_facility = work_record.facility or (work_record.kapatilan_talep.facility if work_record.kapatilan_talep_id else None)

        # Lookup by benzersiz_kod (GET API for HTMX/JS)
        benzersiz_kod = request.GET.get("benzersiz_kod", "").strip()
        if benzersiz_kod and request.headers.get("Accept") == "application/json":
            station = (
                Station.objects.filter(benzersiz_kod=benzersiz_kod)
                .select_related("zone", "zone__facility", "zone__facility__customer")
                .first()
            )
            if not station:
                return JsonResponse({"found": False}, status=404)
            return JsonResponse({
                "found": True,
                "id": station.pk,
                "benzersiz_kod": station.benzersiz_kod,
                "kod": station.kod,
                "ad": station.ad,
                "zone_kod": station.zone.kod,
                "zone_ad": station.zone.ad,
                "facility_kod": station.zone.facility.kod,
                "facility_ad": station.zone.facility.ad,
                "customer_kod": station.zone.facility.customer.kod,
            })

        # POST: save single or bulk
        if request.method == "POST" and not locked:
            if not self.has_change_permission(request, work_record):
                raise PermissionDenied
            action = request.POST.get("action")
            if action == "save":
                station_id = request.POST.get("station_id")
                tuketim_var = request.POST.get("tuketim_var") in ("1", "true", "on", "yes")
                not_alani = request.POST.get("not_alani", "").strip()
                if station_id:
                    station = get_object_or_404(Station, pk=station_id)
                    obj, _ = WorkRecordStationCount.objects.get_or_create(
                        work_record=work_record,
                        station=station,
                        defaults={"tuketim_var": tuketim_var, "not_alani": not_alani},
                    )
                    if not _:
                        obj.tuketim_var = tuketim_var
                        obj.not_alani = not_alani
                        obj.save()
                    messages.success(request, f"Tüketim kaydedildi: {station.benzersiz_kod}")
            redirect_url = reverse("admin:core_workrecord_istasyon_sayim", args=[object_id])
            fid = request.GET.get("facility") or request.POST.get("facility")
            zid = request.GET.get("zone") or request.POST.get("zone")
            if fid:
                redirect_url += f"?facility={fid}"
                if zid:
                    redirect_url += f"&zone={zid}"
            return redirect(redirect_url)

        # Selected facility/zone for summary and bulk list
        facility_id = request.GET.get("facility") or (str(default_facility.pk) if default_facility else None)
        zone_id = request.GET.get("zone")
        selected_facility = None
        if facility_id:
            try:
                selected_facility = Facility.objects.get(pk=facility_id)
            except Facility.DoesNotExist:
                pass
        if not selected_facility and default_facility:
            selected_facility = default_facility

        # Summary counts
        summary_facility = summary_zone = None
        if selected_facility:
            total_f = Station.objects.filter(zone__facility=selected_facility).count()
            entered_f = WorkRecordStationCount.objects.filter(
                work_record=work_record,
                station__zone__facility=selected_facility,
            ).count()
            summary_facility = {"toplam": total_f, "girilen": entered_f, "kalan": total_f - entered_f}
            if zone_id and selected_facility.bolgeler.filter(pk=zone_id).exists():
                total_z = Station.objects.filter(zone_id=zone_id).count()
                entered_z = WorkRecordStationCount.objects.filter(
                    work_record=work_record,
                    station__zone_id=zone_id,
                ).count()
                summary_zone = {"toplam": total_z, "girilen": entered_z, "kalan": total_z - entered_z}

        # Bakılmış ve bakılmamış istasyonlar (sayım sayfasında sadece listeleme)
        bakilmis_stations = []
        bakilmamis_stations = []
        if selected_facility:
            stations_qs = (
                Station.objects.filter(zone__facility=selected_facility)
                .select_related("zone")
                .order_by("zone__kod", "kod")
            )
            if zone_id:
                stations_qs = stations_qs.filter(zone_id=zone_id)
            existing = {
                sc.station_id: sc
                for sc in WorkRecordStationCount.objects.filter(
                    work_record=work_record,
                    station__in=stations_qs,
                )
            }
            for st in stations_qs:
                row = {"station": st, "count_obj": existing.get(st.pk)}
                if row["count_obj"]:
                    bakilmis_stations.append(row)
                else:
                    bakilmamis_stations.append(row)

        facilities = Facility.objects.select_related("customer").order_by("customer__kod", "kod")[:500]
        zones = list(selected_facility.bolgeler.order_by("kod")) if selected_facility else []

        context = {
            **self.admin_site.each_context(request),
            "title": f"İstasyon sayımı — {work_record}",
            "work_record": work_record,
            "locked": locked,
            "opts": WorkRecord._meta,
            "default_facility": default_facility,
            "selected_facility": selected_facility,
            "selected_zone_id": zone_id,
            "summary_facility": summary_facility,
            "summary_zone": summary_zone,
            "bakilmis_stations": bakilmis_stations,
            "bakilmamis_stations": bakilmamis_stations,
            "facilities": facilities,
            "zones": zones,
            "istasyon_sayim_url": reverse("admin:core_workrecord_istasyon_sayim", args=[work_record.pk]),
            "istasyon_sayim_toplu_url": reverse("admin:core_workrecord_istasyon_sayim_toplu", args=[work_record.pk]),
        }
        return render(request, "admin/core/workrecord/istasyon_sayim.html", context)

    def istasyon_sayim_toplu_view(self, request, object_id):
        """Toplu liste sayfası: tesis/bölge seçip tüm istasyonları düzenlenebilir tabloda gösterir."""
        from django.core.exceptions import PermissionDenied

        work_record = get_object_or_404(
            WorkRecord.objects.select_related("facility", "kapatilan_talep"),
            pk=object_id,
        )
        if not self.has_view_permission(request, work_record):
            raise PermissionDenied
        locked = work_record.bitis_saati is not None
        default_facility = work_record.facility or (work_record.kapatilan_talep.facility if work_record.kapatilan_talep_id else None)

        # POST: save_bulk
        if request.method == "POST" and not locked:
            if not self.has_change_permission(request, work_record):
                raise PermissionDenied
            if request.POST.get("action") == "save_bulk":
                saved = 0
                ids_str = request.POST.get("bulk_station_ids", "")
                for sid_str in ids_str.split(",") if ids_str else []:
                    try:
                        sid = int(sid_str.strip())
                    except (ValueError, TypeError):
                        continue
                    tuketim_var = request.POST.get(f"tuketim_{sid}") in ("1", "true", "on", "yes")
                    not_alani = request.POST.get(f"not_{sid}", "").strip()
                    try:
                        station = Station.objects.get(pk=sid)
                        obj, _ = WorkRecordStationCount.objects.get_or_create(
                            work_record=work_record,
                            station=station,
                            defaults={"tuketim_var": tuketim_var, "not_alani": not_alani},
                        )
                        if not _:
                            obj.tuketim_var = tuketim_var
                            obj.not_alani = not_alani
                            obj.save()
                        saved += 1
                    except Station.DoesNotExist:
                        pass
                if saved:
                    messages.success(request, f"{saved} tüketim kaydı güncellendi.")
            redirect_url = reverse("admin:core_workrecord_istasyon_sayim_toplu", args=[object_id])
            fid = request.GET.get("facility") or request.POST.get("facility")
            zid = request.GET.get("zone") or request.POST.get("zone")
            if fid:
                redirect_url += f"?facility={fid}"
                if zid:
                    redirect_url += f"&zone={zid}"
            return redirect(redirect_url)

        facility_id = request.GET.get("facility") or (str(default_facility.pk) if default_facility else None)
        zone_id = request.GET.get("zone")
        selected_facility = None
        if facility_id:
            try:
                selected_facility = Facility.objects.get(pk=facility_id)
            except Facility.DoesNotExist:
                pass
        if not selected_facility and default_facility:
            selected_facility = default_facility

        bulk_stations = []
        summary_facility = summary_zone = None
        if selected_facility:
            stations_qs = (
                Station.objects.filter(zone__facility=selected_facility)
                .select_related("zone")
                .order_by("zone__kod", "kod")
            )
            if zone_id:
                stations_qs = stations_qs.filter(zone_id=zone_id)
            existing = {
                sc.station_id: sc
                for sc in WorkRecordStationCount.objects.filter(
                    work_record=work_record,
                    station__in=stations_qs,
                )
            }
            for st in stations_qs:
                bulk_stations.append({"station": st, "count_obj": existing.get(st.pk)})

            total_f = Station.objects.filter(zone__facility=selected_facility).count()
            entered_f = WorkRecordStationCount.objects.filter(
                work_record=work_record,
                station__zone__facility=selected_facility,
            ).count()
            summary_facility = {"toplam": total_f, "girilen": entered_f, "kalan": total_f - entered_f}
            if zone_id and selected_facility.bolgeler.filter(pk=zone_id).exists():
                total_z = Station.objects.filter(zone_id=zone_id).count()
                entered_z = WorkRecordStationCount.objects.filter(
                    work_record=work_record,
                    station__zone_id=zone_id,
                ).count()
                summary_zone = {"toplam": total_z, "girilen": entered_z, "kalan": total_z - entered_z}

        facilities = Facility.objects.select_related("customer").order_by("customer__kod", "kod")[:500]
        zones = list(selected_facility.bolgeler.order_by("kod")) if selected_facility else []

        context = {
            **self.admin_site.each_context(request),
            "title": f"İstasyon sayımı (toplu liste) — {work_record}",
            "work_record": work_record,
            "locked": locked,
            "opts": WorkRecord._meta,
            "default_facility": default_facility,
            "selected_facility": selected_facility,
            "selected_zone_id": zone_id,
            "summary_facility": summary_facility,
            "summary_zone": summary_zone,
            "bulk_stations": bulk_stations,
            "facilities": facilities,
            "zones": zones,
            "istasyon_sayim_toplu_url": reverse("admin:core_workrecord_istasyon_sayim_toplu", args=[work_record.pk]),
            "istasyon_sayim_url": reverse("admin:core_workrecord_istasyon_sayim", args=[work_record.pk]),
        }
        return render(request, "admin/core/workrecord/istasyon_sayim_toplu.html", context)

    def istasyon_sayim_link(self, obj):
        if obj is None or not obj.pk:
            return "—"
        url = reverse("admin:core_workrecord_istasyon_sayim", args=[obj.pk])
        return format_html(
            '<a href="{}" class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md '
            'bg-primary-600 text-white hover:bg-primary-700 focus:outline-none focus:ring-2 '
            'focus:ring-offset-2 focus:ring-primary-500 no-underline">İstasyon sayımı</a>',
            url,
        )

    istasyon_sayim_link.short_description = "İstasyon sayımı"


@admin.register(TalepTipi)
class TalepTipiAdmin(ModelAdmin):
    list_display = ("ad", "sira", "created_at")
    list_editable = ("sira",)
    ordering = ("sira", "ad")
    search_fields = ("ad",)


@admin.register(Talep)
class TalepAdmin(ModelAdmin):
    form = TalepAdminForm
    list_display = (
        "tarih", "tip", "durum", "customer", "facility",
        "planlanan_tarih", "planlanan_ekip",
        "iliski_talep",
        "kapandi_mi", "kapatilan_is_kaydi_link", "created_at",
    )
    list_filter = ("tip", "durum", "tarih", "customer", "planlanan_ekip", "created_at")
    search_fields = ("aciklama", "customer__kod", "customer__firma_ismi")
    autocomplete_fields = ["customer", "facility", "tip", "planlanan_ekip", "iliski_talep"]
    date_hierarchy = "tarih"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if "/autocomplete/" in request.path:
            qs = qs.exclude(durum="yapildi")
        return qs

    def kapandi_mi(self, obj):
        from django.core.exceptions import ObjectDoesNotExist
        try:
            obj.kapatilan_is_kaydi
            return "Evet"
        except ObjectDoesNotExist:
            return "Hayır"

    kapandi_mi.short_description = "Kapatıldı"

    def kapatilan_is_kaydi_link(self, obj):
        from django.core.exceptions import ObjectDoesNotExist
        try:
            wr = obj.kapatilan_is_kaydi
            url = reverse("admin:core_workrecord_change", args=[wr.pk])
            return format_html(
                '<a href="{}" class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md '
                'bg-primary-600 text-white hover:bg-primary-700 focus:outline-none focus:ring-2 '
                'focus:ring-offset-2 focus:ring-primary-500 no-underline">{}</a>',
                url, str(wr),
            )
        except ObjectDoesNotExist:
            return "—"

    kapatilan_is_kaydi_link.short_description = "Kapatılan iş kaydı"


@admin.register(WorkRecordStationCount)
class WorkRecordStationCountAdmin(ModelAdmin):
    list_display = ("work_record", "station", "tuketim_var", "created_at")
    list_filter = ("work_record__tarih", "work_record")
    search_fields = ("station__benzersiz_kod",)
    autocomplete_fields = ["work_record", "station"]


@admin.register(FaaliyetRaporu)
class FaaliyetRaporuAdmin(ModelAdmin):
    list_display = ("musteri_kod", "is_kaydi_kod", "rapor_tarihi", "rapor_olusturuldu", "pdf_link", "work_record", "created_at")
    list_filter = ("rapor_olusturuldu", "rapor_tarihi")
    search_fields = ("musteri_kod", "is_kaydi_kod")
    readonly_fields = ("work_record", "musteri_kod", "is_kaydi_kod", "rapor_tarihi", "rapor_olusturuldu", "created_at")

    def has_add_permission(self, request):
        return False  # Raporlar iş kaydından oluşturulur

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def pdf_link(self, obj):
        if not obj or not obj.pdf:
            return "—"
        url = obj.pdf.url if hasattr(obj.pdf, "url") else ""
        if not url:
            return "✓"
        return format_html('<a href="{}" target="_blank" rel="noopener">PDF indir</a>', url)

    pdf_link.short_description = "PDF"


@admin.register(BagimsizTespit)
class BagimsizTespitAdmin(ModelAdmin):
    list_display = (
        "tarih",
        "firma",
        "tesis",
        "yer_aciklamasi_short",
        "raporlandi",
        "created_at",
    )
    list_filter = ("tarih", "firma", "raporlandi", "created_at")
    search_fields = ("yer_aciklamasi", "gozlem_aciklamasi", "oneriler", "firma__kod", "firma__firma_ismi")
    autocomplete_fields = ["firma", "tesis"]
    date_hierarchy = "tarih"
    actions = ["rapor_olustur"]
    fieldsets = (
        (None, {
            "fields": ("tarih", "firma", "tesis", "raporlandi"),
        }),
        ("Açıklamalar", {
            "fields": ("yer_aciklamasi", "gozlem_aciklamasi", "oneriler"),
        }),
        ("Görseller", {
            "fields": ("gorsel1", "gorsel2", "gorsel3"),
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "tesis":
            object_id = getattr(request.resolver_match, "kwargs", {}).get("object_id")
            if object_id:
                try:
                    obj = self.get_object(request, object_id)
                    if obj and obj.firma_id:
                        kwargs["queryset"] = Facility.objects.filter(customer_id=obj.firma_id).order_by("kod")
                except Exception:
                    pass
            return super().formfield_for_foreignkey(db_field, request, **kwargs)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def yer_aciklamasi_short(self, obj):
        if obj.yer_aciklamasi:
            return (obj.yer_aciklamasi[:60] + "…") if len(obj.yer_aciklamasi) > 60 else obj.yer_aciklamasi
        return "—"

    yer_aciklamasi_short.short_description = "Yer açıklaması"

    @admin.action(description="Seçili kayıtlardan rapor oluştur (PDF)")
    def rapor_olustur(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, "En az bir kayıt seçin.", level=messages.WARNING)
            return
        try:
            pdf_bytes = generate_bagimsiz_tespit_raporu_pdf(queryset)
        except Exception as e:
            self.message_user(request, f"PDF oluşturulamadı: {e}", level=messages.ERROR)
            return
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="bagimsiz-tespitler-raporu.pdf"'
        return response


# Kullanıcı admin: profil fotoğrafı (avatar) inline + kare kırpma
class CustomUserAdmin(AuthUserAdmin):
    inlines = [UserProfileInline]

    class Media:
        css = {"all": ("https://cdn.jsdelivr.net/npm/cropperjs@1.6.2/dist/cropper.min.css",)}
        js = (
            "https://cdn.jsdelivr.net/npm/cropperjs@1.6.2/dist/cropper.min.js",
            "core/js/image_crop.js",
        )


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
