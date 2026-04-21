from typing import List
from openai import AsyncOpenAI, APIConnectionError, RateLimitError, APIStatusError
from app.embeddings.base import EmbeddingsAdapter
from app.integrations.exceptions import ProviderAPIError
import structlog
import os

logger = structlog.get_logger(__name__)


class OpenAIAdapter(EmbeddingsAdapter):
    """
    OpenAI embeddings adapter with normalised error handling.
    All OpenAI-specific exceptions are trapped and re-raised as
    ProviderAPIError so upstream callers never depend on openai SDK types.
    """

    def __init__(self, model_name: str = "text-embedding-3-small"):
        self.model_name = model_name
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            logger.warning("OPENAI_API_KEY is not set — embedding calls will fail")
        self.client = AsyncOpenAI(api_key=api_key)

    async def embed_query(self, text: str) -> List[float]:
        if not text or not text.strip():
            return []

        try:
            response = await self.client.embeddings.create(
                input=text.replace("\n", " ").strip(),
                model=self.model_name,
            )
            return response.data[0].embedding
        except RateLimitError as e:
            logger.error("openai_rate_limit", model=self.model_name)
            raise ProviderAPIError(f"OpenAI rate-limited: {e}") from e
        except APIConnectionError as e:
            logger.error("openai_connection_error", model=self.model_name)
            raise ProviderAPIError(f"OpenAI unreachable: {e}") from e
        except APIStatusError as e:
            logger.error("openai_api_error", status=e.status_code, model=self.model_name)
            raise ProviderAPIError(f"OpenAI API error ({e.status_code})") from e
        except Exception as e:
            logger.error("openai_unexpected_error", error=str(e))
            raise ProviderAPIError(f"Embedding failed: {e}") from e

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        cleaned = [t.replace("\n", " ").strip() for t in texts if t and t.strip()]
        if not cleaned:
            return []

        try:
            response = await self.client.embeddings.create(
                input=cleaned, model=self.model_name
            )
            return [data.embedding for data in response.data]
        except RateLimitError as e:
            logger.error("openai_rate_limit_batch", model=self.model_name, count=len(cleaned))
            raise ProviderAPIError(f"OpenAI rate-limited: {e}") from e
        except APIConnectionError as e:
            logger.error("openai_connection_error_batch", model=self.model_name)
            raise ProviderAPIError(f"OpenAI unreachable: {e}") from e
        except APIStatusError as e:
            logger.error("openai_api_error_batch", status=e.status_code, model=self.model_name)
            raise ProviderAPIError(f"OpenAI API error ({e.status_code})") from e
        except Exception as e:
            logger.error("openai_unexpected_error_batch", error=str(e))
            raise ProviderAPIError(f"Embedding failed: {e}") from e
