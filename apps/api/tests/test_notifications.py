import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import NotificationDelivery


@pytest.mark.asyncio
async def test_broadcast_records_delivery_and_absolute_submission_link(
    client: AsyncClient,
    db_session: AsyncSession,
    seeded_entities: dict,
):
    headers = {"Authorization": f"Bearer {seeded_entities['contractor_token']}"}
    boq = await client.post(
        "/api/v1/boqs",
        headers=headers,
        json={"title": "Durban Materials RFQ", "region": "KwaZulu-Natal"},
    )
    item = await client.post(
        f"/api/v1/boqs/{boq.json()['id']}/line-items",
        headers=headers,
        json={
            "description": "25MPa ready-mix concrete delivered in Durban",
            "quantity": 10,
            "unit": "m3",
            "category": "concrete",
        },
    )
    request = await client.post(
        "/api/v1/quote-requests",
        headers=headers,
        json={"line_item_id": item.json()["id"], "response_deadline": "2026-12-31T23:59:59Z"},
    )

    response = await client.post(
        f"/api/v1/quote-requests/{request.json()['id']}/broadcast",
        headers=headers,
    )
    assert response.status_code == 200

    deliveries = await db_session.execute(select(NotificationDelivery))
    records = deliveries.scalars().all()
    assert records
    assert all(record.status == "sent" for record in records)
    assert all(record.channel == "whatsapp" for record in records)

    from app.integrations.notifications.console import ConsoleNotificationProvider
    from app.integrations.notifications import get_notification_provider

    provider = get_notification_provider()
    assert isinstance(provider, ConsoleNotificationProvider)
    assert provider.delivered_notifications
    assert provider.delivered_notifications[-1]["link"].startswith("http://localhost:3000/supplier/quote-requests/")
