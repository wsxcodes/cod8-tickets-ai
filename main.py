import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        # Generate a unique filename using the current time in nanoseconds
        file_name = f"ticket_{time.time_ns()}.json"
    file_path = TICKETS_DIR / file_name
    with file_path.open("w") as f:
        json.dump(ticket, f)
    return {"message": "Ticket saved", "file": str(file_path)}


@app.get("/tickets")
async def list_tickets():
    tickets = []
    # Sort files by their modification time (most recent first)
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
        # Load all tickets
        tickets = []
        for file in TICKETS_DIR.glob("*.json"):
            with file.open("r") as f:
                try:
                    ticket = json.load(f)
                    tickets.append(ticket)
                except Exception:
                    # Skip files that can't be parsed
                    continue

        # Combine ticket info into one context string
        tickets_context = "\n".join(json.dumps(ticket) for ticket in tickets)

        # Updated system message
        system_message = (
            "You are an expert in IT ticketing. Provide clear, concise, and technically accurate "
            "responses about the tickets. The user is only asking about these tickets, so if the "
            "question seems ambiguous, interpret it solely in relation to the tickets. "
            "Do not bring in any external knowledge. Only base your response on the following ticket data. "
            "If the user question cannot be answered from these tickets, respond with: "
            "'No relevant ticket data available to answer that question.'.\n\n"
            f"Here is the context of all existing tickets:\n{tickets_context}"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": payload.question},
            ],
            temperature=0.7,
            max_tokens=150
        )
        answer = response.choices[0].message.content
        return {"answer": answer}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
