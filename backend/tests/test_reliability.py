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

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
async def cleanup():
    logger.debug("Starting cleanup")
    try:
        async with asyncio.timeout(3):
            yield
            gc.collect()
            await asyncio.sleep(0)
            logger.debug("Cleanup complete")
    except asyncio.TimeoutError:
        logger.error("Cleanup fixture timed out")
        raise

@pytest.fixture(scope="function")
async def db_pool():
    logger.debug("Creating database pool")
    pool = None
    try:
        async with asyncio.timeout(5):
            pool = await asyncpg.create_pool(
                "postgresql://postgres:postgres@localhost:5432/test_swarm",
                min_size=1,
                max_size=10,
                timeout=3.0
            )
            logger.debug("Pool created successfully")

            # Create tables
            async with pool.acquire() as conn:
                logger.debug("Creating test tables")
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        content TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            
            yield pool
            
            # Cleanup
            logger.debug("Starting pool cleanup")
            if pool:
                async with pool.acquire() as conn:
                    await conn.execute("DROP TABLE IF EXISTS messages")
                await pool.close()
            logger.debug("Pool cleanup complete")
    except asyncio.TimeoutError:
        logger.error("Database pool fixture timed out")
        if pool:
            await pool.close()
        raise
    except Exception as e:
        logger.error(f"Database pool fixture failed: {e}")
        if pool:
            await pool.close()
        raise

async def get_active_db_connections(pool) -> int:
    logger.debug("Checking active connections")
    try:
        async with asyncio.timeout(3):
            async with pool.acquire() as conn:
                result = await conn.fetchval("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """)
                logger.debug(f"Active connections: {result}")
                return result or 0
    except asyncio.TimeoutError:
        logger.error("Connection count query timed out")
        return 0

@pytest.mark.asyncio(timeout=10)
class TestDatabaseReliability:
    async def test_connection_cleanup(self, db_pool):
        logger.debug("Starting connection cleanup test")
        max_connections = 5
        
        try:
            async with asyncio.timeout(5):
                async def concurrent_sessions(n):
                    async with db_pool.acquire() as conn:
                        await conn.execute("SELECT pg_sleep(0.1)")
                        logger.debug(f"Session {n} completed")
                
                initial_connections = await get_active_db_connections(db_pool)
                tasks = [concurrent_sessions(i) for i in range(max_connections)]
                await asyncio.gather(*tasks)
                await asyncio.sleep(0.2)
                
                final_connections = await get_active_db_connections(db_pool)
                assert final_connections <= max_connections
        except asyncio.TimeoutError:
            logger.error("Connection cleanup test timed out")
            raise

    async def test_connection_error_recovery(self, db_pool):
        logger.debug("Starting error recovery test")
        try:
            async with asyncio.timeout(5):
                db_manager = DatabaseManager()
                with patch('database.AsyncSessionLocal', side_effect=SQLAlchemyError("Test error")):
                    with pytest.raises(SQLAlchemyError):
                        async with db_manager.get_session() as session:
                            await session.execute(text("SELECT 1"))
        except asyncio.TimeoutError:
            logger.error("Error recovery test timed out")
            raise

    async def test_transaction_rollback(self, db_pool):
        logger.debug("Starting transaction rollback test")
        try:
            async with asyncio.timeout(5):
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
        except asyncio.TimeoutError:
            logger.error("Transaction rollback test timed out")
            raise

@pytest.mark.asyncio(timeout=10)
class TestMemoryReliability:
    async def test_memory_snapshot(self):
        logger.debug("Starting memory snapshot test")
        try:
            async with asyncio.timeout(5):
                gc.collect(generation=2)
                memory_before = psutil.Process().memory_info().rss
                logger.debug(f"Initial memory: {memory_before}")
                
                # Create objects in smaller batches
                batch_size = 1000
                objs = []
                for i in range(5):
                    batch = [UserSession("test") for _ in range(batch_size)]
                    objs.extend(batch)
                    await asyncio.sleep(0)
                    logger.debug(f"Created batch {i+1}")
                
                intermediate_memory = psutil.Process().memory_info().rss
                logger.debug(f"Memory after object creation: {intermediate_memory}")
                
                del objs
                gc.collect(generation=2)
                await asyncio.sleep(0.2)
                
                memory_after = psutil.Process().memory_info().rss
                logger.debug(f"Final memory: {memory_after}")
                
                assert memory_after < (memory_before + intermediate_memory) / 2
        except asyncio.TimeoutError:
            logger.error("Memory snapshot test timed out")
            raise

@pytest.mark.asyncio(timeout=10)
class TestResourceManagement:
    async def test_concurrent_session_limits(self, db_pool):
        logger.debug("Starting concurrent session test")
        try:
            async with asyncio.timeout(5):
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
        except asyncio.TimeoutError:
            logger.error("Concurrent session test timed out")
            raise

@pytest.mark.asyncio(timeout=10)
class TestErrorRecovery:
    async def test_connection_pool_recovery(self, db_pool):
        logger.debug("Starting pool recovery test")
        try:
            async with asyncio.timeout(5):
                max_test_connections = 3
                
                async def use_connection():
                    async with db_pool.acquire() as conn:
                        await conn.execute("SELECT 1")
                        await asyncio.sleep(0.1)
                
                initial_size = await get_active_db_connections(db_pool)
                tasks = [use_connection() for _ in range(max_test_connections)]
                await asyncio.gather(*tasks)
                await asyncio.sleep(0.2)
                
                final_size = await get_active_db_connections(db_pool)
                assert final_size <= max_test_connections
        except asyncio.TimeoutError:
            logger.error("Pool recovery test timed out")
            raise

if __name__ == "__main__":
    pytest.main(["-v", "--log-cli-level=DEBUG", "--capture=no"])
