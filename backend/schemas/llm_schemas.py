from typing import Optional

from pydantic import BaseModel


class TextToVector(BaseModel):
    text: str


class ChatCompletionRequest(BaseModel):
    system_message: Optional[str] = None
    user_message: str
