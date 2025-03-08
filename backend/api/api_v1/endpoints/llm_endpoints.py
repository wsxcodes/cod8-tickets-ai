import logging

import semantic_kernel as sk
from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from semantic_kernel.connectors.ai.function_choice_behavior import \
    FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import \
    AzureChatPromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory

from backend import config

logger = logging.getLogger(__name__)
router = APIRouter()

kernel = sk.Kernel()
history = ChatHistory()
execution_settings = AzureChatPromptExecutionSettings()
execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
openai_client = OpenAI(api_key=config.CHATGPT_KEY)

# XXX TODO we need the kernel (history) to be session based


class ChatCompletionRequest(BaseModel):
    system_message: str
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
        if not payload.system_message.strip() or not payload.user_message.strip():
            raise HTTPException(status_code=400, detail="Both system and user messages must be provided")

        # Clear previous chat history
        history.clear()

        # Add the provided system and user messages to the chat history
        history.add_system_message(payload.system_message)
        history.add_user_message(payload.user_message)

        # Get AI response
        result = await chat_completion.get_chat_message_content(
            chat_history=history,
            settings=execution_settings,
            kernel=kernel,
        )

        history.add_message(result)
        return {"answer": str(result)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reset_chat_history")
async def reset_chat_history():
    """
    Endpoint to reset the chat history.
    """
    try:
        history.clear()
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
