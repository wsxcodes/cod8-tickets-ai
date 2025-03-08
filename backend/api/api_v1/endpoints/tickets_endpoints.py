import json
import logging
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend import config

logger = logging.getLogger(__name__)

router = APIRouter()

TICKETS_DIR = config.TICKETS_DIR


@router.post("/tickets/")
async def create_ticket(ticket: dict):
    file_name = ticket.get("filename")
    if not file_name:
        file_name = f"ticket_{time.time_ns()}.json"
    file_path = TICKETS_DIR / file_name
    with file_path.open("w") as f:
        json.dump(ticket, f)
    return {"message": "Ticket saved", "file": str(file_path)}


@router.get("/tickets")
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


@router.get("/tickets")
async def api_list_tickets():
    tickets = []
    for file in TICKETS_DIR.glob("*.json"):
        with file.open("r") as f:
            tickets.append(json.load(f))
    return JSONResponse(content=tickets)
