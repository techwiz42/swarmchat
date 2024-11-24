from pydantic import BaseModel
from typing import List, Dict, Optional

class ChatMessage(BaseModel):
    """Model for chat messages."""
    content: str
    def __str__(self) -> str:
        return self.content

class TokenResponse(BaseModel):
    """Model for token responses."""
    token: str
    username: str

class MessageResponse(BaseModel):
    """Model for chat message responses."""
    response: Optional[str]

class HistoryResponse(BaseModel):
    """Model for chat history responses."""
    messages: List[Dict[str, str]]
