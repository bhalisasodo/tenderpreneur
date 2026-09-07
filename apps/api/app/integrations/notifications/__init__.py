from app.core.config import settings
from app.integrations.notifications.base import NotificationProvider
from app.integrations.notifications.console import ConsoleNotificationProvider
from app.integrations.notifications.email import EmailNotificationProvider

_notification_instance: NotificationProvider = None


def get_notification_provider() -> NotificationProvider:
    global _notification_instance
    if _notification_instance is None:
        if settings.notification_provider.lower() in ("email", "smtp"):
            _notification_instance = EmailNotificationProvider()
        else:
            _notification_instance = ConsoleNotificationProvider()
    return _notification_instance

