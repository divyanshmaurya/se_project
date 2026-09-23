from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import OrganizerProfile, User


class AdminCreateUserForm(AdminUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "display_name", "handle", "role")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class AdminChangeUserForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


class OrganizerProfileInline(admin.StackedInline):
    model = OrganizerProfile
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Administrators provision other administrator accounts here by
    creating a user with the "Administrator" role. The admin site is only
    reachable by administrators, so admin access stays restricted."""

    form = AdminChangeUserForm
    add_form = AdminCreateUserForm
    inlines = [OrganizerProfileInline]

    list_display = ("email", "display_name", "handle", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("email", "display_name", "handle")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login", "is_staff", "is_superuser")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("display_name", "handle", "bio", "home_borough")}),
        ("Role & access", {"fields": ("role", "is_active", "is_staff", "is_superuser")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "display_name",
                    "handle",
                    "role",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_inlines(self, request, obj):
        if obj is not None and obj.is_event_holder:
            return self.inlines
        return []


@admin.register(OrganizerProfile)
class OrganizerProfileAdmin(admin.ModelAdmin):
    list_display = ("organization_name", "user", "website", "updated_at")
    search_fields = ("organization_name", "user__email", "user__handle")
