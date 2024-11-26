from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from datetime import datetime
import secrets
import os 
from typing import Optional, List, Dict
import json
from contextlib import asynccontextmanager
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Get database URL from environment or use default PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/swarmchat"
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String, index=True)
    content = Column(Text)
    response = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    interaction_type = Column(String)
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class LoginHistory(Base):
    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    login_time = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    success = Column(Boolean, default=True)

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text)
    response = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ChatState(Base):
    __tablename__ = "chat_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    state_data = Column(Text)  # JSON string of the state
    updated_at = Column(DateTime, default=datetime.utcnow)

class DatabaseError(Exception):
    def __init__(self, statement, params, original_error):
        self.statement = statement
        self.params = params
        self.original_error = original_error
        super().__init__(f"Database error: {original_error}")

class DatabaseManager:
    DB_POOL_CONFIG = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'max_overflow': 10
    }

    def __init__(self):
        self.engine = create_async_engine(
            DATABASE_URL,
            **self.DB_POOL_CONFIG
        )

    async def handle_db_error(self, error, statement, params):
        logger.error(f"Database error: {error}", exc_info=True)
        raise DatabaseError(statement, params, error)

    @asynccontextmanager
    async def get_session(self):
        session = AsyncSession(self.engine, expire_on_commit=False)
        try:
            yield session
        except Exception as e:
            logger.error(f"Session error: {e}", exc_info=True)
            await session.rollback()
            raise
        finally:
            await session.close()

    async def create_new_session(self, username: str) -> str:
        """Create a new chat session for user and return session_id."""
        session_id = secrets.token_urlsafe(16)
        try:
            async with self.get_session() as session:
                user = await self.get_user_by_username(username)
                if user:
                    # Store session creation time in user_state
                    new_state = {
                        "current_session": session_id,
                        "session_start": datetime.utcnow().isoformat()
                    }
                    await self.update_user_chat_state(username, new_state)
                    await session.commit()
                    logger.info(f"Created new session {session_id} for user {username}")
                    return session_id
        except Exception as e:
            logger.error(f"Error creating new session: {e}", exc_info=True)
            raise
    
    async def get_chat_history(self, username: str) -> List[Dict]:
        """Get chat history for current session only."""
        try:
            async with self.get_session() as session:
                # Get user
                result = await session.execute(
                    select(User).where(User.username == username)
                )
                user = result.scalars().first()
                if not user:
                    return []
            
                # Get user state in the same session
                state_result = await session.execute(
                    select(ChatState).where(ChatState.user_id == user.id)
                )
                chat_state = state_result.scalars().first()
            
                if not chat_state or not chat_state.state_data:
                    return []
                
                try:
                    state_data = json.loads(chat_state.state_data)
                    current_session = state_data.get('current_session')
                    if not current_session:
                        return []
                except json.JSONDecodeError:
                    logger.error(f"JSON decode error for chat state of user {username}")
                    return []

                # Get messages for this session
                result = await session.execute(
                    select(Message)
                    .where(
                        and_(
                            Message.user_id == user.id,
                            Message.session_id == current_session
                        )
                    )
                    .order_by(Message.timestamp)
                )
                history = result.scalars().all()

                return [
                    {
                        "role": "user" if i % 2 == 0 else "assistant",
                        "content": h.content if i % 2 == 0 else h.response
                    }
                    for i, h in enumerate(history)
                ]
        except Exception as e:
            logger.error(f"Error getting chat history: {e}", exc_info=True)
            raise

    async def get_all_user_messages(self, username: str) -> List[Dict]:
        """Get complete message history across all sessions"""
        try:
            async with self.get_session() as session:
                user = await self.get_user_by_username(username)
                if not user:
                    return []
            
                result = await session.execute(
                    select(Message)
                    .where(Message.user_id == user.id)
                    .order_by(Message.timestamp)
                )
                return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting all user messages: {e}", exc_info=True)
            raise

    async def add_to_chat_history(self, username: str, message: str, response: str) -> None:
        """Add message to current session's chat history."""
        try:
            async with self.get_session() as session:
                user = await self.get_user_by_username(username)
                if user:
                    # Get current session_id from user state
                    user_state = await self.get_user_chat_state(username)
                    current_session = user_state.get('current_session')
                    
                    if not current_session:
                        # Create new session if none exists
                        current_session = await self.create_new_session(username)

                    chat_history = Message(
                        user_id=user.id,
                        session_id=current_session,
                        content=message,
                        response=response
                    )
                    session.add(chat_history)
                    await session.commit()
                    logger.info(f"Saved message for user {username} in session {current_session}")
        except Exception as e:
            logger.error(f"Error adding to chat history: {e}", exc_info=True)
            raise

    async def create_tables(self):
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}", exc_info=True)
            raise

    async def get_user_by_username(self, username: str) -> Optional[User]:
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(User).where(User.username == username)
                )
                return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting user by username: {e}", exc_info=True)
            raise

    async def get_user_by_email(self, email: str) -> Optional[User]:
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(User).where(User.email == email)
                )
                return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting user by email: {e}", exc_info=True)
            raise

    async def create_user(self, username: str, email: str, hashed_password: str, created_at: datetime) -> User:
        try:
            async with self.get_session() as session:
                new_user = User(
                    username=username,
                    email=email,
                    hashed_password=hashed_password,
                    created_at=created_at
                )
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                logger.info(f"Created new user: {username}")
                return new_user
        except Exception as e:
            logger.error(f"Error creating user: {e}", exc_info=True)
            raise

    async def get_user_chat_state(self, username: str) -> Dict:
        try:
            async with self.get_session() as session:
                user = await self.get_user_by_username(username)
                if not user:
                    return {}

                result = await session.execute(
                    select(ChatState).where(ChatState.user_id == user.id)
                )
                state = result.scalars().first()

                if state and state.state_data:
                    try:
                        return json.loads(state.state_data)
                    except json.JSONDecodeError:
                        logger.error(f"JSON decode error for chat state of user {username}")
                        return {}
                return {}
        except Exception as e:
            logger.error(f"Error getting user chat state: {e}", exc_info=True)
            raise

    async def update_user_chat_state(self, username: str, state: Dict) -> None:
        try:
            async with self.get_session() as session:
                user = await self.get_user_by_username(username)
                if user:
                    result = await session.execute(
                        select(ChatState).where(ChatState.user_id == user.id)
                    )
                    chat_state = result.scalars().first()

                    state_json = json.dumps(state)

                    if chat_state:
                        chat_state.state_data = state_json
                        chat_state.updated_at = datetime.utcnow()
                    else:
                        chat_state = ChatState(
                            user_id=user.id,
                            state_data=state_json
                        )
                        session.add(chat_state)
                    await session.commit()
                    logger.info(f"Updated chat state for user {username}")
        except Exception as e:
            logger.error(f"Error updating user chat state: {e}", exc_info=True)
            raise

    async def clear_user_chat_state(self, username: str) -> None:
        try:
            async with self.get_session() as session:
                user = await self.get_user_by_username(username)
                if user:
                    result = await session.execute(
                        select(ChatState).where(ChatState.user_id == user.id)
                    )
                    chat_state = result.scalars().first()
                    if chat_state:
                        await session.delete(chat_state)
                        await session.commit()
                        logger.info(f"Cleared chat state for user {username}")
        except Exception as e:
            logger.error(f"Error clearing user chat state: {e}", exc_info=True)
            raise

# Create database manager instance
db_manager = DatabaseManager()
