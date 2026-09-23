from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

from .decorators import role_required
from .forms import (
    CaseInsensitivePasswordResetForm,
    EmailAuthenticationForm,
    EventHolderSignUpForm,
    OrganizerProfileForm,
    ProfileForm,
    UserSignUpForm,
)
from .models import OrganizerProfile, User


def _signup(request, form_class, template_name):
    if request.user.is_authenticated:
        return redirect("accounts:post_login")
    form = form_class(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="accounts.backends.EmailBackend")
        messages.success(request, f"Welcome to NYC Event Explorer, {user.display_name}!")
        return redirect("accounts:post_login")
    return render(request, template_name, {"form": form})


def signup_choice(request):
    if request.user.is_authenticated:
        return redirect("accounts:post_login")
    return render(request, "accounts/signup_choice.html")


def signup_user(request):
    return _signup(request, UserSignUpForm, "accounts/signup_user.html")


def signup_event_holder(request):
    return _signup(request, EventHolderSignUpForm, "accounts/signup_event_holder.html")


class LoginView(auth_views.LoginView):
    form_class = EmailAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


@login_required
def post_login(request):
    """Send each role to its landing page after logging in or signing up."""
    user = request.user
    if user.is_platform_admin:
        return redirect("admin:index")
    if user.is_event_holder:
        return redirect("accounts:organizer_dashboard")
    return redirect("accounts:profile")


@login_required
def profile(request):
    return render(request, "accounts/profile.html", {"profile_user": request.user})


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile_edit.html", {"form": form})


def public_profile(request, handle):
    profile_user = get_object_or_404(
        User.objects.select_related("organizer_profile"),
        handle__iexact=handle,
        is_active=True,
    )
    return render(request, "accounts/public_profile.html", {"profile_user": profile_user})


@role_required(User.Role.EVENT_HOLDER)
def organizer_dashboard(request):
    organizer, _ = OrganizerProfile.objects.get_or_create(
        user=request.user,
        defaults={"organization_name": request.user.display_name},
    )
    return render(request, "accounts/organizer_dashboard.html", {"organizer": organizer})


@role_required(User.Role.EVENT_HOLDER)
def organizer_profile_edit(request):
    organizer, _ = OrganizerProfile.objects.get_or_create(
        user=request.user,
        defaults={"organization_name": request.user.display_name},
    )
    form = OrganizerProfileForm(request.POST or None, instance=organizer)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your organizer profile has been updated.")
        return redirect("accounts:organizer_dashboard")
    return render(request, "accounts/organizer_profile_edit.html", {"form": form})


class PasswordResetView(auth_views.PasswordResetView):
    form_class = CaseInsensitivePasswordResetForm
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/emails/password_reset_email.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed.")
        return super().form_valid(form)
