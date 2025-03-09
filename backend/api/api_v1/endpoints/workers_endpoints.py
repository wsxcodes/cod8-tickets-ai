import logging

from fastapi import APIRouter
from workers.process_tickets_worker import 

logger = logging.getLogger(__name__)

router = APIRouter()


# XXX TODO add customer (create DB schema per customer etc etc..)
@router.get("/import_historical_tickets")
async def import_historical_tickets(csv_filename: str = "data/Bank_Design_Equipment_FY2024.csv"):
    """
    Generate a vectorized knowledgebase from historical support tickets.
    """
    # XXX TODO
    ...
