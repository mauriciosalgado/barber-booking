# Backend — Booking API

FastAPI + SQLModel API with a built-in admin UI (SQLAdmin) at `/admin`.

## Project layout

```
app/
├── config.py         settings from env vars
├── database.py       engine + session dependency
├── security.py       bcrypt, JWT, auth guards
├── email.py          SMTP helper
├── limiter.py        rate limiting
├── seed.py           owner + barber + services on first start
├── scheduling.py     slot generation (pure logic, no DB)
├── availability.py   open slots (working hours − lunch − booked − closures − past)
├── admin.py          /admin web UI
├── main.py           app + router wiring
├── models/           one file per entity (table + API schemas)
└── routers/          endpoints grouped by resource
tests/                pytest suite
```

## Running

```bash
uv sync
cp .env.example .env   # fill in the values
uv run serve           # http://127.0.0.1:8000 (auto-reload)
```

## Tests

```bash
uv run pytest
```

107 tests against a throwaway SQLite DB. Covers slot logic, all booking rules,
email verification, password reset, closures, services, and permissions.

## Configuration

Every value in `.env.example` is required (missing = startup error).

| Variable | Purpose |
| -------- | ------- |
| `SHOP_NAME`, `SHOP_TIMEZONE` | Shop identity |
| `OWNER_EMAIL`, `OWNER_NAME`, `OWNER_PASSWORD` | Seeded admin account |
| `JWT_SECRET` | Signs login/verify/reset tokens — `openssl rand -hex 32` |
| `DATABASE_URL` | SQLite (dev) or Postgres (prod) |
| `CORS_ORIGINS` | Allowed browser origins (comma-separated, or `*`) |
| `PUBLIC_BASE_URL` | Public URL used in email links |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM` | Outgoing mail (empty host = disabled) |
| `SMTP_STARTTLS`, `SMTP_USERNAME`, `SMTP_PASSWORD` | TLS + auth for production mail |
| `SHOP_BRAND`, `SHOP_BACKGROUND`, `SHOP_HEADLINE` | Starting theme (owner changes live) |
| `SHOP_LOGO_PATH` | Optional file path to seed the logo on first start |

## Key design decisions

- **Availability is computed, not stored.** Working hours − lunch − booked − closures − past.
- **One grid for all services.** Step = GCD of service durations. A 15-min booking at 09:00 still lets a 30-min cut start at 09:15.
- **Booking lead time** of 1 hour — no last-minute slots.
- **Customer cancel cut-off** of 1 hour — staff can always cancel.
- **Rate limiting** on auth endpoints (login, register, reset).
- **Cascade deletes** — removing a barber removes their hours and appointments.
- **SQLite foreign keys enabled** via `PRAGMA foreign_keys=ON` so dev matches Postgres.

## Auth

- Passwords hashed with bcrypt, never stored in plain text.
- Login returns a JWT (24h TTL, HS256, signed with `JWT_SECRET`).
- Email verification and password reset use purpose-scoped JWTs (same secret, different `purpose` claim).
- Admin UI uses session cookies (same credentials, `is_admin` required).

## SMTP

`send_email(to, subject, body)` in `app/email.py`. Supports STARTTLS + login
when configured, or plain SMTP for dev (Mailpit). Empty `SMTP_HOST` disables
sending entirely. Mail failures never block requests — logged as warnings.
