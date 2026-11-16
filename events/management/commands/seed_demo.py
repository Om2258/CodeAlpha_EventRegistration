from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import Event


class Command(BaseCommand):
    help = "Create or refresh three sample events for local API demos."

    def handle(self, *args, **options):
        now = timezone.now()
        samples = [
            {
                "title": "Backend Builders Meetup",
                "description": "A practical evening on APIs, databases, and dependable services.",
                "starts_at": now + timedelta(days=7),
                "location": "North Hall",
                "capacity": 40,
            },
            {
                "title": "Designing Better APIs",
                "description": "Hands-on patterns for clear, useful, and maintainable API design.",
                "starts_at": now + timedelta(days=14),
                "location": "Studio 2",
                "capacity": 24,
            },
            {
                "title": "Python Community Night",
                "description": "Short talks and conversation for Python developers of all levels.",
                "starts_at": now + timedelta(days=21),
                "location": "Riverside Room",
                "capacity": 60,
            },
        ]
        for sample in samples:
            Event.objects.update_or_create(
                title=sample["title"], defaults=sample
            )
        self.stdout.write(self.style.SUCCESS(f"Created or refreshed {len(samples)} demo events."))
