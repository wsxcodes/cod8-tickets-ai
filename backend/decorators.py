import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def log_endpoint(f):
    @wraps(f)
    async def wrapper(*args, **kw):
        start_time = time.time()
        logger.info(f"Endpoint [{f.__name__}] - Start")

        result = await f(*args, **kw)  # Ensure the async function is awaited

        elapsed_time = time.time() - start_time
        logger.info(f"Endpoint [{f.__name__}] - End - Elapsed Time: {elapsed_time:.2f}s")

        return result

    return wrapper
