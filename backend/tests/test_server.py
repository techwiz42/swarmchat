import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from fastapi.testclient import TestClient
from database import User, DatabaseManager
from routes import router
from session import UserSession

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_user():
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashedpw",
        created_at=datetime.utcnow()
    )

@pytest.fixture
def mock_get_user_response(mock_user):
    mock_scalar = AsyncMock()
    mock_scalar.first.return_value = mock_user
    mock_result = AsyncMock()
    mock_result.scalars.return_value = mock_scalar
    return mock_result

@pytest.fixture
def test_client():
    return TestClient(router)

class TestDatabaseManager:
    async def test_get_user_by_username(self, mock_user, mock_get_user_response):
        with patch('database.DatabaseManager.get_session') as mock_get_session:
            db_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = db_session
            db_session.execute.return_value = mock_get_user_response
            
            db_manager = DatabaseManager()
            result = await db_manager.get_user_by_username("testuser")
            assert result == mock_user

    async def test_create_new_session(self, mock_user, mock_get_user_response):
        with patch('database.DatabaseManager.get_session') as mock_get_session, \
             patch('database.DatabaseManager.get_user_by_username') as mock_get_user, \
             patch('database.DatabaseManager.update_user_chat_state') as mock_update:
            
            db_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = db_session
            mock_get_user.return_value = mock_user
            mock_update.return_value = None
            db_session.execute.return_value = mock_get_user_response
            
            db_manager = DatabaseManager()
            session_id = await db_manager.create_new_session("testuser")
            assert isinstance(session_id, str)
            assert len(session_id) > 0

    async def test_add_to_chat_history(self, mock_user, mock_get_user_response):
        with patch('database.DatabaseManager.get_session') as mock_get_session, \
             patch('database.DatabaseManager.get_user_by_username') as mock_get_user, \
             patch('database.DatabaseManager.get_user_chat_state') as mock_get_state:
            
            db_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = db_session
            mock_get_user.return_value = mock_user
            mock_get_state.return_value = {"current_session": "test_session"}
            db_session.execute.return_value = mock_get_user_response
            
            db_manager = DatabaseManager()
            await db_manager.add_to_chat_history("testuser", "Hello", "Hi")
            db_session.add.assert_called_once()

class TestUserSession:
    def test_init(self):
        session = UserSession("testuser")
        assert session.username == "testuser"
        assert not session.first_message_sent

    async def test_send_first_message(self):
        session = UserSession("testuser")
        message = await session.send_first_message()
        assert message is not None
        assert session.first_message_sent
        assert len(session.messages) == 1
        assert session.messages[0]["role"] == "assistant"

    def test_select_random_agent(self):
        session = UserSession("testuser")
        agent = session.select_random_agent()
        assert agent is not None
        assert hasattr(agent, 'name')

class TestRoutes:
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        with patch('routes.auth_manager.get_current_user', return_value="testuser"):
            yield

    async def test_chat_new_user(self, test_client):
        with patch('routes.db_manager.get_chat_history') as mock_history, \
             patch('routes.client.chat.completions.create') as mock_chat:
            
            mock_history.return_value = []
            mock_chat.return_value = Mock(choices=[Mock(message=Mock(content="Welcome!"))])
            
            response = test_client.post(
                "/api/chat",
                json={"content": "Hello"},
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            assert "Welcome" in response.json()["response"]

    async def test_chat_returning_user(self, test_client):
        with patch('routes.db_manager.get_chat_history') as mock_history, \
             patch('routes.client.chat.completions.create') as mock_chat:
            
            mock_history.return_value = [{"role": "user", "content": "Previous"}]
            mock_chat.return_value = Mock(choices=[Mock(message=Mock(content="Hello again!"))])
            
            response = test_client.post(
                "/api/chat",
                json={"content": "Hello"},
                headers={"Authorization": "Bearer test_token"}
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
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        with patch('auth.jwt.encode') as mock_encode:
            mock_encode.return_value = test_token
            from auth import auth_manager
            result = auth_manager.create_access_token({"sub": "test"})
            assert result == test_token

if __name__ == "__main__":
    pytest.main(["-v"])
