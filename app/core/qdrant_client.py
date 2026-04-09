import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PayloadSchemaType
from qdrant_client.http import exceptions
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Qdrant client
qdrant_client: QdrantClient = None


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((exceptions.UnexpectedResponse, ConnectionError))
)
async def init_qdrant():
    """Initialize Qdrant connection with retry logic and create collections."""
    global qdrant_client

    try:
        qdrant_client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            grpc_port=settings.QDRANT_GRPC_PORT,
            prefer_grpc=True,
        )

        # Test connection
        qdrant_client.get_collections()
        logger.info("Qdrant connection established at %s:%s", settings.QDRANT_HOST, settings.QDRANT_PORT)
    except Exception as e:
        logger.error("Failed to connect to Qdrant: %s", e)
        raise


def ensure_collection_exists(collection_name: str, vector_size: int):
    """Ensure a Qdrant collection exists with the given vector size.

    Also creates a keyword payload index on `doc_id` for O(log n) filtered search.
    """
    if qdrant_client is None:
        raise RuntimeError("Qdrant client not initialized. Call init_qdrant() first.")

    try:
        qdrant_client.get_collection(collection_name)
        logger.debug("Qdrant collection '%s' already exists", collection_name)
    except Exception:
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection '%s' (dim=%d)", collection_name, vector_size)

    # Ensure doc_id payload index exists for fast filtered searches.
    # create_payload_index is idempotent — safe to call on every startup.
    try:
        qdrant_client.create_payload_index(
            collection_name=collection_name,
            field_name="doc_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.debug("Payload index on doc_id ensured for '%s'", collection_name)
    except Exception as e:
        # May fail if index already exists with same schema — non-fatal
        logger.debug("Payload index check for '%s': %s", collection_name, e)


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client instance."""
    if qdrant_client is None:
        raise RuntimeError("Qdrant client not initialized. Call init_qdrant() first.")
    return qdrant_client
