from app.core.config import settings
from app.integrations.notifications.base import NotificationProvider
from app.integrations.notifications.console import ConsoleNotificationProvider
from app.integrations.notifications.email import EmailNotificationProvider
from app.integrations.notifications.webhook import WebhookNotificationProvider

_notification_instance: NotificationProvider = None


def get_notification_provider() -> NotificationProvider:
    global _notification_instance
    if _notification_instance is None:
        provider_name = settings.notification_provider.lower()
        if provider_name in ("email", "smtp"):
            _notification_instance = EmailNotificationProvider()
        elif provider_name == "webhook":
            _notification_instance = WebhookNotificationProvider(
                webhook_url=settings.notification_webhook_url,
                auth_token=settings.notification_webhook_token,
            )
        else:
            _notification_instance = ConsoleNotificationProvider()
    return _notification_instance
