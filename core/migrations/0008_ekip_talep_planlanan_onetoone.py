# Generated manually: Ekip model, Talep planlanan alanları, Talep–WorkRecord OneToOne

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def ensure_unique_kapatilan_is_kaydi(apps, schema_editor):
    """Aynı iş kaydına bağlı birden fazla talep varsa sadece birini tut, diğerlerini null yap."""
    Talep = apps.get_model("core", "Talep")
    seen_work_ids = set()
    for talep in Talep.objects.filter(kapatilan_is_kaydi_id__isnull=False).order_by("pk"):
        wid = talep.kapatilan_is_kaydi_id
        if wid in seen_work_ids:
            talep.kapatilan_is_kaydi_id = None
            talep.save(update_fields=["kapatilan_is_kaydi_id"])
        else:
            seen_work_ids.add(wid)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_taleptipi_and_talep_tip_fk"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Ekip",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kod", models.CharField(max_length=20, unique=True, verbose_name="Ekip kodu")),
                ("kisi_sayisi", models.PositiveSmallIntegerField(default=0, verbose_name="Ekip kişi sayısı")),
                ("uyeler", models.TextField(blank=True, help_text="Üye isimleri veya not (serbest metin)", verbose_name="Ekip üyeleri")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")),
                ("ekip_lideri", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lideri_oldugu_ekipler", to=settings.AUTH_USER_MODEL, verbose_name="Ekip lideri")),
            ],
            options={
                "verbose_name": "Ekip",
                "verbose_name_plural": "Ekipler",
                "ordering": ["kod"],
            },
        ),
        migrations.AddField(
            model_name="talep",
            name="planlanan_tarih",
            field=models.DateField(blank=True, null=True, verbose_name="Planlanan tarih"),
        ),
        migrations.AddField(
            model_name="talep",
            name="planlanan_ekip",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="planlanan_talepler",
                to="core.ekip",
                verbose_name="Planlanan ekip",
            ),
        ),
        migrations.RunPython(ensure_unique_kapatilan_is_kaydi, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="talep",
            name="kapatilan_is_kaydi",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="kapatilan_talep",
                to="core.workrecord",
                verbose_name="Kapatılan iş kaydı",
            ),
        ),
    ]
