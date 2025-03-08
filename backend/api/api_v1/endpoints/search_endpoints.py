import logging
from typing import List, Optional

from fastapi import APIRouter, Query

from backend import config
from backend.interfaces.azure_ai_search import AzureSearchClient

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
    top_k: int = Query(10, description="Number of top results to return"),
    include_vector: bool = Query(False, description="Whether to include vector in the response")
):
    """Perform hybrid search with optional text query and embedding."""
    results = search_client.hybrid_search(
        text_query=text_query,
        embedding=embedding if embedding else None,
        top_k=top_k
    )

    if not include_vector:
        for result in results:
            result.pop("vector", None)

    return results

@router.get("/fulltext_search")
def fulltext_search(
    text_query: str = Query(..., description="Text query for full-text search"),
    top_k: int = Query(10, description="Number of top results to return"),
    include_vector: bool = Query(False, description="Whether to include vector in the response")
):
    """Perform full-text search with the given query."""
    results = search_client.fulltext_search(
        text_query=text_query,
        top_k=top_k
    )

    if not include_vector:
        for result in results:
            result.pop("vector", None)

    return results


@router.get("/vector_search")
def vector_search(
    embedding: List[float] = Query(..., description="Embedding vector for vector search"),
    top_k: int = Query(10, description="Number of top results to return"),
    include_vector: bool = Query(False, description="Whether to include vector in the response")
):
    """Perform vector-based search with the given embedding."""
    results = search_client.vector_search(
        embedding=embedding,
        top_k=top_k
    )

    if not include_vector:
        for result in results:
            result.pop("vector", None)

    return results


@router.get("/get_document")
def get_document(doc_id: str = Query(..., description="ID of the document to retrieve")):
    """Retrieve a document by its ID."""
    result = search_client.get_document(doc_id)
    return result


@router.get("/list_documents")
def list_documents(
    batch_size: int = Query(1000, description="Number of documents to retrieve per batch"),
    limit: int = Query(10, description="Total number of documents to retrieve"),
    offset: int = Query(0, description="Number of documents to skip")
):
    """List documents in the index with optional limit and offset."""
    results = search_client.list_documents(batch_size=batch_size, limit=limit, offset=offset)
    return results
