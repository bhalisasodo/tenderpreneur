import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("boqpro.notifications.email")


class EmailNotificationProvider:
    """Outbound email notification provider supporting standard SMTP/TLS with formatted HTML & plain-text fallbacks."""

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
        self.from_email = from_email or settings.smtp_from_email or "BoQPro Sourcing <quotes@boqpro.co.za>"

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
        msg["Subject"] = f"Urgent RFQ: {boq_title} — {quantity} {unit}"
        msg["From"] = self.from_email
        msg["To"] = supplier_contact

        plain_text = f"""Dear {supplier_name},

You have received an urgent Request for Quotation (RFQ) via the BoQPro verified contractor network.

Project / Tender: {boq_title}
Item Required: {quantity} {unit} of {line_item_description}
Response Deadline: {response_deadline_iso}

To review item specifications and submit your competitive unit rate online in under 60 seconds, tap the secure link below:
{submission_link}

Regards,
BoQPro Supplier Sourcing Team
support@boqpro.co.za | https://boqpro.co.za
"""
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; }}
    .header {{ background-color: #12233F; padding: 24px; text-align: center; color: #ffffff; }}
    .header h1 {{ margin: 0; font-size: 20px; font-weight: bold; letter-spacing: -0.5px; }}
    .badge {{ display: inline-block; background-color: #D9A94A; color: #12233F; font-size: 11px; font-weight: 800; padding: 3px 10px; border-radius: 12px; margin-bottom: 8px; text-transform: uppercase; }}
    .content {{ padding: 28px 24px; }}
    .item-card {{ background-color: #f1f5f9; border-left: 4px solid #12233F; padding: 16px; border-radius: 8px; margin: 20px 0; }}
    .item-desc {{ font-size: 15px; font-weight: 700; color: #0f172a; margin-bottom: 6px; }}
    .item-meta {{ font-size: 13px; color: #475569; }}
    .btn {{ display: block; text-align: center; background-color: #059669; color: #ffffff; text-decoration: none; padding: 14px 24px; border-radius: 10px; font-weight: 700; font-size: 15px; margin: 24px 0 12px 0; }}
    .deadline {{ text-align: center; font-size: 12px; color: #e11d48; font-weight: 600; }}
    .footer {{ background-color: #f8fafc; padding: 16px 24px; text-align: center; font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="badge">BoQPro RFQ Alert</div>
      <h1>Request for Quotation</h1>
    </div>
    <div class="content">
      <p style="margin-top: 0;">Dear <strong>{supplier_name}</strong>,</p>
      <p>A tendering contractor has requested pricing on your verified trade catalog for the following project:</p>
      
      <div class="item-card">
        <div class="item-desc">{line_item_description}</div>
        <div class="item-meta">Required Quantity: <strong>{quantity} {unit}</strong></div>
        <div class="item-meta">Tender Reference: <strong>{boq_title}</strong></div>
      </div>

      <a href="{submission_link}" class="btn">Submit Quote Online (1-Click) &rarr;</a>
      
      <div class="deadline">Response Deadline: {response_deadline_iso}</div>
      <p style="font-size: 12px; color: #64748b; text-align: center; margin-top: 16px;">
        No login password required on mobile. Tap the button above to enter your unit price in ZAR.
      </p>
    </div>
    <div class="footer">
      BoQPro &bull; Bid-Pricing Infrastructure for South African Contractors &amp; Suppliers<br>
      © 2026 BoQPro (Pty) Ltd. All rights reserved.
    </div>
  </div>
</body>
</html>
"""
        msg.set_content(plain_text)
        msg.add_alternative(html_content, subtype="html")

        # Offload sync SMTP network call to async worker threadpool
        return await asyncio.to_thread(self._send_sync, msg)
