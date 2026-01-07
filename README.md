# Agent Platform - Multi-Agent AI System

[![Deploy Application](https://github.com/secprog/private-agents-repo/actions/workflows/deploy.yml/badge.svg)](https://github.com/secprog/private-agents-repo/actions/workflows/deploy.yml)

A comprehensive multi-agent AI platform built with Google ADK SDK and A2A protocol for agent-to-agent communication. The platform features a master orchestrator that intelligently routes tasks to specialized agents, with full support for chat history, memory, and file attachments.

## 🌟 Features

### Core Capabilities
- **Modular Architecture**: Clean separation of concerns with shared modules
- **Multi-Agent System**: Orchestrator agent with specialized agents (CyberSecurity, DevOps, Data, ML)
- **A2A Protocol**: Secure HTTPS-based agent-to-agent communication using Google ADK SDK
- **Intelligent Routing**: Automatic task analysis and routing to appropriate agents
- **Real-time Communication**: WebSocket support for live updates and notifications
- **Memory & History**: Complete chat history with persistent storage
- **File Attachments**: Support for uploading and processing file attachments
- **Modern UI**: Beautiful, responsive JavaScript frontend with dark/light themes

### 🏗️ Modular Structure
- **Shared Modules**: Common data models, A2A client, LLM integration, database utilities
- **Custom LLM Integration**: Native OpenAI and Gemini support in `shared/models/`
- **Clean Separation**: Business logic separated from API handlers
- **Reusable Components**: Shared modules eliminate code duplication
- **Easy Testing**: Modules can be tested independently
- **Scalable Design**: Easy to add new agents and capabilities

### Specialized Agents

#### 🤖 Orchestrator Agent
- Task analysis and routing
- Agent health monitoring
- Load balancing
- Session management
- Central coordination

#### 🔒 CyberSecurity Agent
- Security vulnerability analysis
- Threat detection
- OWASP Top 10 scanning
- Security recommendations
- Pattern-based detection

#### 🚀 DevOps Agent
- Deployment configurations
- CI/CD pipeline generation
- Infrastructure as Code templates
- Docker/Kubernetes configurations
- Monitoring setup

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+
- OpenAI API key OR Google AI API key (for Gemini)

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/agent-platform.git
cd agent-platform
```

### 2. Setup Virtual Environment (Recommended)
The platform uses a single shared virtual environment for all components to simplify development and testing.

#### Automated Setup (Recommended)
```bash
# Windows
setup.bat

# Linux/macOS
./setup.sh
```

#### Manual Setup
```bash
# Create shared virtual environment
python -m venv venv

# Activate and install dependencies
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

# Install all requirements
pip install -r agents/shared/requirements.txt
pip install -r agents/orchestrator/requirements.txt
pip install -r agents/cybersecurity/requirements.txt
pip install -r agents/devops/requirements.txt
```

### 3. Configure LLM Provider

#### Google Gemini
```bash
# Set your Google AI API key
export GOOGLE_API_KEY="your-google-ai-api-key-here"

# Or create a .env file
echo "GOOGLE_API_KEY=your-google-ai-api-key-here" > .env
```

### 4. Start the Platform

#### Option A: Docker Compose (Recommended for Production)
```bash
docker-compose up -d
```

#### Option B: Virtual Environment (Recommended for Development)
```bash
# Activate shared virtual environment
activate.bat  # Windows
# source ./activate.sh  # Linux/macOS

# Terminal 1 - Orchestrator Agent
python -m agents.orchestrator.orchestrator

# Terminal 2 - CyberSecurity Agent
python -m agents.cybersecurity.cybersecurity_agent

# Terminal 3 - DevOps Agent
python -m agents.devops.devops_agent

# Terminal 4 - Frontend
cd frontend
npm install
npm start
```

### 7. Access the Platform
- **Frontend**: http://localhost:3000 (or https://localhost with nginx)
- **Orchestrator API**: https://localhost:8000 (internal A2A communication)
- **Internal Agents**: Not exposed externally (secure internal networking)

## 🏗️ Architecture

### 🔒 Secure Multi-Agent Architecture

The platform implements a **secure, layered architecture** where:

- **Frontend** communicates with **Orchestrator Agent** via A2A protocol
- **Orchestrator Agent** routes tasks to **Internal Agents** via secure internal networking
- **Internal Agents** are not exposed externally - only accessible through the orchestrator
- **Docker internal networking** ensures secure agent-to-agent communication
- **Only Frontend and Orchestrator** are exposed to external traffic

### 🛡️ Security Benefits

- **Reduced Attack Surface**: Only 2 endpoints exposed instead of 4+
- **Internal Agent Protection**: Specialized agents are completely isolated
- **A2A Protocol Security**: All communication uses secure HTTPS with A2A protocol
- **Network Isolation**: Internal agents communicate via Docker internal network
- **Centralized Control**: All external access goes through the orchestrator

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (JavaScript)                │
│                   Beautiful Modern UI                    │
└────────────────────────┬────────────────────────────────┘
                         │ A2A Protocol (HTTPS)
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Orchestrator Agent (Python)                 │
│                    Route & Coordinate                    │
│                  (Only Exposed Agent)                    │
└──────────┬──────────────┬──────────────┬────────────────┘
           │              │              │
      A2A Protocol   A2A Protocol   A2A Protocol
    (Internal Only) (Internal Only) (Internal Only)
           │              │              │
           ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  Cyber   │   │  DevOps  │   │   Data   │
    │ Security │   │  Agent   │   │  Agent   │
    │  Agent   │   │          │   │          │
    │(Internal)│   │(Internal)│   │(Internal)│
    └──────────┘   └──────────┘   └──────────┘
           │              │              │
           └──────────────┴──────────────┘
                         │
                    ┌────┴────┐
                    │         │
                 File Storage  Cache
```

## 🛠️ Development

### Virtual Environment Management

The platform uses a single shared virtual environment for all components to simplify development and testing.

#### Virtual Environment Structure
```
agent-platform/
├── venv/                 # Shared virtual environment for all agents
├── activate.bat          # Windows activation script
├── activate.sh           # Linux/macOS activation script
└── setup_simple_venv.py  # Setup script
```

#### Benefits of Shared Virtual Environment
- **Simplified Setup**: Single environment to manage
- **Faster Development**: No need to switch between environments
- **Easier Testing**: All dependencies available in one place
- **Reduced Complexity**: Less configuration and maintenance

### Project Structure
```
agent-platform/
├── shared/
│   └── models/              # Custom LLM integrations
│       ├── openai_llm.py    # Native OpenAI integration
│       ├── registry.py      # LLM registration
│       └── README.md        # LLM documentation
├── agents/
│   ├── orchestrator/        # Main orchestrator agent
│   ├── cybersecurity/       # Security analysis agent
│   └── devops/             # DevOps automation agent
├── frontend/               # JavaScript frontend
├── examples/               # Usage examples
├── test_*.py              # Integration tests
└── docker-compose.yml     # Container orchestration
```

#### Managing Virtual Environment
```bash
# Recreate virtual environment
python setup_simple_venv.py

# Activate environment
# Windows
activate.bat

# Linux/macOS
source activate.sh

# Deactivate current environment
deactivate
```

### Running Without Docker

#### Orchestrator Agent
```bash
cd agents/orchestrator
pip install -r requirements.txt
uvicorn orchestrator:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

#### CyberSecurity Agent
```bash
cd agents/cybersecurity
pip install -r requirements.txt
uvicorn cybersecurity_agent:app --host 0.0.0.0 --port 8001 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

#### DevOps Agent
```bash
cd agents/devops
pip install -r requirements.txt
uvicorn devops_agent:app --host 0.0.0.0 --port 8002 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

#### Frontend
```bash
cd frontend
npm install
npm start
```

## 📝 API Documentation

### Chat Endpoint
```http
POST /chat
Content-Type: application/json

{
    "session_id": "session_123",
    "user_id": "user_456",
    "content": "Analyze this code for security vulnerabilities",
    "attachments": []
}
```

### A2A Protocol Message Format
```json
{
    "id": "message_id",
    "sender_id": "agent_id",
    "recipient_id": "target_agent_id",
    "message_type": "task_assignment",
    "content": {},
    "metadata": {},
    "timestamp": "2023-01-01T00:00:00Z"
}
```

### A2A Protocol Implementation

The platform implements proper A2A protocol with dynamic agent discovery:

#### Agent Discovery Process
1. **Orchestrator** queries known agent endpoints for capabilities
2. **Agents** respond with their capability cards
3. **Orchestrator** builds dynamic registry of available agents
4. **Task routing** uses capability matching for optimal agent selection

#### Frontend to Orchestrator A2A Communication
```javascript
// Frontend sends A2A message to orchestrator
const a2aMessage = {
    id: "msg_123",
    sender_id: "user_456",
    recipient_id: "orchestrator",
    message_type: "chat_request",
    content: {
        session_id: "session_789",
        user_id: "user_456",
        content: "Analyze this code for security vulnerabilities",
        attachments: []
    },
    metadata: {
        timestamp: "2023-01-01T00:00:00Z",
        source: "frontend"
    }
};

// Send via HTTP POST to root endpoint
fetch('https://localhost:8000', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(a2aMessage)
});
```

## 🔧 Configuration

### LLM Providers
The platform supports multiple LLM providers with automatic detection:

#### Google Gemini Models
- **gemini-2.0-flash**: Latest Gemini model with advanced capabilities
- **gemini-1.5-pro**: High-performance model
- **gemini-1.5-flash**: Fast and efficient

### Model Selection
The platform automatically selects the best available model based on your API key:
- If `GOOGLE_API_KEY` is set → Uses Gemini models

### Google Gemini Setup

#### 1. Get Google AI API Key
1. Go to [Google AI Studio](https://aistudio.google.com)
2. Sign in with your Google account
3. Click "Get API Key"
4. Create a new API key
5. Copy the key

#### 2. Configure Gemini
```bash
# Set environment variable
export GOOGLE_API_KEY="your-google-api-key-here"

# Or add to .env file
echo "GOOGLE_API_KEY=your-google-api-key-here" >> .env
```

#### 3. Use Gemini in Your Code
```python
from google.adk.agents import Agent

# Simple usage - platform auto-detects Gemini
agent = Agent(model="gemini-2.0-flash")

# The platform automatically uses Gemini when GOOGLE_API_KEY is set
```

### File Handling

#### OpenAI File Support
- **Images**: PNG, JPEG, GIF, WebP (base64 encoded)
- **PDFs**: Via Files API upload or base64 for vision models
- **Documents**: Word docs via Files API or base64
- **File References**: Converted to text descriptions

#### Gemini File Support
- **Images**: PNG, JPEG, GIF, WebP (base64 encoded)
- **PDFs**: Direct support with file references
- **Documents**: Word docs, text files
- **File References**: Full URI support (GCS, HTTPS)


### SSL/TLS
- Development uses self-signed certificates
- Production should use proper certificates from a CA
- All agent communication uses HTTPS with A2A protocol

## 📦 Docker Deployment

### Building Images
```bash
docker-compose build
```

### Starting Services
```bash
docker-compose up -d
```

### Viewing Logs
```bash
docker-compose logs -f orchestrator
docker-compose logs -f cybersecurity-agent
docker-compose logs -f devops-agent
docker-compose logs -f frontend
```

### Stopping Services
```bash
docker-compose down
```

### Removing Volumes
```bash
docker-compose down -v
```

## 🔐 Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **SSL Certificates**: Use proper certificates in production
3. **Authentication**: Implement user authentication for production
4. **Rate Limiting**: Configure rate limiting in nginx
5. **CORS**: Adjust CORS settings based on your deployment
6. **Secrets Management**: Use environment variables or secret management tools

## 🧪 Testing

### Unit Tests
```bash
cd backend
pytest tests/
```

### Integration Tests
```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 📊 Monitoring

The platform includes basic health check endpoints:
- Orchestrator: https://localhost:8000/
- CyberSecurity: https://localhost:8001/
- DevOps: https://localhost:8002/
- Frontend: http://localhost:3000/health

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## 🆘 Troubleshooting

### Common Issues

#### WebSocket Connection Failed
- Check if all services are running
- Verify SSL certificates are generated
- Check firewall settings

#### Agent Not Responding
- Check agent logs: `docker-compose logs agent-name`
- Verify A2A protocol configuration
- Check network connectivity between containers

#### LLM Connection Issues
- Verify your API key is set correctly
- Check if you have sufficient API credits
- Ensure the model name is supported

## 📚 Additional Resources

- [Google ADK SDK Documentation](https://developers.google.com/adk)
- [A2A Protocol Specification](https://docs.a2a-protocol.org)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Docker Compose Documentation](https://docs.docker.com/compose)

## 👥 Support

For issues and questions:
- Create an issue on GitHub
- Contact the development team
- Check the documentation

---

Built with ❤️ using Google ADK SDK and modern web technologies
