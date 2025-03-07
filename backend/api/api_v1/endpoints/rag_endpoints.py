from fastapi import Query
from typing import Optional, List
from backend.interfaces.azure_ai_search import AzureSearchClient
from backend import config
import logging
from typing import Dict

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()

search_client = AzureSearchClient(
    service_url=config.AZURE_AI_SEARCH_SERVICE,
    index_name="ticket_index",
    api_key=config.AZURE_AI_SEARCH_API_KEY,
    vector_field="vector"
)


@router.get("/hybrid_search")
def hybrid_search(
    text_query: Optional[str] = Query(None, description="Text query for hybrid search"),
    embedding: Optional[List[float]] = Query(None, description="Embedding vector for hybrid search"),
    top_k: int = Query(10, description="Number of top results to return")
):
    """Perform hybrid search with optional text query and embedding."""
    results = search_client.hybrid_search(
        text_query=text_query,
        embedding=embedding if embedding else None,
        top_k=top_k
    )
    return results
