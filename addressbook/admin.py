from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import ContactCategory, Contact


@admin.register(ContactCategory)
class ContactCategoryAdmin(ModelAdmin):
    list_display = ("ad", "sira", "created_at")
    list_editable = ("sira",)
    ordering = ("sira", "ad")
    search_fields = ("ad",)


@admin.register(Contact)
class ContactAdmin(ModelAdmin):
    list_display = ("ad_soyad", "category", "customer", "facility", "telefon", "email", "created_at")
    list_filter = ("category", "customer", "created_at")
    search_fields = ("ad_soyad", "telefon", "email", "customer__firma_ismi", "facility__ad")
    autocomplete_fields = ["customer", "facility"]
