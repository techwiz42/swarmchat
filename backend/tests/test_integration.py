import pytest
import asyncio
import aiohttp
import logging
from databases import Database
from fastapi.testclient import TestClient
from server import app
from database import db_manager
from unittest.mock import AsyncMock, Mock, patch
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
def mock_env():
    with patch.dict(os.environ, {'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY')}):
        yield


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

    async def test_registration_and_auth_flow(self, test_client, test_db):
        try:
            register_data = {
                "username": "testuser1",
                "email": "test1@example.com",
                "password": "testpass123"
            }
            response = test_client.post("/api/register", json=register_data)
            logger.debug(f"Register response: {response.status_code} - {response.json()}")
            assert response.status_code == 200

            login_data = {
                "username": register_data["username"],
                "password": register_data["password"],
                "grant_type": "password"
            }
            response = test_client.post("/api/token", data=login_data)
            logger.debug(f"Login response: {response.status_code} - {response.json()}")
            assert response.status_code == 200
        except Exception as e:
            logger.error(f"Test failed: {str(e)}", exc_info=True)
            raise

    async def test_chat_flow(self, test_client, test_db):
        try:
            register_data = {
                "username": "chatuser",
                "email": "chat@example.com",
                "password": "testpass123"
            }
            test_client.post("/api/register", json=register_data)
            
            login_response = test_client.post("/api/token", data={
                "username": register_data["username"],
                "password": register_data["password"],
                "grant_type": "password"
            })
            logger.debug(f"Login response: {login_response.status_code} - {login_response.json()}")
            
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            chat_messages = ["Hello", "/hemingway", "Tell me a story"]
            for message in chat_messages:
                response = test_client.post(
                    "/api/chat",
                    headers=headers,
                    json={"content": message}
                )
                logger.debug(f"Chat response: {response.status_code} - {response.json()}")
                assert response.status_code == 200
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Test failed: {str(e)}", exc_info=True)
            raise

    async def test_chat_history(self, test_client, test_db):
        try:
            register_data = {
                "username": "historyuser",
                "email": "history@example.com",
                "password": "testpass123"
            }
            test_client.post("/api/register", json=register_data)
            
            login_response = test_client.post("/api/token", data={
                "username": register_data["username"],
                "password": register_data["password"],
                "grant_type": "password"
            })
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Send a message
            test_client.post(
                "/api/chat",
                headers=headers,
                json={"content": "Test message"}
            )

            # Get history
            response = test_client.get("/api/history", headers=headers)
            assert response.status_code == 200
            history = response.json()["messages"]
            assert len(history) > 0
        except Exception as e:
            logger.error(f"Test failed: {str(e)}", exc_info=True)
            raise

    async def test_error_handling(self, test_client, test_db):
        headers = {"Authorization": "Bearer invalid_token"}
        response = test_client.post(
            "/api/chat",
            headers=headers,
            json={"content": "Test"}
        )
        assert response.status_code == 401

        response = test_client.post("/api/register", json={
            "username": "test@test.com",
            "email": "invalid_email",
            "password": "short"
        })
        assert response.status_code == 422

    async def test_load_handling(self, test_client, test_db):
        try:
            tokens = []
            for i in range(5):
                register_data = {
                    "username": f"loaduser{i}",
                    "email": f"load{i}@example.com",
                    "password": "testpass123"
                }
                test_client.post("/api/register", json=register_data)
                
                login_response = test_client.post("/api/token", data={
                    "username": register_data["username"],
                    "password": register_data["password"],
                    "grant_type": "password"
                })
                tokens.append(login_response.json()["access_token"])

            async def send_messages(token):
                headers = {"Authorization": f"Bearer {token}"}
                for _ in range(3):
                    response = test_client.post(
                        "/api/chat",
                        headers=headers,
                        json={"content": "Load test message"}
                    )
                    assert response.status_code in [200, 503]
                    await asyncio.sleep(random.uniform(0.1, 0.3))

            await asyncio.gather(*[
                send_messages(token) for token in tokens
            ])
        except Exception as e:
            logger.error(f"Test failed: {str(e)}", exc_info=True)
            raise

if __name__ == "__main__":
    pytest.main(["-v", "--log-cli-level=DEBUG"])
