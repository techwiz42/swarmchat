import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from routes import router, chat_manager
from unittest.mock import Mock, patch
import base64

@pytest.fixture
def client():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

class TestRoutes:
    async def test_get_token_from_auth_valid(self, client):
        token = "valid-token"
        headers = {"Authorization": f"Bearer {token}"}
        request = Mock()
        request.headers = headers
        result = await get_token_from_auth(request)
        assert result == token

    async def test_get_token_from_auth_invalid(self, client):
        headers = {"Authorization": "Invalid format"}
        request = Mock()
        request.headers = headers
        with pytest.raises(HTTPException) as exc:
            await get_token_from_auth(request)
        assert exc.value.status_code == 401

    async def test_get_token_from_auth_missing(self, client):
        request = Mock()
        request.headers = {}
        with pytest.raises(HTTPException) as exc:
            await get_token_from_auth(request)
        assert exc.value.status_code == 401

    async def test_login_endpoint(self, client):
        username = "test_user"
        password = "dummy"
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers = {"Authorization": f"Basic {credentials}"}
        
        response = client.post("/api/login", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["username"] == username

    async def test_login_invalid_credentials(self, client):
        headers = {"Authorization": "Basic invalid"}
        response = client.post("/api/login", headers=headers)
        assert response.status_code == 401

    async def test_chat_endpoint(self, client):
        # Mock successful session
        mock_response = "Mock response"
        with patch('routes.chat_manager.process_message', 
                  return_value=mock_response):
            response = client.post(
                "/api/chat",
                headers={"Authorization": "Bearer valid-token"},
                json={"content": "test message"}
            )
            assert response.status_code == 200
            assert response.json()["response"] == mock_response

    async def test_chat_invalid_token(self, client):
        response = client.post(
            "/api/chat",
            headers={"Authorization": "Bearer invalid-token"},
            json={"content": "test message"}
        )
        assert response.status_code == 401

    async def test_history_endpoint(self, client):
        # Mock successful session
        mock_messages = [
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "response"}
        ]
        with patch('routes.chat_manager.get_session_safe') as mock_session:
            mock_session.return_value.__aenter__.return_value.messages = mock_messages
            response = client.get(
                "/api/history",
                headers={"Authorization": "Bearer valid-token"}
            )
            assert response.status_code == 200
            assert response.json()["messages"] == mock_messages

    async def test_history_invalid_token(self, client):
        response = client.get(
            "/api/history",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401

    async def test_debug_endpoint(self, client):
        response = client.get("/api/debug")
        assert response.status_code == 200
        data = response.json()
        assert "env_vars" in data
        assert "working_directory" in data
        assert "python_path" in data
