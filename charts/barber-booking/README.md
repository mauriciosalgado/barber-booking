# barber-booking Helm chart

One install = one shop. Install it again with a different release name and
`values-<shop>.yaml` for another shop on the same cluster.

## Local, no-registry deployment

For trying this out on `kind`, `minikube`, `k3d`, or Docker Desktop's
built-in Kubernetes — no image registry, no CI pipeline, no pull
credentials:

```bash
./scripts/deploy-local.sh
```

This builds `backend/` and `frontend/` with `docker build`, loads the images
straight into your cluster (`kind load docker-image` / `minikube image
load` / `k3d image import`, or nothing extra needed on Docker Desktop, whose
cluster shares your local Docker daemon), then runs `helm upgrade --install`
using `values-local.yaml` (dev-only secrets, no Ingress, plain http). Reach
it with `kubectl port-forward` — the script prints the exact commands.

Run it again anytime you change code — it rebuilds and re-deploys.

## Production deployment

Requires a real image registry (build/push `backend/` and `frontend/` there
first) and an Ingress controller with TLS (e.g. nginx-ingress + cert-manager).

```bash
helm install ribeiro ./charts/barber-booking -f values-ribeiro.yaml
```

Minimum required values (see `values.yaml` for the full, commented list):

```yaml
jwtSecret: "" # openssl rand -hex 32
shop:
  name: "Ribeiro Barbeiro"
  owner:
    email: "me@myshop.pt"
    password: "a strong password"
image:
  backend:
    repository: ghcr.io/you/barber-booking-backend
    tag: "v1.0.0"
  frontend:
    repository: ghcr.io/you/barber-booking-frontend
    tag: "v1.0.0"
ingress:
  host: shop.example.com
  apiHost: api.shop.example.com
email:
  smtpHost: "smtp.your-provider.com"
  smtpUsername: "..."
  smtpPassword: "..."
```

### Database

SQLite (default) needs nothing extra — a 1Gi PVC is created automatically.
For Postgres, either point at a managed instance:

```yaml
database:
  type: postgres
  externalUrl: "postgresql://<user>:<secret>@<host>:5432/<database>"
```

or use the chart's built-in single-replica Postgres:

```yaml
database:
  type: postgres
postgresql:
  enabled: true
  password: "a strong password"
```

### Why backend/frontend replicas stay at 1

- **Backend**: SQLite is a single file (one writer at a time), and the login
  rate limiter counts in memory per pod. Scaling needs Postgres *and* a
  shared rate-limit store (e.g. Redis) — neither is wired up here.
- **Frontend**: Reflex keeps UI state in memory per worker. Scaling needs
  Reflex's Redis-backed state manager — not wired up here either.

Both are fine for a single shop's traffic. See the root `README.md`'s
"Known limitations" section for the full reasoning.
