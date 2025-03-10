import logging

from fastapi import APIRouter, HTTPException

from backend import config
from backend.dependencies import (chat_completion, execution_settings,
                                  get_history, kernel, openai_client,
                                  session_histories)
from backend.schemas.llm_schemas import ChatCompletionRequest, TextToVector

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat_completion")
async def chat_completion_endpoint(payload: ChatCompletionRequest, session_id: str):
    try:
        if not payload.user_message.strip():
            raise HTTPException(status_code=400, detail="User message must be provided")

        history = get_history(session_id)
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
