from django.conf import settings
from django.db import models
from django.db.models import Q


class Event(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField()
    starts_at = models.DateTimeField()
    location = models.CharField(max_length=200)
    capacity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(capacity__gte=1), name="event_capacity_at_least_one"
            )
        ]

    def __str__(self):
        return self.title


class Registration(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_registrations",
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="registrations"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event"], name="unique_registration_per_user_event"
            )
        ]

    def __str__(self):
        return f"{self.user} — {self.event}"
