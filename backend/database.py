from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from datetime import datetime
import os
from typing import Optional, List, Dict
import json
from contextlib import asynccontextmanager

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

class ChatToken(Base):
    __tablename__ = "chat_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_valid = Column(Boolean, default=True)

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

class DatabaseManager:
    @asynccontextmanager
    async def get_session(self) -> AsyncSession:
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except:
                await session.rollback()
                raise

    async def create_tables(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        async with self.get_session() as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            return result.scalars().first()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        async with self.get_session() as session:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            return result.scalars().first()

    async def create_user(self, username: str, email: str, hashed_password: str, created_at: datetime) -> User:
        async with self.get_session() as session:
            new_user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                created_at=created_at
            )
            session.add(new_user)
            return new_user

    async def store_chat_token(self, user_id: int, token: str) -> None:
        async with self.get_session() as session:
            chat_token = ChatToken(user_id=user_id, token=token)
            session.add(chat_token)

    async def invalidate_chat_token(self, token: str) -> None:
        async with self.get_session() as session:
            result = await session.execute(
                select(ChatToken).where(ChatToken.token == token)
            )
            chat_token = result.scalars().first()
            if chat_token:
                chat_token.is_valid = False

    async def validate_chat_token(self, token: str) -> bool:
        async with self.get_session() as session:
            result = await session.execute(
                select(ChatToken).where(
                    ChatToken.token == token,
                    ChatToken.is_valid == True
                )
            )
            return result.scalars().first() is not None

    async def get_chat_history(self, username: str) -> List[Dict]:
        async with self.get_session() as session:
            user = await self.get_user_by_username(username)
            if not user:
                return []

            result = await session.execute(
                select(Message)
                .where(Message.user_id == user.id)
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

    async def add_to_chat_history(self, username: str, message: str, response: str) -> None:
        async with self.get_session() as session:
            user = await self.get_user_by_username(username)
            if user:
                chat_history = Message(
                    user_id=user.id,
                    content=message,
                    response=response
                )
                session.add(chat_history)

    async def get_user_chat_state(self, username: str) -> Dict:
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
                    return {}
            return {}

    async def update_user_chat_state(self, username: str, state: Dict) -> None:
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

    async def clear_user_chat_state(self, username: str) -> None:
        async with self.get_session() as session:
            user = await self.get_user_by_username(username)
            if user:
                result = await session.execute(
                    select(ChatState).where(ChatState.user_id == user.id)
                )
                chat_state = result.scalars().first()
                if chat_state:
                    await session.delete(chat_state)

# Create database manager instance
db_manager = DatabaseManager()
