from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils import timezone

handle_validator = RegexValidator(
    regex=r"^[a-zA-Z0-9_]{3,30}$",
    message="Handles must be 3-30 characters: letters, numbers and underscores only.",
)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).lower()
        if extra_fields.get("handle"):
            extra_fields["handle"] = extra_fields["handle"].lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.USER)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        if extra_fields["role"] == User.Role.ADMIN:
            raise ValueError("Use create_admin() to provision administrator accounts.")
        return self._create_user(email, password, **extra_fields)

    def create_event_holder(self, email, password=None, **extra_fields):
        extra_fields["role"] = User.Role.EVENT_HOLDER
        return self.create_user(email, password, **extra_fields)

    def create_admin(self, email, password=None, **extra_fields):
        """Administrator accounts can only be created through this method,
        which is called from the Django admin or the ``create_admin``
        management command - never from public sign-up."""
        extra_fields["role"] = User.Role.ADMIN
        extra_fields.setdefault("display_name", "Administrator")
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        return self.create_admin(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        USER = "user", "User"
        EVENT_HOLDER = "event_holder", "Event Holder"
        ADMIN = "admin", "Administrator"

    email = models.EmailField("email address", unique=True)
    display_name = models.CharField(max_length=60)
    handle = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        validators=[handle_validator],
        help_text="Unique public handle, e.g. @nyc_explorer.",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    bio = models.TextField(max_length=500, blank=True)
    home_borough = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ("manhattan", "Manhattan"),
            ("brooklyn", "Brooklyn"),
            ("queens", "Queens"),
            ("bronx", "The Bronx"),
            ("staten_island", "Staten Island"),
        ],
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_email_ci"),
            models.UniqueConstraint(Lower("handle"), name="unique_handle_ci"),
        ]

    def __str__(self):
        return f"{self.display_name} <{self.email}>"

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email).lower()
        if self.handle:
            self.handle = self.handle.lower()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        if self.handle:
            self.handle = self.handle.lower()
        else:
            self.handle = None
        # Administrator access follows the role: admins get full access to
        # the admin site, nobody else can reach it.
        if self.role == self.Role.ADMIN:
            self.is_staff = True
            self.is_superuser = True
        else:
            self.is_staff = False
            self.is_superuser = False
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.display_name

    def get_short_name(self):
        return self.display_name

    def get_absolute_url(self):
        if self.handle:
            return reverse("accounts:public_profile", args=[self.handle])
        return reverse("accounts:profile")

    @property
    def is_regular_user(self):
        return self.role == self.Role.USER

    @property
    def is_event_holder(self):
        return self.role == self.Role.EVENT_HOLDER

    @property
    def is_platform_admin(self):
        return self.role == self.Role.ADMIN


class OrganizerProfile(models.Model):
    """Extra public information shown for Event Holder (business) accounts."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="organizer_profile"
    )
    organization_name = models.CharField(max_length=120)
    description = models.TextField(max_length=2000, blank=True)
    website = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.organization_name
