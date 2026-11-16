# CodeAlpha Event Registration System

A Django and SQLite API for browsing events and managing user registrations. It includes capacity enforcement, per-user registration ownership, CSRF-protected session authentication, and a Django admin panel for event organizers.

## Requirements

- Python 3.10+

## Run locally

```bash
cd CodeAlpha_EventRegistration
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

The API is available at <http://127.0.0.1:8000/api/> and the organizer panel is at <http://127.0.0.1:8000/admin/>.

For deployment, set `DJANGO_SECRET_KEY` to a private random value, set `DJANGO_DEBUG=false`, and configure `DJANGO_ALLOWED_HOSTS`. Do not deploy with the local development key.

## Authentication and CSRF

The API uses Django session authentication. First call `GET /api/csrf/` and save both the `csrftoken` cookie and `csrfToken` response value. Send the cookie and an `X-CSRFToken` header with every `POST`, including signup and login. Keep the session cookie returned by login for later requests.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/csrf/` | Get a CSRF token |
| POST | `/api/auth/signup/` | Create an account with `username` and `password` |
| POST | `/api/auth/login/` | Start a session |
| POST | `/api/auth/logout/` | End the current session |
| GET | `/api/auth/me/` | Get the signed-in user |
| GET | `/api/events/` | List upcoming events; optional `?search=term` |
| GET | `/api/events/{id}/` | View event details |
| GET | `/api/registrations/` | View the signed-in user's registrations |
| POST | `/api/registrations/` | Register with `{"event_id": 1}` |
| POST | `/api/registrations/{id}/` | Cancel the signed-in user's registration |

Responses are JSON. Registrations are unique per user and event, capacity is checked before registration, and users can only cancel their own registrations. Events and registrations can be managed by authorized staff in Django admin.

## Tests

```bash
python manage.py test
```
