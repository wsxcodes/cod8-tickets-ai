from typing import Optional

from pydantic import BaseModel


class TextToVector(BaseModel):
    text: str


class ChatCompletionRequest(BaseModel):
    session_id: str
    system_message: Optional[str] = None
    user_message: str
