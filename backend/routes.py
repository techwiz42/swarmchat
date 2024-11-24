import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from models import TokenResponse, MessageResponse, HistoryResponse, ChatMessage
from manager import SwarmChatManager

router = APIRouter()
security = HTTPBasic()
logger = logging.getLogger(__name__)
chat_manager = SwarmChatManager()

async def get_token_from_auth(request: Request) -> str:
    """Extract token from Authorization header."""
    auth = request.headers.get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header"
        )
    return auth.split(' ')[1]

@router.post("/api/login", response_model=TokenResponse)
async def login(credentials: HTTPBasicCredentials = Depends(security)) -> TokenResponse:
    """Handle user login."""
    try:
        logger.info("Login attempt: %s", credentials.username)
        token = await chat_manager.create_session(credentials.username)
        logger.info("Session created successfully for user: %s", credentials.username)
        return TokenResponse(token=token, username=credentials.username)
    except Exception as e:
        logger.error(
            "Login failed for user %s: %s",
            credentials.username,
            str(e),
            exc_info=True
        )
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}") from e

@router.post("/api/chat", response_model=MessageResponse)
async def send_message(
    message: ChatMessage,
    request: Request,
    token: str = Depends(get_token_from_auth)
) -> MessageResponse:
    """Handle chat messages."""
    logger.info("Processing chat message")
    response = await chat_manager.process_message(token, message.content, request)
    return MessageResponse(response=response)

@router.get("/api/history", response_model=HistoryResponse)
async def get_history(token: str = Depends(get_token_from_auth)) -> HistoryResponse:
    """Get chat history."""
    logger.debug("Retrieving chat history")
    async with chat_manager.get_session_safe(token) as session:
        if not session:
            raise HTTPException(status_code=401, detail="Invalid session")
        return HistoryResponse(messages=session.messages)

@router.get("/api/debug")
async def debug_info():
    """Get debug information about the server environment."""
    import os
    import sys
    return {
        "env_vars": {k: v[:4] + "..." if k == "OPENAI_API_KEY" else v 
                     for k, v in os.environ.items()},
        "working_directory": os.getcwd(),
        "user": os.getuid(),
        "group": os.getgid(),
        "python_path": sys.path,
    }
