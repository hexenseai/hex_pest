from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"
    verbose_name = "Çekirdek"

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.db.models.signals import post_save

        from .models import UserProfile

        User = get_user_model()

        def create_user_profile(sender, instance, created, **kwargs):
            if created:
                UserProfile.objects.get_or_create(user=instance)

        post_save.connect(create_user_profile, sender=User)
