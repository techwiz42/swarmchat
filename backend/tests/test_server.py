import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
import os
import asyncio
from server import app, create_app
from models import TokenResponse, MessageResponse, HistoryResponse
from manager import SwarmChatManager
from session import UserSession

# Test client setup
@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_openai_key():
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key-123'}):
        yield

@pytest.fixture
def mock_session():
    session = UserSession("test_user")
    session.messages = [
        {"role": "assistant", "content": "Hello, I'm the moderator."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    return session

@pytest.fixture
def mock_chat_manager(mock_session):
    manager = SwarmChatManager()
    manager.sessions = {"test_user": mock_session}
    manager.tokens = {"test-token-123": "test_user"}
    return manager

# Basic route tests
def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 404

# Authentication tests
def test_login_success(client, mock_openai_key):
    credentials = "test_user:dummy"
    credentials_bytes = credentials.encode('ascii')
    auth_header = f"Basic {credentials_bytes.b64encode().decode()}"
    
    response = client.post(
        "/api/login",
        headers={"Authorization": auth_header}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["username"] == "test_user"

def test_login_no_credentials(client):
    response = client.post("/api/login")
    assert response.status_code == 401

def test_login_invalid_credentials(client):
    response = client.post(
        "/api/login",
        headers={"Authorization": "Basic invalid"}
    )
    assert response.status_code == 401

# Chat endpoint tests
def test_chat_message_success(client, mock_chat_manager):
    with patch('routes.chat_manager', mock_chat_manager):
        response = client.post(
            "/api/chat",
            headers={"Authorization": "Bearer test-token-123"},
            json={"content": "Hello"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data

def test_chat_invalid_token(client):
    response = client.post(
        "/api/chat",
        headers={"Authorization": "Bearer invalid-token"},
        json={"content": "Hello"}
    )
    assert response.status_code == 401

def test_chat_no_auth_header(client):
    response = client.post(
        "/api/chat",
        json={"content": "Hello"}
    )
    assert response.status_code == 401

def test_chat_empty_message(client, mock_chat_manager):
    with patch('routes.chat_manager', mock_chat_manager):
        response = client.post(
            "/api/chat",
            headers={"Authorization": "Bearer test-token-123"},
            json={"content": ""}
        )
        assert response.status_code == 400

# History endpoint tests
def test_history_success(client, mock_chat_manager):
    with patch('routes.chat_manager', mock_chat_manager):
        response = client.get(
            "/api/history",
            headers={"Authorization": "Bearer test-token-123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) == 3

def test_history_invalid_token(client):
    response = client.get(
        "/api/history",
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401

# Session management tests
def test_session_creation():
    session = UserSession("test_user")
    assert session.username == "test_user"
    assert session.messages == []
    assert session.first_message_sent == False

@pytest.mark.asyncio
async def test_session_first_message():
    session = UserSession("test_user")
    message = await session.send_first_message()
    assert message is not None
    assert session.first_message_sent == True
    assert len(session.messages) == 1

# Agent selection tests
def test_agent_selection():
    session = UserSession("test_user")
    agent = session.select_random_agent()
    assert agent is not None
    assert hasattr(agent, 'name')
    assert hasattr(agent, 'instructions')

# Chat manager tests
@pytest.mark.asyncio
async def test_chat_manager_creation():
    manager = SwarmChatManager()
    assert manager.sessions == {}
    assert manager.tokens == {}

@pytest.mark.asyncio
async def test_chat_manager_session_creation():
    manager = SwarmChatManager()
    token = await manager.create_session("test_user")
    assert token is not None
    assert "test_user" in manager.sessions
    assert token in manager.tokens

# Error handling tests
def test_invalid_message_format(client, mock_chat_manager):
    with patch('routes.chat_manager', mock_chat_manager):
        response = client.post(
            "/api/chat",
            headers={"Authorization": "Bearer test-token-123"},
            json={"invalid": "format"}
        )
        assert response.status_code == 422

def test_server_error_handling(client, mock_chat_manager):
    with patch('routes.chat_manager.process_message', side_effect=Exception("Test error")):
        response = client.post(
            "/api/chat",
            headers={"Authorization": "Bearer test-token-123"},
            json={"content": "Hello"}
        )
        assert response.status_code == 500

# Performance tests
@pytest.mark.asyncio
async def test_concurrent_sessions():
    manager = SwarmChatManager()
    tokens = await asyncio.gather(*[
        manager.create_session(f"user_{i}")
        for i in range(10)
    ])
    assert len(tokens) == 10
    assert len(manager.sessions) == 10

# Integration tests
def test_full_chat_flow(client, mock_openai_key):
    # Login
    credentials = "test_user:dummy"
    credentials_bytes = credentials.encode('ascii')
    auth_header = f"Basic {credentials_bytes.b64encode().decode()}"
    
    login_response = client.post(
        "/api/login",
        headers={"Authorization": auth_header}
    )
    assert login_response.status_code == 200
    token = login_response.json()["token"]
    
    # Send message
    chat_response = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Hello"}
    )
    assert chat_response.status_code == 200
    
    # Get history
    history_response = client.get(
        "/api/history",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert history_response.status_code == 200
    messages = history_response.json()["messages"]
    assert len(messages) >= 2  # Initial message + our message + response

# Security tests
def test_xss_prevention(client, mock_chat_manager):
    with patch('routes.chat_manager', mock_chat_manager):
        response = client.post(
            "/api/chat",
            headers={"Authorization": "Bearer test-token-123"},
            json={"content": "<script>alert('xss')</script>"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "<script>" not in data["response"]

def test_sql_injection_prevention(client, mock_chat_manager):
    with patch('routes.chat_manager', mock_chat_manager):
        response = client.post(
            "/api/chat",
            headers={"Authorization": "Bearer test-token-123"},
            json={"content": "'; DROP TABLE users; --"}
        )
        assert response.status_code == 200
