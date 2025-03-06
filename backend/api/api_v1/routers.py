from fastapi import APIRouter

from backend.api.api_v1.endpoints import generic_endpoints, workers_endpoints, llm_endpoints, tickets_endpoints

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
