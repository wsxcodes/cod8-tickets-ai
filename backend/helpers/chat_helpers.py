import json
from typing import Union
from fastapi import HTTPException
from semantic_kernel.contents.chat_history import ChatHistory

from backend.session_state import get_history
from backend.api.api_v1.endpoints.tickets_endpoints import get_ticket


def get_existing_history(session_id: str) -> ChatHistory:
    history = get_history(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session history not found")
    return history


def get_ticket(ticket_id: str):
    response = await get_ticket(ticket_id=ticket_id)
    ticket_json = json.loads(response.body.decode("utf-8"))
    ticket_text = ticket_json.get("title", "") + " " + ticket_json.get("description", "")
    return ticket_text, ticket_json
