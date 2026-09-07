from typing import Optional, Protocol, List


class NotificationProvider(Protocol):
    async def send_quote_request_notification(
        self,
        supplier_id: str,
        supplier_name: str,
        supplier_contact: str,
        channel: str,  # "whatsapp", "email", "sms"
        boq_title: str,
        line_item_description: str,
        quantity: float,
        unit: str,
        response_deadline_iso: str,
        submission_link: str,
    ) -> bool:
        """Dispatches quote request notification to matched supplier."""
        ...
