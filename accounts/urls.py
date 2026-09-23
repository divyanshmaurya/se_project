from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup_choice, name="signup"),
    path("signup/user/", views.signup_user, name="signup_user"),
    path("signup/event-holder/", views.signup_event_holder, name="signup_event_holder"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("welcome/", views.post_login, name="post_login"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("organizer/", views.organizer_dashboard, name="organizer_dashboard"),
    path("organizer/edit/", views.organizer_profile_edit, name="organizer_profile_edit"),
    path("password/change/", views.PasswordChangeView.as_view(), name="password_change"),
    path("password/reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path(
        "password/reset/sent/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("u/<str:handle>/", views.public_profile, name="public_profile"),
]
