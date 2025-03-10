import logging
from typing import Dict

from fastapi import APIRouter

from backend.decorators import log_endpoint

logger = logging.getLogger(__name__)

router = APIRouter()


# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@router.get("/health")
@log_endpoint
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "OK",
        "message": "Application is healthy",
    }
