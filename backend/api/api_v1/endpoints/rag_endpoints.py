import logging
from typing import Dict

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/xxx")
def xxx() -> Dict[str, str]:
    """xxx"""
    return {
        "status": "XXX",
        "message": "Working on this currently.",
    }
