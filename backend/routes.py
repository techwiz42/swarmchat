import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import json

from models import (
    TokenResponse,
    MessageResponse,
    HistoryResponse,
    ChatMessage,
    UserCreate,
    UserResponse,
    UserUpdate,
    UserInteractionResponse,
    LoginHistoryResponse
)
from database import DatabaseManager, User, Message, UserInteraction, LoginHistory
from auth import auth_manager
from manager import SwarmChatManager

router = APIRouter()
logger = logging.getLogger(__name__)
access_logger = logging.getLogger("swarm.access")
chat_manager = SwarmChatManager()
db_manager = DatabaseManager()

# Dependency to get database session
async def get_db():
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()

@router.post("/api/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle user registration."""
    try:
        # Check if username exists
        if db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
            
        # Check if email exists
        if user_data.email and db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
            
        # Create new user
        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=User.hash_password(user_data.password)
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Log successful registration
        client_ip = request.client.host
        await db_manager.log_login(
            db,
            user.id,
            client_ip,
            'success',
            request.headers.get('user-agent')
        )
        
        logger.info(f"New user registered: {user.username}")
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at
        )
        
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/api/token", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Handle user login and token generation."""
    try:
        user = await auth_manager.authenticate_user(
            form_data.username,
            form_data.password
        )
        
        client_ip = request.client.host
        
        if not user:
            # Log failed login attempt
            await db_manager.log_login(
                db,
                None,
                client_ip,
                'failed',
                request.headers.get('user-agent')
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Log successful login
        await db_manager.log_login(
            db,
            user.id,
            client_ip,
            'success',
            request.headers.get('user-agent')
        )
        
        # Create session in SwarmChat manager
        chat_token = await chat_manager.create_session(user.username)
        
        # Create JWT token
        access_token = auth_manager.create_access_token(
            data={"sub": user.username}
        )
        
        logger.info(f"User logged in: {user.username}")
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            chat_token=chat_token,
            username=user.username
        )
        
    except Exception as e:
        logger.error(f"Login failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/api/chat", response_model=MessageResponse)
async def send_message(
    message: ChatMessage,
    request: Request,
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Handle chat messages with database persistence."""
    try:
        # Get chat token from header
        chat_token = request.headers.get('X-Chat-Token')
        if not chat_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing chat token"
            )
            
        # Create interaction record
        interaction = await db_manager.log_interaction(
            db,
            user_id=current_user.id,
            ip_address=request.client.host,
            session_id=chat_token,
            prompt=message.content
        )
        
        try:
            # Process message through SwarmChat
            response = await chat_manager.process_message(
                chat_token,
                message.content,
                request
            )
            
            # Store user message in database
            user_message = Message(
                user_id=current_user.id,
                role="user",
                content=message.content,
                interaction_id=interaction.id
            )
            db.add(user_message)
            
            # Store assistant response in database
            if response:
                assistant_message = Message(
                    user_id=current_user.id,
                    role="assistant",
                    content=response,
                    interaction_id=interaction.id
                )
                db.add(assistant_message)
                
                # Update interaction record with response
                await db_manager.update_interaction(
                    db,
                    interaction.id,
                    response=response,
                    status='completed'
                )
            
            db.commit()
            return MessageResponse(response=response)
            
        except Exception as e:
            # Update interaction record with error
            await db_manager.update_interaction(
                db,
                interaction.id,
                error_message=str(e),
                status='failed'
            )
            raise
            
    except Exception as e:
        logger.error(f"Message processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )

@router.get("/api/history", response_model=HistoryResponse)
async def get_history(
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat history from database."""
    try:
        messages = db.query(Message)\
            .filter(Message.user_id == current_user.id)\
            .order_by(Message.timestamp)\
            .all()
            
        return HistoryResponse(
            messages=[{
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            } for msg in messages]
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch history: {str(e)}"
        )

@router.get("/api/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(auth_manager.get_current_user)
):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at
    )

@router.put("/api/me", response_model=UserResponse)
async def update_user(
    user_data: UserUpdate,
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Update user information."""
    try:
        if user_data.email and user_data.email != current_user.email:
            if db.query(User).filter(User.email == user_data.email).first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            current_user.email = user_data.email
            
        if user_data.password:
            current_user.password_hash = User.hash_password(user_data.password)
            
        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)
        
        return UserResponse(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            created_at=current_user.created_at
        )
        
    except Exception as e:
        logger.error(f"Failed to update user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )

@router.post("/api/logout")
async def logout(
    request: Request,
    current_user: User = Depends(auth_manager.get_current_user)
):
    """Handle user logout."""
    try:
        chat_token = request.headers.get('X-Chat-Token')
        if chat_token:
            # Clean up SwarmChat session
            await chat_manager.cleanup_session(chat_token)
            
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )

@router.get("/api/interactions", response_model=List[UserInteractionResponse])
async def get_interactions(
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's interaction history."""
    try:
        interactions = db.query(UserInteraction)\
            .filter(UserInteraction.user_id == current_user.id)\
            .order_by(UserInteraction.start_time.desc())\
            .all()
            
        return [UserInteractionResponse(
            id=interaction.id,
            start_time=interaction.start_time,
            end_time=interaction.end_time,
            prompt=interaction.prompt,
            response=interaction.response,
            agent_name=interaction.agent_name,
            status=interaction.status,
            error_message=interaction.error_message
        ) for interaction in interactions]
        
    except Exception as e:
        logger.error(f"Failed to fetch interactions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch interactions: {str(e)}"
        )

@router.get("/api/login-history", response_model=List[LoginHistoryResponse])
async def get_login_history(
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's login history."""
    try:
        history = db.query(LoginHistory)\
            .filter(LoginHistory.user_id == current_user.id)\
            .order_by(LoginHistory.timestamp.desc())\
            .all()
            
        return [LoginHistoryResponse(
            timestamp=entry.timestamp,
            ip_address=entry.ip_address,
            status=entry.status,
            user_agent=entry.user_agent
        ) for entry in history]
        
    except Exception as e:
        logger.error(f"Failed to fetch login history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch login history: {str(e)}"
        )
