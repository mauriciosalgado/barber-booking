# Barber Booking

Online appointment booking for barber shops. Customers register, pick a barber,
choose a service, and reserve a slot. The owner manages everything from the site
or a built-in admin console.

**One deployment = one shop.** Configure via `docker-compose.yml` and the same
images run any shop.

## Layout

```
backend/             FastAPI + SQLModel API with /admin console
frontend/            Reflex UI (pure Python)
docker-compose.yml   single config surface — edit and run
```

## Quick start

```bash
docker compose up
```

| What | URL |
| ---- | --- |
| Website | http://localhost:3000 |
| API docs | http://localhost:8000/docs |
| Admin console | http://localhost:8000/admin |
| Caught emails | http://localhost:8025 |

Owner login: **`owner@theshop.com`** / **`change-me`**.

## Configuration

Edit the `environment` block in `docker-compose.yml`. Everything is in one place.

### Shop identity (required)

| Variable | Example |
| -------- | ------- |
| `SHOP_NAME` | `"Ribeiro Barbeiro"` |
| `SHOP_TIMEZONE` | `"Europe/Lisbon"` |
| `OWNER_NAME` | `"Paquito"` |
| `OWNER_EMAIL` | `"me@myshop.pt"` |
| `OWNER_PASSWORD` | a strong password |
| `JWT_SECRET` | `openssl rand -hex 32` |

> **JWT_SECRET** signs every login, verification, and password-reset token. If
> someone guesses it they can log in as any user. Generate one per shop with
> `openssl rand -hex 32`.

### Branding (optional — owner changes live from the UI)

| Variable | Default |
| -------- | ------- |
| `SHOP_BRAND` | `#9e7b53` (accent colour) |
| `SHOP_BACKGROUND` | `#f6f1e9` (page colour) |
| `SHOP_HEADLINE` | `"A sua cadeira está à espera"` |

These seed the database on first start. After that, the owner controls
colours, logo, and headline from the UI.

### Email (required for production)

| Variable | Dev default |
| -------- | ----------- |
| `SMTP_HOST` | `smtp` (Mailpit) |
| `SMTP_PORT` | `1025` |
| `SMTP_FROM` | `no-reply@theshop.com` |
| `SMTP_USERNAME` | _(empty)_ |
| `SMTP_PASSWORD` | _(empty)_ |
| `SMTP_STARTTLS` | _(false)_ |

In production, point at a real provider (Brevo, Mailgun, SES, etc.) with
`SMTP_STARTTLS=true` and credentials set.

**Important**: the backend only speaks **STARTTLS**, not implicit TLS
(`smtplib.SMTP(...).starttls()` in `app/email.py`, no `SMTP_SSL`). Use
port **587** with `SMTP_STARTTLS=true`. Don't use port 465 — it expects TLS
from the first byte and will hang/fail with this code.

**Test it for real after deploy** — a broken SMTP config never fails the
request (`send_email()` no-ops if `SMTP_HOST` is empty, and any real send
error is caught and logged, not surfaced to the user). Register a throwaway
account and confirm the verification email actually lands in an inbox — a
`200 OK` response doesn't prove anything was sent.

#### Option A — Gmail app password (quickest, no domain needed)

1. Turn on 2-Step Verification: <https://myaccount.google.com/security>
2. Generate an app password: <https://myaccount.google.com/apppasswords> →
   name it (e.g. `barber-booking`) → copy the 16-character code shown.
3. Configure:

   | Variable | Value |
   | -------- | ----- |
   | `SMTP_HOST` | `smtp.gmail.com` |
   | `SMTP_PORT` | `587` |
   | `SMTP_STARTTLS` | `true` |
   | `SMTP_FROM` | your Gmail address |
   | `SMTP_USERNAME` | your Gmail address |
   | `SMTP_PASSWORD` | the 16-character app password (not your Google login password) |

   Caveats: mail comes from a `@gmail.com` address (not shop-branded), and
   Gmail's free tier caps at ~500 emails/day (plenty for one shop).

   **If "App Passwords" isn't available on that page**, it's one of:
   - 2-Step Verification isn't actually on yet (recheck step 1 — it can
     take a minute to propagate).
   - It's a Google Workspace (work/school) account and the admin disabled
     app passwords org-wide — use a personal `@gmail.com` account instead,
     or ask the admin.
   - Advanced Protection Program is enabled on the account — it disables
     app passwords outright as a security measure.

#### Option B — Gmail sending as your own domain (if you own one)

Gives you a `noreply@yourshop.com` sender using the same Gmail app password
above, no real mail server of your own needed:

1. **Cloudflare (or any DNS host with email forwarding)**: create a routing
   rule forwarding `noreply@yourshop.com` → your Gmail address. Note this is
   **inbound-only** — it lets you receive/verify at that address, it is
   *not* an outbound SMTP relay and can't be used as `SMTP_HOST` directly.
2. **Gmail → Settings → Accounts and Import → Send mail as → Add another
   email address** → enter `noreply@yourshop.com`.
3. Gmail will ask for an SMTP relay to verify sending through — point it at
   **Gmail's own server**, authenticating as yourself:
   - SMTP Server: `smtp.gmail.com`, Port: `587` (TLS)
   - Username: your Gmail address, Password: the app password from Option A
4. Gmail emails a confirmation link to `noreply@yourshop.com`, which arrives
   in your Gmail inbox via the Cloudflare forward — click it to finish.
