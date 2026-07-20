# barber-booking Helm chart

One install = one shop. Install it again with a different release name and
values file for another shop on the same cluster.

## GitOps (ArgoCD)

This chart is designed to be referenced directly from your GitOps repo as a
"local"/path source — no chart repository or `helm push` needed, ArgoCD just
renders `charts/barber-booking` out of this git repo at whatever revision you
pin.

Two things ArgoCD does **not** do for you, which stay outside this chart:

1. **Building/pushing images.** Helm/ArgoCD only deploy manifests — your CI
   still needs to build `backend/` and `frontend/` and push them to a
   registry ArgoCD's cluster can pull from. Point `image.*.repository/tag` at
   the result.
2. **Secrets.** Don't put `jwtSecret`, `shop.owner.password`, or SMTP
   credentials in a values file committed to your GitOps repo. Instead:
   - create a Kubernetes Secret named e.g. `<shop>-backend-secret` with keys
     `JWT_SECRET`, `OWNER_PASSWORD`, `SMTP_USERNAME`, `SMTP_PASSWORD` — via
     whatever your GitOps setup already uses for this (Sealed Secrets,
     External Secrets Operator, SOPS, a cloud secret manager, or just
     `kubectl create secret` once, out of band), and
   - set `existingSecret: <that name>` in this shop's values. The chart then
     skips creating its own Secret and reads from yours. Same pattern for the
     built-in Postgres's password via `postgresql.existingSecret`.

Example `Application`, in your GitOps repo:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ribeiro-barbeiro
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/you/barber-booking.git
    targetRevision: main # or a tag, e.g. v1.0.0
    path: charts/barber-booking
    helm:
      valueFiles:
        - $values/shops/ribeiro/values.yaml # values live in your GitOps repo
  sources: # if values live in a separate repo, use the multi-source form:
    - repoURL: https://github.com/you/barber-booking.git
      targetRevision: main
      path: charts/barber-booking
    - repoURL: https://github.com/you/gitops.git
      targetRevision: main
      ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: ribeiro-barbeiro
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

(The two `source`/`sources` blocks above are alternatives — use `source`
with an inline `valueFiles` path if your values live in the same repo as
this chart, or the multi-source `sources` form if they live in your
separate GitOps repo, which is the common pattern.)

One `Application` per shop; each just needs its own values file and its own
`existingSecret`.

## First shop — what to configure

1. **Build and push images** to a registry your cluster can pull from (this
   is outside the chart — your existing CI does this):
   `ghcr.io/you/barber-booking-backend:v1.0.0` and `...-frontend:v1.0.0`.
2. **DNS**: point two hostnames at your Ingress controller's load balancer —
   one for the website, one for the API (e.g. `shop.example.com` and
   `api.shop.example.com`). They must be different hosts (see `values.yaml`
   comments on `ingress.host`/`ingress.apiHost` for why).
3. **TLS**: either have cert-manager issue a cert automatically (uncomment
   the `cert-manager.io/cluster-issuer` annotation in `ingress.annotations`)
   or bring your own cert as a Secret named `ingress.tls.secretName`.
4. **Secrets**: create the backend Secret out-of-band (see GitOps section
   above) with `JWT_SECRET` (generate: `openssl rand -hex 32`),
   `OWNER_PASSWORD` (the owner's login password), and `SMTP_USERNAME`/
   `SMTP_PASSWORD` if your mail provider needs them. Reference it via
   `existingSecret`.
5. **Values file** for the shop — minimum needed (everything else has
   sensible defaults; see `values.yaml` for the full commented list):

   ```yaml
   existingSecret: "ribeiro-backend-secret"

   shop:
     name: "Ribeiro Barbeiro"
     owner:
       name: "Paquito"
       email: "paquito@ribeirobarbeiro.pt"
     # brand/background/headline are optional — the owner can change all
     # three live from the UI after first login anyway.

   image:
     backend:
       repository: ghcr.io/you/barber-booking-backend
       tag: "v1.0.0"
     frontend:
       repository: ghcr.io/you/barber-booking-frontend
       tag: "v1.0.0"

   ingress:
     className: nginx # or whatever your cluster's Ingress controller is
     host: shop.ribeirobarbeiro.pt
     apiHost: api.ribeirobarbeiro.pt

   email:
     smtpHost: "smtp.your-provider.com"
     smtpFrom: "no-reply@ribeirobarbeiro.pt"
     # smtpUsername/smtpPassword come from existingSecret, not here.
   ```

6. **Sync** in ArgoCD (or let `syncPolicy.automated` do it). Watch the
   rollout: `kubectl get pods -n ribeiro-barbeiro -w`.
7. **Log in** as the owner at `https://shop.ribeirobarbeiro.pt` with the
   email above and the password from your Secret, and finish setup from the
   UI (logo, brand colours, working hours, services — see the root
   `README.md`'s "How it works").

That's the whole first-shop checklist. Everything else (database choice,
replicas, resource limits, CORS) has a working default — only touch it if
you have a specific reason to (see below).

## Database

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
  existingSecret: "ribeiro-postgres-secret" # POSTGRES_PASSWORD key
```

## Local testing (optional, no registry)

Not part of the GitOps flow above — just for trying the chart out by hand on
`kind`/`minikube`/`k3d`/Docker Desktop. See the commands at the top of
`values-local.yaml`.

## Why backend/frontend replicas stay at 1

- **Backend**: SQLite is a single file (one writer at a time), and the login
  rate limiter counts in memory per pod. Scaling needs Postgres *and* a
  shared rate-limit store (e.g. Redis) — neither is wired up here.
- **Frontend**: Reflex keeps UI state in memory per worker. Scaling needs
  Reflex's Redis-backed state manager — not wired up here either.

Both are fine for a single shop's traffic. See the root `README.md`'s
"Known limitations" section for the full reasoning.
