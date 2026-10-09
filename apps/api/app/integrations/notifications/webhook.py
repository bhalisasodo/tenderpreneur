import logging
from typing import Optional
import httpx
from app.integrations.notifications.base import NotificationProvider

logger = logging.getLogger("boqpro.notifications.webhook")


class WebhookNotificationProvider(NotificationProvider):
    """Outbound webhook notification provider for SMS / WhatsApp aggregators (e.g. Twilio, Africa's Talking)."""

    def __init__(self, webhook_url: Optional[str] = None, auth_token: Optional[str] = None):
        self.webhook_url = webhook_url
        self.auth_token = auth_token

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
        if not self.webhook_url:
            logger.info(
                "[WEBHOOK DRY-RUN] Alert dispatched for %s (%s): %s of %s -> %s",
                supplier_name,
                supplier_contact,
                quantity,
                line_item_description,
                submission_link,
            )
            return True

        payload = {
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "supplier_contact": supplier_contact,
            "channel": channel,
            "project_title": boq_title,
            "item_description": line_item_description,
            "quantity": quantity,
            "unit": unit,
            "deadline": response_deadline_iso,
            "submission_link": submission_link,
        }

        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self.webhook_url, json=payload, headers=headers)
                return res.is_success
        except Exception as exc:
            logger.error("Failed to post notification to webhook %s: %s", self.webhook_url, exc)
            return False
