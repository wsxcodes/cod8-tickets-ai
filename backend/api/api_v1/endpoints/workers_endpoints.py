import logging

from fastapi import APIRouter


logger = logging.getLogger(__name__)

router = APIRouter()


# XXX TODO add customer (create DB schema per customer etc etc..)
@router.get("/import_historical_tickets")
def import_historical_tickets(csv_filename: str = "data/Bank_Design_Equipment_FY2024.csv"):
    """
    Generate a vectorized knowledgebase from historical support tickets.
    """
    tickets_df = import_ticket_csv(csv_filename)
    for _, ticket in tickets_df.iterrows():
        ticket = vectorize_ticket(ticket)
        upload_ticket(ticket)
