from django.urls import path

from . import views


urlpatterns = [
    path("csrf/", views.csrf_token, name="csrf-token"),
    path("auth/signup/", views.signup, name="signup"),
    path("auth/login/", views.login, name="login"),
    path("auth/logout/", views.logout, name="logout"),
    path("auth/me/", views.current_user, name="current-user"),
    path("events/", views.event_list, name="event-list"),
    path("events/<int:event_id>/", views.event_detail, name="event-detail"),
    path("registrations/", views.registration_list_create, name="registration-list"),
    path(
        "registrations/<int:registration_id>/",
        views.registration_cancel,
        name="registration-cancel",
    ),
]
