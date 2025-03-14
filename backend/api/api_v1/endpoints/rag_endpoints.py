import json
import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.utils.logging import setup_logging

from backend import config
from backend.api.api_v1.endpoints.tickets_endpoints import get_ticket
from backend.api.api_v1.endpoints.search_endpoints import hybrid_search_with_vectorization
from backend.decorators import log_endpoint
from backend.dependencies import chat_completion, execution_settings, kernel
from backend.helpers.chat_helpers import get_existing_history
from backend.session_state import (get_current_context_ticket, get_history,
                                   set_current_context_ticket)

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
    system_message: Optional[str] = None


class Answer(BaseModel):
    answer: str
    context_ticket_id: str


TICKETS_DIR = config.TICKETS_DIR

SETUP_ASSISTANT = (
    "You are an expert in IT ticketing. Provide clear, concise, and technically accurate responses."
    "Format your answers neatly using Markdown lists, headings, or line breaks as appropriate."
    "Do not include any HTML tags—just use Markdown or plain text formatting."
    "Every question I ask relates to the context provided."
)


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


@router.post("/support_workflow")
@log_endpoint
async def support_workflow(session_id: str, support_workflow_step: int, question: str = Body(...), history: ChatHistory = Depends(get_existing_history)):
    history = get_history(session_id)
    next_workflow_action_step = 1
    similar_tickets = None

    logger.info("System message added for session_id: %s", session_id)
    if support_workflow_step == 1:
        next_workflow_action_step = 2
        if not question:
            raise HTTPException(status_code=400, detail="Empty query was provided")
        system_message = (
            SETUP_ASSISTANT +  # NoQA
            " In addition, examine the JSON data representing the tickets loaded in memory. "
            "When my question explicitly refers to a ticket (by its unique identifier, title, or description), "
            "match it against the JSON ticket records. Then, extract the ticketID from the matching JSON object "
            "and set that as the value for context_ticket_id. "
            "If there is no clear match, do not fabricate a ticket id; instead, return context_ticket_id as null or leave it empty."
        )  # NoQA

    elif support_workflow_step == 2:
        next_workflow_action_step = 3
        system_message = "Please analyze the current ticket information and suggest any similar tickets that may provide relevant context."
        question = "Say something like I will analyze the current ticket data thoroughly to identify any similar historical tickets that might provide relevant context to help solving this ticket. But rephrase it."  # NoQA

    elif support_workflow_step == 3:
        next_workflow_action_step = 4
        # XXX assesment....
        system_message = ""
        current_context_ticket = get_current_context_ticket(session_id=session_id)
        ticket_text = ""
        if current_context_ticket:
            response = await get_ticket(ticket_id=current_context_ticket)
            ticket_json = json.loads(response.body.decode("utf-8"))
            ticket_text = ticket_json.get("title", "") + " " + ticket_json.get("description", "")

        if ticket_text:
            logger.info("Ticket text retrieved: %s", ticket_text)
            similar_tickets = await hybrid_search_with_vectorization(text_query=ticket_text, top_k=5, include_vector=False)
            # Exclude tickets not meeting the absolute bare minimum threshold
            similar_tickets = [ticket for ticket in similar_tickets if ticket["@search.score"] >= 0.03]
        
    elif support_workflow_step == 4:
        # XXX TODO I found this information useful / these tickets are not much of a use for us...
        next_workflow_action_step = 5
        ...
    elif support_workflow_step == 5:
        # XXX TODO resolution suggestion
        next_workflow_action_step = 1
        ...
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported workflow step: {support_workflow_step}.")

    try:
        history.add_system_message(system_message)
        history.add_user_message(question)

        # Setup response format
        execution_settings.structured_json_response = True
        execution_settings.response_format = Answer

        # Get the AI response, instructing the kernel to follow a strict response format
        result = await chat_completion.get_chat_message_content(
            chat_history=history,
            settings=execution_settings,
            kernel=kernel
        )

        # Convert the result to a string and try to parse it as JSON
        result_str = str(result)
        try:
            parsed_result = json.loads(result_str)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Kernel response did not follow the strict JSON format.")

        # Optionally add the result to history
        history.add_message({"role": "assistant", "content": result_str})

        # Decide on the next action step
        recent_context_ticket = get_current_context_ticket(session_id=session_id)
        current_context_ticket = parsed_result["context_ticket_id"]
        if current_context_ticket:
            if current_context_ticket != recent_context_ticket:
                logger.info("Context ticket has changed from %s to %s for session_id: %s", recent_context_ticket, current_context_ticket, session_id)
        else:
            parsed_result["context_ticket_id"] = recent_context_ticket

        # Inject next workflow step into the response
        parsed_result["next_workflow_action_step"] = next_workflow_action_step
        set_current_context_ticket(session_id=session_id, ticket_id=parsed_result["context_ticket_id"])

        if similar_tickets:
            parsed_result["similar_tickets"] = similar_tickets["value"]

        # Return the parsed JSON object directly (ensuring it has exactly the expected keys)
        return parsed_result

    except Exception as e:
        logger.error("Error in support_workflow: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


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
        history.add_system_message(SETUP_ASSISTANT)
        logger.info("System message added for session_id: %s", session_id)
        return {"message": "Support assistant setup successfully"}
    except Exception as e:
        logger.info("Error setting up support assistant for session_id: %s - %s", session_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))
