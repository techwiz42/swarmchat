from pydantic import BaseModel, EmailStr, validator
from typing import List, Dict, Optional
from datetime import datetime

class UserCreate(BaseModel):
    """Schema for user registration."""
    username: str
    email: Optional[EmailStr]
    password: str

    @validator('username')
    def username_validator(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v

    @validator('password')
    def password_validator(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserUpdate(BaseModel):
    """Schema for user information updates."""
    email: Optional[EmailStr]
    password: Optional[str]

    @validator('password')
    def password_validator(cls, v):
        if v and len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserResponse(BaseModel):
    """Schema for user information response."""
    id: int
    username: str
    email: Optional[EmailStr]
    created_at: datetime

    class Config:
        orm_mode = True

class ChatMessage(BaseModel):
    """Model for chat messages."""
    content: str
    
    def __str__(self) -> str:
        return self.content

class TokenResponse(BaseModel):
    """Model for token responses."""
    access_token: str
    token_type: str
    username: str

class MessageResponse(BaseModel):
    """Model for chat message responses."""
    response: Optional[str]

class HistoryResponse(BaseModel):
    """Model for chat history responses."""
    messages: List[Dict[str, str | datetime]]

    class Config:
        orm_mode = True

class UserInteractionResponse(BaseModel):
    """Model for user interaction responses."""
    id: int
    start_time: datetime
    end_time: Optional[datetime]
    prompt: str
    response: Optional[str]
    agent_name: Optional[str]
    status: str
    error_message: Optional[str]

    class Config:
        orm_mode = True

class LoginHistoryResponse(BaseModel):
    """Model for login history responses."""
    timestamp: datetime
    ip_address: str
    status: str
    user_agent: Optional[str]

    class Config:
        orm_mode = True
