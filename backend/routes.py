from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import jwt
import openai
from openai import AsyncOpenAI  # New import
from passlib.context import CryptContext
import secrets
import logging
from dotenv import load_dotenv
import json
import os
from manager import SwarmChatManager
from database import db_manager, User, Message, UserInteraction, LoginHistory
from sqlalchemy.orm import Session
from models import TokenResponse
from auth import auth_manager
from agents import (
    moderator,
    transfer_to_hemmingway,
    transfer_to_pynchon,
    transfer_to_dickinson,
    transfer_to_dale_carnegie,
    transfer_to_shrink,
    transfer_to_flapper,
    transfer_to_bullwinkle,
    transfer_to_yogi_berra,
    transfer_to_yogi_bhajan,
    transfer_to_mencken
)

load_dotenv()

# Initialize the client
api_key = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=api_key)

# Set up logging
logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter()

async def get_db():
    """Get database session."""
    # 1. Create a new database session
    db = db_manager.get_session()
    
    try:
        # 2. Yield the session for use in the route
        yield db
    finally:
        # 3. Always close the session, even if there's an error
        #FIXME - the db object doesn't have a close method
        #db.close()
        print("Fix this or there will be trouble...")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    content: str

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    response: str

    class Config:
        from_attributes = True

class HistoryResponse(BaseModel):
    messages: List[dict]

    class Config:
        from_attributes = True

# Agent transfer functions
AGENT_TRANSFERS = {
    "hemingway": transfer_to_hemmingway,
    "pynchon": transfer_to_pynchon,
    "dickinson": transfer_to_dickinson,
    "carnegie": transfer_to_dale_carnegie,
    "shrink": transfer_to_shrink,
    "flapper": transfer_to_flapper,
    "bullwinkle": transfer_to_bullwinkle,
    "yogi_berra": transfer_to_yogi_berra,
    "yogi_bhajan": transfer_to_yogi_bhajan,
    "mencken": transfer_to_mencken
}

chat_manager = SwarmChatManager()

@router.post("/api/token", response_model=TokenResponse)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    try:
        user = await auth_manager.authenticate_user(
            form_data.username,
            form_data.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create new session
        await db_manager.create_new_session(user.username)
        
        access_token = auth_manager.create_access_token(
            data={"sub": user.username}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user.username
        }
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Registration endpoint
@router.post("/api/register", response_model=dict)
async def register_user(user: UserCreate):
    try:
        # Check if username already exists
        existing_user = await db_manager.get_user_by_username(user.username)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Username already registered"
            )
            
        # Check if email already exists
        existing_email = await db_manager.get_user_by_email(user.email)
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        # Hash the password
        hashed_password = pwd_context.hash(user.password)
        
        # Create the user
        new_user = await db_manager.create_user(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
            created_at=datetime.utcnow()
        )

        return {
            "username": new_user.username,
            "email": new_user.email,
            "message": "User created successfully"
        }

    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred during registration"
        )

