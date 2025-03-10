import logging
import uuid
from typing import Dict

from fastapi import APIRouter, Request

from backend.decorators import log_endpoint

logger = logging.getLogger(__name__)

router = APIRouter()

# Ensure logging is properly configured
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@router.get("/refresh_session_id", response_model=Dict[str, str])
@log_endpoint
async def refresh_session_id(request: Request):
    """Refresh the session ID."""
    session_id = str(uuid.uuid4())
    request.session["session_id"] = session_id  # Store in session
    logger.info(f"Generated and stored new session_id: {session_id}")
    return {"session_id": session_id}
