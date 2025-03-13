import logging
from typing import Optional

import semantic_kernel as sk
from openai import OpenAI
from semantic_kernel.connectors.ai.function_choice_behavior import \
    FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import \
    AzureChatPromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory

from backend import config

logger = logging.getLogger(__name__)

session_histories = {}
context_ticket_ids = {}

kernel = sk.Kernel()
execution_settings = AzureChatPromptExecutionSettings()
execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
openai_client = OpenAI(api_key=config.CHATGPT_KEY)

chat_completion = AzureChatCompletion(
    deployment_name=config.DEPLOYMENT_NAME,
    endpoint=config.OPENAI_ENDPOINT,
    api_key=config.OPENAI_API_KEY,
)


def get_history(session_id: str) -> ChatHistory:
    if session_id not in session_histories:
        session_histories[session_id] = ChatHistory()
    return session_histories[session_id]


def get_current_context_ticket(session_id: str) -> Optional[str]:
    """
    Retrieve the current (active) ticket ID for the given session.
    Returns None if no ticket has been set.
    """
    return context_ticket_ids.get(session_id)


def set_current_context_ticket(session_id: str, ticket_id: str) -> None:
    """
    Set or update the current (active) ticket ID for the given session.
    """
    context_ticket_ids[session_id] = ticket_id
