"""FastAPI-based chat application that manages multi-agent conversations using a swarm architecture."""

import asyncio
import logging
import random
import secrets
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional, AsyncGenerator
from logging.handlers import RotatingFileHandler
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends, Request
import uvicorn
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from dotenv import load_dotenv
from config import JWT_SECRET_KEY, DATABASE_URL, ENVIRONMENT

# Load environment variables
load_dotenv()

# Import our components
from database import engine, Base, db_manager
from auth import auth_manager
from routes import router
from agents import (
    moderator,
    transfer_to_hemmingway,
    transfer_to_pynchon,
    transfer_to_dickinson,
    transfer_to_shrink
)

# Create logging directory if it doesn't exist
LOG_DIR = "/var/log/swarm"
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging handlers
def setup_logging():
    # Configure main application logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),  # This ensures console output
            RotatingFileHandler(
                os.path.join(LOG_DIR, "swarm_chat.log"),
                maxBytes=10_485_760,
                backupCount=5,
                encoding='utf-8'
            )
        ],
    )

    # Configure access logger
    access_logger = logging.getLogger("swarm.access")
    access_logger.setLevel(logging.INFO)
    access_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "access.log"),
        maxBytes=10_485_760,
        backupCount=5,
        encoding='utf-8'
    )
    access_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    access_handler.setFormatter(access_formatter)
    access_logger.addHandler(access_handler)

    # Configure error logger
    error_logger = logging.getLogger("swarm.error")
    error_logger.setLevel(logging.ERROR)
    error_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "error.log"),
        maxBytes=10_485_760,
        backupCount=5,
        encoding='utf-8'
    )
    error_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
        'Exception: %(exc_info)s'
    )
    error_handler.setFormatter(error_formatter)
    error_logger.addHandler(error_handler)

    # Set uvicorn access logger
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.handlers = []
    uvicorn_access_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "uvicorn_access.log"),
        maxBytes=10_485_760,
        backupCount=5,
        encoding='utf-8'
    )
    uvicorn_access_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    uvicorn_logger.addHandler(uvicorn_access_handler)
    uvicorn_logger.setLevel(logging.INFO)

async def create_tables():
    try:
        await db_manager.create_tables()
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Error creating database tables: {e}")
        raise

# Create the app object at module level
app = FastAPI(title="SwarmChat API", version="1.0.0")
app.include_router(router)

# Add CORS middleware with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://swarmchat.me",
        "https://dev.swarmchat.me"
        "https://swarmchat.me:3000",
        "https://dev.swarmchat.me:3001"
    ],
    allow_credentials=True,
    allow_methods=["GET","POST"],  # Or specific methods ["GET", "POST", "PUT", "DELETE"]
    allow_headers=["*"],  # Or specific headers
)

