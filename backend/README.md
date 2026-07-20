# Barber Booking

A small web API for booking haircuts. Customers register, pick a barber, see
that barber's open slots for a day, and book one. The shop owner is
an admin who manages barbers and their weekly schedules — either through the
API or a ready-made **admin web UI**.

## How it's structured

**One deployment = one shop.** Everything that differs between shops — the
name, timezone, database, auth secret and owner account — comes from
environment variables (see `.env.example`). The code never changes per shop,
so the same image runs any barber shop.

**Roles.** A `User` is the login identity; `is_admin` marks the owner. A
`Barber` is a 1:1 extension of a user (the bookable person). The owner is
created as an admin automatically on first startup from the `OWNER_*` config.

**Scheduling.** Availability is computed, not stored: a barber's working hours
for that weekday, minus the lunch break, minus already-booked slots, minus any
time in the past, and minus anything sooner than a one-hour **booking lead time**
(no last-minute slots). Each service carries its own length, and the day's open
times fall on one fixed grid stepped by the finest common service length (the
GCD of the barber's service durations — 15 minutes for a 15/30-minute shop). One
shared grid means a short booking never pushes a longer service off a usable
start: a 15-minute booking at 09:00 still lets a 30-minute cut start at 09:15 or
09:30. Weekdays are named (`"Monday"` … `"Sunday"`) via a small `Weekday` enum,
so the API and admin forms are self-describing instead of using bare numbers.

**Booking.** A logged-in customer reserves one of those open slots
(`POST /appointments`); the server re-checks the slot is genuinely free against
the same availability logic, and a unique constraint on `(barber, time)` stops
two people grabbing it at once. Customers list (`GET /appointments`) and cancel
(`DELETE /appointments/{id}`) their own bookings, but **can't cancel within an
hour** of the appointment (the owner still can). A barber sees who's booked with
them via `GET /barbers/{id}/appointments` (optionally `?date=…`), restricted to
that barber or an admin. Emails are normalized to lowercase, and a
timezone-aware `start_at` is converted to the shop's local time before storing.

**Closures.** The owner can close the shop for a period — a holiday, say —
with `POST /closures` (`start_at`, `end_at`, optional `reason`). Those slots
disappear from availability for everyone, and any appointments already booked
inside the period are cancelled automatically. Closures are public
(`GET /closures`) so a frontend can show a banner, and the owner removes them
with `DELETE /closures/{id}` to reopen the slots.

**Admin UI.** The owner gets a CRUD interface at `/admin` (powered by SQLAdmin)
to manage users, barbers, working hours, services, appointments and closures,
protected by
the same owner login as the API. It is **not** a raw database editor — the same
rules run here as in the API: working hours are validated (start before end,
break within hours), a new appointment must land on a genuinely free slot (inside
working hours, not already taken, not during a closure, not in the past, and a
barber can't book themselves), and creating a closure cancels the appointments it
overlaps.

**Data integrity.** A few database constraints keep the data honest no matter
which path writes it: one `Barber` per user, at most one working-hours row per
`(barber, weekday)` — so a barber has **at most seven**, one per day — and one
appointment per `(barber, time)`. Deletes **cascade**: removing a barber also
removes their working hours and appointments, and removing a customer removes
their appointments, so nothing is left orphaned. Foreign keys are enforced in
both databases — Postgres does this natively, and for SQLite we switch it on per
connection with `PRAGMA foreign_keys=ON` (it's off by default there), so dev
behaves the same as production.

## Authentication

Passwords are never stored in the clear — they're hashed with bcrypt when a user
registers, and only the hash is kept.

**API (token-based).** You log in at `POST /auth/token` with email + password.
If they match, you get back a **JWT** signed with `JWT_SECRET` that carries your
user id and expires after a day. To call a protected endpoint, send it as
`Authorization: Bearer <token>`. FastAPI decodes the token, loads the user, and
injects it — endpoints just declare `CurrentUser` (any logged-in user) or
`AdminUser` (must have `is_admin`) and the check happens automatically.

**Admin UI (session-based).** `/admin` uses the same email + password, but keeps
you signed in with a signed session cookie instead of a bearer token. Only users
with `is_admin` can get in.

**Email verification.** New customers register unverified. Registration emails
them a signed, single-purpose JWT link (`GET /auth/verify?token=…`); until they
follow it they can browse and see availability but **cannot book** (booking
returns 403). `POST /auth/resend-verification` sends a fresh link. The owner is
seeded already verified. A mail outage never blocks signup — the account is
created and the link can be resent.

The verification link is not a random string stored in a table — it's a JWT
signed with `JWT_SECRET` and stamped with a `purpose: "verify"` claim plus a
one-day expiry (`create_verification_token` in `security.py`). Verifying decodes
it, checks the signature *and* that the purpose is `verify`, and reads the user
id from it — so a login token can't verify an account and an expired link is
rejected. There's nothing to clean up because nothing is persisted: the token
itself is the proof.

### SMTP integration

Email goes out through plain SMTP, wrapped in one tiny helper —
`send_email(to, subject, body)` in `app/email.py`. It's deliberately dumb: build
an `EmailMessage`, open an `smtplib.SMTP` connection to `SMTP_HOST:SMTP_PORT`,
send, done. Three environment variables configure it and nothing else touches
mail:

| Variable    | Meaning                                              |
| ----------- | ---------------------------------------------------- |
| `SMTP_HOST` | Mail server host. **Empty = sending disabled.**      |
| `SMTP_PORT` | Mail server port (e.g. `1025` for Mailpit, `587` TLS)|
| `SMTP_FROM` | The `From:` address on outgoing mail                 |
| `SMTP_STARTTLS` | `true` to upgrade the connection to TLS (prod)   |
| `SMTP_USERNAME` | Mailbox login; empty = no authentication (dev)   |
| `SMTP_PASSWORD` | Mailbox app-password, paired with the username   |

Because the mail server is external, the same code runs in every environment —
only the variables change:

- **Dev / Docker** — `docker compose` runs **Mailpit**, a throwaway inbox that
  captures every message so you can read verification links at
  <http://localhost:8025>. Mailpit needs no login and no TLS, so
  `SMTP_STARTTLS`, `SMTP_USERNAME` and `SMTP_PASSWORD` stay empty. (Mailpit is
  multi-arch and runs natively on Apple Silicon.)
- **Production** — relay through a managed provider or the shop's own mailbox
  (see below); set `SMTP_STARTTLS=true` and the username/password.
- **Tests / no-mail runs** — leave `SMTP_HOST` empty and `send_email` returns
  immediately without connecting.

`send_email` turns each option on only when its setting is present: STARTTLS
happens if `SMTP_STARTTLS` is true, and it logs in only if `SMTP_USERNAME` is
set — so the one function covers Mailpit and a real provider without branching
per environment.

Sending is best-effort at the point it matters: registration wraps the send in a
`try/except OSError`, logs a warning on failure, and still returns the created
account, so a mail outage can never turn a signup into an error.

#### Setting up a personalized email and wiring it in

The recommended approach is **not** to run your own outbound mail server —
deliverability (IP reputation, blocklists, DNS) is a job in itself. Instead, use
**one dedicated mailbox on your own domain** that exists only to send these
messages (verification, password reset, later notifications), and relay through
your mail host's SMTP server. Here's the whole path from nothing to working
email.

**1. Have a domain.** You need a domain for the shop, e.g. `theshop.com`. If you
don't have one, buy it from any registrar (Namecheap, Cloudflare, Porkbun, …).

**2. Add email hosting for that domain.** Pick one provider that hosts mailboxes
*on your domain* and gives you an SMTP endpoint. Common choices:

| Provider          | Good when…                         | SMTP host (example)          |
| ----------------- | ---------------------------------- | ---------------------------- |
| Google Workspace  | you already use Gmail/Google       | `smtp.gmail.com`             |
| Zoho Mail         | cheapest custom-domain mailboxes   | `smtp.zoho.com`              |
| Fastmail          | simple, privacy-friendly           | `smtp.fastmail.com`          |
| Migadu            | flat price, unlimited addresses    | `smtp.migadu.com`            |
| Amazon SES        | high volume, pay-per-email         | `email-smtp.<region>.amazonaws.com` |

During setup the provider asks you to **verify the domain** by adding a couple of
DNS records (they show the exact values) — this is what lets you send *as*
`@theshop.com`.

**3. Create the mailbox.** In the provider's admin, create the sending address,
e.g. **`no-reply@theshop.com`**. Give it a strong password.

**4. Get SMTP credentials.** You want:
- the **SMTP host** and **port** (almost always `587` with STARTTLS),
- a **username** — usually the full address `no-reply@theshop.com`,
- a **password** — prefer an **app-password / SMTP key** over the mailbox's login
  password. Most providers require this if 2-factor is on:
  - *Google Workspace*: enable 2-Step Verification → create an **App Password**.
  - *Amazon SES*: create **SMTP credentials** (they're different from your AWS keys).
  - *Zoho / Fastmail*: generate an **app-specific password**.

**5. Add the anti-spam DNS records.** So mail isn't flagged as spam, add these
for the sending domain (your provider gives you the exact values):
- **SPF** — a TXT record listing who may send for the domain.
- **DKIM** — a TXT/CNAME record that cryptographically signs your mail.
- **DMARC** — a TXT record telling receivers what to do with mail that fails the
  first two (start with `p=none` while testing).

**6. Wire it into the app.** Put the values in the deployment's environment (in a
Secret — never in the image or git):

```dotenv
SMTP_HOST="smtp.your-provider.com"
SMTP_PORT="587"
SMTP_STARTTLS="true"
SMTP_USERNAME="no-reply@theshop.com"
SMTP_PASSWORD="the-app-password"
SMTP_FROM="no-reply@theshop.com"

# Also make the links in emails point at the real site:
PUBLIC_BASE_URL="https://booking.theshop.com"
```

That's it — no code changes. `send_email` reads these, opens STARTTLS, logs in,
and sends. Because everything funnels through that one helper, the same mailbox
also carries password-reset mail and any future notifications.

**7. Test it.** Register a throwaway customer against the deployed API and confirm
the verification email arrives in a real inbox (check the spam folder the first
time). If nothing arrives, check the app logs for the warning `Could not send
verification email…` — a failed send is logged, never silently swallowed.

> Tip: keep local dev on **Mailpit** (no host verification, no DNS, no
> credentials). Only production needs the steps above; switching between them is
> purely a matter of which env vars are set.

Both auth paths share one helper — `authenticate_user()` in `security.py` — so
"check an email and password" lives in exactly one place.

## Tech stack

- [uv](https://docs.astral.sh/uv/) — packaging & environments
- [FastAPI](https://fastapi.tiangolo.com/) — web framework, with automatic
  OpenAPI docs at `/docs`
- [SQLModel](https://sqlmodel.tiangolo.com/) — models & queries (synchronous)
- [SQLAdmin](https://aminalaee.dev/sqladmin/) — the `/admin` web UI
- SQLite for local dev, PostgreSQL in production
- JWT auth with bcrypt-hashed passwords

## Project layout

```
app/
├── config.py       # settings, read from the environment
├── database.py     # engine + the per-request session dependency
├── security.py     # password hashing, JWT, current-user/admin guards
├── email.py        # sending transactional email over SMTP
├── seed.py         # creates the owner admin on startup
├── scheduling.py   # slot generation (pure logic)
├── availability.py # a barber's open slots (working hours − lunch − booked − past − closures)
├── admin.py        # the /admin web UI (SQLAdmin)
├── main.py         # builds the app and wires routers
├── models/         # one file per entity: the table plus its API schemas
└── routers/        # endpoints grouped by resource (auth, barbers,
                    #   appointments, closures, system)

tests/              # pytest suite (pure slot logic + full API behaviour)
```

## Getting started

```bash
uv sync                       # create the virtual environment
cp .env.example .env          # then fill in the values (all are required)
uv run serve                  # start the dev server (auto-reload)
```

Then:

- **API docs** — <http://127.0.0.1:8000/docs>. Use **Authorize** to log in as the
  owner (the `OWNER_EMAIL` / `OWNER_PASSWORD` from your `.env`). The login field
  labelled "username" takes the email.
- **Admin UI** — <http://127.0.0.1:8000/admin>. Log in with the same owner
  credentials to manage the shop.

## Running the tests

```bash
uv run pytest
```

The suite runs against a throwaway SQLite database and covers the pure slot
logic plus the full API — registration, email verification, login, working
hours, availability, every booking rule (inside working hours, a schedule must
exist, verified customers only, no double-booking, cancellation), and closures
(blocking slots and cancelling overlapping bookings).

## Configuration

Every value in `.env.example` is required — a missing one stops the app at
startup rather than letting it run misconfigured.

### Generating `JWT_SECRET`

`JWT_SECRET` is the key that signs and verifies login tokens (HS256, a symmetric
algorithm — the same secret signs and checks). It can technically be *any*
string, but it must be **long, random and secret** — anyone who knows it can mint
valid tokens for any user. Don't use a memorable passphrase.

Generate a fresh 256-bit value with any of:

```bash
openssl rand -hex 32                                  # 64 hex characters
openssl rand -base64 32
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Each shop gets its own secret. Keep it out of source control (it lives in `.env`
locally, and in a Secret in production). Rotating it invalidates every existing
token, so all users simply log in again.

| Variable                                      | Purpose                         |
| --------------------------------------------- | ------------------------------- |
| `SHOP_NAME`, `SHOP_TIMEZONE`                  | Shop identity                   |
| `SHOP_BRAND`, `SHOP_BACKGROUND`              | Starting colours (hex); owner recolours live from the UI |
| `SHOP_HEADLINE`                              | Starting sign-in headline; owner can change it live |
| `SHOP_LOGO_PATH`                             | Optional file to seed the logo on first start (owner can replace it later) |
| `DATABASE_URL`                                | The shop's own database         |
| `JWT_SECRET`                                  | Signing secret for login tokens |
| `OWNER_EMAIL`, `OWNER_NAME`, `OWNER_PASSWORD` | Owner admin, seeded on startup  |
| `CORS_ORIGINS`                                | Browser origins allowed to call the API (comma-separated, or `*`) |
| `PUBLIC_BASE_URL`                             | Public URL of the app, used to build email links |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`         | Outgoing mail; an empty host disables sending |
| `SMTP_STARTTLS`, `SMTP_USERNAME`, `SMTP_PASSWORD` | Optional TLS + login for a production mailbox (empty in dev) |

## Running with Docker

The whole app runs from the **repo root** with one command. `docker compose`
builds the backend and the frontend, and also starts **Mailpit** — a throwaway
SMTP server that catches every outgoing email so you can read verification links
in a browser.

```bash
docker compose up --build   # run from the repository root
```

- **Website** — <http://localhost:3000>
- **API** — <http://localhost:8000> (docs at `/docs`)
- **Caught emails** — <http://localhost:8025> (Mailpit web UI)

SMTP is a *separate* service, not part of the app image: in dev it's Mailpit; in
production you point `SMTP_HOST` at a managed provider (SES, SendGrid, …). The
image exposes `/health` (liveness) and `/health/ready` (readiness — checks the
database) for orchestrators to probe.
