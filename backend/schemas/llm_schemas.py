from pydantic import BaseModel
from typing import Optional


class TextToVector(BaseModel):
    text: str

class ChatCompletionRequest(BaseModel):
    session_id: str
    system_message: Optional[str] = None
    user_message: str
