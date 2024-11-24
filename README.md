# SwarmChat

SwarmChat is an interactive web application that creates and orchestrates AI agents using OpenAI's Swarm framework. The application enables dynamic conversations with multiple AI personalities, each with their own unique characteristics and communication styles.

## Features

- Multiple AI personalities including:
  - Ernest Hemingway (direct, terse prose)
  - Thomas Pynchon (complex, postmodern style)
  - Emily Dickinson (poetic and contemplative)
  - Dale Carnegie (motivational and positive)
  - H. L. Mencken (cynical journalist)
  - A Freudian Psychoanalyst
  - A 1920s Flapper
  - Bullwinkle J. Moose
  - Yogi Berra
  - Yogi Bhajan

- Real-time conversation with dynamically switching agents
- Speech-to-text and text-to-speech capabilities
- Session management and chat history
- Secure API endpoints with token-based authentication

## Technical Stack

### Backend
- FastAPI (Python)
- OpenAI Swarm Framework for agent orchestration
- Async/await for concurrent operations
- Robust logging system
- Token-based authentication

### Frontend
- React
- Tailwind CSS for styling
- shadcn/ui components
- WebSpeech API integration for voice features

## Architecture

The application is structured in a modular fashion:

- `server.py`: Main FastAPI application entry point
- `agents.py`: Agent definitions and management
- `models.py`: Pydantic models for data validation
- `routes.py`: API endpoint definitions
- `manager.py`: Session and chat management
- `session.py`: Individual session handling

The frontend is organized into reusable components:
- Chat interface
- Agent dialog system
- Voice interaction controls
- Session management

## Testing

The project includes a comprehensive test suite that covers unit tests, integration tests, and security tests.

### Test Structure
```
/tests
├── __init__.py
├── conftest.py          # Test configuration and fixtures
├── test_manager.py      # Tests for session management
├── test_session.py      # Tests for individual sessions
├── test_routes.py       # Tests for API endpoints
└── requirements-test.txt
```

### Test Categories

#### Unit Tests
- Session management functionality
- Agent selection and behavior
- Token handling and validation
- Message processing
- User session state management

#### Integration Tests
- Complete chat flow (login → message → response)
- Session persistence
- Agent switching behavior
- Concurrent session handling

#### Security Tests
- Authentication and authorization
- Token validation
- XSS prevention
- SQL injection prevention

#### Performance Tests
- Concurrent session creation
- Message handling under load
- Agent switching performance

### Running Tests

Install test dependencies:
```bash
pip install -r tests/requirements-test.txt
```

Run the full test suite:
```bash
python -m pytest tests/ -v --cov=.
```

Run specific test categories:
```bash
# Unit tests
pytest tests/test_session.py -v

# Integration tests
pytest tests/test_routes.py -v

# Coverage report
pytest tests/ -v --cov=. --cov-report=term-missing
```

## Setup

1. Clone the repository
2. Install backend dependencies:
```bash
pip install -r requirements.txt
```
3. Install frontend dependencies:
```bash
cd frontend
npm install
```
4. Set up environment variables:
```bash
export OPENAI_API_KEY=your_api_key
```
5. Run the backend:
```bash
python server.py
```
6. Run the frontend:
```bash
npm start
```

## Deployment

The application can be deployed using:
- Nginx as reverse proxy
- SSL/TLS encryption
- PM2 or similar for process management

## API Endpoints

- `/api/login`: User authentication
- `/api/chat`: Message handling
- `/api/history`: Chat history retrieval

## Contributing

Contributions are welcome! Please ensure all tests pass before submitting pull requests. New features should include appropriate test coverage.

## License

[Add your chosen license here]

## Acknowledgments

- OpenAI for the Swarm framework
- The FastAPI team
- React and shadcn/ui developers
