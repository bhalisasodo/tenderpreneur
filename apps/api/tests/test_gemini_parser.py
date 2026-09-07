import pytest
from app.integrations.llm.base import ParseResultDTO
from app.integrations.llm.gemini import GeminiLLMProvider
from app.integrations.llm.stub import StubLLMProvider
from app.integrations.llm import get_llm_provider


@pytest.mark.asyncio
async def test_gemini_provider_fallback_when_no_api_key():
    """Verify GeminiLLMProvider gracefully falls back to StubLLMProvider when no API key is configured."""
    provider = GeminiLLMProvider(api_key=None)
    sample_text = """
    Bill of Quantities: Civil Works
    Tender Ref: SANRAL-2026-042
    1.01 Excavation in earth for foundation trenches 250 m3
    1.02 Supply 25MPa ready-mix concrete 80 m3
    1.03 50kg Portland cement bags 300 no
    """
    res = await provider.parse_boq_document(sample_text, filename="tender_sample.txt")
    assert isinstance(res, ParseResultDTO)
    assert len(res.line_items) >= 3
    assert res.title_hint is not None
    assert any(item.category == "earthworks" for item in res.line_items)
    assert any(item.category == "concrete" for item in res.line_items)
    assert any(item.category == "building-materials" for item in res.line_items)


@pytest.mark.asyncio
async def test_get_llm_provider_factory():
    """Verify get_llm_provider factory returns a valid LLMProvider implementation."""
    provider = get_llm_provider()
    assert hasattr(provider, "parse_boq_document")
