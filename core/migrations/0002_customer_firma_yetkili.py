# Generated manually: ad_soyad -> firma_ismi, yetkili_ad_soyad eklendi, telefon opsiyonel

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='customer',
            old_name='ad_soyad',
            new_name='firma_ismi',
        ),
        migrations.AlterField(
            model_name='customer',
            name='firma_ismi',
            field=models.CharField(max_length=200, verbose_name='Firma ismi'),
        ),
        migrations.AddField(
            model_name='customer',
            name='yetkili_ad_soyad',
            field=models.CharField(blank=True, max_length=200, verbose_name='Yetkili adı soyadı'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='telefon',
            field=models.CharField(blank=True, max_length=50, verbose_name='Telefon'),
        ),
    ]
