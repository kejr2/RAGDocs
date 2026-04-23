import asyncio
import logging
import os
from typing import Optional, AsyncGenerator
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

logger = logging.getLogger(__name__)

ANSWER_MODEL = "claude-opus-4-5"
ENHANCE_MODEL = "claude-haiku-4-5-20251001"


class ClaudeService:
    """Service for Anthropic Claude integration with retry logic and streaming support."""

    def __init__(self):
        self.enabled = False
        self.client: Optional[anthropic.Anthropic] = None
        self._initialize()

    def _initialize(self):
        api_key = settings.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set — answers will use basic fallback formatting")
            self.enabled = False
            return
        try:
            self.client = anthropic.Anthropic(api_key=api_key)
            self.enabled = True
            logger.info("Claude API initialized (answer=%s, enhance=%s)", ANSWER_MODEL, ENHANCE_MODEL)
        except Exception as e:
            logger.warning("Error initializing Claude client: %s", e)
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
    def generate_answer(self, query: str, context: str, model: Optional[str] = None) -> Optional[str]:
        """Generate answer using Claude with automatic retry on failure."""
        if not self.enabled or not self.client:
            return None
        use_model = model or ANSWER_MODEL
        try:
            message = self.client.messages.create(
                model=use_model,
                max_tokens=2048,
                messages=[{"role": "user", "content": self._build_prompt(query, context)}]
            )
            return message.content[0].text
        except Exception as e:
            logger.error("Claude API error: %s", e)
            raise

    def enhance_query(self, prompt: str) -> Optional[str]:
        """Call Claude Haiku for fast, cheap query enhancement."""
        if not self.enabled or not self.client:
            return None
        try:
            message = self.client.messages.create(
                model=ENHANCE_MODEL,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            logger.error("Claude enhance error: %s", e)
            return None

    async def stream_answer(self, query: str, context: str, model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream answer tokens from Claude as an async generator."""
        if not self.enabled or not self.client:
            yield "Claude is not configured. Please set ANTHROPIC_API_KEY."
            return

        use_model = model or ANSWER_MODEL
        prompt = self._build_prompt(query, context)

        def _collect_chunks() -> list:
            chunks = []
            with self.client.messages.stream(
                model=use_model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    chunks.append(text)
            return chunks

        try:
            chunks = await asyncio.to_thread(_collect_chunks)
            for chunk in chunks:
                yield chunk
        except Exception as e:
            logger.error("Claude streaming error: %s", e)
            yield f"\n\n[Error generating response: {e}]"

    def count_tokens(self, query: str, context: str) -> int:
        """Estimate token count for a prompt (used for metrics logging)."""
        if not self.enabled or not self.client:
            return 0
        try:
            result = self.client.messages.count_tokens(
                model=ANSWER_MODEL,
                messages=[{"role": "user", "content": self._build_prompt(query, context)}]
            )
            return result.input_tokens
        except Exception:
            # Rough estimate: 1 token ≈ 4 chars
            return (len(query) + len(context)) // 4


# Global Claude service instance
claude_service = ClaudeService()
