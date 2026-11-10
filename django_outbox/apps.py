from django.apps import AppConfig


class OutboxConfig(AppConfig):
    name = "django_outbox"
    verbose_name = "Outbox"
    default_auto_field = "django.db.models.BigAutoField"
