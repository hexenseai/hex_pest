from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone

from .models import Customer, Facility, Zone, Station, Talep


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ("kod", "firma_ismi", "adres", "not_alani")
        widgets = {
            "kod": forms.TextInput(attrs={"class": "w-full rounded-md border border-gray-300 px-3 py-2"}),
            "firma_ismi": forms.TextInput(attrs={"class": "w-full rounded-md border border-gray-300 px-3 py-2"}),
            "adres": forms.Textarea(attrs={"class": "w-full rounded-md border border-gray-300 px-3 py-2", "rows": 2}),
            "not_alani": forms.Textarea(attrs={"class": "w-full rounded-md border border-gray-300 px-3 py-2", "rows": 2}),
        }


class FacilityForm(forms.ModelForm):
    """Tesis formu (liste sayfasındaki ekleme/düzenleme için; customer dahil)."""
    class Meta:
        model = Facility
        fields = ("customer", "kod", "ad", "adres", "not_alani")
        widgets = {
            "customer": forms.Select(attrs={"class": "w-full rounded-md border border-gray-300 px-3 py-2"}),
            "kod": forms.TextInput(attrs={"class": "w-full rounded-md border border-gray-300 px-3 py-2"}),
            "ad": forms.TextInput(attrs={"class": "w-full rounded-md border border-gray-300 px-3 py-2"}),
            "adres": forms.Textarea(attrs={"class": "w-full rounded-md border border-gray-300 px-3 py-2", "rows": 2}),
            "not_alani": forms.Textarea(attrs={"class": "w-full rounded-md border border-gray-300 px-3 py-2", "rows": 2}),
        }


class FacilityInlineForm(forms.ModelForm):
    """Müşteri altında inline tesis formset için (customer formdan kaldırıldı)."""
    class Meta:
        model = Facility
        fields = ("kod", "ad", "adres", "not_alani")
        widgets = {
            "kod": forms.TextInput(attrs={"class": "w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"}),
            "ad": forms.TextInput(attrs={"class": "w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"}),
            "adres": forms.Textarea(attrs={"class": "w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm", "rows": 1}),
            "not_alani": forms.TextInput(attrs={"class": "w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"}),
        }


class ZoneForm(forms.ModelForm):
    """Bölge ekleme (HTMX)."""
    class Meta:
        model = Zone
        fields = ("kod", "ad", "not_alani")
        widgets = {
            "kod": forms.TextInput(attrs={"class": "w-full rounded border border-gray-300 px-2 py-1.5 text-sm", "placeholder": "Kod"}),
            "ad": forms.TextInput(attrs={"class": "w-full rounded border border-gray-300 px-2 py-1.5 text-sm", "placeholder": "Ad"}),
            "not_alani": forms.TextInput(attrs={"class": "w-full rounded border border-gray-300 px-2 py-1.5 text-sm", "placeholder": "Not"}),
        }


class StationForm(forms.ModelForm):
    """İstasyon ekleme (HTMX)."""
    class Meta:
        model = Station
        fields = ("kod", "ad",)
        widgets = {
            "kod": forms.TextInput(attrs={"class": "w-full rounded border border-gray-300 px-2 py-1.5 text-sm", "placeholder": "Kod"}),
            "ad": forms.TextInput(attrs={"class": "w-full rounded border border-gray-300 px-2 py-1.5 text-sm", "placeholder": "İstasyon adı"}),
        }


FacilityFormSet = inlineformset_factory(
    Customer,
    Facility,
    form=FacilityInlineForm,
    extra=1,
    can_delete=True,
    min_num=0,
)


class TalepAdminForm(forms.ModelForm):
    """Admin talep formu: yeni kayıtta talep tarihi bugün ile dolar."""
    class Meta:
        model = Talep
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        if instance is None or not getattr(instance, "pk", None):
            kwargs.setdefault("initial", {})
            if "tarih" not in kwargs["initial"]:
                kwargs["initial"]["tarih"] = timezone.localdate()
        super().__init__(*args, **kwargs)
