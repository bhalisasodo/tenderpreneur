import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_supplier_matching(client: AsyncClient, seeded_entities: dict):
    token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Match building materials in KwaZulu-Natal
    res = await client.get(
        "/api/v1/suppliers/match?category=building-materials&region=KwaZulu-Natal",
        headers=headers,
    )
    assert res.status_code == 200
    matches = res.json()
    assert len(matches) >= 1
    matched_names = [m["legal_name"] for m in matches]
    assert "Durban Builders Hub" in matched_names

    # Match concrete in Gauteng
    res_gp = await client.get(
        "/api/v1/suppliers/match?category=concrete&region=Gauteng",
        headers=headers,
    )
    assert res_gp.status_code == 200
    gp_matches = res_gp.json()
    gp_names = [m["legal_name"] for m in gp_matches]
    assert "AfriReady Concrete Solutions" in gp_names
