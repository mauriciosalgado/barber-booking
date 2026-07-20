# Barber Booking

Online appointment booking for barber shops. Customers register, pick a barber,
choose a service, and reserve a slot. The owner manages everything from the site
or a built-in admin console.

**One deployment = one shop.** Configure via `docker-compose.yml` and the same
images run any shop.

```
backend/             FastAPI + SQLModel API, with /admin (SQLAdmin)
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

## Configure for your shop

Edit the `environment` block in `docker-compose.yml`. Everything is in one place.

### 1. Shop identity (required)

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

### 2. Branding (optional — owner can change live from the UI)

| Variable | Default |
| -------- | ------- |
| `SHOP_BRAND` | `#9e7b53` (accent colour) |
| `SHOP_BACKGROUND` | `#f6f1e9` (page colour) |
| `SHOP_HEADLINE` | `"A sua cadeira está à espera"` |

These seed the database on first start. After that, the owner controls
colours, logo, and headline from the **Aparência** card in the UI.

### 3. Email (required for production)

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

### 4. Infrastructure (required for production)

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
| `REFLEX_API_URL` | `http://localhost:8001` |
| `ADMIN_URL` | `http://localhost:8000/admin` |

### 5. HTTPS

The app does not terminate TLS. Put a reverse proxy in front (Caddy, nginx,
Traefik, k8s Ingress, cloud LB) and set all `*_URL` vars to `https://` addresses.
Lock `CORS_ORIGINS` to the frontend's real origin.

### 6. Production database

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

- **Scheduling** — working hours minus lunch, minus booked, minus closures,
  minus the past. All services share one grid (step = GCD of service lengths).
- **Services** — each barber has a menu (e.g. Corte 30min, Barba 15min). The
  owner edits them live; bookings snapshot the duration.
- **Weekly recurrence** — optionally, customers repeat a booking weekly (barber
  controls the cap).
- **Email verification** — new accounts must confirm before booking.
- **Password reset** — `POST /auth/forgot-password` → email link →
  `POST /auth/reset-password`.
- **Rate limiting** — 10/min login, 5/min register, 3/min reset.
- **Closures** — the owner blocks a period; overlapping bookings are cancelled.

## Development without Docker

```bash
cd backend && uv sync && cp .env.example .env && uv run serve
cd frontend && uv sync && API_URL=http://localhost:8000 uv run reflex run
```

## Deploy

Both images are stateless, configured by env vars, and expose `/health` +
`/health/ready` for orchestrator probes. They drop into any container platform
(k8s, ECS, etc.). Supply secrets through your platform's secret store.
