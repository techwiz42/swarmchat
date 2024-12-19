import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, patch
from databases import Database
from fastapi.testclient import TestClient
from server import app
from database import db_manager
from unittest.mock import AsyncMock, Mock, patch
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture(autouse=True)
def mock_env():
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key-123'}):
        yield

@pytest.fixture
def mock_openai():
    with patch("openai.AsyncOpenAI") as mock:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create.return_value.choices = [
            AsyncMock(message=AsyncMock(content="Mocked response"))
        ]
        mock.return_value = mock_instance
        yield mock

class TestIntegration:
    @pytest.fixture(scope="module")
    async def test_db(self):
        database_url = "postgresql+asyncpg://testuser:testpass123@localhost:5432/swarm_test"
        db = Database(database_url)
        await db.connect()
        await db_manager.create_tables()
        yield db
        await db.disconnect()

    @pytest.fixture
    async def test_client(self):
        return TestClient(app)

    async def test_registration_and_auth_flow(self, test_client, test_db, mock_openai):
        register_data = {
            "username": "testuser1",
            "email": "test1@example.com",
            "password": "testpass123"
        }
        response = test_client.post("/api/register", json=register_data)
        assert response.status_code == 200

        login_data = {
            "username": register_data["username"],
            "password": register_data["password"],
            "grant_type": "password"
        }
        response = test_client.post("/api/token", data=login_data)
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_chat_flow(self, test_client, test_db, mock_openai):
        response = await self._login_user(test_client, "chatuser", "chat@example.com")
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        chat_response = test_client.post(
            "/api/chat",
            headers=headers,
            json={"content": "Hello"}
        )
        assert chat_response.status_code == 200

    async def test_chat_history(self, test_client, test_db, mock_openai):
        response = await self._login_user(test_client, "historyuser", "history@example.com")
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        test_client.post("/api/chat", headers=headers, json={"content": "Test"})
        history = test_client.get("/api/history", headers=headers)
        assert history.status_code == 200
        assert len(history.json()["messages"]) > 0

    async def test_load_handling(self, test_client, test_db, mock_openai):
        async def user_session(username):
            response = await self._login_user(test_client, username, f"{username}@test.com")
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            for _ in range(2):
                response = test_client.post(
                    "/api/chat",
                    headers=headers,
                    json={"content": "Test"}
                )
                assert response.status_code in [200, 503]
                await asyncio.sleep(0.1)

        await asyncio.gather(*[
            user_session(f"loaduser{i}") for i in range(3)
        ])

    async def _login_user(self, client, username, email):
        register_data = {
            "username": username,
            "email": email,
            "password": "testpass123"
        }
        client.post("/api/register", json=register_data)
        
        return client.post("/api/token", data={
            "username": username,
            "password": "testpass123",
            "grant_type": "password"
        })

if __name__ == "__main__":
    pytest.main(["-v"])
