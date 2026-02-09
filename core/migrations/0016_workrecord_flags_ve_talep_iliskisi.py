# Migration: İş kaydına iki flag + ilişki WorkRecord üzerine (kapatilan_talep)

import django.db.models.deletion
from django.db import migrations, models


def talep_iliskisini_workrecorda_taşı(apps, schema_editor):
    """Eski: Talep.kapatilan_is_kaydi_id -> WorkRecord. Yeni: WorkRecord.kapatilan_talep_id -> Talep."""
    Talep = apps.get_model("core", "Talep")
    WorkRecord = apps.get_model("core", "WorkRecord")
    for talep in Talep.objects.filter(kapatilan_is_kaydi_id__isnull=False):
        wr = WorkRecord.objects.get(pk=talep.kapatilan_is_kaydi_id)
        wr.kapatilan_talep_id = talep.pk
        wr.save(update_fields=["kapatilan_talep_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_tespit_tanimlari_ve_workrecord_tespit"),
    ]

    operations = [
        migrations.AddField(
            model_name="workrecord",
            name="gozlem_ziyareti_yapilmali",
            field=models.BooleanField(default=False, verbose_name="Gözlem ziyareti yapılmalı mı?"),
        ),
        migrations.AddField(
            model_name="workrecord",
            name="sozlesme_disi_islem_var",
            field=models.BooleanField(default=False, verbose_name="Sözleşme dışı işlem var mı?"),
        ),
        migrations.AddField(
            model_name="workrecord",
            name="kapatilan_talep",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="kapatilan_is_kaydi",
                to="core.talep",
                verbose_name="Kapatılan talep",
            ),
        ),
        migrations.RunPython(talep_iliskisini_workrecorda_taşı, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="talep",
            name="kapatilan_is_kaydi",
        ),
    ]
