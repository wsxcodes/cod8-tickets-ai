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


@router.get("/count_session_ids", response_model=Dict[str, int])
@log_endpoint
async def count_session_ids(request: Request):
    """Count the number of active session IDs."""
    session_store = request.session.get("session_store", {})
    count = len(session_store)
    logger.info("Active session ID count: %d", count)
    return {"count": count}

@router.get("/list_session_ids", response_model=Dict[str, list])
@log_endpoint
async def list_session_ids(request: Request):
    """List all active session IDs."""
    session_store = request.session.get("session_store", {})
    session_ids = list(session_store.keys())  # Extract session IDs
    logger.info("Listing all active session IDs: %s", session_ids)
    return {"session_ids": session_ids}

@router.get("/refresh_session_id", response_model=Dict[str, str])
@log_endpoint
async def refresh_session_id(request: Request):
    """Refresh the session ID."""
    session_id = str(uuid.uuid4())
    request.session["session_id"] = session_id  # Store in session
    logger.info(f"Generated and stored new session_id: {session_id}")
    return {"session_id": session_id}


@router.get("/clear_session_id", response_model=Dict[str, str])
@log_endpoint
async def clear_session_id(request: Request):
    """Clear the session ID."""
    request.session["session_id"] = ""  # Set session ID to blank
    logger.info("Cleared session ID")
    return {"message": "Session ID cleared"}
