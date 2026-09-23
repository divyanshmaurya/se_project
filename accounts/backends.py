from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Authenticate with an email address (case-insensitive) and password."""

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        User = get_user_model()
        email = email or username or kwargs.get(User.USERNAME_FIELD)
        if not email or password is None:
            return None
        try:
            user = User.objects.get(email__iexact=email.strip())
        except User.DoesNotExist:
            # Run the hasher anyway to reduce timing differences.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
