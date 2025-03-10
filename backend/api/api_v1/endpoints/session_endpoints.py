import logging
import uuid
from typing import Dict

from fastapi import APIRouter, Request

from backend.decorators import log_endpoint
from backend.dependencies import get_history, session_histories

logger = logging.getLogger(__name__)

router = APIRouter()

# Ensure logging is properly configured
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@router.get("/get_session_id", response_model=Dict[str, str])
@log_endpoint
async def get_session_id(request: Request):
    """Return the current session id."""
    session_id = request.session.get("session_id", "")
    if session_id:
        logger.info("Retrieved session id: %s", session_id)
        return {"session_id": session_id}
    else:
        logger.info("No session id present in session")
        return {"message": "No session id set."}


@router.get("/refresh_session_id", response_model=Dict[str, str])
@log_endpoint
async def refresh_session_id(request: Request):
    """Refresh the session ID."""
    session_id = str(uuid.uuid4())
    request.session["session_id"] = session_id  # Store in session
    get_history(session_id)
    logger.info("Generated and stored new session_id: %s", session_id)
    return {"session_id": session_id}


@router.get("/clear_session_id", response_model=Dict[str, str])
@log_endpoint
async def clear_session_id(request: Request):
    """Clear the session ID."""
    old_session_id = request.session.get("session_id", "")
    request.session["session_id"] = ""  # Clear session ID
    if old_session_id in session_histories:
        del session_histories[old_session_id]
        logger.info("Removed chat history for session_id: %s", old_session_id)
    logger.info("Cleared session ID")
    return {"message": "Session ID cleared"}


@router.get("/count_session_ids", response_model=Dict[str, int])
@log_endpoint
async def count_session_ids(request: Request):
    """Count the number of active session IDs."""
    count = len(session_histories)
    logger.info("Active session ID count: %d", count)
    return {"count": count}


@router.get("/list_session_ids", response_model=Dict[str, list])
@log_endpoint
async def list_session_ids(request: Request):
    """List all active session IDs."""
    session_ids = list(session_histories.keys())
    logger.info("Listing all active session IDs: %s", session_ids)
    return {"session_ids": session_ids}
