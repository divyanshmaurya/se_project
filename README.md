# NYC Event Explorer

An interactive NYC event discovery and planning application built with Python and Django.
Users can search, explore, save and organize NYC events into personal plans, and connect
with other people interested in the same events.

## Implemented: Epic 1 — Account Registration & Management

| User story | Where |
|---|---|
| User creates an account with email + password | `/accounts/signup/user/` |
| User chooses a display name and unique handle | Sign-up form; handles are unique case-insensitively; public page at `/accounts/u/<handle>/` |
| User logs in with email + password | `/accounts/login/` (email is case-insensitive) |
| User edits profile | `/accounts/profile/edit/` (display name, handle, bio, home borough) |
| Event holder creates a business account | `/accounts/signup/event-holder/` (also creates an organizer profile) |
| Event holder logs in | `/accounts/login/` → redirected to the organizer dashboard |
| Event holder edits organizer profile | `/accounts/organizer/edit/` |
| User / event holder resets password by email | `/accounts/password/reset/` (link emailed, expires in 1 hour) |
| Administrator provisions admin accounts | `python manage.py create_admin`, or in the Django admin by creating a user with the *Administrator* role |
| Administrator logs in | `/accounts/login/` → redirected to `/admin/` |

Roles: `user`, `event_holder`, `admin`. Public sign-up can only create `user` and
`event_holder` accounts; administrator accounts can only be created by an existing
administrator (admin site) or from the server command line (`create_admin`).
Only administrators can reach the Django admin site.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py create_admin      # first administrator account
python manage.py runserver
```

Open http://127.0.0.1:8000/.

In development, emails (such as password reset links) are printed to the console
running `runserver`.

## Running tests

```bash
python manage.py test
```

## Configuration

Settings are read from environment variables (defaults are for local development):

| Variable | Default |
|---|---|
| `DJANGO_SECRET_KEY` | insecure dev key — **set in production** |
| `DJANGO_DEBUG` | `True` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` |
| `DJANGO_EMAIL_BACKEND` | console backend |
| `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`, `DJANGO_EMAIL_USE_TLS` | SMTP settings for real email delivery |
| `DJANGO_DEFAULT_FROM_EMAIL` | `NYC Event Explorer <no-reply@nyceventexplorer.local>` |

## Project layout

```
nyc_events/     Django project (settings, root URLs, home view)
accounts/       Epic 1: custom User model, organizer profiles, auth views, admin
templates/      HTML templates
static/         CSS
```
