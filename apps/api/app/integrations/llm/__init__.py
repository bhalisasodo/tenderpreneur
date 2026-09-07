from app.core.config import settings
from app.integrations.llm.base import LLMProvider, ParseResultDTO, ParsedLineItemDTO
from app.integrations.llm.stub import StubLLMProvider
from app.integrations.llm.gemini import GeminiLLMProvider

_llm_instance: LLMProvider = None


def get_llm_provider() -> LLMProvider:
    global _llm_instance
    if _llm_instance is None:
        if settings.llm_provider == "gemini" or settings.gemini_api_key:
            _llm_instance = GeminiLLMProvider(api_key=settings.gemini_api_key)
        else:
            _llm_instance = StubLLMProvider()
    return _llm_instance

