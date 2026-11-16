import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.utils import timezone

from .models import Event, Registration


class EventRegistrationApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alex", password="Example-passphrase-47"
        )
        self.event = Event.objects.create(
            title="Backend Builders Meetup",
            description="A practical evening for backend developers.",
            starts_at=timezone.now() + timedelta(days=14),
            location="North Hall",
            capacity=2,
        )
        self.client.force_login(self.user)

    def json_request(self, method, path, data=None, client=None):
        return getattr(client or self.client, method)(
            path,
            data=json.dumps(data or {}),
            content_type="application/json",
        )

    def test_lists_upcoming_events_and_filters_by_title(self):
        response = self.client.get("/api/events/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["events"]), 1)
        self.assertEqual(response.json()["events"][0]["spots_remaining"], 2)

        filtered = self.client.get("/api/events/?search=builders")
        self.assertEqual(len(filtered.json()["events"]), 1)
        self.assertEqual(len(self.client.get("/api/events/?search=music").json()["events"]), 0)

    def test_event_details_and_missing_event(self):
        response = self.client.get(f"/api/events/{self.event.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], self.event.title)
        self.assertEqual(self.client.get("/api/events/99999/").status_code, 404)

    def test_users_can_register_list_and_cancel(self):
        response = self.json_request(
            "post", "/api/registrations/", {"event_id": self.event.id}
        )
        self.assertEqual(response.status_code, 201)
        registration_id = response.json()["id"]
        self.assertEqual(Registration.objects.count(), 1)

        listing = self.client.get("/api/registrations/")
        self.assertEqual(len(listing.json()["registrations"]), 1)
        self.assertEqual(listing.json()["registrations"][0]["event"]["id"], self.event.id)

        cancelled = self.client.post(f"/api/registrations/{registration_id}/")
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(Registration.objects.count(), 0)

    def test_duplicate_registration_is_rejected(self):
        first = self.json_request(
            "post", "/api/registrations/", {"event_id": self.event.id}
        )
        duplicate = self.json_request(
            "post", "/api/registrations/", {"event_id": self.event.id}
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 409)

    def test_event_capacity_is_enforced(self):
        self.event.capacity = 1
        self.event.save(update_fields=["capacity"])
        another_user = User.objects.create_user(
            username="sam", password="Example-passphrase-47"
        )
        self.assertEqual(
            self.json_request(
                "post", "/api/registrations/", {"event_id": self.event.id}
            ).status_code,
            201,
        )
        other_client = Client()
        other_client.force_login(another_user)
        full = self.json_request(
            "post",
            "/api/registrations/",
            {"event_id": self.event.id},
            client=other_client,
        )
        self.assertEqual(full.status_code, 409)
        self.assertEqual(full.json()["error"], "This event is full.")

    def test_users_cannot_cancel_other_users_registration(self):
        registration = Registration.objects.create(user=self.user, event=self.event)
        other_user = User.objects.create_user(
            username="sam", password="Example-passphrase-47"
        )
        other_client = Client()
        other_client.force_login(other_user)
        response = other_client.post(f"/api/registrations/{registration.id}/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Registration.objects.filter(pk=registration.id).exists())

    def test_registration_requires_authentication_and_valid_payload(self):
        anonymous = Client()
        self.assertEqual(anonymous.get("/api/registrations/").status_code, 401)
        response = self.json_request(
            "post", "/api/registrations/", {"event_id": "not-an-integer"}
        )
        self.assertEqual(response.status_code, 400)

    def test_signup_and_login_api(self):
        anonymous = Client()
        signup = self.json_request(
            "post",
            "/api/auth/signup/",
            {"username": "new-user", "password": "Strong-Passphrase-984"},
            client=anonymous,
        )
        self.assertEqual(signup.status_code, 201)

        login = self.json_request(
            "post",
            "/api/auth/login/",
            {"username": "new-user", "password": "Strong-Passphrase-984"},
            client=anonymous,
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(anonymous.get("/api/auth/me/").json()["username"], "new-user")

    def test_csrf_is_required_for_mutating_requests(self):
        client = Client(enforce_csrf_checks=True)
        response_without_token = self.json_request(
            "post",
            "/api/auth/signup/",
            {"username": "csrf-user", "password": "Strong-Passphrase-984"},
            client=client,
        )
        self.assertEqual(response_without_token.status_code, 403)

        token_response = client.get("/api/csrf/")
        token = token_response.json()["csrfToken"]
        response_with_token = client.post(
            "/api/auth/signup/",
            data=json.dumps(
                {"username": "csrf-user", "password": "Strong-Passphrase-984"}
            ),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response_with_token.status_code, 201)


class EventModelConstraintTests(TestCase):
    def test_capacity_must_be_positive(self):
        event = Event.objects.create(
            title="Invalid capacity",
            description="",
            starts_at=timezone.now() + timedelta(days=1),
            location="Hall",
            capacity=1,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Event.objects.filter(pk=event.pk).update(capacity=0)
