import json
import logging
import os
import time
from pathlib import Path

import semantic_kernel as sk
from fastapi import FastAPI, HTTPException, Request
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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

import logging
from typing import Dict

from fastapi import APIRouter

from backend.decorators import log_endpoint

logger = logging.getLogger(__name__)

router = APIRouter()


@app.post("/tickets/")
async def create_ticket(ticket: dict):
    file_name = ticket.get("filename")
    if not file_name:
        file_name = f"ticket_{time.time_ns()}.json"
    file_path = TICKETS_DIR / file_name
    with file_path.open("w") as f:
        json.dump(ticket, f)
    return {"message": "Ticket saved", "file": str(file_path)}


@app.get("/tickets")
async def list_tickets():
    tickets = []
    files = sorted(
        TICKETS_DIR.glob("*.json"),
        key=lambda file: file.stat().st_mtime,
        reverse=True
    )
    for file in files:
        with file.open("r") as f:
            ticket = json.load(f)
            ticket['path'] = "ticket_files/" + file.name
            tickets.append(ticket)
    return JSONResponse(content=tickets)


@app.get("/api/tickets")
async def api_list_tickets():
    tickets = []
    for file in TICKETS_DIR.glob("*.json"):
        with file.open("r") as f:
            tickets.append(json.load(f))
    return JSONResponse(content=tickets)