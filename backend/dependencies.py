import logging

import semantic_kernel as sk
from openai import OpenAI
from semantic_kernel.connectors.ai.function_choice_behavior import \
    FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import \
    AzureChatPromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory

from backend import config

logger = logging.getLogger(__name__)

session_histories = {}

kernel = sk.Kernel()
execution_settings = AzureChatPromptExecutionSettings()
execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
openai_client = OpenAI(api_key=config.CHATGPT_KEY)


def get_history(session_id: str) -> ChatHistory:
    if session_id not in session_histories:
        session_histories[session_id] = ChatHistory()
    return session_histories[session_id]
