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
| `DJANGO_SECRET_KEY` | insecure dev key — **required** when `DJANGO_DEBUG` is off |
| `DJANGO_DEBUG` | `True` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty — full origins, e.g. `https://example.com` |
| `DATABASE_URL` | SQLite file `db.sqlite3` — use PostgreSQL in production |
| `DJANGO_SECURE_SSL_REDIRECT` | `True` when `DJANGO_DEBUG` is off |
| `DJANGO_SECURE_HSTS_SECONDS` | `0` |
| `DJANGO_EMAIL_BACKEND` | console backend |
| `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`, `DJANGO_EMAIL_USE_TLS` | SMTP settings for real email delivery |
| `DJANGO_DEFAULT_FROM_EMAIL` | `NYC Event Explorer <no-reply@nyceventexplorer.local>` |

## Deployment (Vercel)

Vercel detects Django automatically (via `manage.py`), runs `collectstatic` during the
build and serves static files from its CDN. The app's own `*.vercel.app` domains are
added to `ALLOWED_HOSTS` automatically.

1. In Vercel, **Add New → Project** and import this GitHub repository.
2. Before the first deploy, add environment variables:
   `DJANGO_DEBUG=False` and `DJANGO_SECRET_KEY=<long random string>`.
3. Add a Postgres database: project → **Storage** → create/connect a Postgres
   provider (e.g. Neon). This sets `DATABASE_URL`. SQLite does not work on Vercel
   because its filesystem is read-only and not persistent.
4. Deploy, then create the tables and the first admin from your own machine using the
   same database URL:
   ```bash
   export DATABASE_URL="<the DATABASE_URL value from Vercel>"
   python manage.py migrate
   python manage.py create_admin
   ```
   Re-run `migrate` this way whenever a change adds migrations.

Password-reset emails go to the Vercel function logs until `DJANGO_EMAIL_*` is configured.

## Deployment (AWS Elastic Beanstalk)

The app is production-ready: gunicorn serves it (`Procfile`), whitenoise serves static
files, `DATABASE_URL` selects the database, and `/healthz/` answers load-balancer health
checks. EB-specific config lives in `.ebextensions/` and `.platform/`
(migrations run on deploy; static files are collected before each deploy).

SQLite is only for local development — production needs PostgreSQL, because EB
instances are replaced and their disks wiped.

```bash
pip install awsebcli
eb init nyc-event-explorer --platform "Python 3.12" --region us-east-1
eb create nyc-events-prod --single            # or omit --single for a load balancer
```

Create a PostgreSQL database (Amazon RDS, kept separate from the EB environment so it
survives environment rebuilds), allow the EB instances' security group to reach it on
port 5432, then set the environment variables:

```bash
eb setenv \
  DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')" \
  DJANGO_ALLOWED_HOSTS="<env-name>.<region>.elasticbeanstalk.com" \
  DJANGO_CSRF_TRUSTED_ORIGINS="http://<env-name>.<region>.elasticbeanstalk.com" \
  DATABASE_URL="postgres://<user>:<password>@<rds-endpoint>:5432/<dbname>"
eb deploy
eb ssh -c "cd /var/app/current && source /var/app/venv/*/bin/activate && python manage.py create_admin"
```

Once HTTPS is set up on the load balancer, set `DJANGO_SECURE_SSL_REDIRECT=True`,
use `https://` in `DJANGO_CSRF_TRUSTED_ORIGINS`, and consider `DJANGO_SECURE_HSTS_SECONDS`.
For real password-reset emails, set the `DJANGO_EMAIL_*` variables (e.g. Amazon SES SMTP).

The same `Procfile` and settings also work on Heroku, Railway or Render
(add `python manage.py migrate` and `collectstatic` as release/build steps there).

## Project layout

```
nyc_events/     Django project (settings, root URLs, home view)
accounts/       Epic 1: custom User model, organizer profiles, auth views, admin
templates/      HTML templates
static/         CSS
```
