import json
from json import JSONDecodeError

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import Event, Registration


def read_json(request):
    if request.content_type != "application/json":
        return None, JsonResponse(
            {"error": "Send the request as application/json."}, status=415
        )
    try:
        payload = json.loads(request.body)
    except (JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"error": "The request body must be valid JSON."}, status=400)
    if not isinstance(payload, dict):
        return None, JsonResponse({"error": "The JSON body must be an object."}, status=400)
    return payload, None


def require_authenticated(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication is required."}, status=401)
    return None


def serialize_event(event):
    registered = event.registrations.count()
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "starts_at": event.starts_at.isoformat(),
        "location": event.location,
        "capacity": event.capacity,
        "registered_count": registered,
        "spots_remaining": max(event.capacity - registered, 0),
    }


@require_GET
def csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})


@require_POST
def signup(request):
    payload, error = read_json(request)
    if error:
        return error

    username = payload.get("username")
    password = payload.get("password")
    if not isinstance(username, str) or not username.strip():
        return JsonResponse({"error": "A username is required."}, status=400)
    if not isinstance(password, str) or not password:
        return JsonResponse({"error": "A password is required."}, status=400)

    username = username.strip()
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({"error": "That username is already registered."}, status=409)

    try:
        validate_password(password, user=User(username=username))
        user = User.objects.create_user(username=username, password=password)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=400)
    except IntegrityError:
        return JsonResponse({"error": "That username is already registered."}, status=409)

    return JsonResponse({"id": user.id, "username": user.username}, status=201)


@require_POST
def login(request):
    payload, error = read_json(request)
    if error:
        return error
    username = payload.get("username")
    password = payload.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return JsonResponse({"error": "Username and password are required."}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"error": "Invalid username or password."}, status=401)
    auth_login(request, user)
    return JsonResponse({"id": user.id, "username": user.username})


@require_POST
def logout(request):
    authentication_error = require_authenticated(request)
    if authentication_error:
        return authentication_error
    auth_logout(request)
    return JsonResponse({"message": "Logged out."})


@require_GET
def current_user(request):
    authentication_error = require_authenticated(request)
    if authentication_error:
        return authentication_error
    return JsonResponse({"id": request.user.id, "username": request.user.username})


@require_GET
def event_list(request):
    events = Event.objects.filter(starts_at__gte=timezone.now())
    search = request.GET.get("search", "").strip()
    if search:
        events = events.filter(title__icontains=search)
    return JsonResponse({"events": [serialize_event(event) for event in events]})


@require_GET
def event_detail(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    return JsonResponse(serialize_event(event))


@require_http_methods(["GET", "POST"])
def registration_list_create(request):
    authentication_error = require_authenticated(request)
    if authentication_error:
        return authentication_error
    if request.method == "POST":
        return registration_create(request)

    registrations = Registration.objects.filter(user=request.user).select_related("event")
    return JsonResponse(
        {
            "registrations": [
                {
                    "id": registration.id,
                    "event": serialize_event(registration.event),
                    "created_at": registration.created_at.isoformat(),
                }
                for registration in registrations
            ]
        }
    )


@require_POST
def registration_create(request):
    authentication_error = require_authenticated(request)
    if authentication_error:
        return authentication_error

    payload, error = read_json(request)
    if error:
        return error
    event_id = payload.get("event_id")
    if isinstance(event_id, bool) or not isinstance(event_id, int) or event_id < 1:
        return JsonResponse({"error": "A positive integer event_id is required."}, status=400)

    try:
        with transaction.atomic():
            event = Event.objects.select_for_update().get(pk=event_id)
            if event.starts_at < timezone.now():
                return JsonResponse({"error": "This event has already started."}, status=409)
            if Registration.objects.filter(user=request.user, event=event).exists():
                return JsonResponse({"error": "You are already registered for this event."}, status=409)
            if event.registrations.count() >= event.capacity:
                return JsonResponse({"error": "This event is full."}, status=409)
            registration = Registration.objects.create(user=request.user, event=event)
    except Event.DoesNotExist:
        return JsonResponse({"error": "Event not found."}, status=404)
    except IntegrityError:
        return JsonResponse({"error": "You are already registered for this event."}, status=409)

    return JsonResponse(
        {
            "id": registration.id,
            "event": serialize_event(event),
            "created_at": registration.created_at.isoformat(),
        },
        status=201,
    )


@require_POST
def registration_cancel(request, registration_id):
    authentication_error = require_authenticated(request)
    if authentication_error:
        return authentication_error
    registration = get_object_or_404(
        Registration, pk=registration_id, user=request.user
    )
    registration.delete()
    return JsonResponse({"message": "Registration cancelled."})
