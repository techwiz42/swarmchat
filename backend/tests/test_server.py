import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, UTC, timedelta
from fastapi.testclient import TestClient
from fastapi import status, HTTPException
from database import User, DatabaseManager, Base
from routes import router
from session import UserSession
from jose import jwt, JWTError
from config import JWT_SECRET_KEY, JWT_ALGORITHM
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
async def setup_test():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    loop.close()

@pytest.fixture
def mock_user():
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashedpw",
        created_at=datetime.now(UTC)
    )

@pytest.fixture
def mock_get_user_response(mock_user):
    return Mock(scalars=Mock(return_value=Mock(first=Mock(return_value=mock_user))))

@pytest.fixture
def test_client():
    return TestClient(router)

@pytest.fixture
def valid_token():
    return jwt.encode(
        {"sub": "testuser", "exp": datetime.now(UTC).timestamp() + 3600},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )

class TestDatabaseManager:
    async def test_get_user_by_username(self, mock_user, mock_get_user_response):
        with patch('database.DatabaseManager.get_session') as mock_get_session:
            db_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = db_session
            db_session.execute = AsyncMock(return_value=mock_get_user_response)
            
            db_manager = DatabaseManager()
            result = await db_manager.get_user_by_username("testuser")
            assert result == mock_user

    async def test_create_new_session(self, mock_user):
        with patch('database.DatabaseManager.get_session') as mock_get_session, \
             patch('database.DatabaseManager.get_user_by_username') as mock_get_user, \
             patch('database.DatabaseManager.update_user_chat_state') as mock_update:
            
            db_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = db_session
            mock_get_user.return_value = mock_user
            mock_update.return_value = None
            
            db_manager = DatabaseManager()
            session_id = await db_manager.create_new_session("testuser")
            assert isinstance(session_id, str)
            assert len(session_id) > 0

    @patch('database.DatabaseManager.get_session')
    @patch('database.DatabaseManager.get_user_by_username') 
    @patch('database.DatabaseManager.get_user_chat_state')
    async def test_add_to_chat_history(self, mock_state, mock_get_user, mock_get_session, mock_user):
        session = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = session
        mock_get_user.return_value = Mock(id=1, username="testuser")
        mock_state.return_value = {"current_session": "test_session"}
    
        db_manager = DatabaseManager()
        await db_manager.add_to_chat_history("testuser", "Hello", "Hi")
        session.add.assert_called_once()

class TestUserSession:
    def test_init(self):
        session = UserSession("testuser")
        assert session.username == "testuser"
        assert len(session.messages) == 0

    def test_select_random_agent(self):
        session = UserSession("testuser")
        agent = session.select_random_agent()
        assert agent is not None
        assert hasattr(agent, 'name')

class TestRoutes:
    @patch('routes.db_manager.get_user_by_username')
    @patch('routes.auth_manager.get_current_user')
    @patch('routes.db_manager.get_user_chat_state')
    async def test_chat_new_user(self, mock_state, mock_auth, mock_get_user, test_client, valid_token):
        mock_auth.return_value = "testuser"
        mock_get_user.return_value = Mock(id=1, username="testuser")
        mock_state.return_value = {}
    
        mock_completion = Mock(choices=[Mock(message=Mock(content="Welcome!"))])
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_completion
    
        with patch('routes.db_manager.get_chat_history', return_value=[]), \
            patch('routes.client', mock_client), \
            patch('routes.db_manager.add_to_chat_history', return_value=None), \
            patch('routes.db_manager.update_user_chat_state', return_value=None):
        
            response = test_client.post(
                "/api/chat",
                json={"content": "Hello"},
                headers={"Authorization": f"Bearer {valid_token}"}
            )
        
            assert response.status_code == 200
            assert "Welcome" in response.json()["response"]

    @patch('routes.db_manager.get_user_by_username')
    @patch('routes.auth_manager.get_current_user')
    @patch('routes.db_manager.get_user_chat_state')
    @patch('routes.moderator')
    async def test_chat_returning_user(self, mock_moderator, mock_state, mock_auth, mock_get_user, test_client, valid_token):
        mock_auth.return_value = "testuser"
        mock_get_user.return_value = Mock(id=1, username="testuser")
        mock_state.return_value = {}
        mock_moderator.instructions = "test instructions"
        mock_moderator.name = "moderator"
        mock_moderator.model = "gpt-3.5"
    
        mock_client = AsyncMock()
        mock_completion = Mock(choices=[Mock(message=Mock(content="Hello again!"))])
        mock_client.chat.completions.create.return_value = mock_completion
    
        with patch('routes.client', mock_client), \
            patch('routes.db_manager.get_chat_history', return_value=[{"role": "user", "content": "Previous"}]), \
            patch('routes.db_manager.add_to_chat_history', return_value=None), \
            patch('routes.db_manager.update_user_chat_state', return_value=None):
        
            response = test_client.post(
                "/api/chat",
                json={"content": "Hello"},
                headers={"Authorization": f"Bearer {valid_token}"}
            )
        
            assert response.status_code == 200
            assert "Hello again" in response.json()["response"]

class TestAuth:
    def test_verify_password(self):
        with patch('auth.pwd_context.verify') as mock_verify:
            mock_verify.return_value = True
            from auth import auth_manager
            result = auth_manager.verify_password("test", "hashed")
            assert result is True

    async def test_authenticate_user_success(self, mock_user):
        with patch('auth.db_manager.get_user_by_username') as mock_get_user, \
             patch('auth.auth_manager.verify_password') as mock_verify:
            
            mock_get_user.return_value = mock_user
            mock_verify.return_value = True
            
            from auth import auth_manager
            result = await auth_manager.authenticate_user("testuser", "password")
            assert result == mock_user

    async def test_authenticate_user_fail(self):
        with patch('auth.db_manager.get_user_by_username') as mock_get_user:
            mock_get_user.return_value = None
            
            from auth import auth_manager
            result = await auth_manager.authenticate_user("bad", "wrong")
            assert result is False

    def test_create_access_token(self):
        with patch('auth.jwt.encode') as mock_encode:
            mock_encode.return_value = "test.jwt.token"
            from auth import auth_manager
            result = auth_manager.create_access_token({"sub": "test"})
            assert result == "test.jwt.token"

    async def test_get_current_user_success(self, mock_user, valid_token):
        with patch('auth.db_manager.get_user_by_username') as mock_get_user:
            mock_get_user.return_value = mock_user
            from auth import auth_manager
            result = await auth_manager.get_current_user(valid_token)
            assert result == "testuser"

    async def test_get_current_user_invalid_token(self):
        from auth import auth_manager
        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.get_current_user("invalid.token")
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

if __name__ == "__main__":
    pytest.main(["-v"])
