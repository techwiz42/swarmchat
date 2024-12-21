from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import jwt
import openai
from openai import AsyncOpenAI
from passlib.context import CryptContext
import secrets
import logging
from dotenv import load_dotenv
import tiktoken
import json
import os
from manager import SwarmChatManager
from database import db_manager, User, Message, UserInteraction, LoginHistory
from sqlalchemy.orm import Session
from models import TokenResponse
from auth import auth_manager
from agents import (
    MODEL,
    moderator,
    transfer_to_hemmingway,
    transfer_to_pynchon,
    transfer_to_dickinson,
    transfer_to_shrink
)

load_dotenv()
encoding = tiktoken.encoding_for_model(MODEL)

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

class TokenResponseWithMessage(TokenResponse):
    initial_message: str

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
    "shrink": transfer_to_shrink
}

chat_manager = SwarmChatManager()

@router.post("/api/token", response_model=TokenResponseWithMessage)
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

        # Check user history to determine if new or returning
        all_history = await db_manager.get_all_user_messages(user.username)
        current_history = await db_manager.get_chat_history(user.username)
        
        #if all_history, this is a returning user. 
        #truncate the most recent 8k tokens to use as moderator.contect
        if all_history:
            history_string = result_string = "\n".join([str(row.content) for row in all_history])
            token_history = encoding.encode(history_string)
            truncated_history = token_history[-7500:]
            truncated_text = encoding.decode(truncated_history)
        else:
            truncated_text = ""
        # Create conversation context with moderator's instructions
        user_status = "new" if not all_history else "returning"
        conversation = [
            {"role": "system", "content": moderator.instructions},
            {"role": "system", "content": f"This is a {user_status} user named {user.username}. "
                                        f"If new user: Welcome them to SwarmChat, express interest in learning about them, "
                                        f"and ask what brings them here. "
                                        f"If returning: Welcome them back and ask what they'd like to discuss. "
                                        "Your goals are to stimulate conersation, generate insigt, keep a light and playful tone, "
                                        "summarize previous conversations. You sometimes ask personal questions."
                                        "You sometimes make unsolicited suggestions and observations. "
                                        "Do not always end your responses by asking the user a question. "
                                        "Do not be overly positive. "
                                        f"User input from previous conversations: {truncated_text}"}
        ]

        # Prepare API call parameters
        completion_params = {
            "model": moderator.model,
            "messages": conversation,
        }

        # Only add tools if they exist and are properly formatted
        if hasattr(moderator, 'functions') and isinstance(moderator.functions, list):
            # Convert functions to tools format if needed
            tools = []
            for func in moderator.functions:
                if isinstance(func, dict) and "function" in func:
                    tools.append({"type": "function", "function": func["function"]})
                elif isinstance(func, dict):
                    tools.append({"type": "function", "function": func})
            
            if tools:
                completion_params["tools"] = tools
                if hasattr(moderator, 'tool_choice') and moderator.tool_choice:
                    completion_params["tool_choice"] = moderator.tool_choice

        # Get moderator's initial greeting using the OpenAI client
        chat_completion = await client.chat.completions.create(**completion_params)
        initial_message = chat_completion.choices[0].message.content
        
        # Store the initial message in chat history
        await db_manager.add_to_chat_history(
            user.username, 
            None,  # No user message yet
            initial_message
        )
        
        # Update user's chat state
        await db_manager.update_user_chat_state(
            user.username,
            {
                "current_agent": moderator.name,
                "last_interaction": datetime.utcnow().isoformat()
            }
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user.username,
            "initial_message": initial_message
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
    current_user: str = Depends(auth_manager.get_current_user)
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
            *[{"role": m["role"], "content": m["content"]} for m in chat_history],
            {"role": "system", "content": "Your goals are to stimulate conersation, generate insigt, keep a light and playful tone, "
                                        "You may end your response in one of several ways: you can summarize the user's entry, "
                                        "You can ask a personal question about the user, "
                                        "you sometimes make unsolicited suggestions and observations. "
                                        "Never end your response by asking the user if he or she would like you to tell them more about your response."},
            {"role": "user", "content": message.content}
        ]

        # Prepare the API call parameters
        completion_params = {
            "model": current_agent.model,
            "messages": conversation,
        }

        # Only add tools if they exist and are properly formatted
        if hasattr(current_agent, 'functions') and isinstance(current_agent.functions, list):
            # Convert functions to tools format if needed
            tools = []
            for func in current_agent.functions:
                if isinstance(func, dict) and "function" in func:
                    tools.append({"type": "function", "function": func["function"]})
                elif isinstance(func, dict):
                    tools.append({"type": "function", "function": func})

            if tools:
                completion_params["tools"] = tools
                if hasattr(current_agent, 'tool_choice') and current_agent.tool_choice:
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
async def logout(current_user: str = Depends(auth_manager.get_current_user)):
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

@router.post("/api/request-verification")
async def request_verification(
    current_user: str = Depends(auth_manager.get_current_user)
):
    try:
        user = await db_manager.get_user_by_username(current_user)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        if user.email_verified:
            raise HTTPException(status_code=400, detail="Email already verified")
            
        token = await token_manager.create_verification_token(user.id)
        success = email_service.send_verification_email(
            user.email,
            token,
            os.getenv("BASE_URL", "http://localhost:3000")
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send verification email")
            
        return {"message": "Verification email sent"}
        
    except Exception as e:
        logger.error(f"Error requesting verification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/verify-email")
async def verify_email(token: str):
    try:
        user_id = await token_manager.verify_email_token(token)
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
            
        return {"message": "Email verified successfully"}
        
    except Exception as e:
        logger.error(f"Error verifying email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/request-password-reset")
async def request_password_reset(email: str):
    try:
        user = await db_manager.get_user_by_email(email)
        if not user:
            # Return success even if user not found to prevent email enumeration
            return {"message": "If the email exists, a password reset link will be sent"}
            
        token = await token_manager.create_password_reset_token(user.id)
        success = email_service.send_password_reset_email(
            email,
            token,
            os.getenv("BASE_URL", "http://localhost:3000")
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send reset email")
            
        return {"message": "If the email exists, a password reset link will be sent"}
        
    except Exception as e:
        logger.error(f"Error requesting password reset: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/reset-password")
async def reset_password(token: str, new_password: str):
    try:
        user_id = await token_manager.verify_reset_token(token)
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
            
        # Hash the new password
        hashed_password = auth_manager.get_password_hash(new_password)
        
        # Update the user's password
        async with db_manager.get_session() as session:
            await session.execute(
                """
                UPDATE users
                SET hashed_password = :password
                WHERE id = :user_id
                """,
                {"password": hashed_password, "user_id": user_id}
            )
            await session.commit()
            
        return {"message": "Password reset successfully"}
        
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@router.get("/api/health")
async def health_check():
    return {"status": "healthy"}
