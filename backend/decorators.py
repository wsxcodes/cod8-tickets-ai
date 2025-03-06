import logging
import time
from functools import wraps

from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


def log_endpoint(f):
    @wraps(f)
    def wrapper(*args, **kw):
        start_time = time.time()
        logger.info(f"Endpoint [{f.__name__}] - Start")

        result = f(*args, **kw)

        elapsed_time = time.time() - start_time
        logger.info(f"Endpoint [{f.__name__}] - End - Elapsed Time: {elapsed_time:.2f}s")  # NoQA

        return result
    return wrapper


def retry_on_error(error_cls, attempts=5, wait_interval=2):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            @retry(
                stop=stop_after_attempt(attempts),
                wait=wait_fixed(wait_interval),
                retry_error_cls=error_cls
            )
            async def retried_func():
                return await func(*args, **kwargs)

            return await retried_func()

        return wrapper

    return decorator
