import pytest
import asyncio
from manager import SwarmChatManager
from session import UserSession
from fastapi import HTTPException, Request
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
class TestSwarmChatManager:
    @pytest.fixture
    async def manager(self):
        return SwarmChatManager()

    @pytest.fixture
    def mock_request(self):
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request

    async def test_init(self, manager):
        assert manager.sessions == {}
        assert manager.tokens == {}
        assert manager.sessions_lock is not None
        assert manager.tokens_lock is not None

    async def test_log_access(self, manager, mock_request):
        # Setup
        token = "test-token"
        async with manager.tokens_lock:
            manager.tokens[token] = "test-user"
        
        # Test
        await manager.log_access(token, mock_request, "test-message", "test-content")
        # In real implementation, would verify log file contents

    async def test_get_token_username(self, manager):
        # Setup
        token = "test-token"
        username = "test-user"
        async with manager.tokens_lock:
            manager.tokens[token] = username
        
        # Test
        result = await manager.get_token_username(token)
        assert result == username

    async def test_get_session_safe(self, manager):
        # Setup
        token = "test-token"
        username = "test-user"
        session = UserSession(username)
        async with manager.tokens_lock:
            manager.tokens[token] = username
        async with manager.sessions_lock:
            manager.sessions[username] = session

        # Test
        async with manager.get_session_safe(token) as safe_session:
            assert safe_session == session

    async def test_get_session_safe_invalid_token(self, manager):
        async with manager.get_session_safe("invalid-token") as session:
            assert session is None

    async def test_create_session(self, manager):
        username = "test-user"
        token = await manager.create_session(username)
        
        assert token is not None
        assert username in manager.sessions
        assert token in manager.tokens
        assert manager.tokens[token] == username

    async def test_create_session_duplicate(self, manager):
        username = "test-user"
        token1 = await manager.create_session(username)
        token2 = await manager.create_session(username)
        
        assert token1 != token2
        assert username in manager.sessions
        assert token2 in manager.tokens
        assert manager.tokens[token2] == username

    async def test_process_message(self, manager, mock_request):
        # Setup
        username = "test-user"
        token = await manager.create_session(username)
        
        # Test
        response = await manager.process_message(token, "Hello", mock_request)
        assert response is not None
        
        session = manager.sessions[username]
        assert len(session.messages) > 0
        assert any(msg["role"] == "user" and msg["content"] == "Hello" 
                  for msg in session.messages)

    async def test_process_message_invalid_token(self, manager, mock_request):
        with pytest.raises(HTTPException) as exc:
            await manager.process_message("invalid-token", "Hello", mock_request)
        assert exc.value.status_code == 401

    async def test_concurrent_session_creation(self, manager):
        usernames = [f"user{i}" for i in range(10)]
        tokens = await asyncio.gather(
            *[manager.create_session(username) for username in usernames]
        )
        
        assert len(tokens) == 10
        assert len(manager.sessions) == 10
        assert len(manager.tokens) == 10
        assert len(set(tokens)) == 10  # All tokens should be unique
