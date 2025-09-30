# Docker Compose Environment Configuration

This guide explains how to use environment files with Docker Compose instead of hardcoded values.

## 🚀 **Environment File Setup**

### **1. Create Environment File**

Copy the example environment file and customize it:

```bash
cp docker.env .env
```

### **2. Edit Your Environment Variables**

Open `.env` file and customize the values:

```bash
# Database Configuration
POSTGRES_DB=agent_platform
POSTGRES_USER=admin
POSTGRES_PASSWORD=your-secure-password-here
DATABASE_URL=postgresql://admin:your-secure-password-here@postgres:5432/agent_platform

# JWT Configuration
JWT_SECRET_KEY=your-very-secure-secret-key-change-this-in-production

# LLM Provider Configuration
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-azure-openai-key
AZURE_OPENAI_DEPLOYMENT=gpt-4
OPENAI_API_KEY=your-openai-api-key

# Agent Endpoints
ORCHESTRATOR_ENDPOINT=http://orchestrator:8000
CYBERSECURITY_AGENT_ENDPOINT=http://cybersecurity-agent:8001
DEVOPS_AGENT_ENDPOINT=http://devops-agent:8002

# Frontend Configuration
API_ENDPOINT=http://orchestrator:8000

# Port Configuration
POSTGRES_PORT=5432
ORCHESTRATOR_PORT=8000
CYBERSECURITY_PORT=8001
DEVOPS_PORT=8002
FRONTEND_PORT=3000

# Container Names
POSTGRES_CONTAINER=agent-platform-postgres
ORCHESTRATOR_CONTAINER=agent-platform-orchestrator
CYBERSECURITY_CONTAINER=agent-platform-cybersecurity
DEVOPS_CONTAINER=agent-platform-devops
FRONTEND_CONTAINER=agent-platform-frontend

# Network Configuration
NETWORK_NAME=agent-network
```

## 🔧 **How to Use**

### **Method 1: Default .env file (Recommended)**

Docker Compose automatically reads `.env` file:

```bash
docker-compose up -d
```

### **Method 2: Custom Environment File**

Specify a custom environment file:

```bash
docker-compose --env-file docker.env up -d
```

### **Method 3: Multiple Environment Files**

You can use multiple environment files:

```bash
docker-compose --env-file .env --env-file .env.local up -d
```

### **Method 4: Override with Command Line**

Override specific variables:

```bash
POSTGRES_PASSWORD=newpassword docker-compose up -d
```

## 🎯 **Benefits**

1. **Security**: Keep sensitive data out of version control
2. **Flexibility**: Easy to change configuration without editing docker-compose.yml
3. **Environment-specific**: Different configs for dev/staging/production
4. **Team-friendly**: Each developer can have their own .env file

## 📁 **File Structure**

```
project/
├── docker-compose.yml          # Uses environment variables
├── docker.env                  # Example environment file
├── .env                        # Your actual environment file (gitignored)
└── .env.example               # Template for team members
```

## 🔒 **Security Best Practices**

1. **Never commit .env files** to version control
2. **Use strong passwords** and secret keys
3. **Rotate secrets regularly** in production
4. **Use different configs** for different environments
5. **Restrict file permissions**: `chmod 600 .env`

## 🚀 **Production Deployment**

For production, consider:

1. **Environment-specific files**: `.env.production`
2. **Secret management**: Use Docker Secrets or external secret managers
3. **Configuration validation**: Ensure all required variables are set
4. **Monitoring**: Log configuration loading for debugging

## 📝 **Example Commands**

```bash
# Development
docker-compose --env-file .env.dev up -d

# Staging
docker-compose --env-file .env.staging up -d

# Production
docker-compose --env-file .env.production up -d

# Override specific variables
POSTGRES_PASSWORD=prodpassword docker-compose --env-file .env.production up -d
```

## 🐛 **Troubleshooting**

### **Environment variables not loading?**

1. Check file location (should be in same directory as docker-compose.yml)
2. Verify file format (no spaces around `=`)
3. Check file permissions
4. Use `docker-compose config` to see resolved values

### **Default values not working?**

Make sure to use the format: `${VARIABLE:-default_value}`

### **Special characters in values?**

Quote values with special characters:
```bash
JWT_SECRET_KEY="your-secret-with-special-chars!"
```
