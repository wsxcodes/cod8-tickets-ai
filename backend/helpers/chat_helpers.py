from fastapi import HTTPException
from semantic_kernel.contents.chat_history import ChatHistory

from backend.dependencies import get_history


def get_existing_history(session_id: str) -> ChatHistory:
    history = get_history(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session history not found")
    return history
