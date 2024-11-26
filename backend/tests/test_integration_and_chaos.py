import pytest
import asyncio
import aiohttp
import docker
import psutil
import random
from typing import List, AsyncGenerator
from contextlib import asynccontextmanager
from databases import Database
from fastapi.testclient import TestClient
from server import app
import logging

# Integration Tests
class TestIntegration:
    @pytest.fixture(scope="module")
    async def test_db(self):
        database_url = "postgresql+asyncpg://test:test@localhost:5432/test_swarm"
        db = Database(database_url)
        await db.connect()
        yield db
        await db.disconnect()

    async def test_full_conversation_flow(self, test_db):
        async with aiohttp.ClientSession() as session:
            # Register
            register_resp = await session.post("/api/register", json={
                "username": "integrationuser",
                "email": "integration@test.com",
                "password": "testpass123"
            })
            assert register_resp.status == 200

            # Login
            login_resp = await session.post("/api/token", data={
                "username": "integrationuser",
                "password": "testpass123"
            })
            assert login_resp.status == 200
            token = (await login_resp.json())["access_token"]

            # Start chat with moderator greeting
            headers = {"Authorization": f"Bearer {token}"}
            chat_resp = await session.post("/api/chat", 
                headers=headers,
                json={"content": "Hello"}
            )
            assert "Welcome" in (await chat_resp.json())["response"]

            # Test agent switching
            for _ in range(3):
                chat_resp = await session.post("/api/chat",
                    headers=headers,
                    json={"content": "Tell me a story"}
                )
                assert chat_resp.status == 200

# Chaos Testing
class TestChaos:
    @pytest.fixture
    async def docker_client(self):
        return docker.from_env()

    async def simulate_network_issues(self):
        """Simulate network latency and packet loss"""
        import subprocess
        try:
            subprocess.run(["tc", "qdisc", "add", "dev", "lo", "root", "netem", 
                          "delay", "100ms", "10ms", "distribution", "normal"])
            yield
        finally:
            subprocess.run(["tc", "qdisc", "del", "dev", "lo", "root"])

    async def simulate_resource_pressure(self):
        """Consume CPU and memory resources"""
        def stress_cpu():
            while True:
                _ = [i * i for i in range(1000000)]

        processes = []
        try:
            for _ in range(psutil.cpu_count()):
                p = multiprocessing.Process(target=stress_cpu)
                p.start()
                processes.append(p)
            yield
        finally:
            for p in processes:
                p.terminate()

    @asynccontextmanager
    async def create_chaos_environment(self, docker_client):
        """Set up chaos testing environment"""
        containers = []
        try:
            # Start dependent services
            db = docker_client.containers.run(
                "postgres:13",
                environment={"POSTGRES_PASSWORD": "test"},
                detach=True
            )
            redis = docker_client.containers.run(
                "redis:6",
                detach=True
            )
            containers.extend([db, redis])

            # Allow services to start
            await asyncio.sleep(10)
            yield
        finally:
            for container in containers:
                container.stop()
                container.remove()

    @pytest.mark.chaos
    async def test_system_under_chaos(self, docker_client):
        async with self.create_chaos_environment(docker_client):
            client = TestClient(app)
            
            # Create test user
            response = client.post("/api/register", json={
                "username": "chaosuser",
                "email": "chaos@test.com",
                "password": "test123"
            })
            assert response.status_code == 200

            # Run chaos scenarios
            async with self.simulate_network_issues():
                async with self.simulate_resource_pressure():
                    # Perform rapid concurrent requests
                    async def make_request():
                        for _ in range(10):
                            response = client.post("/api/chat",
                                headers={"Authorization": "Bearer <token>"},
                                json={"content": "Hello"}
                            )
                            assert response.status_code in [200, 503]
                            await asyncio.sleep(random.uniform(0.1, 0.5))

                    # Run multiple concurrent clients
                    tasks = [make_request() for _ in range(5)]
                    await asyncio.gather(*tasks)

# Load Testing
class TestLoad:
    async def test_sustained_load(self):
        async def user_session(session_id: int):
            async with aiohttp.ClientSession() as session:
                for _ in range(10):
                    response = await session.post("/api/chat",
                        headers={"Authorization": f"Bearer test_token_{session_id}"},
                        json={"content": "Test message"}
                    )
                    assert response.status == 200
                    await asyncio.sleep(random.uniform(1, 3))

        # Simulate 50 concurrent users
        user_tasks = [user_session(i) for i in range(50)]
        await asyncio.gather(*user_tasks)

# Recovery Testing
class TestRecovery:
    async def test_database_recovery(self, docker_client):
        container = docker_client.containers.get("swarm_db")
        
        # Force stop database
        container.stop()
        await asyncio.sleep(5)
        
        # Restart database
        container.start()
        await asyncio.sleep(10)
        
        # Verify system recovers
        client = TestClient(app)
        response = client.post("/api/chat",
            headers={"Authorization": "Bearer test_token"},
            json={"content": "Hello"}
        )
        assert response.status_code == 200

if __name__ == "__main__":
    pytest.main(["-v", "--log-cli-level=INFO"])
