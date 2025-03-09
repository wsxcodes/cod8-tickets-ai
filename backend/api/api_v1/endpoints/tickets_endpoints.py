import json
import logging
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend import config

logger = logging.getLogger(__name__)

router = APIRouter()

TICKETS_DIR = config.TICKETS_DIR

# XXX TODO update history here
@router.post("/tickets/")
async def create_ticket(ticket: dict):
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


@router.delete("/tickets/{ticket_name}")
async def delete_ticket(ticket_name: str):
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
async def api_list_tickets():
    tickets = []
    for file in TICKETS_DIR.glob("*.json"):
        with file.open("r") as f:
            tickets.append(json.load(f))
    return JSONResponse(content=tickets)
