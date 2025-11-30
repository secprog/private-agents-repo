# OpenMemory Self-Hosted Setup

This directory contains the setup for self-hosted OpenMemory integration.

## Quick Setup

### Automated Setup (Recommended)

Run the setup script to automatically clone and configure OpenMemory:

**Windows (Command Prompt):**
```cmd
cd openmemory
setup-openmemory.cmd
```

**Windows (PowerShell):**
```powershell
cd openmemory
.\setup-openmemory.ps1
```

**Linux/Mac:**
```bash
cd openmemory
chmod +x setup-openmemory.sh
./setup-openmemory.sh
```

### Manual Setup

If you prefer to set up manually:

1. **Clone the OpenMemory repository:**
   ```bash
   git clone https://github.com/mem0ai/mem0.git
   ```

2. **Copy the API files:**
   ```bash
   # Copy the api directory contents to this location
   cp -r mem0/openmemory/api/* ./openmemory/api/
   ```

   Or alternatively, update the `build.context` in `docker-compose.yml` to point directly to the cloned repository:
   ```yaml
   build:
     context: ../mem0/openmemory/api  # Adjust path as needed
     dockerfile: Dockerfile
   ```

3. **Set environment variables in your `.env` file:**

   **Required Variables:**
   ```env
   # Core Configuration (REQUIRED for production)
   OM_API_KEY=your_api_key_here  # REQUIRED - API key for OpenMemory authentication
   OPENAI_API_KEY=your_openai_api_key  # REQUIRED if using OpenAI embeddings
   OPENMEMORY_PORT=8765
   ```

   **Optional Configuration Variables:**
   ```env
   # Performance Tier (default: hybrid)
   OM_TIER=hybrid  # Options: hybrid, smart, deep, fast
   
   # Database Configuration (defaults to SQLite)
   OM_DB_PATH=/data/openmemory.db
   OM_METADATA_BACKEND=sqlite  # Options: sqlite, postgres
   OM_VECTOR_BACKEND=sqlite  # Options: sqlite, pgvector, weaviate
   
   # Embedding Provider (default: openai)
   OM_EMBEDDINGS=openai  # Options: synthetic, openai, gemini, ollama, aws
   OM_OPENAI_MODEL=text-embedding-3-small
   OM_OPENAI_BASE_URL=  # Optional: for Azure OpenAI or custom endpoint
   
   # PostgreSQL Configuration (if using PostgreSQL)
   OM_POSTGRES_HOST=postgres
   OM_POSTGRES_PORT=5432
   OM_POSTGRES_DB=openmemory
   OM_POSTGRES_USER=your_user
   OM_POSTGRES_PASSWORD=your_password
   
   # Background Process Configuration
   OM_AUTO_REFLECT=true
   OM_REFLECT_INTERVAL=3600
   OM_REFLECT_MIN_MEMORIES=10
   OM_USER_SUMMARY_INTERVAL=86400
   
   # Memory Decay Configuration
   OM_DECAY_LAMBDA=0.1
   OM_DECAY_INTERVAL_MINUTES=60
   OM_DECAY_RATIO=0.1
   OM_DECAY_REINFORCE_ON_QUERY=true
   ```

   See `docker-compose.yml` for the complete list of available environment variables.

4. **Build and start:**
   ```bash
   docker-compose up -d openmemory
   ```

## Access

- OpenMemory API: http://localhost:8765
- API Documentation: http://localhost:8765/docs

## Multi-User Support

OpenMemory supports multiple users by accepting a `user_id` parameter in API requests. **Do not rely on the `USER` environment variable for multi-user scenarios.**

### How It Works

1. **Single User (Testing):** The `USER` environment variable can be set as a default for simple testing scenarios.

2. **Multiple Users (Production):** Pass the `user_id` in each API request:
   ```python
   # Example API call with user context
   import requests
   
   response = requests.post(
       "http://localhost:8765/memories",
       json={
           "user_id": "user_123",  # Pass actual user ID from your auth system
           "memory": "User prefers dark mode interface"
       }
   )
   ```

3. **User Isolation:** Each `user_id` has completely isolated memory storage. Memories are automatically scoped to the user ID provided in the request.

### Integration in Your Application

When integrating OpenMemory with your agent platform:
- Extract the user ID from your authentication/session system
- Include the `user_id` parameter in all OpenMemory API calls
- Do not use a global `USER` environment variable for production multi-user deployments

## Notes

- The OpenMemory API requires an OpenAI API key to function
- The `USER` environment variable is optional and only used as a default for single-user testing
- For multi-user scenarios, always pass `user_id` in API requests
- Data is persisted in the `openmemory_data` Docker volume
- Each user's memories are isolated based on the `user_id` parameter

## References

- [OpenMemory Quickstart Guide](https://docs.mem0.ai/openmemory/quickstart)
- [OpenMemory GitHub Repository](https://github.com/mem0ai/mem0/tree/main/openmemory)

