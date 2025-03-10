import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from semantic_kernel.contents.chat_history import ChatHistory

from backend import config
from backend.dependencies import (chat_completion, execution_settings,
                                  get_history, kernel)
from backend.helpers.chat_helpers import get_existing_history

logger = logging.getLogger(__name__)
router = APIRouter()


class Question(BaseModel):
    question: str


TICKETS_DIR = config.TICKETS_DIR


@router.post("/support_enquiry")
async def support_enquiry(payload: Question, session_id: str, history: ChatHistory = Depends(get_existing_history)):
    try:
        if not payload.question.strip():
            raise HTTPException(status_code=400, detail="Empty query was provided")

        # Load all tickets to provide context to the AI
        tickets = []
        for file in TICKETS_DIR.glob("*.json"):
            with file.open("r") as f:
                try:
                    ticket = json.load(f)
                    tickets.append(ticket)
                except Exception:  # Skip files that can't be parsed
                    continue

        # Get AI response
        result = await chat_completion.get_chat_message_content(
            chat_history=history,
            settings=execution_settings,
            kernel=kernel,
        )

        history.add_message(result)
        return {"answer": str(result)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load_tickets_to_memory")
async def load_tickets(session_id: str):
    try:
        tickets = []
        for file in TICKETS_DIR.glob("*.json"):
            with file.open("r") as f:
                try:
                    ticket = json.load(f)
                    tickets.append(ticket)
                except Exception:  # Skip files that can't be parsed
                    continue

        # Combine ticket info into one context string
        tickets_context = "\n".join([json.dumps(ticket) for ticket in tickets])

        history = get_history(session_id)
        if history is None:
            raise HTTPException(status_code=404, detail="Session history not found")

        # Store ticket data in history
        history.add_user_message(f"Here is the context of all existing tickets:\n{tickets_context}")

        return {"message": "Tickets loaded into memory successfully", "ticket_count": len(tickets)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear_memory")
async def clear_memory(session_id: str):
    history = get_history(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session history not found")

    try:
        # Clear existing history
        history.clear()
        return {"message": "Memory cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/setup_support_assistant")
async def setup_support_assistant(session_id: str):
    history = get_history(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session history not found")
    try:
        # Add system instructions
        history.add_system_message(
            "You are an expert in IT ticketing. Provide clear, concise, and technically accurate responses. "
            "Format your answers neatly using Markdown lists, headings, or line breaks as appropriate. "
            "Do not include any HTML tags—just use Markdown or plain text formatting. "
            "Every question I ask relates to the context provided."
        )
        return {"message": "Support assistant setup successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
