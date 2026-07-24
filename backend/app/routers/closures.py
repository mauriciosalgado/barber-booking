"""Shop closures — the owner blocks a period; overlapping appointments are cancelled."""

from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, status
from sqlmodel import col, select

from app.availability import cancel_appointments_between
from app.database import SessionDep
from app.models import Closure, ClosureCreate, ClosureRead
from app.notifications import notify_cancellation
from app.security import AdminUser

router = APIRouter(prefix="/closures", tags=["closures"])


@router.post("", response_model=ClosureRead, status_code=status.HTTP_201_CREATED)
def create_closure(
    data: ClosureCreate, session: SessionDep, admin: AdminUser
) -> ClosureRead:
    closure = Closure(**data.model_dump())
    session.add(closure)
    cancelled_count, notifications = cancel_appointments_between(
        session, closure.start_at, closure.end_at
    )
    session.commit()
    session.refresh(closure)
    for email, name, start_at in notifications:
        notify_cancellation(
            email,
            name,
            start_at,
            reason=closure.reason,
            caused_by_closure=True,
        )
    return ClosureRead(
        id=closure.id,  # type: ignore[arg-type]
        start_at=closure.start_at,
        end_at=closure.end_at,
        reason=closure.reason,
        cancelled_appointments=cancelled_count,
    )


@router.get("", response_model=list[ClosureRead])
def list_closures(session: SessionDep) -> Sequence[Closure]:
    return session.exec(select(Closure).order_by(col(Closure.start_at))).all()


@router.delete("/{closure_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_closure(closure_id: int, session: SessionDep, admin: AdminUser) -> None:
    closure = session.get(Closure, closure_id)
    if closure is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Closure not found")
    session.delete(closure)
    session.commit()
