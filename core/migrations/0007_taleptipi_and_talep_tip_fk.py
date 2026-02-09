# Generated manually for Talep tip -> TalepTipi FK

from django.db import migrations, models
import django.db.models.deletion


def create_talep_tipleri_and_migrate_tip(apps, schema_editor):
    TalepTipi = apps.get_model("core", "TalepTipi")
    Talep = apps.get_model("core", "Talep")

    # Varsayılan tipler (eskisiyle uyumlu)
    tip_sikayet = TalepTipi.objects.create(ad="Şikayet", sira=1)
    tip_yapilacak = TalepTipi.objects.create(ad="Yapılacak", sira=2)

    # Eski tip (CharField) değerine göre yeni tip_fk ataması
    for talep in Talep.objects.all():
        if talep.tip == "sikayet":
            talep.tip_new_id = tip_sikayet.pk
        elif talep.tip == "yapilacak":
            talep.tip_new_id = tip_yapilacak.pk
        else:
            talep.tip_new_id = tip_sikayet.pk
        talep.save(update_fields=["tip_new_id"])


def reverse_migrate_tip(apps, schema_editor):
    TalepTipi = apps.get_model("core", "TalepTipi")
    Talep = apps.get_model("core", "Talep")

    sikayet = TalepTipi.objects.filter(ad="Şikayet").first()
    yapilacak = TalepTipi.objects.filter(ad="Yapılacak").first()
    for talep in Talep.objects.all():
        if talep.tip_new_id == sikayet.pk if sikayet else None:
            talep.tip = "sikayet"
        elif talep.tip_new_id == yapilacak.pk if yapilacak else None:
            talep.tip = "yapilacak"
        else:
            talep.tip = "sikayet"
        talep.save(update_fields=["tip"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_station_kod_from_benzersiz"),
    ]

    operations = [
        migrations.CreateModel(
            name="TalepTipi",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ad", models.CharField(max_length=100, verbose_name="Ad")),
                ("sira", models.PositiveSmallIntegerField(default=0, help_text="Liste sıralaması", verbose_name="Sıra")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")),
            ],
            options={
                "verbose_name": "Talep tipi",
                "verbose_name_plural": "Talep tipleri",
                "ordering": ["sira", "ad"],
            },
        ),
        migrations.AddField(
            model_name="talep",
            name="tip_new",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="core.taleptipi",
                verbose_name="Tip",
            ),
        ),
        migrations.RunPython(create_talep_tipleri_and_migrate_tip, reverse_migrate_tip),
        migrations.RemoveField(
            model_name="talep",
            name="tip",
        ),
        migrations.RenameField(
            model_name="talep",
            old_name="tip_new",
            new_name="tip",
        ),
        migrations.AlterField(
            model_name="talep",
            name="tip",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="talepler",
                to="core.taleptipi",
                verbose_name="Tip",
            ),
        ),
    ]
