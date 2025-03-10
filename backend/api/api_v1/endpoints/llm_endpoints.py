import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

from backend import config
from backend.dependencies import (execution_settings, get_history, kernel,
                                  openai_client, session_histories)

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatCompletionRequest(BaseModel):
    session_id: str
    system_message: Optional[str] = None
    user_message: str


class TextToVector(BaseModel):
    text: str


chat_completion = AzureChatCompletion(
    deployment_name=config.DEPLOYMENT_NAME,
    endpoint=config.OPENAI_ENDPOINT,
    api_key=config.OPENAI_API_KEY,
)

kernel.add_service(chat_completion)


@router.post("/chat_completion")
async def chat_completion_endpoint(payload: ChatCompletionRequest):
    try:
        if not payload.user_message.strip():
            raise HTTPException(status_code=400, detail="User message must be provided")

        history = get_history(payload.session_id)
        if history is None:
            raise HTTPException(status_code=404, detail="Session history not found")

        if not history.messages and payload.system_message:
            history.add_system_message(payload.system_message)

        history.add_user_message(payload.user_message)

        result = await chat_completion.get_chat_message_content(
            chat_history=history,
            settings=execution_settings,
            kernel=kernel,
        )

        if not result:
            raise HTTPException(status_code=500, detail="Empty response from AI model")

        history.add_message(result)
        return {"answer": str(result)}

    except HTTPException as http_exc:
        raise http_exc  # Keep HTTPExceptions as they are

    except Exception as e:
        logger.error(f"Chat completion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e) or "Internal server error")


@router.delete("/reset_chat_history")
async def reset_chat_history(session_id: str):
    """
    Endpoint to reset the chat history for a given session.
    """
    try:
        if session_id in session_histories:
            session_histories[session_id].clear()
        return {"detail": "Chat history has been reset."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vectorize")
async def vectorize_endpoint(payload: TextToVector):
    """
    Endpoint to vectorize input text using OpenAI embeddings.
    """
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Empty text provided")

    try:
        response = openai_client.embeddings.create(
            input=payload.text,
            model=config.OPENAI_EMBEDDING_MODEL
        )
        embedding_vector = response.data[0].embedding
        return {"vector": embedding_vector}
    except Exception as e:
        logger.error(f"Error vectorizing text: {e}")
        raise HTTPException(status_code=500, detail="Error processing vectorization")
