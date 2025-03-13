from typing import Optional
from semantic_kernel.contents.chat_history import ChatHistory

session_histories = {}
context_ticket_ids = {}


def get_history(session_id: str) -> ChatHistory:
    if session_id not in session_histories:
        session_histories[session_id] = ChatHistory()
    return session_histories[session_id]


def get_current_context_ticket(session_id: str) -> Optional[str]:
    """
    Retrieve the current (active) ticket ID for the given session.
    Returns None if no ticket has been set.
    """
    return context_ticket_ids.get(session_id)


def set_current_context_ticket(session_id: str, ticket_id: str) -> None:
    """
    Set or update the current (active) ticket ID for the given session.
    """
    context_ticket_ids[session_id] = ticket_id
