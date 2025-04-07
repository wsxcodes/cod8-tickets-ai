import logging

from fastapi import APIRouter

from backend.decorators import log_endpoint

logger = logging.getLogger(__name__)

router = APIRouter()


# XXX TODO add customer (create DB schema per customer etc etc..)

@router.get("/import_historical_tickets")
@log_endpoint
async def import_historical_tickets(csv_folder_path: str):
    """
    Generate a vectorized knowledgebase from historical support tickets.
    """
    # XXX TODO
    ...
