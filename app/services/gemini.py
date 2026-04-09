import asyncio
import logging
import os
from typing import Optional, AsyncGenerator
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for Gemini AI integration with retry logic and streaming support."""

    def __init__(self):
        self.enabled = False
        self.model = None
        self._initialize()

    def _initialize(self):
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        model_name = settings.GEMINI_MODEL or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        if not api_key:
            logger.warning("GEMINI_API_KEY not set — answers will use basic fallback formatting")
            self.enabled = False
            return

        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            self.enabled = True
            logger.info("Gemini API initialized with model: %s", model_name)
        except Exception as e:
            logger.warning("Error initializing Gemini: %s", e)
            self.enabled = False

    def _build_prompt(self, query: str, context: str) -> str:
        return f"""You are an expert documentation assistant. Provide accurate, helpful answers using the provided context when available, and your general knowledge when the context is insufficient.

CONTEXT FROM DOCUMENTATION:
{context}

USER QUESTION: {query}

INSTRUCTIONS:
1. Use the provided context as your primary source. Supplement with general knowledge when context is incomplete.
2. For code queries: produce ONE complete, working code example combining all required pieces. Include imports, setup, and error handling.
3. For definition/concept queries: give a clear explanation first, then supporting details.
4. Format responses in Markdown. Use code blocks with language tags (```python, ```javascript, etc.).
5. If context has no relevant information, answer from general knowledge but be transparent.
6. Keep responses concise and well-structured.

ANSWER:"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def generate_answer(self, query: str, context: str) -> Optional[str]:
        """Generate answer using Gemini AI with automatic retry on failure."""
        if not self.enabled or not self.model:
            return None

        try:
            response = self.model.generate_content(
                self._build_prompt(query, context),
                generation_config={
                    "temperature": 0.3,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                }
            )
            return response.text
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            raise

    async def stream_answer(self, query: str, context: str) -> AsyncGenerator[str, None]:
        """Stream answer tokens from Gemini API as an async generator.

        The Gemini SDK is synchronous, so we run it in a thread pool via
        asyncio.to_thread() to avoid blocking the event loop.
        """
        if not self.enabled or not self.model:
            yield "Gemini is not configured. Please set GEMINI_API_KEY."
            return

        try:
            prompt = self._build_prompt(query, context)
            config = {
                "temperature": 0.3,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }

            def _collect_chunks() -> list:
                resp = self.model.generate_content(prompt, generation_config=config, stream=True)
                return [chunk.text for chunk in resp if chunk.text]

            chunks = await asyncio.to_thread(_collect_chunks)
            for chunk in chunks:
                yield chunk

        except Exception as e:
            logger.error("Gemini streaming error: %s", e)
            yield f"\n\n[Error generating response: {e}]"


# Global Gemini service instance
gemini_service = GeminiService()
