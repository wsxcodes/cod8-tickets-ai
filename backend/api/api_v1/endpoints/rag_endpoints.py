import json
import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.utils.logging import setup_logging

from backend import config
from backend.api.api_v1.endpoints.search_endpoints import \
    hybrid_search_with_vectorization
from backend.api.api_v1.endpoints.tickets_endpoints import delete_ticket
from backend.decorators import log_endpoint
from backend.dependencies import chat_completion, execution_settings, kernel
from backend.helpers.chat_helpers import (get_chat_completion_content,
                                          get_existing_history,
                                          get_ticket_data)
from backend.helpers.utils import send_email
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
    function_call: Optional[str] = None


TICKETS_DIR = config.TICKETS_DIR

SETUP_ASSISTANT = (
    "You are an expert in IT ticketing. Provide clear, concise, and technically accurate responses.\n"
    "Format your answers neatly using Markdown lists, headings, or line breaks as appropriate.\n"
    "Do not include any HTML tags—just use Markdown or plain text formatting.\n"
    "Every question I ask relates to the context provided.\n"
    "When I ask you to escalate an issue, respond with function_call 'email_escalation'.\n"
)


def load_tickets_and_update_history(history):
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
        logger.info(f"tickets_context = {tickets_context}")

    return {"message": "Tickets loaded into memory successfully", "ticket_count": len(tickets)}


@router.post("/generic_support_enquiry")
@log_endpoint
async def generic_support_enquiry(session_id: str, payload: Question, history: ChatHistory = Depends(get_existing_history)):
    history = get_history(session_id)

    try:
        if not payload.question.strip():
            raise HTTPException(status_code=400, detail="Empty query was provided")

        # Load all tickets to provide context to the AI
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
        if not question:
            raise HTTPException(status_code=400, detail="Empty query was provided")
        system_message = (
            SETUP_ASSISTANT +  # NoQA
            "In addition, examine the JSON data representing the tickets loaded in memory.\n"
            "When my question explicitly refers to a ticket (by its unique identifier, title, or description),\n"
            "match it against the JSON ticket records. Then, extract the ticket_id from the matching JSON object\n"
            "and set that as the value for context_ticket_id.\n"
            "If there is no clear match, do not fabricate a ticket id; instead, return context_ticket_id as null or leave it empty.\n"
            "Avoid asking what action user wants to take regarding the ticket.\n"
        )  # NoQA

    elif support_workflow_step == 2:
        next_workflow_action_step = 3
        system_message = "Please analyze the current ticket information and suggest any similar tickets that may provide relevant context."
        question = "Say something like I will analyze the current ticket data to identify any similar historical tickets that might provide relevant context to help solving this ticket. But rephrase it. Keep it short."  # NoQA

    elif support_workflow_step == 3:
        next_workflow_action_step = 4
        current_context_ticket = get_current_context_ticket(session_id=session_id)
        ticket_text, ticket_json = await get_ticket_data(ticket_id=current_context_ticket)

        if ticket_text:
            logger.info("Ticket text retrieved: %s", ticket_text)
            similar_tickets = await hybrid_search_with_vectorization(text_query=ticket_text, top_k=5, include_vector=False)
            similar_tickets = similar_tickets["value"]

        history.clear()
        load_tickets_and_update_history(history)

        system_message = SETUP_ASSISTANT + (
            "You are an IT support expert tasked with analyzing historical tickets to determine if they offer any useful insight for resolving the current ticket.\n"  # NoQA
            "1. Provide a brief analysis focused solely on identifying any directly actionable insights for resolving the current ticket. Do not include any detailed summaries or digests of the ticket contents.\n"  # NoQA
            "2. If no tickets offer clear, useful information, briefly mention that explicitly, but still squeeze out at least some small insight or suggestion based on the historical tickets, even if it's minimal.\n"  # NoQA
            "Ensure your response is strictly limited to this analysis or the stated message."
        )
        question = (
            f"Current ticket: {ticket_json}\nHistorical tickets: {similar_tickets}"
         )

    elif support_workflow_step == 4:
        next_workflow_action_step = 1
        current_context_ticket = get_current_context_ticket(session_id=session_id)
        ticket_text, ticket_json = await get_ticket_data(ticket_id=current_context_ticket)

        system_message = SETUP_ASSISTANT
        question = f"Help me to resolve this ticket: {ticket_json}"

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported workflow step: {support_workflow_step}.")

    try:
        history.add_system_message(system_message)
        history.add_user_message(question)

        # Setup response format
        execution_settings.structured_json_response = True
        execution_settings.response_format = Answer

        # Get the AI response, instructing the kernel to follow a strict response format
        result = await get_chat_completion_content(history=history, execution_settings=execution_settings, kernel=kernel)

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
                next_workflow_action_step = 2
                logger.info("Context ticket has changed from %s to %s for session_id: %s", recent_context_ticket, current_context_ticket, session_id)
        else:
            parsed_result["context_ticket_id"] = recent_context_ticket

        # Inject next workflow step into the response
        parsed_result["next_workflow_action_step"] = next_workflow_action_step
        set_current_context_ticket(session_id=session_id, ticket_id=parsed_result["context_ticket_id"])

        if similar_tickets:
            parsed_result["semantic_ticket_matches"] = similar_tickets

        function_call = parsed_result.get("function_call") or None
        if function_call:
            if function_call == "email_escalation":
                escalation_payload = Question(
                    question="Write short escalation email about this ticket to L2. Sign it as Jakub. Leave out subject, provide just the email body."
                )
                history.add_user_message(escalation_payload.question)
                result = await get_chat_completion_content(
                    history=history,
                    execution_settings=execution_settings,
                    kernel=kernel
                )
                result = json.loads(str(result))

                ticket_text, ticket_json = await get_ticket_data(ticket_id=current_context_ticket)
                email_subject = f"Escalation: Ticket {current_context_ticket} - {ticket_json["title"]}"
                send_email(to_addr="jakub.kudlacek@cod8.io", subject=email_subject, body=result["answer"])
                send_email(to_addr="janfilipsgt@gmail.com", subject=email_subject, body=result["answer"])

                logger.info(f"Deleting ticket {current_context_ticket}")
                await delete_ticket(ticket_id=current_context_ticket)
                # Refresh tickets AI memory
                await load_tickets(session_id)
                logger.info("** Successfully loaded tickets for session_id: %s", session_id)

                answer_obj = Answer(
                    answer=f"I have escalated {current_context_ticket} to T2.",
                    context_ticket_id="",
                    function_call="email_escalation"
                )
                parsed_result = answer_obj.dict()
                parsed_result["next_workflow_action_step"] = 1
                current_context_ticket = None
                set_current_context_ticket(session_id=session_id, ticket_id="")

        # XXX TODO zresetovat historiu (a znovu nasetapovat veci) ked context_ticket changes

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
        return load_tickets_and_update_history(history)

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
