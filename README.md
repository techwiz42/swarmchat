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

Fork this repo and go nuts.

## License

None atall

## Acknowledgments

- OpenAI for the Swarm framework
- The FastAPI team
- React and shadcn/ui developers
