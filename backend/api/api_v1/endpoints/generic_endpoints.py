import logging
from typing import Dict

from fastapi import APIRouter


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "OK",
        "message": "Application is healthy",
    }
