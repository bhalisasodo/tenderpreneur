import logging

logger = logging.getLogger("boqpro.notifications")


class ConsoleNotificationProvider:
    """Development-only no-op that never reports a successful delivery."""

    async def send_quote_request_notification(
        self,
        supplier_id: str,
        supplier_name: str,
        supplier_contact: str,
        channel: str,
        boq_title: str,
        line_item_description: str,
        quantity: float,
        unit: str,
        response_deadline_iso: str,
        submission_link: str,
    ) -> bool:
        logger.warning(
            "Notification was not sent because the development console provider is configured."
        )
        return False
