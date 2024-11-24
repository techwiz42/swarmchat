import pytest
from session import UserSession
from swarm import Agent
import asyncio

class TestUserSession:
    @pytest.fixture
    def session(self):
        return UserSession("test_user")

    def test_init(self, session):
        assert session.username == "test_user"
        assert session.messages == []
        assert session.client is not None
        assert isinstance(session.agent, Agent)
        assert session.lock is not None
        assert session.first_message_sent is False

    @pytest.mark.asyncio
    async def test_send_first_message(self, session):
        message = await session.send_first_message()
        assert message is not None
        assert session.first_message_sent is True
        assert len(session.messages) == 1
        assert session.messages[0]["role"] == "assistant"
        
        # Test sending first message again
        second_message = await session.send_first_message()
        assert second_message is None

    def test_select_random_agent(self, session):
        agent = session.select_random_agent()
        assert agent is not None
        assert isinstance(agent, Agent)
        assert hasattr(agent, 'name')
        assert hasattr(agent, 'instructions')

    def test_multiple_agent_selections(self, session):
        # Test that we can get different agents
        agents = set()
        for _ in range(50):  # Try multiple times to get different agents
            agent = session.select_random_agent()
            agents.add(agent.name)
        assert len(agents) > 1  # Should get different agents

    @pytest.mark.asyncio
    async def test_concurrent_access(self, session):
        async def add_message():
            async with session.lock:
                session.messages.append({"role": "user", "content": "test"})
                await asyncio.sleep(0.1)  # Simulate some work
                return len(session.messages)

        # Run concurrent access
        results = await asyncio.gather(
            *[add_message() for _ in range(5)]
        )
        
        # Check that all operations were completed sequentially
        assert results == [1, 2, 3, 4, 5]
        assert len(session.messages) == 5

    def test_agent_transfer(self, session):
        initial_agent = session.agent
        new_agent = session.select_random_agent()
        session.agent = new_agent
        assert session.agent != initial_agent

    def test_message_format(self, session):
        session.messages.append({"role": "user", "content": "test"})
        assert isinstance(session.messages, list)
        assert all(isinstance(msg, dict) for msg in session.messages)
        assert all("role" in msg and "content" in msg for msg in session.messages)
