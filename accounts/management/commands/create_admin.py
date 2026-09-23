import getpass

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = (
        "Provision a platform administrator account. Administrator accounts "
        "cannot be created through public sign-up."
    )

    def add_arguments(self, parser):
        parser.add_argument("--email", help="Administrator email address.")
        parser.add_argument("--display-name", default="Administrator")
        parser.add_argument("--handle", default=None)
        parser.add_argument(
            "--password",
            help="Password (omit to be prompted; avoid on shared machines).",
        )

    def handle(self, *args, **options):
        email = (options["email"] or input("Email: ")).strip().lower()
        if not email:
            raise CommandError("An email address is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError(f"An account with email {email} already exists.")

        password = options["password"]
        if not password:
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Password (again): "):
                raise CommandError("Passwords do not match.")

        candidate = User(email=email, display_name=options["display_name"])
        try:
            password_validation.validate_password(password, candidate)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages))

        user = User.objects.create_admin(
            email=email,
            password=password,
            display_name=options["display_name"],
            handle=options["handle"],
        )
        self.stdout.write(self.style.SUCCESS(f"Administrator account created for {user.email}."))
