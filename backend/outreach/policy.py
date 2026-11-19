"""Compuerta de envío. development y test no pueden salir de dry-run."""

from backend.core.security_policy import outreach_is_live

__all__ = ["OutreachDeliveryBlocked", "outreach_is_live"]


class OutreachDeliveryBlocked(RuntimeError):
    """El proceso intentó un envío real sin autorización de entorno."""
