"""Module for defining and managing different conversational agents and their behaviors."""

from typing import List
import random
# pylint: disable=E0401
from swarm import Agent # type: ignore

# Constants
AUTHORS: List[str] = [
    "Hemmingway",
    "Pynchon", 
    "Emily Dickenson"
]

MODEL = "gpt-4o-mini"

def get_author() -> str:
    """Get a random author from the AUTHORS list."""
    return random.choice(AUTHORS)

def transfer_back_to_moderator() -> Agent:
    """Return the moderator agent after each response."""
    return moderator

def transfer_to_hemmingway() -> Agent:
    """Return the Hemmingway agent."""
    return hemmingway_agent

def transfer_to_pynchon() -> Agent:
    """Return the Pynchon agent."""
    return pynchon_agent

def transfer_to_dickinson() -> Agent:
    """Return the Dickinson agent."""
    return dickinson_agent

def transfer_to_shrink() -> Agent:
    """Return the psychoanalyst agent."""
    return shrink_agent

# Agent Definitions
moderator = Agent(
    name="Moderator",
    model=MODEL,
    instructions=f"Transfer to agent whose name == {get_author()}. "
                "Call this function after that agent's response",
    functions = [] if hasattr(Agent, 'functions') else []
) 

hemmingway_agent = Agent(
    name="Hemmingway",
    model=MODEL,
    instructions="Answer as Hemmingway. Do not begin your answer with 'Ah'. "
                "Introduce yourself by agent name",
    functions = [] if hasattr(Agent, 'functions') else []
)

pynchon_agent = Agent(
    name="Pynchon",
    model=MODEL,
    instructions="Answer as Pynchon. Do not begin your answer with 'Ah'. "
                "Introduce yourself by agent name",
    functions = [] if hasattr(Agent, 'functions') else []
)

dickinson_agent = Agent(
    name="Emily Dickenson",
    model=MODEL,
    instructions="Answer as Emily Dickenson. Do not begin your answer with 'Ah'. "
                "Introduce yourself by agent name",
    functions = [] if hasattr(Agent, 'functions') else []
)

shrink_agent = Agent(
    name="A Freudian Psychoanalyst",
    model=MODEL,
    instructions="Answer as A Freudian Psychoanalyst. Do not begin your answer with 'Ah'. "
                "Introduce yourself by agent name",
    functions = [] if hasattr(Agent, 'functions') else []
)

moderator.functions = [
    transfer_to_hemmingway,
    transfer_to_pynchon,
    transfer_to_dickinson,
    transfer_to_shrink,
]

# Add transfer back function to all agents
for agent in [
    hemmingway_agent, 
    pynchon_agent, 
    dickinson_agent,
    shrink_agent
]:
    agent.functions.append(transfer_back_to_moderator)
