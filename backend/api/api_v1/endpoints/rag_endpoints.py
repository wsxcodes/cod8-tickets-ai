import json
import logging

import semantic_kernel as sk
from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from semantic_kernel.connectors.ai.function_choice_behavior import \
    FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import \
    AzureChatPromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory

from backend import config

logger = logging.getLogger(__name__)
router = APIRouter()

kernel = sk.Kernel()
history = ChatHistory()
execution_settings = AzureChatPromptExecutionSettings()
execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
openai_client = OpenAI(api_key=config.CHATGPT_KEY)


class Question(BaseModel):
    question: str


class TextToVector(BaseModel):
    text: str


chat_completion = AzureChatCompletion(
    deployment_name=config.DEPLOYMENT_NAME,
    endpoint=config.OPENAI_ENDPOINT,
    api_key=config.OPENAI_API_KEY,
)

kernel.add_service(chat_completion)

TICKETS_DIR = config.TICKETS_DIR


#XXX TODO we need the kernel (history) to be session based

@router.post("/support_enquiry")
async def support_enquiry(payload: Question):
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

        # Combine ticket info into one context string
        tickets_context = "\n".join([json.dumps(ticket) for ticket in tickets])

        # Add system instructions
        history.add_system_message(
            "You are an expert in IT ticketing. Provide clear, concise, and technically accurate responses. "
            "Format your answers neatly using Markdown lists, headings, or line breaks as appropriate. "
            "Do not include any HTML tags—just use Markdown or plain text formatting. "
            "Every question I ask relates to the context provided. "
        )

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
async def load_tickets():
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

        # Store ticket data in history
        history.add_user_message(f"Here is the context of all existing tickets:\n{tickets_context}")

        return {"message": "Tickets loaded into memory successfully", "ticket_count": len(tickets)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear_memory")
async def clear_memory():
    try:
        # Clear existing history
        history.clear()
        return {"message": "Memory cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask")
async def setup_support_assistant():
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
