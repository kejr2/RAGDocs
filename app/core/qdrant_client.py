from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from qdrant_client.http import exceptions
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

# Global Qdrant client
qdrant_client: QdrantClient = None


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((exceptions.UnexpectedResponse, ConnectionError))
)
async def init_qdrant():
    """Initialize Qdrant connection with retry logic and create collections"""
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
        
        # Collections will be created dynamically with correct dimensions when needed
        print("✅ Qdrant connection established")
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")
        raise


def ensure_collection_exists(collection_name: str, vector_size: int):
    """Ensure a Qdrant collection exists with the given vector size"""
    if qdrant_client is None:
        raise RuntimeError("Qdrant client not initialized. Call init_qdrant() first.")
    
    try:
        qdrant_client.get_collection(collection_name)
        print(f"✅ Qdrant collection '{collection_name}' already exists")
    except:
        # Create collection with specified vector size
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        print(f"✅ Created Qdrant collection '{collection_name}' with size {vector_size}")


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client instance"""
    if qdrant_client is None:
        raise RuntimeError("Qdrant client not initialized. Call init_qdrant() first.")
    return qdrant_client

