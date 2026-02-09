from django import forms
from django.forms import inlineformset_factory

from core.models import Customer, Facility
from .models import ContactCategory, Contact


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ("category", "ad_soyad", "telefon", "email", "not_alani")
        widgets = {
            "category": forms.Select(attrs={"class": "w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"}),
            "ad_soyad": forms.TextInput(attrs={"class": "w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"}),
            "telefon": forms.TextInput(attrs={"class": "w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"}),
            "email": forms.EmailInput(attrs={"class": "w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"}),
            "not_alani": forms.TextInput(attrs={"class": "w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"}),
        }


CustomerContactFormSet = inlineformset_factory(
    Customer,
    Contact,
    form=ContactForm,
    extra=1,
    can_delete=True,
    min_num=0,
    fk_name="customer",
    exclude=("facility",),
)

FacilityContactFormSet = inlineformset_factory(
    Facility,
    Contact,
    form=ContactForm,
    extra=1,
    can_delete=True,
    min_num=0,
    fk_name="facility",
    exclude=("customer",),
)
