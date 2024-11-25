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
    transfer_to_dale_carnegie,
    transfer_to_shrink,
    transfer_to_flapper,
    transfer_to_bullwinkle,
    transfer_to_yogi_berra,
    transfer_to_yogi_bhajan,
    transfer_to_mencken
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

def create_app() -> FastAPI:
    # Initialize FastAPI app
    app = FastAPI(title="SwarmChat API", version="1.0.0")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000",
                      "http://swarmchat.me:3000",
                      "http://swarmchat.me",
                      "http://0.0.0.0:3000",
                      "http://localhost:3001"
                      "http://dev.swarmchat.me",
                      "http://dev.swarmchat.me:3001",
                      "http://0.0.0.0:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
   
    def redact_sensitive_data(body_str: str) -> str:
        """Redact sensitive information from request bodies."""
        try:
            # Try to parse as JSON first
            body = json.loads(body_str)
            sensitive_fields = {'password', 'confirmPassword', 'token', 'access_token', 'refresh_token', 'api_key'}
        
            for field in sensitive_fields:
                if field in body:
                    body[field] = '[REDACTED]'
            return json.dumps(body)
        except json.JSONDecodeError:
            # If not JSON, try to handle form-urlencoded
            if 'password=' in body_str:
                # Use regex to replace password value
                body_str = re.sub(r'password=([^&]*)', 'password=[REDACTED]', body_str)
            return body_str

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        if request.method == "POST":
            body = await request.body()
            try:
                body_str = body.decode()
                # Redact sensitive data before logging
                safe_body = redact_sensitive_data(body_str)
                logger = logging.getLogger(__name__)
                logger.info(f"Request Body: {safe_body}")
                # We need to restore the body content for the request to continue processing
                await request.json()
            except:
                pass
    
        response = await call_next(request)
        return response
    
    # Include routes
    app.include_router(router)
    
    return app

def main():
    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Print environment status
    logger.info("Starting SwarmChat server...")
    logger.info("OpenAI API Key status: %s", "Present" if os.getenv("OPENAI_API_KEY") else "Missing")
    logger.info("Database URL: %s", os.getenv("DATABASE_URL", "sqlite:///./swarmchat.db"))
    logger.info("Environment: %s", os.getenv("ENVIRONMENT", "development"))
    
    # Initialize database
    try:
        logger.info("Initializing database...")
        db_manager.create_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Database initialization failed", exc_info=True)
        raise
    
    # Create and run app
    try:
        app = create_app()
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8001,
            log_level="info"
        )
        server = uvicorn.Server(config)
        server.run()
    except KeyboardInterrupt:
        logger.info("Server shutting down by user request...")
    except Exception as e:
        logger.error("Server crashed", exc_info=True)
        raise
    finally:
        logger.info("Server shutdown complete")

if __name__ == "__main__":
    main()
