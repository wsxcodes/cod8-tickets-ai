import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from semantic_kernel.utils.logging import setup_logging

from backend import config
from backend.decorators import log_endpoint

logger = logging.getLogger(__name__)

router = APIRouter()


class Question(BaseModel):
    question: str


TICKETS_DIR = config.TICKETS_DIR

# Set up logging for the kernel
setup_logging()

# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@router.post("/tickets/")
@log_endpoint
async def create_ticket(request: Request):
    data = await request.json()

    ticket_id = data.get("ticketID")
    if not ticket_id:
        return JSONResponse(status_code=400, content={"message": "ticketID is required"})

    ticket_path = TICKETS_DIR / f"{ticket_id}.json"
    with ticket_path.open("w") as f:
        json.dump(data, f, indent=2)

    return {
        "message": "Ticket created and memory refreshed"
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


@router.delete("/tickets/{ticket_id}")
@log_endpoint
async def delete_ticket(ticket_id: str):
    file_path = TICKETS_DIR / f"{ticket_id}.json"
    if not file_path.exists():
        return {"message": "Ticket not found"}

    file_path.unlink()

    return {
        "message": "Ticket deleted and memory refreshed"
    }


@router.get("/tickets")
@log_endpoint
async def api_list_tickets():
    tickets = []
    for file in TICKETS_DIR.glob("*.json"):
        with file.open("r") as f:
            tickets.append(json.load(f))
    return JSONResponse(content=tickets)


@router.get("/tickets/{ticket_id}")
@log_endpoint
async def get_ticket(ticket_id: str):
    ticket_path = TICKETS_DIR / f"{ticket_id}.json"
    if not ticket_path.exists():
        return JSONResponse(status_code=404, content={"message": "Ticket not found"})
    with ticket_path.open("r") as f:
        ticket = json.load(f)
    return JSONResponse(content=ticket)
