import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import NotificationDelivery


@pytest.mark.asyncio
async def test_console_broadcast_records_failed_delivery_without_exposing_link(
    client: AsyncClient,
    db_session: AsyncSession,
    seeded_entities: dict,
):
    headers = {"Authorization": f"Bearer {seeded_entities['contractor_token']}"}
    boq = await client.post(
        "/api/v1/boqs",
        headers=headers,
        json={"title": "Durban Materials RFQ", "region": "eThekwini"},
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
    assert all(record.status == "failed" for record in records)
    assert all(record.channel == "whatsapp" for record in records)

    assert response.json()["notification_failed_count"] == len(records)


@pytest.mark.asyncio
async def test_broadcast_reports_delivery_failures_and_allows_retry(
    client: AsyncClient,
    db_session: AsyncSession,
    seeded_entities: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    class StubProvider:
        def __init__(self, result: bool):
            self.result = result
            self.submission_links = []

        async def send_quote_request_notification(self, **kwargs) -> bool:
            self.submission_links.append(kwargs["submission_link"])
            return self.result

    contractor_headers = {"Authorization": f"Bearer {seeded_entities['contractor_token']}"}
    failed_provider = StubProvider(False)
    successful_provider = StubProvider(True)
    boq = await client.post(
        "/api/v1/boqs",
        headers=contractor_headers,
        json={"title": "Delivery retry test", "region": "eThekwini"},
    )
    item = await client.post(
        f"/api/v1/boqs/{boq.json()['id']}/line-items",
        headers=contractor_headers,
        json={
            "description": "Supply concrete aggregate to construction site",
            "quantity": 12,
            "unit": "m3",
            "category": "concrete",
        },
    )
    request = await client.post(
        "/api/v1/quote-requests",
        headers=contractor_headers,
        json={"line_item_id": item.json()["id"], "response_deadline": "2026-12-31T23:59:59Z"},
    )
    broadcast_url = f"/api/v1/quote-requests/{request.json()['id']}/broadcast"

    monkeypatch.setattr(
        "app.domains.quotes.router.get_notification_provider",
        lambda: failed_provider,
    )
    failed = await client.post(broadcast_url, headers=contractor_headers)
    assert failed.status_code == 200
    assert failed.json()["notification_failed_count"] == 2
    assert failed.json()["notification_accepted_count"] == 0

    monkeypatch.setattr(
        "app.domains.quotes.router.get_notification_provider",
        lambda: successful_provider,
    )
    retried = await client.post(broadcast_url, headers=contractor_headers)
    assert retried.status_code == 200
    assert retried.json()["notification_attempted_count"] == 2
    assert retried.json()["notification_accepted_count"] == 2

    records_result = await db_session.execute(select(NotificationDelivery))
    records = records_result.scalars().all()
    assert len(records) == 4
    assert sum(record.status == "failed" for record in records) == 2
    assert sum(record.status == "sent" for record in records) == 2
    assert all("#access_token=" in link for link in successful_provider.submission_links)
    assert all("?access_token=" not in link for link in successful_provider.submission_links)
