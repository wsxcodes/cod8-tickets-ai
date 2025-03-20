import logging

import semantic_kernel as sk
from openai import OpenAI
from semantic_kernel.connectors.ai.function_choice_behavior import \
    FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import \
    AzureChatPromptExecutionSettings

from backend import config

logger = logging.getLogger(__name__)

kernel = sk.Kernel()
execution_settings = AzureChatPromptExecutionSettings()
execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
openai_client = OpenAI(api_key=config.CHATGPT_KEY)

chat_completion = AzureChatCompletion(
    AZURE_OPENAI_DEPLOYMENT_NAME=config.AZURE_OPENAI_DEPLOYMENT_NAME,
    endpoint=config.OPENAI_ENDPOINT,
    api_key=config.OPENAI_API_KEY,
    api_version=config.AZURE_OPENAI_MODEL_VERSION
)
