"""Best-effort customer notifications for booking lifecycle events."""

import logging
from datetime import datetime

from app.config import get_settings
from app.email import send_email

logger = logging.getLogger(__name__)


def notify_cancellation(
    email: str,
    name: str,
    start_at: datetime,
    *,
    reason: str | None = None,
    caused_by_closure: bool = False,
) -> None:
    """Tell a registered customer one appointment was cancelled by staff."""
    when = start_at.strftime("%d/%m/%Y às %H:%M")
    shop = get_settings().shop_name
    reason_line = f"\nMotivo: {reason.strip()}" if reason and reason.strip() else ""
    cause_line = (
        "\nEsta marcação foi cancelada devido a um fecho da barbearia."
        if caused_by_closure
        else ""
    )
    try:
        send_email(
            email,
            "Marcação cancelada",
            f"Olá {name},\n\n"
            f"A sua marcação em {shop} no dia {when} foi cancelada."
            f"{cause_line}{reason_line}\n\n"
            "Pode voltar a marcar quando quiser.",
        )
    except OSError as error:
        logger.warning("Could not send cancellation email to %s: %s", email, error)


def notify_series_cancellation(
    email: str, name: str, *, anchor_at: datetime, canceled_count: int
) -> None:
    """Tell a registered customer their standing weekly schedule was ended."""
    when = anchor_at.strftime("%A, %d/%m/%Y às %H:%M")
    shop = get_settings().shop_name
    count_line = (
        f"Foram canceladas {canceled_count} marcações futuras dessa série.\n\n"
        if canceled_count > 0
        else ""
    )
    try:
        send_email(
            email,
            "Horário fixo cancelado",
            f"Olá {name},\n\n"
            f"O seu horário fixo em {shop} ({when}) foi cancelado pela barbearia.\n\n"
            f"{count_line}"
            "Pode voltar a marcar quando quiser.",
        )
    except OSError as error:
        logger.warning(
            "Could not send recurring-cancellation email to %s: %s", email, error
        )
