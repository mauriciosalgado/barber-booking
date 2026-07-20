#!/usr/bin/env bash
# Build the backend/frontend images locally and deploy straight to a local
# Kubernetes cluster — no registry, no CI pipeline, no image-pull credentials.
#
# Works with kind, minikube, k3d, and Docker Desktop's built-in cluster
# (detected from your current `kubectl` context). Anything else is assumed
# to already share the local Docker daemon.
#
# Usage:
#   ./scripts/deploy-local.sh                  # install/upgrade release "shop"
#   RELEASE=other ./scripts/deploy-local.sh     # a second shop, same cluster
#   ./scripts/deploy-local.sh -f my-values.yaml # extra Helm args pass through
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

TAG="${TAG:-dev}"
RELEASE="${RELEASE:-shop}"
NAMESPACE="${NAMESPACE:-default}"
BACKEND_IMAGE="barber-booking-backend:${TAG}"
FRONTEND_IMAGE="barber-booking-frontend:${TAG}"

echo "==> Building images (tag: ${TAG})"
docker build -t "$BACKEND_IMAGE" ./backend
docker build -t "$FRONTEND_IMAGE" ./frontend

CONTEXT="$(kubectl config current-context 2>/dev/null || true)"
echo "==> Current kube context: ${CONTEXT:-<none>}"

case "$CONTEXT" in
  kind-*)
    CLUSTER="${CONTEXT#kind-}"
    echo "==> Loading images into kind cluster '$CLUSTER'"
    kind load docker-image "$BACKEND_IMAGE" "$FRONTEND_IMAGE" --name "$CLUSTER"
    ;;
  minikube | minikube-*)
    echo "==> Loading images into minikube"
    minikube image load "$BACKEND_IMAGE"
    minikube image load "$FRONTEND_IMAGE"
    ;;
  k3d-*)
    CLUSTER="${CONTEXT#k3d-}"
    echo "==> Importing images into k3d cluster '$CLUSTER'"
    k3d image import "$BACKEND_IMAGE" "$FRONTEND_IMAGE" -c "$CLUSTER"
    ;;
  docker-desktop)
    echo "==> Docker Desktop's cluster shares the local Docker daemon — nothing to load."
    ;;
  "")
    echo "==> No kube context set. Point kubectl at a cluster first (kind/minikube/k3d)." >&2
    exit 1
    ;;
  *)
    echo "==> Unrecognised context '$CONTEXT' — assuming it shares the local Docker daemon."
    echo "    If pods show ImagePullBackOff, load '$BACKEND_IMAGE' and"
    echo "    '$FRONTEND_IMAGE' into it yourself first."
    ;;
esac

echo "==> Installing/upgrading Helm release '$RELEASE' in namespace '$NAMESPACE'"
helm upgrade --install "$RELEASE" ./charts/barber-booking \
  --namespace "$NAMESPACE" --create-namespace \
  -f charts/barber-booking/values-local.yaml \
  --set image.backend.repository=barber-booking-backend \
  --set image.backend.tag="$TAG" \
  --set image.frontend.repository=barber-booking-frontend \
  --set image.frontend.tag="$TAG" \
  "$@"

echo "==> Done. Watch it come up with: kubectl get pods -n $NAMESPACE -w"
echo "==> Then, in two other terminals:"
echo "      kubectl port-forward -n $NAMESPACE svc/${RELEASE}-barber-booking-frontend 3000:3000 8001:8001"
echo "      kubectl port-forward -n $NAMESPACE svc/${RELEASE}-barber-booking-backend 8000:8000"
echo "    Website: http://localhost:3000   API docs: http://localhost:8000/docs"