5. Configure the shop with the same `SMTP_USERNAME`/`SMTP_PASSWORD` as
   Option A, but:

   ```
   SMTP_FROM="Your Shop Name <noreply@yourshop.com>"
   ```

   Since `yourshop.com` has no SPF/DKIM record authorizing Google to send on
   its behalf, most inboxes will show "via gmail.com" next to the sender —
   cosmetic, mail still delivers.

#### Option C — a real transactional provider (most "proper")

Verify `yourshop.com` with a provider like Brevo (free tier, 300/day), SES,
Mailgun, or SendGrid — each walks you through adding **SPF and DKIM DNS
records** (a couple of TXT/CNAME entries at your DNS host, e.g. Cloudflare).
Once verified, use the provider's own SMTP host/port and an API-key-style
username/password — no Gmail or app password involved, and no "via
gmail.com" caveat since the domain is now properly authenticated.

### Infrastructure (required for production)

**Backend:**

| Variable | Dev default |
| -------- | ----------- |
| `DATABASE_URL` | `sqlite:////data/barber.db` |
| `CORS_ORIGINS` | `*` |
| `PUBLIC_BASE_URL` | `http://localhost:8000` |

**Frontend:**

| Variable | Dev default |
| -------- | ----------- |
| `API_URL` | `http://backend:8000` |
| `PUBLIC_API_URL` | `http://localhost:8000` |
| `ADMIN_URL` | `http://localhost:8000/admin` |

### HTTPS

The app does not terminate TLS. Put a reverse proxy in front (Caddy, nginx,
Traefik, k8s Ingress, cloud LB) and set all `*_URL` vars to `https://`.
Lock `CORS_ORIGINS` to the frontend's real origin.

### Production database

Swap SQLite for Postgres and remove the `./data:/data` volume:

```yaml
DATABASE_URL: "postgresql://user:pass@host:5432/barber"
```

### Go-live checklist

1. `openssl rand -hex 32` → `JWT_SECRET`
2. Set `SHOP_NAME`, `OWNER_*`, `SHOP_TIMEZONE`
3. Point `SMTP_*` at a real mail provider
4. Set `CORS_ORIGINS` to the frontend's URL
5. Set all `*_URL` vars to real `https://` addresses
6. HTTPS in front (reverse proxy)
7. `docker compose up`

## How it works

- **Scheduling** — working hours − lunch − booked − closures − past. All
  services share one grid (step = GCD of service lengths).
- **Services** — each barber has a menu (e.g. Corte 30min, Barba 15min).
  Bookings snapshot the duration.
- **Weekly recurrence** — customers repeat a booking weekly (barber controls cap).
- **Email verification** — new accounts must confirm before booking.
- **Password reset** — forgot-password → email link → reset-password.
- **Rate limiting** — 10/min login, 5/min register, 3/min reset.
- **Closures** — owner blocks a period; overlapping bookings are cancelled.
- **Admin console** — full CRUD over users, barbers, services, hours,
  appointments, closures, and settings at `/admin`.

## Development without Docker

```bash
cd backend && uv sync && cp .env.example .env && uv run serve
cd frontend && uv sync && API_URL=http://localhost:8000 uv run reflex run
```

## Deploy

Both images are stateless, configured by env vars, and expose `/health` +
`/health/ready` for orchestrator probes. Supply secrets through your platform's
secret store.

### Kubernetes

A Helm chart lives in `charts/barber-booking/` — one install per shop, with
an optional built-in Postgres, designed to be deployed via GitOps (e.g.
ArgoCD referencing it directly from this repo) or `helm install` by hand.
See `charts/barber-booking/README.md` for the ArgoCD setup, the first-shop
checklist, and secrets handling.

## Known limitations

These are deliberate tradeoffs for a small, single-shop deployment — not bugs.
Revisit them only if your situation changes.

- **One backend replica.** The rate limiter (`slowapi`) stores counts in
  memory. With a single replica this is correct; with more than one, each
  pod counts independently, so limits get proportionally more lenient
  (never more strict, so this is not a security hole — just less precise).
  A shared backend (e.g. Redis) would be needed to scale horizontally.
- **JWTs aren't revocable.** Logout is client-side only, and changing or
  resetting a password does not invalidate previously-issued access tokens
  — they remain valid until they naturally expire (24h). This is a standard
  stateless-JWT tradeoff. If you need instant revocation, you'd need a
  server-side token blocklist or session store.
- **Frontend runs in Reflex dev mode.** `reflex run --env prod --single-port`
  was tested and works on the surface, but throws a repeated internal
  `AssertionError` (a WebSocket-vs-static-file routing bug in how Reflex
  multiplexes both on one port). Dev mode is verified stable with zero
  errors across every flow, just heavier/unoptimized. Don't switch without
  first resolving that bug or splitting frontend/backend behind a proxy
  that routes WebSocket traffic separately (e.g. Traefik). The Helm chart
  works around this by giving Reflex's event backend its own Ingress path
  rules rather than relying on Reflex's single-port mode.
- **SQLite by default.** Fine for one shop's traffic; a single file, no
  separate DB server to run. Swap to Postgres (see above, or the Helm
  chart's built-in Postgres option) if you need concurrent writers or
  managed backups.
- **No schema migrations.** `create_all()` only adds new tables, never new
  columns to existing ones. A schema change on a live database needs a
  manual migration or a DB reset. Adopt Alembic if the schema will keep
  evolving after go-live.
