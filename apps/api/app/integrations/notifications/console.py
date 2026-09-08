import logging
from typing import Dict, List
from app.integrations.notifications.base import NotificationProvider

logger = logging.getLogger("boqpro.notifications")


class ConsoleNotificationProvider:
    """Logs notifications to console and stores in-memory delivery log for inspectability."""

    def __init__(self):
        self.delivered_notifications: List[Dict] = []

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
        record = {
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "channel": channel,
            "recipient": supplier_contact,
            "boq_title": boq_title,
            "item": f"{quantity} {unit} of {line_item_description}",
            "deadline": response_deadline_iso,
            "link": submission_link,
        }
        self.delivered_notifications.append(record)
        print(f"\n🔔 [NOTIFICATION DISPATCHED] -> Channel: {channel.upper()} | Recipient: {supplier_contact} ({supplier_name})")
        print(f"   Project: {boq_title}")
        print(f"   Request: {quantity} {unit} - {line_item_description}")
        print(f"   Deadline: {response_deadline_iso}")
        print(f"   Direct Submission URL: {submission_link}\n")
        return True
