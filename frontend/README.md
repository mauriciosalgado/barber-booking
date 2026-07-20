# Frontend — Booking Website

Built with [Reflex](https://reflex.dev) — the entire UI is pure Python, no
HTML/JS/CSS files. It compiles to a React app served to the browser.

## Layout

```
shop/
├── shop.py    page shell: navbar, hero, layout, colour-mode driver
├── state.py   all page state + API communication
├── views.py   UI components: auth, customer booking, barber agenda, admin panel
└── ui.py      design system: derived palette, reusable pieces (card, step, row)
rxconfig.py    Reflex config (ports, theme plugin)
```

## How it works

One page that adapts to who's signed in:

| Role | What they see |
| ---- | ------------- |
| Signed out | Login/register form with configurable headline |
| Customer | Barber → service → day → slot booking flow + their appointments |
| Barber | Their agenda, working hours editor, services editor |
| Owner | All of the above + branding controls + link to admin console |

The owner's two chosen colours (brand + background) derive a full legible palette
at runtime via CSS variables — the whole site re-themes live.

## Run locally

The backend must be running (see `../backend/`).

```bash
uv sync
API_URL=http://localhost:8000 uv run reflex run
```

Website → http://localhost:3000

## Environment variables

| Variable | Purpose | Default |
| -------- | ------- | ------- |
| `API_URL` | Backend URL (server-side calls) | `http://localhost:8000` |
| `PUBLIC_API_URL` | Backend URL the browser uses (logo, favicon) | same as `API_URL` |
| `ADMIN_URL` | Link shown to the owner for the admin console | `http://localhost:8000/admin` |
| `MAIL_INBOX_URL` | Dev only: link to Mailpit for the verify banner | _(empty)_ |

## In Docker

The root `docker-compose.yml` builds and runs this alongside the backend — no
manual setup needed. See the [root README](../README.md).
