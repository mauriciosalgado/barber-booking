# Backend — Booking API

FastAPI + SQLModel REST API with a built-in admin console at `/admin` (SQLAdmin).

## Layout

```
app/
├── main.py           app entry point, router wiring
├── config.py         all settings (from environment)
├── database.py       engine + session dependency
├── security.py       bcrypt hashing, JWT creation/validation, auth guards
├── email.py          SMTP send helper
├── limiter.py        rate limiting setup
├── seed.py           first-start seeding (owner, barber, services, logo)
├── scheduling.py     slot generation (pure logic, no I/O)
├── availability.py   open-slot computation (hours − lunch − booked − closures − past)
├── admin.py          /admin console (SQLAdmin views + validation hooks)
├── models/           one file per entity — DB table + request/response schemas
└── routers/          one file per resource — auth, barbers, appointments, closures, services, settings, system
tests/                pytest integration + unit tests
```

## Run locally

```bash
uv sync
cp .env.example .env    # fill in all values
uv run serve            # starts on http://127.0.0.1:8000 with auto-reload
```

- API docs → http://127.0.0.1:8000/docs (use **Authorize** to log in as the owner)
- Admin console → http://127.0.0.1:8000/admin

## Tests

```bash
uv run pytest
```

107 tests against a throwaway SQLite DB covering: slot logic, booking rules,
email verification, password reset, rate limiting, closures, services, recurrence, and permissions.

## Configuration

All values in `.env.example` are required — a missing one stops the app at startup.

| Variable | Purpose |
| -------- | ------- |
| `SHOP_NAME` | Displayed in the header, emails, API title |
| `SHOP_TIMEZONE` | IANA timezone for all scheduling logic |
| `OWNER_EMAIL`, `OWNER_NAME`, `OWNER_PASSWORD` | Admin account, seeded on first start |
| `JWT_SECRET` | Signs all tokens — generate with `openssl rand -hex 32` |
| `DATABASE_URL` | `sqlite:///./barber.db` (dev) or `postgresql://…` (prod) |
| `CORS_ORIGINS` | Allowed browser origins, comma-separated or `*` |
| `PUBLIC_BASE_URL` | Used in email links (verification, password reset) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM` | Outgoing mail; empty host disables sending |
| `SMTP_STARTTLS`, `SMTP_USERNAME`, `SMTP_PASSWORD` | TLS + auth for production SMTP |
| `SHOP_BRAND`, `SHOP_BACKGROUND`, `SHOP_HEADLINE` | Initial theme (owner overrides from UI) |
| `SHOP_LOGO_PATH` | Optional file to seed the logo on first start |

## Key design points

- **Availability is computed live** — never stored. Working hours minus lunch, minus booked slots, minus closures, minus the past.
- **Fixed slot grid** — step is the GCD of the barber's service durations. A 15-min booking never blocks a 30-min service from a valid start.
- **1-hour booking lead** — customers can't grab last-minute slots.
- **1-hour cancel cut-off** — customers can't cancel too late; staff always can.
- **Rate limiting** — login (10/min), register (5/min), password reset (3/min).
- **Cascade deletes** — removing a barber removes their hours/appointments.
- **SQLite foreign keys enabled** via PRAGMA so dev matches Postgres behaviour.

## Auth

- Passwords hashed with **bcrypt**.
- Login returns a **JWT** (HS256, 24h TTL, signed with `JWT_SECRET`).
- Verification and password-reset use the same JWT machinery with a `purpose` claim — tokens are not interchangeable.
- Admin console uses **session cookies** (same email/password, requires `is_admin`).

## Health probes

- `GET /health` — liveness (process is up)
- `GET /health/ready` — readiness (database reachable)
