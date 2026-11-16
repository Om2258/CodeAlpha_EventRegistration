from django.contrib import admin

from .models import Event, Registration


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "starts_at", "location", "capacity", "registration_count")
    list_filter = ("starts_at",)
    search_fields = ("title", "location")
    date_hierarchy = "starts_at"

    @admin.display(description="Registrations")
    def registration_count(self, event):
        return event.registrations.count()


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "created_at")
    list_filter = ("event", "created_at")
    search_fields = ("user__username", "event__title")
    readonly_fields = ("created_at",)
