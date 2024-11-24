import asyncio
import logging
import secrets
from typing import Dict, Optional, AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import HTTPException, Request
from session import UserSession

logger = logging.getLogger(__name__)
access_logger = logging.getLogger("swarm.access")

class SwarmChatManager:
    """Manager class for handling chat sessions."""

    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        self.tokens: Dict[str, str] = {}
        self.sessions_lock: asyncio.Lock = asyncio.Lock()
        self.tokens_lock: asyncio.Lock = asyncio.Lock()
        logger.info("SwarmChatManager initialized")

    async def log_access(self, token: str, request: Request, message_type: str, content: str):
        """Log access information"""
        try:
            async with self.tokens_lock:
                username = self.tokens.get(token)
                if not username:
                    return

            client_ip = request.client.host if request.client else "unknown"
            log_message = (
                f"IP: {client_ip} | "
                f"User: {username} | "
                f"Type: {message_type} | "
                f"Content: {content}"
            )
            access_logger.info(log_message)
        except Exception as e:
            logger.error(f"Error logging access: {str(e)}")

    async def get_token_username(self, token: str) -> Optional[str]:
        """Get username associated with token."""
        async with self.tokens_lock:
            return self.tokens.get(token)

    @asynccontextmanager
    async def get_session_safe(
        self, token: str
    ) -> AsyncGenerator[Optional[UserSession], None]:
        """Safely get a session with proper locking."""
        if not token:
            logger.warning("No token provided")
            yield None
            return

        try:
            username = await self.get_token_username(token)
            if not username:
                logger.warning("Invalid token attempted: %s...", token[:8])
                yield None
                return

            async with self.sessions_lock:
                session = self.sessions.get(username)
                if not session:
                    logger.warning("No session found for username: %s", username)
                    yield None
                    return

                async with session.lock:
                    logger.debug("Session acquired for user: %s", username)
                    try:
                        yield session
                    finally:
                        logger.debug("Session released for user: %s", username)

        except Exception as e:
            logger.error("Error in get_session_safe: %s", str(e))
            yield None

    async def create_session(self, username: str) -> str:
        """Create a new session with proper locking and detailed logging."""
        try:
            logger.info("Starting session creation for user: %s", username)
            token: str = secrets.token_urlsafe(32)

            logger.debug("Created token for user %s: %s...", username, token[:8])

            async with self.sessions_lock:
                logger.debug("Acquired sessions lock for user: %s", username)
                try:
                    session = UserSession(username)
                    self.sessions[username] = session
                    logger.debug("Created UserSession object for user: %s", username)
                
                    init_message = await session.send_first_message()
                    logger.debug("Sent first message for user %s: %s", username, init_message)
                except Exception as session_error:
                    logger.error(
                        "Error during session object creation for user %s: %s",
                        username,
                        str(session_error),
                        exc_info=True
                    )
                    raise

            async with self.tokens_lock:
                logger.debug("Acquired tokens lock for user: %s", username)
                self.tokens[token] = username

            logger.info("Successfully created session for user: %s", username)
            return token

        except Exception as e:
            logger.error(
                "Session creation failed for user %s: %s",
                username,
                str(e),
                exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error creating session: {str(e)}"
            ) from e

    async def process_message(
        self, token: str, content: str, request: Request
    ) -> Optional[str]:
        """Process a message and return the response."""
        try:
            await self.log_access(token, request, "prompt", content)

            async with self.get_session_safe(token) as session:
                if not session:
                    raise HTTPException(status_code=401, detail="Invalid session")

                session.messages.append({"role": "user", "content": content})
                
                if session.first_message_sent:
                    session.agent = session.select_random_agent()
                    logger.info("Using agent: %s", session.agent.name)

                response = await asyncio.to_thread(
                    session.client.run, agent=session.agent, messages=session.messages
                )

                if response.messages:
                    latest_message = response.messages[-1]
                    if latest_message.get("role") == "assistant":
                        session.messages = response.messages
                        response_content = latest_message.get("content")
                        await self.log_access(token, request, "response", response_content)
                        return response_content

                return None

        except Exception as e:
            logger.error("Message processing error: %s", str(e), exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Error processing message: {str(e)}"
            ) from e
