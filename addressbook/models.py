from django.db import models


class ContactCategory(models.Model):
    """İletişim kategorisi: Yetkili, Muhasebe, Tesis Sorumlusu vb."""
    ad = models.CharField("Kategori adı", max_length=100)
    sira = models.PositiveSmallIntegerField("Sıra", default=0, help_text="Liste sıralaması")
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "İletişim kategorisi"
        verbose_name_plural = "İletişim kategorileri"
        ordering = ["sira", "ad"]

    def __str__(self):
        return self.ad


class Contact(models.Model):
    """
    İletişim kaydı. Müşteri veya tesis altında tanımlanır.
    Müşteri düzeyinde: customer dolu, facility boş.
    Tesis düzeyinde: facility dolu, customer boş (müşteri facility.customer ile bulunur).
    """
    category = models.ForeignKey(
        ContactCategory,
        on_delete=models.PROTECT,
        related_name="contacts",
        verbose_name="Kategori",
    )
    customer = models.ForeignKey(
        "core.Customer",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="contacts",
        verbose_name="Müşteri",
    )
    facility = models.ForeignKey(
        "core.Facility",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="contacts",
        verbose_name="Tesis",
    )
    ad_soyad = models.CharField("Adı soyadı", max_length=200)
    telefon = models.CharField("Telefon", max_length=50, blank=True)
    email = models.EmailField("E-posta", blank=True)
    not_alani = models.CharField("Not", max_length=200, blank=True)
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "İletişim"
        verbose_name_plural = "İletişimler"
        ordering = ["category", "ad_soyad"]

    def __str__(self):
        return f"{self.category.ad}: {self.ad_soyad}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.customer_id and not self.facility_id:
            raise ValidationError("Müşteri veya tesis seçilmelidir.")
        if self.customer_id and self.facility_id and self.facility.customer_id != self.customer_id:
            raise ValidationError("Tesis, seçilen müşteriye ait olmalıdır.")

    def save(self, *args, **kwargs):
        if self.facility_id and not self.customer_id:
            self.customer_id = self.facility.customer_id
        super().save(*args, **kwargs)
