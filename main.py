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

# Initialize the kernel
kernel = sk.Kernel()

# Use environment variables from the working example
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")

# Create the Azure Chat Completion service using the working example’s parameters
chat_completion = AzureChatCompletion(
    deployment_name=DEPLOYMENT_NAME,
    endpoint=OPENAI_ENDPOINT,
    api_key=OPENAI_API_KEY,
)

kernel.add_service(chat_completion)

# Set up logging for the kernel
setup_logging()
logging.getLogger("kernel").setLevel(logging.DEBUG)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/ticket_files", StaticFiles(directory="tickets"), name="ticket_files")

templates = Jinja2Templates(directory="templates")

TICKETS_DIR = Path("tickets")
TICKETS_DIR.mkdir(exist_ok=True)


class Question(BaseModel):
    question: str


history = ChatHistory()
execution_settings = AzureChatPromptExecutionSettings()
execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()


@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
