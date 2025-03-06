import logging

from fastapi import APIRouter

from workers.process_tickets_worker import (process_ticket_csv, upload_ticket,
                                            vectorize_ticket)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/process_tickets")
def process_tickets(csv_filename: str = "data/Bank_Design_Equipment_FY2024.csv"):
    tickets_df = process_ticket_csv(csv_filename)
    for _, ticket in tickets_df.iterrows():
        ticket = vectorize_ticket(ticket)
        upload_ticket(ticket)
