from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm

from .models import OrganizerProfile, User, handle_validator


def _clean_unique_handle(handle, exclude_pk=None):
    handle = (handle or "").strip().lstrip("@").lower()
    handle_validator(handle)
    qs = User.objects.filter(handle__iexact=handle)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise forms.ValidationError("That handle is already taken.")
    return handle


class BaseSignUpForm(forms.ModelForm):
    """Shared email + password sign-up logic for users and event holders."""

    role = User.Role.USER

    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ["email", "display_name", "handle"]
        labels = {"handle": "Handle"}
        help_texts = {
            "handle": "3-30 letters, numbers or underscores. Others can find you by @handle.",
        }
        widgets = {"email": forms.EmailInput(attrs={"autocomplete": "email"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["handle"].required = True
        self.fields["display_name"].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_handle(self):
        return _clean_unique_handle(self.cleaned_data.get("handle"))

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("The two passwords do not match.")
        return p2

    def _post_clean(self):
        super()._post_clean()
        password = self.cleaned_data.get("password2")
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error("password2", error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.role
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserSignUpForm(BaseSignUpForm):
    role = User.Role.USER


class EventHolderSignUpForm(BaseSignUpForm):
    role = User.Role.EVENT_HOLDER

    organization_name = forms.CharField(max_length=120, label="Organization name")
    website = forms.URLField(required=False, assume_scheme="https")

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            OrganizerProfile.objects.create(
                user=user,
                organization_name=self.cleaned_data["organization_name"],
                website=self.cleaned_data.get("website", ""),
                contact_email=user.email,
            )
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )

    error_messages = {
        "invalid_login": "Please enter a correct email and password.",
        "inactive": "This account has been deactivated.",
    }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["display_name", "handle", "bio", "home_borough"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["display_name"].required = True
        # Admins may leave the handle blank; everyone else must have one.
        self.fields["handle"].required = not self.instance.is_platform_admin

    def clean_handle(self):
        handle = self.cleaned_data.get("handle")
        if not handle and self.instance.is_platform_admin:
            return None
        return _clean_unique_handle(handle, exclude_pk=self.instance.pk)


class OrganizerProfileForm(forms.ModelForm):
    class Meta:
        model = OrganizerProfile
        fields = ["organization_name", "description", "website", "contact_email", "phone"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["website"].assume_scheme = "https"


class CaseInsensitivePasswordResetForm(PasswordResetForm):
    """Match the account regardless of how the email's case was typed."""

    def get_users(self, email):
        return (
            u
            for u in User.objects.filter(email__iexact=email.strip(), is_active=True)
            if u.has_usable_password()
        )
