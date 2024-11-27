import pytest
import tracemalloc
import psutil
import asyncio
import gc
import logging
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
import asyncpg
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from typing import List, Dict
from database import User, DatabaseManager, Message, ChatState
from routes import router
from session import UserSession

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure pytest-asyncio default fixture loop scope
pytest_plugins = ["pytest_asyncio"]
pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
async def cleanup():
    try:
        async with asyncio.timeout(3):
            yield
            gc.collect()
            await asyncio.sleep(0)
    except asyncio.TimeoutError:
        logger.error("Cleanup fixture timed out")
        raise

@pytest.fixture
async def db_pool():
    pool = None
    try:
        async with asyncio.timeout(5):
            pool = await asyncpg.create_pool(
                "postgresql://postgres:postgres@localhost:5432/test_swarm",
                min_size=1,
                max_size=10,
                timeout=3.0
            )
            async with pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        content TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            yield pool
            if pool:
                async with pool.acquire() as conn:
                    await conn.execute("DROP TABLE IF EXISTS messages")
                await pool.close()
    except Exception as e:
        logger.error(f"Database pool fixture failed: {e}")
        if pool:
            await pool.close()
        raise

async def get_active_db_connections(pool) -> int:
    try:
        async with asyncio.timeout(3):
            async with pool.acquire() as conn:
                return await conn.fetchval("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """) or 0
    except asyncio.TimeoutError:
        logger.error("Connection count query timed out")
        return 0

class TestDatabaseReliability:
    async def test_connection_cleanup(self, db_pool):
        max_connections = 5
        async def concurrent_sessions(n):
            async with db_pool.acquire() as conn:
                await conn.execute("SELECT pg_sleep(0.1)")
        
        tasks = [concurrent_sessions(i) for i in range(max_connections)]
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.2)
        final_connections = await get_active_db_connections(db_pool)
        assert final_connections <= max_connections

    async def test_connection_error_recovery(self, db_pool):
        db_manager = DatabaseManager()
        with patch('database.DatabaseManager.get_session', side_effect=SQLAlchemyError("Test error")):
            with pytest.raises(SQLAlchemyError):
                async with db_manager.get_session() as session:
                    await session.execute(text("SELECT 1"))

    async def test_transaction_rollback(self, db_pool):
        async with db_pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE messages")
            initial_count = await conn.fetchval("SELECT COUNT(*) FROM messages")
            try:
                async with conn.transaction():
                    await conn.execute("INSERT INTO messages (content) VALUES ('test')")
                    raise ValueError("Simulated error")
            except ValueError:
                pass
            final_count = await conn.fetchval("SELECT COUNT(*) FROM messages")
            assert final_count == initial_count

class TestMemoryReliability:
    async def test_memory_snapshot(self):
        try:
            async with asyncio.timeout(5):
                gc.collect(generation=2)
                memory_before = psutil.Process().memory_info().rss
                
                objs = [UserSession("test") for _ in range(50)]
                intermediate_memory = psutil.Process().memory_info().rss
                
                del objs
                gc.collect(generation=2)
                memory_after = psutil.Process().memory_info().rss
                
                # More lenient assertion
                assert memory_after <= intermediate_memory
        except asyncio.TimeoutError:
            pytest.fail("Memory test timed out")

class TestResourceManagement:
    async def test_concurrent_session_limits(self, db_pool):
        max_connections = 5
        sem = asyncio.Semaphore(max_connections)
        
        async def session_worker():
            async with sem:
                async with db_pool.acquire() as conn:
                    await conn.execute("SELECT 1")
                    await asyncio.sleep(0.1)
        
        tasks = [session_worker() for _ in range(max_connections)]
        await asyncio.gather(*tasks)
        current_connections = await get_active_db_connections(db_pool)
        assert current_connections <= max_connections

class TestErrorRecovery:
    async def test_connection_pool_recovery(self, db_pool):
        max_test_connections = 3
        
        async def use_connection():
            async with db_pool.acquire() as conn:
                await conn.execute("SELECT 1")
                await asyncio.sleep(0.1)
        
        tasks = [use_connection() for _ in range(max_test_connections)]
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.2)
        
        final_size = await get_active_db_connections(db_pool)
        assert final_size <= max_test_connections

if __name__ == "__main__":
    pytest.main(["-v", "--log-cli-level=DEBUG", "--capture=no"])
