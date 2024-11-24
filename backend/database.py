from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, validates
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import bcrypt
import logging
from typing import Optional
import os
import re

# Configure logging
logger = logging.getLogger(__name__)

# Create SQLAlchemy base class
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    last_login = Column(DateTime)
    is_active = Column(String(1), default='Y')
    
    # Relationships
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    interactions = relationship("UserInteraction", back_populates="user", cascade="all, delete-orphan")
    login_history = relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_username', 'username'),
        Index('idx_email', 'email'),
    )
    
    @validates('username')
    def validate_username(self, key, username):
        if not username:
            raise ValueError("Username cannot be empty")
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not re.match("^[a-zA-Z0-9_-]+$", username):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return username

    @validates('email')
    def validate_email(self, key, email):
        if email:  # Email is optional
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                raise ValueError("Invalid email format")
        return email
    
    @staticmethod
    def hash_password(password: str) -> str:
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                self.password_hash.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    interaction_id = Column(Integer, ForeignKey('user_interactions.id', ondelete='CASCADE'), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="messages")
    interaction = relationship("UserInteraction", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_interaction', 'interaction_id'),
    )
    
    @validates('role')
    def validate_role(self, key, role):
        if role not in ['user', 'assistant']:
            raise ValueError("Role must be either 'user' or 'assistant'")
        return role

class UserInteraction(Base):
    __tablename__ = 'user_interactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    ip_address = Column(String(45), nullable=False)  # Support both IPv4 and IPv6
    session_id = Column(String(255), nullable=False)  # Store chat token
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    agent_name = Column(String(100), nullable=True)  # Store which agent responded
    start_time = Column(DateTime, server_default=func.now())
    end_time = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False)  # 'completed', 'failed', 'processing'
    error_message = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="interactions")
    messages = relationship("Message", back_populates="interaction", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_session', 'user_id', 'session_id'),
        Index('idx_start_time', 'start_time'),
    )
    
    @validates('status')
    def validate_status(self, key, status):
        if status not in ['completed', 'failed', 'processing']:
            raise ValueError("Invalid status value")
        return status

class LoginHistory(Base):
    __tablename__ = 'login_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    ip_address = Column(String(45), nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    status = Column(String(20), nullable=False)  # 'success' or 'failed'
    user_agent = Column(Text, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="login_history")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_login', 'user_id', 'timestamp'),
        Index('idx_ip_address', 'ip_address'),
    )
    
    @validates('status')
    def validate_status(self, key, status):
        if status not in ['success', 'failed']:
            raise ValueError("Status must be either 'success' or 'failed'")
        return status

class DatabaseManager:
    def __init__(self):
        self.setup_database()
        
    def setup_database(self):
        """Initialize database connection and session factory"""
        try:
            database_url = os.getenv('DATABASE_URL', 'sqlite:///./swarmchat.db')
            
            # Configure SQLite for better concurrency if using SQLite
            if database_url.startswith('sqlite'):
                connect_args = {'check_same_thread': False}
            else:
                connect_args = {}
            
            self.engine = create_engine(
                database_url,
                connect_args=connect_args,
                pool_size=5 if not database_url.startswith('sqlite') else None,
                max_overflow=10 if not database_url.startswith('sqlite') else None,
                pool_timeout=30 if not database_url.startswith('sqlite') else None
            )
            
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
            
            logger.info(f"Database initialized with URL: {database_url}")
            
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise
        
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise
    
    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()
    
    async def log_interaction(
        self,
        db_session,
        user_id: int,
        ip_address: str,
        session_id: str,
        prompt: str,
        agent_name: str = None
    ) -> UserInteraction:
        """Create a new interaction record"""
        try:
            interaction = UserInteraction(
                user_id=user_id,
                ip_address=ip_address,
                session_id=session_id,
                prompt=prompt,
                agent_name=agent_name,
                status='processing'
            )
            db_session.add(interaction)
            db_session.commit()
            db_session.refresh(interaction)
            return interaction
            
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Error logging interaction: {str(e)}")
            raise
    
    async def update_interaction(
        self,
        db_session,
        interaction_id: int,
        response: str = None,
        error_message: str = None,
        status: str = 'completed'
    ):
        """Update an existing interaction record"""
        try:
            interaction = db_session.query(UserInteraction).get(interaction_id)
            if interaction:
                interaction.response = response
                interaction.error_message = error_message
                interaction.status = status
                interaction.end_time = datetime.utcnow()
                db_session.commit()
            else:
                logger.warning(f"No interaction found with id: {interaction_id}")
                
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Error updating interaction: {str(e)}")
            raise
    
    async def log_login(
        self,
        db_session,
        user_id: Optional[int],
        ip_address: str,
        status: str,
        user_agent: str = None
    ):
        """Log login attempt"""
        try:
            if user_id:  # Only create login history for valid users
                login_record = LoginHistory(
                    user_id=user_id,
                    ip_address=ip_address,
                    status=status,
                    user_agent=user_agent
                )
                db_session.add(login_record)
                
                if status == 'success':
                    user = db_session.query(User).get(user_id)
                    if user:
                        user.last_login = datetime.utcnow()
                
                db_session.commit()
                
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Error logging login: {str(e)}")
            raise

# Create database manager instance
db_manager = DatabaseManager()

# Initialize database (create tables)
try:
    db_manager.create_tables()
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")
    raise
