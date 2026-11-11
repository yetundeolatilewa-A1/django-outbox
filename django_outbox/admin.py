from django.contrib import admin

from .models import Delivery, Endpoint, Message


@admin.register(Endpoint)
class EndpointAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "url")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type", "created_at")
    search_fields = ("event_type", "id")
    date_hierarchy = "created_at"


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("message", "endpoint", "status", "attempts", "last_status_code", "next_attempt_at")
    list_filter = ("status", "endpoint")
    actions = ["retry_selected"]

    @admin.action(description="Retry selected deliveries (reset attempts)")
    def retry_selected(self, request, queryset):
        from django.utils import timezone

        updated = queryset.exclude(status=Delivery.Status.DELIVERED).update(
            status=Delivery.Status.PENDING, attempts=0, next_attempt_at=timezone.now()
        )
        self.message_user(request, f"{updated} deliveries queued for retry.")
