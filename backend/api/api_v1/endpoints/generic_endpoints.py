import logging
from typing import Dict

from fastapi import APIRouter

from backend.decorators import log_endpoint

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
@log_endpoint
def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "OK",
        "message": "Application is healthy",
    }
