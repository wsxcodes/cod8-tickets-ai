import json
import logging
import time

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.utils.logging import setup_logging

from backend import config
from backend.decorators import log_endpoint
from backend.helpers.chat_helpers import get_existing_history

logger = logging.getLogger(__name__)

router = APIRouter()

TICKETS_DIR = config.TICKETS_DIR

# Set up logging for the kernel
setup_logging()

# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@router.post("/tickets")
@log_endpoint
async def create_ticket(ticket: dict, history: ChatHistory = Depends(get_existing_history)):
    file_name = ticket.get("filename")
    if not file_name:
        file_name = f"ticket_{time.time_ns()}.json"
    file_path = TICKETS_DIR / file_name
    with file_path.open("w") as f:
        json.dump(ticket, f)

    from backend.api.api_v1.endpoints.rag_endpoints import load_tickets
    refresh_response = await load_tickets()

    return {
        "message": "Ticket saved and memory refreshed",
        "file": str(file_path),
        "ticket_count": refresh_response.get("ticket_count")
    }


@router.get("/tickets")
@log_endpoint
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


@router.delete("/tickets/{ticket_name:path}")
@log_endpoint
async def delete_ticket(ticket_name: str):
    if ticket_name.startswith("ticket_files/"):
        ticket_name = ticket_name[len("ticket_files/"):]
    file_path = TICKETS_DIR / ticket_name
    if not file_path.exists():
        return {"message": "Ticket not found"}

    file_path.unlink()

    from backend.api.api_v1.endpoints.rag_endpoints import load_tickets
    refresh_response = await load_tickets()

    return {
        "message": "Ticket deleted and memory refreshed",
        "ticket_count": refresh_response.get("ticket_count")
    }


@router.get("/tickets")
@log_endpoint
async def api_list_tickets():
    tickets = []
    for file in TICKETS_DIR.glob("*.json"):
        with file.open("r") as f:
            tickets.append(json.load(f))
    return JSONResponse(content=tickets)
