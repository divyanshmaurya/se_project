import re
from io import StringIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import OrganizerProfile

User = get_user_model()
PASSWORD = "Sup3r-secret-pass!"


def make_user(email="alice@example.com", handle="alice", **kwargs):
    kwargs.setdefault("display_name", "Alice")
    return User.objects.create_user(email=email, password=PASSWORD, handle=handle, **kwargs)


def make_event_holder(email="org@example.com", handle="brooklyn_arts"):
    user = User.objects.create_event_holder(
        email=email, password=PASSWORD, display_name="Brooklyn Arts", handle=handle
    )
    OrganizerProfile.objects.create(user=user, organization_name="Brooklyn Arts Co")
    return user


class UserSignUpTests(TestCase):
    url = reverse("accounts:signup_user")

    def data(self, **overrides):
        data = {
            "email": "New.User@Example.com",
            "display_name": "New User",
            "handle": "new_user",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        data.update(overrides)
        return data

    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(self.url, self.data())
        self.assertRedirects(response, reverse("accounts:post_login"), target_status_code=302)
        user = User.objects.get()
        self.assertEqual(user.email, "new.user@example.com")
        self.assertEqual(user.role, User.Role.USER)
        self.assertEqual(user.handle, "new_user")
        self.assertFalse(user.is_staff)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_email_rejected_case_insensitively(self):
        make_user(email="new.user@example.com", handle="other")
        response = self.client.post(self.url, self.data())
        self.assertContains(response, "An account with this email already exists.")
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_handle_rejected_case_insensitively(self):
        make_user(email="someone@example.com", handle="new_user")
        response = self.client.post(self.url, self.data(handle="NEW_User"))
        self.assertContains(response, "That handle is already taken.")

    def test_invalid_handle_rejected(self):
        response = self.client.post(self.url, self.data(handle="no spaces!"))
        self.assertContains(response, "Handles must be 3-30 characters")
        self.assertFalse(User.objects.exists())

    def test_leading_at_sign_is_stripped_from_handle(self):
        self.client.post(self.url, self.data(handle="@new_user"))
        self.assertEqual(User.objects.get().handle, "new_user")

    def test_password_mismatch_rejected(self):
        response = self.client.post(self.url, self.data(password2="different-pass-123"))
        self.assertContains(response, "The two passwords do not match.")

    def test_weak_password_rejected(self):
        response = self.client.post(self.url, self.data(password1="123", password2="123"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_role_cannot_be_escalated_via_post(self):
        self.client.post(self.url, self.data(role="admin", is_staff="on", is_superuser="on"))
        user = User.objects.get()
        self.assertEqual(user.role, User.Role.USER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)


class EventHolderSignUpTests(TestCase):
    def test_signup_creates_business_account_with_organizer_profile(self):
        response = self.client.post(
            reverse("accounts:signup_event_holder"),
            {
                "email": "hello@queensjazz.org",
                "display_name": "Queens Jazz",
                "handle": "queensjazz",
                "organization_name": "Queens Jazz Collective",
                "website": "queensjazz.org",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
            follow=True,
        )
        user = User.objects.get()
        self.assertEqual(user.role, User.Role.EVENT_HOLDER)
        self.assertEqual(user.organizer_profile.organization_name, "Queens Jazz Collective")
        self.assertEqual(user.organizer_profile.website, "https://queensjazz.org")
        self.assertRedirects(response, reverse("accounts:organizer_dashboard"))

    def test_organization_name_required(self):
        response = self.client.post(
            reverse("accounts:signup_event_holder"),
            {
                "email": "hello@queensjazz.org",
                "display_name": "Queens Jazz",
                "handle": "queensjazz",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())


class LoginTests(TestCase):
    def login(self, email, password=PASSWORD):
        return self.client.post(reverse("accounts:login"), {"username": email, "password": password})

    def test_user_logs_in_with_email_and_lands_on_profile(self):
        make_user()
        response = self.login("ALICE@example.com")
        self.assertRedirects(response, reverse("accounts:post_login"), fetch_redirect_response=False)
        response = self.client.get(reverse("accounts:post_login"))
        self.assertRedirects(response, reverse("accounts:profile"))

    def test_event_holder_lands_on_organizer_dashboard(self):
        make_event_holder()
        self.login("org@example.com")
        response = self.client.get(reverse("accounts:post_login"))
        self.assertRedirects(response, reverse("accounts:organizer_dashboard"))

    def test_admin_lands_on_admin_site(self):
        User.objects.create_admin(email="admin@example.com", password=PASSWORD)
        self.login("admin@example.com")
        response = self.client.get(reverse("accounts:post_login"))
        self.assertRedirects(response, reverse("admin:index"))

    def test_wrong_password_rejected(self):
        make_user()
        response = self.login("alice@example.com", "wrong-password")
        self.assertContains(response, "Please enter a correct email and password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_inactive_user_cannot_log_in(self):
        make_user(is_active=False)
        self.login("alice@example.com")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout(self):
        make_user()
        self.client.login(email="alice@example.com", password=PASSWORD)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)


class ProfileTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.login(email="alice@example.com", password=PASSWORD)

    def test_profile_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("accounts:profile"))
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={reverse('accounts:profile')}"
        )

    def test_edit_profile(self):
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "display_name": "Alice B",
                "handle": "alice_b",
                "bio": "Jazz and art fan",
                "home_borough": "brooklyn",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "Alice B")
        self.assertEqual(self.user.handle, "alice_b")
        self.assertEqual(self.user.home_borough, "brooklyn")

    def test_keeping_own_handle_is_allowed(self):
        response = self.client.post(
            reverse("accounts:profile_edit"), {"display_name": "Alice", "handle": "Alice"}
        )
        self.assertRedirects(response, reverse("accounts:profile"))

    def test_cannot_take_another_users_handle(self):
        make_user(email="bob@example.com", handle="bob")
        response = self.client.post(
            reverse("accounts:profile_edit"), {"display_name": "Alice", "handle": "bob"}
        )
        self.assertContains(response, "That handle is already taken.")

    def test_public_profile_found_by_handle(self):
        response = self.client.get(reverse("accounts:public_profile", args=["ALICE"]))
        self.assertContains(response, "@alice")
        self.assertNotContains(response, "alice@example.com")

    def test_public_profile_404_for_unknown_handle(self):
        response = self.client.get(reverse("accounts:public_profile", args=["nobody"]))
        self.assertEqual(response.status_code, 404)

    def test_change_password(self):
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": PASSWORD,
                "new_password1": "An0ther-good-pass",
                "new_password2": "An0ther-good-pass",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("An0ther-good-pass"))


class OrganizerProfileTests(TestCase):
    def setUp(self):
        self.holder = make_event_holder()

    def test_regular_user_cannot_access_organizer_pages(self):
        make_user()
        self.client.login(email="alice@example.com", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("accounts:organizer_dashboard")).status_code, 403)
        self.assertEqual(self.client.get(reverse("accounts:organizer_profile_edit")).status_code, 403)

    def test_edit_organizer_profile(self):
        self.client.login(email="org@example.com", password=PASSWORD)
        response = self.client.post(
            reverse("accounts:organizer_profile_edit"),
            {
                "organization_name": "Brooklyn Arts Collective",
                "description": "Community art shows in Bushwick.",
                "website": "https://bkarts.example.com",
                "contact_email": "events@bkarts.example.com",
                "phone": "718-555-0100",
            },
        )
        self.assertRedirects(response, reverse("accounts:organizer_dashboard"))
        self.holder.organizer_profile.refresh_from_db()
        self.assertEqual(
            self.holder.organizer_profile.organization_name, "Brooklyn Arts Collective"
        )

    def test_public_page_shows_organizer_info(self):
        response = self.client.get(reverse("accounts:public_profile", args=["brooklyn_arts"]))
        self.assertContains(response, "Brooklyn Arts Co")
        self.assertContains(response, "Event holder")

    def test_dashboard_creates_missing_organizer_profile(self):
        holder = User.objects.create_event_holder(
            email="new@example.com", password=PASSWORD, display_name="New Org", handle="neworg"
        )
        self.client.login(email="new@example.com", password=PASSWORD)
        response = self.client.get(reverse("accounts:organizer_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(OrganizerProfile.objects.filter(user=holder).exists())


class PasswordResetTests(TestCase):
    def test_full_password_reset_flow(self):
        user = make_user()
        response = self.client.post(
            reverse("accounts:password_reset"), {"email": "Alice@Example.com"}
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["alice@example.com"])

        link = re.search(r"https?://[^/]+(/\S+)", mail.outbox[0].body).group(1)
        response = self.client.get(link, follow=True)
        self.assertContains(response, "Choose a new password")
        response = self.client.post(
            response.redirect_chain[-1][0],
            {"new_password1": "Brand-new-pass-42", "new_password2": "Brand-new-pass-42"},
        )
        self.assertRedirects(response, reverse("accounts:password_reset_complete"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("Brand-new-pass-42"))

    def test_unknown_email_sends_nothing_but_same_response(self):
        response = self.client.post(
            reverse("accounts:password_reset"), {"email": "ghost@example.com"}
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_token_shows_error(self):
        response = self.client.get(
            reverse("accounts:password_reset_confirm", args=["MQ", "bad-token"])
        )
        self.assertContains(response, "Link invalid or expired")


class AdminProvisioningTests(TestCase):
    def test_create_user_refuses_admin_role(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email="x@example.com", password=PASSWORD, role=User.Role.ADMIN
            )

    def test_management_command_creates_admin(self):
        out = StringIO()
        call_command(
            "create_admin",
            email="Ops@Example.com",
            password=PASSWORD,
            display_name="Ops",
            stdout=out,
        )
        admin = User.objects.get(email="ops@example.com")
        self.assertTrue(admin.is_platform_admin)
        self.assertTrue(admin.is_staff)
        self.assertIn("Administrator account created", out.getvalue())

    def test_management_command_rejects_duplicate_and_weak_password(self):
        make_user(email="taken@example.com")
        with self.assertRaises(CommandError):
            call_command("create_admin", email="taken@example.com", password=PASSWORD)
        with self.assertRaises(CommandError):
            call_command("create_admin", email="new@example.com", password="123")

    def test_non_admins_cannot_reach_admin_site(self):
        make_user()
        self.client.login(email="alice@example.com", password=PASSWORD)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response.url)

    def test_role_change_away_from_admin_revokes_staff(self):
        admin = User.objects.create_admin(email="a@example.com", password=PASSWORD)
        admin.role = User.Role.USER
        admin.save()
        self.assertFalse(admin.is_staff)
        self.assertFalse(admin.is_superuser)

    def test_admin_can_provision_another_admin_via_admin_site(self):
        User.objects.create_admin(email="root@example.com", password=PASSWORD)
        self.client.login(email="root@example.com", password=PASSWORD)
        response = self.client.post(
            reverse("admin:accounts_user_add"),
            {
                "email": "second@example.com",
                "display_name": "Second Admin",
                "handle": "",
                "role": "admin",
                "usable_password": "true",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_admin = User.objects.get(email="second@example.com")
        self.assertTrue(new_admin.is_platform_admin)
        self.assertTrue(new_admin.is_staff)
        self.client.logout()
        self.client.login(email="second@example.com", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)
