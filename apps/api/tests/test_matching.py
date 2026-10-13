import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_supplier_matching(client: AsyncClient, seeded_entities: dict):
    token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Match building materials in the eThekwini pilot region
    res = await client.get(
        "/api/v1/suppliers/match?category=building-materials&region=eThekwini",
        headers=headers,
    )
    assert res.status_code == 200
    matches = res.json()
    assert len(matches) >= 1
    matched_names = [m["legal_name"] for m in matches]
    assert "Durban Builders Hub" in matched_names

    electrical_res = await client.get(
        "/api/v1/suppliers/match?category=electrical&region=eThekwini",
        headers=headers,
    )
    assert electrical_res.status_code == 200
    assert electrical_res.json() == []

    # The supplier network is intentionally not active outside eThekwini.
    res_gp = await client.get(
        "/api/v1/suppliers/match?category=concrete&region=Gauteng",
        headers=headers,
    )
    assert res_gp.status_code == 200
    assert res_gp.json() == []
