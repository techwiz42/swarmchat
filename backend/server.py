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
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from swarm import Swarm, Agent

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

# Import routes after logging is configured
from routes import router

def create_app() -> FastAPI:
    app = FastAPI()
    
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
    
    # Include routes
    app.include_router(router)
    
    return app

# Create the FastAPI app
app = create_app()

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"\n{'='*50}")
    print(f"Request: {request.method} {request.url}")
    print(f"Headers: {request.headers}")
    
    if request.method == "POST":
        body = await request.body()
        try:
            print(f"Body: {body.decode()}")
        except:
            print(f"Body: {body}")
    
    response = await call_next(request)
    print(f"Status Code: {response.status_code}")
    print(f"{'='*50}\n")
    return response

def main():
    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Print OpenAI API key status
    print("OpenAI API Key status:", "Present" if os.getenv("OPENAI_API_KEY") else "Missing")
    print("Key starts with:", os.getenv("OPENAI_API_KEY")[:4] + "..." if os.getenv("OPENAI_API_KEY") else "None")
    
    # Create and run app
    logger.info("Starting Swarm Chat server...")
    try:
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
