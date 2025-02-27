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

# Get Azure OpenAI configuration from environment variables or use defaults
deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME", "your_models_deployment_name")
api_key = os.getenv("OPENAI_API_KEY", "your_api_key")
base_url = os.getenv("AZURE_BASE_URL", "your_base_url")

# Create the Azure Chat Completion service and add it to the kernel
chat_completion = AzureChatCompletion(
    deployment_name=deployment_name,
    api_key=api_key,
    base_url=base_url,
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
        # Load all tickets to provide context
        tickets = []
        for file in TICKETS_DIR.glob("*.json"):
            with file.open("r") as f:
                try:
                    ticket = json.load(f)
                    tickets.append(ticket)
                except Exception:
                    continue
        tickets_context = "\n".join(json.dumps(ticket) for ticket in tickets)

        # Build the combined user message with context
        user_message = f"{payload.question}\nContext of tickets:\n{tickets_context}"

        # Create a ChatHistory and add the user's message
        history = ChatHistory()
        history.add_user_message(user_message)

        # Set up prompt execution settings (enable automatic function choice if needed)
        execution_settings = AzureChatPromptExecutionSettings()
        execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

        # Get chat response asynchronously using the AzureChatCompletion service
        result = await chat_completion.get_chat_message_content(
            chat_history=history,
            settings=execution_settings,
            kernel=kernel,
        )

        # Add the assistant's response to the history (optional for future context)
        history.add_message(result)

        return {"answer": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
