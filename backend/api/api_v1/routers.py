from fastapi import APIRouter

from backend.api.api_v1.endpoints import (generic_endpoints, llm_endpoints,
                                          search_endpoints, tickets_endpoints,
                                          workers_endpoints, rag_endpoints)

api_router = APIRouter()

# Generic Endpoints
api_router.include_router(
    generic_endpoints.router,
    tags=["Generic"]
)

# LLM Endpoints
api_router.include_router(
    llm_endpoints.router,
    tags=["LLM"]
)

# Search Endpoints
api_router.include_router(
    search_endpoints.router,
    tags=["Search"]
)

# RAG Endpoints
api_router.include_router(
    rag_endpoints.router,
    tags=["RAG"]
)

# Tickets Endpoints
api_router.include_router(
    tickets_endpoints.router,
    tags=["Tickets"]
)

# Workers Endpoints
api_router.include_router(
    workers_endpoints.router,
    tags=["Workers"]
)