@router.post("/api/chat", response_model=MessageResponse)
async def chat(
    message: ChatMessage,
    request: Request,
    current_user: str = Depends(auth_manager.get_current_user)  # Remove chat_token dependency
):
    try:
        # Get user's chat history and state
        user_state = await db_manager.get_user_chat_state(current_user)
        chat_history = await db_manager.get_chat_history(current_user)

        # Initialize response variables
        response = None
        new_state = user_state.copy() if user_state else {}

        # Check for agent transfer commands
        transfer_command = None
        for cmd, agent in AGENT_TRANSFERS.items():
            if f"/{cmd}" in message.content.lower():
                transfer_command = agent
                break

        # Process the message
        current_agent = None
        if transfer_command:
            current_agent = transfer_command
        elif not user_state or 'current_agent' not in user_state:
            current_agent = moderator
        else:
            current_agent = AGENT_TRANSFERS.get(user_state['current_agent'], moderator)

        # Create conversation context with agent's instructions
        conversation = [
            {"role": "system", "content": current_agent.instructions},
            *[{"role": m["role"], "content": m["content"]} for m in chat_history[-5:]],
            {"role": "user", "content": message.content}
        ]

        # Prepare the API call parameters
        completion_params = {
            "model": current_agent.model,
            "messages": conversation,
        }

        # Only add tools if they exist and are properly formatted
        if current_agent.functions and isinstance(current_agent.functions, list):
            # Convert functions to tools format if needed
            tools = []
            for func in current_agent.functions:
                if isinstance(func, dict) and "function" in func:
                    tools.append({"type": "function", "function": func["function"]})
                elif isinstance(func, dict):
                    tools.append({"type": "function", "function": func})

            if tools:
                completion_params["tools"] = tools
                if current_agent.tool_choice:
                    completion_params["tool_choice"] = current_agent.tool_choice

        # Call OpenAI with the new client approach
        chat_completion = await client.chat.completions.create(**completion_params)

        response = chat_completion.choices[0].message.content

        # Update state with current agent
        new_state["current_agent"] = current_agent.name
        new_state["last_interaction"] = datetime.utcnow().isoformat()

        # Update user state and chat history
        await db_manager.update_user_chat_state(current_user, new_state)
        await db_manager.add_to_chat_history(current_user, message.content, response)

        return {"response": response}

    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your message"
        )

@router.post("/api/chat", response_model=MessageResponse)
async def chat(
    message: ChatMessage,
    request: Request,
    current_user: str = Depends(auth_manager.get_current_user),
):
    try:
        # Get user's chat history and state
        user_state = await db_manager.get_user_chat_state(current_user)
        chat_history = await db_manager.get_chat_history(current_user)

        # Initialize response variables
        response = None
        new_state = user_state.copy() if user_state else {}

        # Check for agent transfer commands
        transfer_command = None
        for cmd, agent in AGENT_TRANSFERS.items():
            if f"/{cmd}" in message.content.lower():
                transfer_command = agent
                break

        # Process the message
        current_agent = None
        if transfer_command:
            current_agent = transfer_command
        elif not user_state or 'current_agent' not in user_state:
            current_agent = moderator
        else:
            current_agent = AGENT_TRANSFERS.get(user_state['current_agent'], moderator)

        # Create conversation context with agent's instructions
        conversation = [
            {"role": "system", "content": current_agent.instructions},
            *[{"role": m["role"], "content": m["content"]} for m in chat_history[-5:]],
            {"role": "user", "content": message.content}
        ]

        # Call OpenAI with the new client approach
        chat_completion = await client.chat.completions.create(
            model=current_agent.model,
            messages=conversation,
            tools=current_agent.functions if current_agent.functions else None,
            tool_choice=current_agent.tool_choice if current_agent.tool_choice else None
        )

        response = chat_completion.choices[0].message.content

        # Update state with current agent
        new_state["current_agent"] = current_agent.name
        new_state["last_interaction"] = datetime.utcnow().isoformat()

        # Update user state and chat history
        await db_manager.update_user_chat_state(current_user, new_state)
        await db_manager.add_to_chat_history(current_user, message.content, response)

        return {"response": response}

    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your message"
        )

# Get chat history endpoint
@router.get("/api/history", response_model=HistoryResponse)
async def get_history(current_user: str = Depends(auth_manager.get_current_user)):
    try:
        history = await db_manager.get_chat_history(current_user)
        return {"messages": history}
    except Exception as e:
        logger.error(f"History retrieval error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving chat history"
        )

@router.post("/api/logout")
async def logout(current_user: str = Depends(auth_manager.get_current_user)):  # Remove chat_token dependency
    try:
        # Just clear user chat state
        await db_manager.clear_user_chat_state(current_user)
        return {"message": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred during logout"
        )

# Health check endpoint
@router.get("/api/health")
async def health_check():
    return {"status": "healthy"}
