import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("boqpro.notifications.email")


class EmailNotificationProvider:
    """Outbound email notification provider supporting standard SMTP/TLS with fallback logging."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
        from_email: Optional[str] = None,
    ):
        self.host = host or settings.smtp_host
        self.port = port or settings.smtp_port
        self.username = username or settings.smtp_username
        self.password = password or settings.smtp_password
        self.use_tls = use_tls if use_tls is not None else settings.smtp_use_tls
        self.from_email = from_email or settings.smtp_from_email or "noreply@boqpro.co.za"

    def _send_sync(self, msg: EmailMessage) -> bool:
        if not self.host:
            logger.info(
                "SMTP host not configured. Notification recorded in dry-run mode for: %s",
                msg["To"],
            )
            return True

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
            return True
        except Exception as exc:
            logger.error("Failed to send email to %s via SMTP: %s", msg["To"], exc)
            return False

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
        msg = EmailMessage()
        msg["Subject"] = f"Request for Quotation: {boq_title}"
        msg["From"] = self.from_email
        msg["To"] = supplier_contact

        body = f"""Dear {supplier_name},

You have received an urgent Request for Quotation (RFQ) via BoQPro.

Project: {boq_title}
Item: {quantity} {unit} of {line_item_description}
Response Deadline: {response_deadline_iso}

To review item specifications and submit your tender price online, please use the secure link below:
{submission_link}

Regards,
The BoQPro Procurement Team
"""
        msg.set_content(body)

        # Offload sync SMTP network call to async worker threadpool
        return await asyncio.to_thread(self._send_sync, msg)
