import json
import time
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

TICKETS_DIR = Path("tickets")
TICKETS_DIR.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/tickets/")
async def create_ticket(ticket: dict):
    timestamp = int(time.time() * 1000)
    file_path = TICKETS_DIR / f"ticket_{timestamp}.json"
    with file_path.open("w") as f:
        json.dump(ticket, f)
    return {"message": "Ticket saved", "file": str(file_path)}

@app.get("/tickets", response_class=HTMLResponse)
async def list_tickets(request: Request):
    tickets = []
    for file in TICKETS_DIR.glob("*.json"):
        with file.open("r") as f:
            tickets.append(json.load(f))
    return templates.TemplateResponse("tickets.html", {"request": request, "tickets": tickets})

@app.get("/api/tickets")
async def api_list_tickets():
    tickets = []
    for file in TICKETS_DIR.glob("*.json"):
        with file.open("r") as f:
            tickets.append(json.load(f))
    return JSONResponse(content=tickets)
