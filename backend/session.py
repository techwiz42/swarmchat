import asyncio
import logging
import random
from typing import List, Optional
from swarm import Swarm, Agent
import gc
from agents import (
    moderator,
    transfer_to_hemmingway,
    transfer_to_pynchon,
    transfer_to_dickinson,
    transfer_to_dale_carnegie,
    transfer_to_shrink,
    transfer_to_flapper,
    transfer_to_bullwinkle,
    transfer_to_yogi_berra,
    transfer_to_mencken,
    transfer_to_yogi_bhajan
)

logger = logging.getLogger(__name__)

class UserSession:
    """Class to manage user sessions."""

    def __init__(self, username: str):
        """
        self.username: str = username
        self.messages: List[dict] = []
        self.client: Swarm = Swarm()
        self.agent: Agent = moderator
        self.lock: asyncio.Lock = asyncio.Lock()
        self.first_message_sent: bool = False
        """
        self.username = username
        self._messages = []
        self.cleanup_handlers = []
        logger.info("New session created for user: %s", self.username)

    def __del__(self):
        self._messages.clear()
        gc.collect()

    @property
    def messages(self):
        return self._messages.copy()

    async def send_first_message(self) -> Optional[str]:
        """Send initial moderator message."""
        try:
            if not self.first_message_sent:
                initial_message = "Hello, I'm the moderator. I'm here to help guide our conversation. What's on your mind today?"
                self.messages.append({"role": "assistant", "content": initial_message})
                self.first_message_sent = True
                return initial_message
            return None
        except Exception as e:
            logger.error("Error sending first message: %s", str(e))
            return None

    def select_random_agent(self) -> Agent:
        """Select and instantiate a random agent."""
        agents = [
            transfer_to_hemmingway,
            transfer_to_pynchon,
            transfer_to_dickinson,
            transfer_to_dale_carnegie,
            transfer_to_shrink,
            transfer_to_flapper,
            transfer_to_bullwinkle,
            transfer_to_yogi_berra,
            transfer_to_mencken,
            transfer_to_yogi_bhajan
        ]
        selected_func = random.choice(agents)
        new_agent = selected_func()
        logger.info("Selected random agent: %s", new_agent.name)
        return new_agent
