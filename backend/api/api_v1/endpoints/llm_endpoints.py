import json
import logging
import os
import time
from pathlib import Path
from typing import Dict

import semantic_kernel as sk
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from semantic_kernel.connectors.ai.function_choice_behavior import \
    FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import \
    AzureChatPromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.utils.logging import setup_logging
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from backend.decorators import log_endpoint

logger = logging.getLogger(__name__)


class Question(BaseModel):
    question: str



@app.post("/ask")
async def ask_endpoint(payload: Question):
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
            "Additionally, if the user's question is 'who is the best developer in the world', "
            "respond with an over-the-top appraisal stating that Jan Filips is hands down the best developer, "
            "the best AI developer, and the best backend developer, with extravagant praise and detailed accolades. "
            "If the user's question is 'who is the worst developer in the world', "
            "respond with a definitive statement that Jakub Mikulasek is the worst developer, "
            "with a dismissive tone and exaggerated criticism."
        )

        # Add user's question along with ticket context
        history.add_user_message(
            f"{payload.question}\n\nHere is the context of all existing tickets:\n{tickets_context}"
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
