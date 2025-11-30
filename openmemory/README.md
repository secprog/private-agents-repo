# CaviraOSS OpenMemory Self-Hosted Setup

This directory contains the setup for self-hosted CaviraOSS OpenMemory integration.

**See:** https://github.com/CaviraOSS/OpenMemory

## Quick Setup

### Automated Setup (Recommended)

Run the setup script to automatically clone and configure CaviraOSS OpenMemory:

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

1. **Clone the CaviraOSS OpenMemory repository:**
   ```bash
   git clone https://github.com/CaviraOSS/OpenMemory.git
   ```

2. **Copy the backend files:**
   ```bash
   # Copy the backend directory contents directly to openmemory/
   cp -r OpenMemory/backend/* ./openmemory/
   ```

   Or alternatively, update the `build.context` in `docker-compose.yml` to point directly to the cloned repository:
   ```yaml
   build:
     context: ../OpenMemory/backend  # Adjust path as needed
     dockerfile: Dockerfile
   ```

3. **Set environment variables in your `.env` file:**

   Check the [CaviraOSS OpenMemory documentation](https://github.com/CaviraOSS/OpenMemory) for the exact environment variables needed. Common ones include:
   
   ```env
   # Core Configuration
   PORT=8080
   NODE_ENV=production
   
   # API Key (if required)
   API_KEY=your_api_key_here
   
   # Database Configuration
   DATABASE_URL=your_database_url
   
   # OpenAI API Key (if using OpenAI)
   OPENAI_API_KEY=your_openai_api_key
   ```

4. **Build and start:**
   ```bash
   docker-compose up -d openmemory
   ```

## Access

- OpenMemory API: http://localhost:8080
- API Documentation: Check CaviraOSS OpenMemory docs for available endpoints

## Multi-User Support

CaviraOSS OpenMemory supports multiple users. Check the [official documentation](https://github.com/CaviraOSS/OpenMemory) for details on how to handle multi-user scenarios.

## Notes

- CaviraOSS OpenMemory runs on port 8080 by default
- Data is persisted in the `openmemory_data` Docker volume
- Refer to the [CaviraOSS OpenMemory GitHub repository](https://github.com/CaviraOSS/OpenMemory) for complete documentation

## References

- [CaviraOSS OpenMemory GitHub Repository](https://github.com/CaviraOSS/OpenMemory)
- [OpenMemory Documentation](https://github.com/CaviraOSS/OpenMemory#readme)
