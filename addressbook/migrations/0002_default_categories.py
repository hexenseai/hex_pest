from django.db import migrations


def create_default_categories(apps, schema_editor):
    ContactCategory = apps.get_model("addressbook", "ContactCategory")
    for i, ad in enumerate(["Yetkili", "Muhasebe", "Tesis Sorumlusu"], start=1):
        ContactCategory.objects.get_or_create(ad=ad, defaults={"sira": i})


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("addressbook", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_categories, noop),
    ]
