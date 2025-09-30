.PHONY: help build up down logs clean install ssl dev prod test

# Default target
help:
	@echo "Agent Platform - Make Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install    - Install all dependencies"
	@echo "  make ssl        - Generate SSL certificates"
	@echo "  make dev        - Start development environment"
	@echo "  make build      - Build all Docker images"
	@echo "  make up         - Start all services"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - View logs from all services"
	@echo "  make clean      - Clean up containers and volumes"
	@echo ""
	@echo "Testing:"
	@echo "  make test       - Run all tests"
	@echo ""
	@echo "Production:"
	@echo "  make prod       - Deploy production environment"

# Install dependencies
install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing cybersecurity agent dependencies..."
	cd agents/cybersecurity && pip install -r requirements.txt
	@echo "Installing devops agent dependencies..."
	cd agents/devops && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Dependencies installed!"

# Generate SSL certificates
ssl:
	@echo "Generating SSL certificates..."
	bash generate-ssl.sh

# Build Docker images
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d
	@echo "Agent Platform is running!"
	@echo "Frontend: http://localhost:3000"
	@echo "Orchestrator API: https://localhost:8000"
	@echo "CyberSecurity Agent: https://localhost:8001"
	@echo "DevOps Agent: https://localhost:8002"

# Stop all services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# View specific service logs
logs-orchestrator:
	docker-compose logs -f orchestrator

logs-cyber:
	docker-compose logs -f cybersecurity-agent

logs-devops:
	docker-compose logs -f devops-agent

logs-frontend:
	docker-compose logs -f frontend

# Clean up
clean:
	docker-compose down -v
	docker system prune -f
	@echo "Cleanup complete!"

# Development mode
dev: ssl build up logs

# Production deployment
prod:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Run tests
test:
	@echo "Running backend tests..."
	cd backend && pytest tests/ || true
	@echo "Running agent tests..."
	cd agents/cybersecurity && pytest tests/ || true
	cd agents/devops && pytest tests/ || true
	@echo "Tests complete!"

# Health check
health:
	@echo "Checking service health..."
	@curl -k https://localhost:8000/ || echo "Orchestrator not responding"
	@curl -k https://localhost:8001/ || echo "CyberSecurity agent not responding"
	@curl -k https://localhost:8002/ || echo "DevOps agent not responding"
	@curl http://localhost:3000/health || echo "Frontend not responding"

# Restart services
restart:
	docker-compose restart

# Update and restart
update: down build up
	@echo "Services updated and restarted!"

# Show running containers
ps:
	docker-compose ps

# Execute command in a service
exec-orchestrator:
	docker-compose exec orchestrator /bin/bash

exec-cyber:
	docker-compose exec cybersecurity-agent /bin/bash

exec-devops:
	docker-compose exec devops-agent /bin/bash

# Database management (PostgreSQL)
db-backup:
	docker-compose exec postgres pg_dump -U admin agent_platform > backup_$(shell date +%Y%m%d_%H%M%S).sql

db-restore:
	@read -p "Enter backup file: " file; \
	docker-compose exec -T postgres psql -U admin -d agent_platform < $$file
