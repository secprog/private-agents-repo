# Agent Platform - Multi-Agent AI System

[![Deploy Application](https://github.com/secprog/private-agents-repo/actions/workflows/deploy.yml/badge.svg)](https://github.com/secprog/private-agents-repo/actions/workflows/deploy.yml)

A comprehensive multi-agent AI platform built with Google ADK SDK and A2A protocol for agent-to-agent communication. The platform features a master orchestrator that intelligently routes tasks to specialized agents, with full support for chat history, memory, and file attachments.

## 🌟 Features

### Core Capabilities
- **Modular Architecture**: Clean separation of concerns with specialized agents
- **Multi-Agent System**: Orchestrator agent with specialized agents (CyberSecurity, Vision, RAG)
- **A2A Protocol**: HTTP-based agent-to-agent communication using Google ADK SDK
- **Intelligent Routing**: Automatic task analysis and routing to appropriate agents
- **Memory & History**: Complete chat history with persistent storage using PostgreSQL
- **File Attachments**: Support for uploading and processing file attachments
- **Modern UI**: Beautiful, responsive JavaScript frontend with dark/light themes
- **LiteLLM Integration**: Unified LLM interface supporting OpenAI, Azure, Google, and more

### 🏗️ Modular Structure
- **Google ADK SDK**: Built on Google Agent Development Kit for robust agent development
- **LiteLLM**: Unified interface for all LLM providers (OpenAI, Azure, Google, etc.)
- **Clean Separation**: Business logic separated from API handlers
- **Database Persistence**: PostgreSQL for sessions, Neo4j for RAG knowledge graphs
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

#### 👁️ Vision Agent
- Image analysis and understanding
- Document processing
- Visual content extraction
- OCR capabilities
- Multi-modal processing

#### 📚 RAG Agent
- Document retrieval and search
- Knowledge extraction
- Vector and graph-based search
- Entity detection and relationships
- Hybrid search capabilities

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
pip install -r agents/orchestrator/requirements.txt
pip install -r agents/cybersecurity/requirements.txt
pip install -r agents/vision/requirements.txt
pip install -r agents/rag/requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and configure your settings:
```bash
# LLM Configuration (LiteLLM supports OpenAI, Azure, Google, etc.)
OPENAI_API_KEY=your-openai-api-key
GOOGLE_API_KEY=your-google-api-key  # Optional, for Gemini models
LLM_MODEL=openai/gpt-5.2-reasoning  # Or any LiteLLM-supported model

# Database Configuration
DATABASE_URL=postgresql://admin:admin123@postgres:5432/agent_platform
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# OpenMemory Configuration
OM_API_KEY=your-openmemory-api-key
OM_BASE_URL=http://openmemory:8080
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

# Terminal 3 - Vision Agent
python -m agents.vision.vision_agent

# Terminal 4 - RAG Agent
python -m agents.rag.rag_agent

# Terminal 5 - Frontend
cd frontend
npm install
npm start
```

### 5. Access the Platform
- **Frontend**: http://localhost:3000
- **Orchestrator API**: http://localhost:8000 (A2A communication)
- **Internal Agents**: Not exposed externally (secure internal networking)

## 🏗️ Architecture

### 🔒 Secure Multi-Agent Architecture

The platform implements a **secure, layered architecture** where:

- **Frontend** communicates with **Orchestrator Agent** via A2A protocol
- **Orchestrator Agent** routes tasks to **Internal Agents** via Docker internal networking
- **Internal Agents** are not exposed externally - only accessible through the orchestrator
- **Docker internal networking** ensures secure agent-to-agent communication
- **Only Frontend and Orchestrator** are exposed to external traffic

### 🛡️ Security Benefits

- **Reduced Attack Surface**: Only 2 endpoints exposed instead of 5+
- **Internal Agent Protection**: Specialized agents are completely isolated
- **A2A Protocol**: Standardized JSON-RPC 2.0 based communication protocol
- **Network Isolation**: Internal agents communicate via Docker internal network
- **Centralized Control**: All external access goes through the orchestrator

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (JavaScript)                │
│                   Beautiful Modern UI                    │
└────────────────────────┬────────────────────────────────┘
                         │ A2A Protocol (HTTP)
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Orchestrator Agent (Python)                 │
│                    Route & Coordinate                    │
│                  (Only Exposed Agent)                    │
└──────────┬────────────────┬──────────────┬──────────────┘
           │                │              │
      A2A Protocol      A2A Protocol  A2A Protocol
    (Internal Only)   (Internal Only) (Internal Only)
           │                │              │
           ▼                ▼              ▼
    ┌──────────┐     ┌──────────┐   ┌──────────┐
    │  Cyber   │     │  Vision  │   │   RAG    │
    │ Security │     │  Agent   │   │  Agent   │
    │  Agent   │     │          │   │          │
    │(Internal)│     │(Internal)│   │(Internal)│
    └──────────┘     └──────────┘   └────┬─────┘
           │                │              │
           └────────────────┴──────────────┘
                         │
                    ┌────┴────┐
                    │         │
               PostgreSQL    Neo4j
              (Sessions)   (Knowledge Graph)
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
├── agents/
│   ├── orchestrator/        # Main orchestrator agent
│   ├── cybersecurity/       # Security analysis agent
│   ├── vision/             # Vision and image processing agent
│   └── rag/                # RAG and document retrieval agent
│       ├── rag_agent.py    # Main agent entry point
│       ├── rag_analysis.py # RAG tools and search implementation
│       └── models.py       # Pydantic data models
├── frontend/               # JavaScript frontend
├── openmemory/            # OpenMemory cognitive engine
├── docker-compose.yml     # Container orchestration
└── .env                   # Environment configuration
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
python orchestrator.py
```

#### CyberSecurity Agent
```bash
cd agents/cybersecurity
pip install -r requirements.txt
python cybersecurity_agent.py
```

#### Vision Agent
```bash
cd agents/vision
pip install -r requirements.txt
python vision_agent.py
```

#### RAG Agent
```bash
cd agents/rag
pip install -r requirements.txt
python rag_agent.py
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

### LLM Configuration

The platform uses **LiteLLM** for unified LLM access, supporting 100+ providers:

#### Supported Providers
- **OpenAI**: GPT-5.2, GPT-5-mini, GPT-4, etc.
- **Google**: Gemini models (gemini-2.0-flash, gemini-1.5-pro, etc.)
- **Azure OpenAI**: Enterprise deployments
- **Anthropic**: Claude models
- **And many more**: See [LiteLLM documentation](https://docs.litellm.ai/docs/providers)

#### Configuration
Set the `LLM_MODEL` environment variable to any LiteLLM-supported model:

```bash
# OpenAI models
LLM_MODEL=openai/gpt-5.2-reasoning
LLM_MODEL=openai/gpt-5-mini

# Google Gemini models
LLM_MODEL=gemini/gemini-2.0-flash

# Azure OpenAI
LLM_MODEL=azure/gpt-4
```

#### Usage in Code
```python
from google.adk.models import LiteLlm
import os

# All agents use LiteLLM for model calls
llm = LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5-mini"))

# Embeddings also use LiteLLM
import litellm
response = litellm.embedding(
    model="text-embedding-3-small",
    input="Your text here"
)
```

### File Handling

The platform supports various file types through the artifact service:

- **Images**: PNG, JPEG, GIF, WebP
- **PDFs**: Document processing and text extraction
- **Documents**: Word docs, text files
- **Vision Processing**: Multi-modal analysis via Vision Agent
- **File Storage**: Configurable artifact service (file or in-memory)

### Database Configuration

- **PostgreSQL**: Session management and persistence (with pgvector extension)
- **Neo4j**: Knowledge graph for RAG agent (vector and graph search)
- **OpenMemory**: Cognitive memory engine for long-term agent memory

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
docker-compose logs -f vision-agent
docker-compose logs -f rag-agent
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
- Orchestrator: http://localhost:8000/
- CyberSecurity: http://localhost:8001/ (internal only)
- Vision: http://localhost:8002/ (internal only)
- RAG: http://localhost:8003/ (internal only)
- Frontend: http://localhost:3000/

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## 🆘 Troubleshooting

### Common Issues

#### Agent Not Responding
- Check agent logs: `docker-compose logs agent-name`
- Verify A2A protocol configuration
- Check network connectivity between containers
- Ensure DATABASE_URL is correctly configured

#### LLM Connection Issues
- Verify your API key is set correctly (OPENAI_API_KEY or GOOGLE_API_KEY)
- Check if you have sufficient API credits
- Ensure the LLM_MODEL format matches LiteLLM syntax (e.g., `openai/gpt-5.2`)
- Check LiteLLM documentation for provider-specific requirements

#### Database Connection Issues
- Ensure PostgreSQL is running: `docker-compose ps postgres`
- Check Neo4j connection for RAG agent
- Verify DATABASE_URL, NEO4J_URI in .env file

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
