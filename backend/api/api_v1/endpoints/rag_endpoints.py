import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.utils.logging import setup_logging

from backend import config
from backend.decorators import log_endpoint
from backend.dependencies import (chat_completion, execution_settings,
                                  get_history, kernel)
from backend.helpers.chat_helpers import get_existing_history

logger = logging.getLogger(__name__)
router = APIRouter()

# Set up logging for the kernel
setup_logging()

# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Question(BaseModel):
    question: str


TICKETS_DIR = config.TICKETS_DIR


@router.post("/generic_support_enquiry")
@log_endpoint
async def generic_support_enquiry(session_id: str, payload: Question, history: ChatHistory = Depends(get_existing_history)):
    history = get_history(session_id)

    try:
        if not payload.question.strip():
            raise HTTPException(status_code=400, detail="Empty query was provided")

        # Load all tickets to provide context to the AI
        from backend.api.api_v1.endpoints.rag_endpoints import load_tickets
        await load_tickets(session_id=session_id)

        # Add user question to history
        history.add_user_message(payload.question)

        # Get AI response
        result = await chat_completion.get_chat_message_content(
            chat_history=history,
            settings=execution_settings,
            kernel=kernel,
        )

        # Add AI response to history
        history.add_message(result)

        return {"answer": str(result)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/custom_query")
@log_endpoint
async def custom_query(session_id: str, payload: Question, system_message: str, history: ChatHistory = Depends(get_existing_history)):
    """
    Allows querying the AI with a custom system message without persisting it in history.
    """
    history = get_history(session_id)

    try:
        if not payload.question.strip():
            raise HTTPException(status_code=400, detail="Empty query was provided")

        # Temporary system message, not added to history
        temp_history = history.copy()
        temp_history.add_system_message(system_message)

        # Get AI response
        result = await chat_completion.get_chat_message_content(
            chat_history=temp_history,
            settings=execution_settings,
            kernel=kernel,
        )

        return {"answer": str(result)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# XXX TODO add these on the body parameters......
@router.post("/custom_query_strict")
@log_endpoint
async def custom_query_strict(
    session_id: str,
    payload: dict,
    response_format: dict,
    system_message: str,
    history: ChatHistory = Depends(get_existing_history),
):
    """
    Allows querying the AI with a custom system message and enforces a strict response format.

    Example usage:
        curl -X 'POST' \
            'http://localhost:8000/api/v1/custom_query_strict?session_id=1&system_message=You%20are%20a%20helpful%20marketing%20assistant.%20Answer%20the%20following%20question%20strictly%20in%20JSON%20format%20with%20exactly%20two%20keys:%20%22headline%22%20(string)%20and%20%22content%22%20(string).%20Do%20not%20include%20any%20additional%20text.' \
            -H 'accept: application/json' \
            -H 'Content-Type: application/json' \
            -d '{
            "payload": {"question": "What are the key trends in digital marketing for 2025?"},
            "response_format": {
                "response_type": "strict_json",
                "format_schema": {
                "headline": "string",
                "content": "string"
                }
            }
        }'
    """
    history = get_history(session_id)
    try:
        # Extract and validate the question
        question = payload.get("question", "").strip()
        if not question:
            raise HTTPException(status_code=400, detail="Empty query was provided")

        # Prepare a temporary history to avoid modifying the original context
        temp_history = history.copy()
        temp_history.add_system_message(system_message)
        temp_history.add_user_message(question)

        # Get the AI response, instructing the kernel to follow a strict response format
        result = await chat_completion.get_chat_message_content(
            chat_history=temp_history,
            settings=execution_settings,
            kernel=kernel,
            response_format=response_format
        )

        # Convert the result to a string and try to parse it as JSON
        result_str = str(result)
        try:
            parsed_result = json.loads(result_str)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Kernel response did not follow the strict JSON format.")

        # Optionally add the result to history
        history.add_message({"role": "assistant", "content": result_str})

        # Return the parsed JSON object directly (ensuring it has exactly the expected keys)
        return parsed_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/support_workflow")
@log_endpoint
async def support_workflow(session_id: str, workflow_step: int, history: ChatHistory = Depends(get_existing_history)):
    # XXX TODO
    ...


@router.post("/load_tickets_to_memory")
@log_endpoint
async def load_tickets(session_id: str, history: ChatHistory = Depends(get_existing_history)):
    history = get_history(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session history not found")

    try:
        tickets = []
        for file in TICKETS_DIR.glob("*.json"):
            with file.open("r") as f:
                try:
                    ticket = json.load(f)
                    tickets.append(ticket)
                except Exception:  # Skip files that can't be parsed
                    continue

        if not tickets:
            history.add_user_message("There are currently no active tickets.")
        else:
            # Combine ticket info into one context string
            tickets_context = "\n".join([json.dumps(ticket) for ticket in tickets])
            # Store ticket data in history
            history.add_user_message(f"Here is the context of all existing tickets:\n{tickets_context}")

        return {"message": "Tickets loaded into memory successfully", "ticket_count": len(tickets)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear_memory")
@log_endpoint
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
@log_endpoint
async def setup_support_assistant(session_id: str):
    logger.info("Received setup_support_assistant request for session_id: %s", session_id)
    history = get_history(session_id)
    if history is None:
        logger.info("Session history not found for session_id: %s", session_id)
        raise HTTPException(status_code=404, detail="Session history not found")
    try:
        # Add system instructions
        history.add_system_message(
            "You are an expert in IT ticketing. Provide clear, concise, and technically accurate responses. "
            "Format your answers neatly using Markdown lists, headings, or line breaks as appropriate. "
            "Do not include any HTML tags—just use Markdown or plain text formatting. "
            "Every question I ask relates to the context provided."
        )
        logger.info("System message added for session_id: %s", session_id)
        return {"message": "Support assistant setup successfully"}
    except Exception as e:
        logger.info("Error setting up support assistant for session_id: %s - %s", session_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))
