import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from semantic_kernel.utils.logging import setup_logging
from starlette.middleware.sessions import SessionMiddleware

from backend import config
from backend.api.api_v1.routers import api_router
from backend.decorators import log_endpoint

API_V1_STR = "/api/v1"

# Set up logging for the kernel
setup_logging()

# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Set up logging for the kernel
setup_logging()
logging.getLogger("kernel").setLevel(logging.DEBUG)

app = FastAPI(
    title="COD8 Neural IT Support Tickets API",
    openapi_url=f"{API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redocs"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add the Session Middleware
app.add_middleware(
    SessionMiddleware, secret_key=config.SECRET_KEY, max_age=3600  # 1 hour
)

# Include routers
app.include_router(api_router, prefix=API_V1_STR)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/ticket_files", StaticFiles(directory="tickets"), name="ticket_files")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@log_endpoint
async def read_index(request: Request):
    logger = logging.getLogger(__name__)

    session_id = request.session.get("session_id")
    if session_id:
        logger.info("Existing session_id found: %s", session_id)
    else:
        logger.info("No session_id found, generating a new one.")

    # XXX TODO integrate check if the id exists with the session_histories (!!)

    # If no session ID exists, generate a new one
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
        request.session["session_id"] = session_id
        logger.info("** Generated new session_id: %s", session_id)

        from backend.api.api_v1.endpoints.rag_endpoints import \
            setup_support_assistant, load_tickets
        try:
            await setup_support_assistant(session_id)
            logger.info("** Successfully set up support assistant for session_id: %s", session_id)
            await load_tickets(session_id)
            logger.info("** Successfully loaded tickets for session_id: %s", session_id)
        except Exception as e:
            logger.error("Failed to set up support assistant: %s", str(e), exc_info=True)

    logger.info("Rendering index page with session_id: %s", session_id)
    return templates.TemplateResponse("index.html", {"request": request, "session_id": session_id})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
