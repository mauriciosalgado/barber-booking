# Barber Booking — Frontend

The booking website, built with [Reflex](https://reflex.dev) — the whole UI is
written in **pure Python** (no HTML or CSS files), so the entire project stays in
one language. It renders to a real React app in the browser.

## The page

A warm, mobile-first, single-column booking flow:

1. **Choose your barber** — selectable cards
2. **Choose a service** — each with its own length (e.g. a 30-min cut, a 15-min beard)
3. **Pick a day** — an on-brand month calendar
4. **Choose a time** — live open slots from the API

Signed in, the page adapts to who's looking: customers book, barbers see their
agenda and manage their schedule and services, and the owner also gets the
branding controls. The shop name, colours, logo and availability all come from
the backend API.

## Structure

```
shop/
├── state.py   # the page's data and how it talks to the API
├── views.py   # the page's components (cards, calendar, lists)
├── ui.py      # the small design system: colours, cards, shared pieces
└── shop.py    # the page shell and layout
rxconfig.py    # Reflex config: ports and the theme
assets/        # static files served at the web root (e.g. the favicon)
```

Colours and the logo are owner-configurable live from the site — see **Configure
for your shop** in the [top-level README](../README.md).

## Running

The backend API must be reachable (see [`../backend`](../backend)). Point the UI
at it with `API_URL`:

```bash
uv sync
API_URL=http://localhost:8000 uv run reflex run
```

- **Website** — <http://localhost:3000>

`API_URL` is where the UI calls the booking API from the server (defaults to
`http://localhost:8000`). `PUBLIC_API_URL` is the browser-facing backend URL used
for the logo and favicon (defaults to `API_URL`). Reflex's own event backend runs
on `8001` so it doesn't clash with the API on `8000`.

### In Docker

The root `docker compose` builds and runs this UI for you alongside the backend
and a dev mail server — see the [top-level README](../README.md).
