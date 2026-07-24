"""System endpoints (health and readiness checks)."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.availability import shop_now
from app.config import get_settings
from app.database import SessionDep

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: the process is up and serving."""
    settings = get_settings()
    return {
        "status": "ok",
        "shop": settings.shop_name,
        "today": shop_now().date().isoformat(),
        "timezone": settings.shop_timezone,
    }


@router.get("/health/ready")
def ready(session: SessionDep) -> dict[str, str]:
    """Readiness: the app can reach its database."""
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Database unavailable"
        ) from exc
    return {"status": "ready"}
