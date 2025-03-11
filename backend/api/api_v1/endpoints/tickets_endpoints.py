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

    ticket_id = data.get("ticket_id")
    if not ticket_id:
        return JSONResponse(status_code=400, content={"message": "ticket_id is required"})

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


@router.delete("/tickets/{ticket_name:path}")
@log_endpoint
async def delete_ticket(ticket_name: str):
    if ticket_name.startswith("ticket_files/"):
        ticket_name = ticket_name[len("ticket_files/"):]
    file_path = TICKETS_DIR / ticket_name
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


@router.post("/is_new_ticket")
@log_endpoint
async def is_new_ticket(session_id: str, payload: Question) -> str:
    # XXX TODO
    ...
