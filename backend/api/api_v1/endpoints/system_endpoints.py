import logging
from collections import defaultdict
from typing import Dict

from fastapi import APIRouter, Depends, Query

from backend.decorators import log_endpoint

# Dictionary to store chat histories per session
# session_histories = defaultdict(ChatHistory)

logger = logging.getLogger(__name__)

router = APIRouter()


import uuid


@router.get("/create_it_support_session")
async def create_ai_history_session():
    # session_id = str(uuid.uuid4())  # Generate a unique session ID
    # session_histories[session_id] = ChatHistory()  # Initialize chat history for this session
    # return {"session_id": session_id}
    return {"xxx":"todo"}  # NoQA
