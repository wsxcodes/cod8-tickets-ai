import json

from fastapi import HTTPException
from semantic_kernel.contents.chat_history import ChatHistory

from backend.api.api_v1.endpoints.tickets_endpoints import get_ticket
from backend.dependencies import chat_completion, execution_settings, kernel
from backend.session_state import get_history


def get_existing_history(session_id: str) -> ChatHistory:
    history = get_history(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session history not found")
    return history


async def get_ticket_data(ticket_id: str):
    response = await get_ticket(ticket_id=ticket_id)
    ticket_json = json.loads(response.body.decode("utf-8"))
    ticket_text = ticket_json.get("title", "") + " " + ticket_json.get("description", "")
    return ticket_text, ticket_json


async def get_chat_completion_content(history, execution_settings, kernel):
    return await chat_completion.get_chat_message_content(
                chat_history=history,
                settings=execution_settings,
                kernel=kernel
            )
