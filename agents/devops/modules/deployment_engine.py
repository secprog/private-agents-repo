"""
Deployment engine for DevOps agent
"""

import os
import logging
from typing import Dict, List, Optional, Any

from modules.models import DeploymentRequest, InfrastructureRequest

logger = logging.getLogger(__name__)


class DeploymentEngine:
    """Deployment automation engine"""
    
    def __init__(self):
        self.supported_environments = ["development", "staging", "production"]
        self.supported_types = ["docker", "kubernetes", "serverless"]
    
    async def process_deployment_request(self, request: DeploymentRequest) -> Dict[str, Any]:
        """Process deployment request"""
        try:
            # Validate request
            if request.environment not in self.supported_environments:
                return {
                    "status": "error",
                    "message": f"Unsupported environment: {request.environment}"
                }
            
            if request.deployment_type not in self.supported_types:
                return {
                    "status": "error",
                    "message": f"Unsupported deployment type: {request.deployment_type}"
                }
            
            # Generate deployment configuration
            config = await self.generate_deployment_config(request)
            
            # Generate deployment scripts
            scripts = await self.generate_deployment_scripts(request, config)
            
            return {
                "status": "completed",
                "deployment_config": config,
                "deployment_scripts": scripts,
                "environment": request.environment,
                "deployment_type": request.deployment_type
            }
            
        except Exception as e:
            logger.error(f"Deployment processing error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def generate_deployment_config(self, request: DeploymentRequest) -> Dict[str, Any]:
        """Generate deployment configuration"""
        config = {
            "project_name": request.project_name,
            "environment": request.environment,
            "deployment_type": request.deployment_type,
            "configuration": request.configuration or {}
        }
        
        if request.deployment_type == "docker":
            config["docker"] = {
                "image": f"{request.project_name}:latest",
                "ports": ["8080:8080"],
                "environment_vars": {
                    "NODE_ENV": request.environment,
                    "PORT": "8080"
                },
                "volumes": [],
                "networks": ["default"]
            }
        elif request.deployment_type == "kubernetes":
            config["kubernetes"] = {
                "namespace": f"{request.project_name}-{request.environment}",
                "replicas": 3 if request.environment == "production" else 1,
                "resources": {
                    "requests": {"cpu": "100m", "memory": "128Mi"},
                    "limits": {"cpu": "500m", "memory": "512Mi"}
                },
                "service": {
                    "type": "LoadBalancer" if request.environment == "production" else "ClusterIP",
                    "port": 80,
                    "target_port": 8080
                }
            }
        elif request.deployment_type == "serverless":
            config["serverless"] = {
                "runtime": "nodejs18.x",
                "handler": "index.handler",
                "timeout": 30,
                "memory": 512,
                "environment": {
                    "NODE_ENV": request.environment
                }
            }
        
        return config
    
    async def generate_deployment_scripts(self, request: DeploymentRequest, config: Dict) -> Dict[str, str]:
        """Generate deployment scripts"""
        scripts = {}
        
        if request.deployment_type == "docker":
            scripts["dockerfile"] = self.generate_dockerfile(request)
            scripts["docker_compose"] = self.generate_docker_compose(request, config)
            scripts["deploy.sh"] = self.generate_docker_deploy_script(request)
        
        elif request.deployment_type == "kubernetes":
            scripts["deployment.yaml"] = self.generate_k8s_deployment(request, config)
            scripts["service.yaml"] = self.generate_k8s_service(request, config)
            scripts["deploy.sh"] = self.generate_k8s_deploy_script(request)
        
        elif request.deployment_type == "serverless":
            scripts["serverless.yml"] = self.generate_serverless_config(request, config)
            scripts["deploy.sh"] = self.generate_serverless_deploy_script(request)
        
        return scripts
    
    def generate_dockerfile(self, request: DeploymentRequest) -> str:
        """Generate Dockerfile"""
        return f"""FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 8080

USER node

CMD ["npm", "start"]
"""
    
    def generate_docker_compose(self, request: DeploymentRequest, config: Dict) -> str:
        """Generate docker-compose.yml"""
        docker_config = config.get("docker", {})
        return f"""version: '3.8'

services:
  {request.project_name}:
    build: .
    ports:
      - "{docker_config.get('ports', ['8080:8080'])[0]}"
    environment:
      NODE_ENV: {request.environment}
      PORT: 8080
    restart: unless-stopped
    networks:
      - {request.project_name}-network

networks:
  {request.project_name}-network:
    driver: bridge
"""
    
    def generate_docker_deploy_script(self, request: DeploymentRequest) -> str:
        """Generate Docker deployment script"""
        return f"""#!/bin/bash

set -e

echo "Deploying {request.project_name} to {request.environment}..."

# Build image
docker build -t {request.project_name}:latest .

# Stop existing container
docker stop {request.project_name} || true
docker rm {request.project_name} || true

# Run new container
docker run -d \\
  --name {request.project_name} \\
  --restart unless-stopped \\
  -p 8080:8080 \\
  -e NODE_ENV={request.environment} \\
  {request.project_name}:latest

echo "Deployment completed successfully!"
"""
    
    def generate_k8s_deployment(self, request: DeploymentRequest, config: Dict) -> str:
        """Generate Kubernetes deployment YAML"""
        k8s_config = config.get("kubernetes", {})
        return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {request.project_name}
  namespace: {k8s_config.get('namespace', 'default')}
spec:
  replicas: {k8s_config.get('replicas', 1)}
  selector:
    matchLabels:
      app: {request.project_name}
  template:
    metadata:
      labels:
        app: {request.project_name}
    spec:
      containers:
      - name: {request.project_name}
        image: {request.project_name}:latest
        ports:
        - containerPort: 8080
        env:
        - name: NODE_ENV
          value: "{request.environment}"
        resources:
          requests:
            cpu: {k8s_config.get('resources', {}).get('requests', {}).get('cpu', '100m')}
            memory: {k8s_config.get('resources', {}).get('requests', {}).get('memory', '128Mi')}
          limits:
            cpu: {k8s_config.get('resources', {}).get('limits', {}).get('cpu', '500m')}
            memory: {k8s_config.get('resources', {}).get('limits', {}).get('memory', '512Mi')}
"""
    
    def generate_k8s_service(self, request: DeploymentRequest, config: Dict) -> str:
        """Generate Kubernetes service YAML"""
        k8s_config = config.get("kubernetes", {})
        service_config = k8s_config.get("service", {})
        return f"""apiVersion: v1
kind: Service
metadata:
  name: {request.project_name}-service
  namespace: {k8s_config.get('namespace', 'default')}
spec:
  selector:
    app: {request.project_name}
  ports:
  - port: {service_config.get('port', 80)}
    targetPort: {service_config.get('target_port', 8080)}
  type: {service_config.get('type', 'ClusterIP')}
"""
    
    def generate_k8s_deploy_script(self, request: DeploymentRequest) -> str:
        """Generate Kubernetes deployment script"""
        return f"""#!/bin/bash

set -e

echo "Deploying {request.project_name} to Kubernetes..."

# Apply deployment
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# Wait for deployment to be ready
kubectl rollout status deployment/{request.project_name}

echo "Kubernetes deployment completed successfully!"
"""
    
    def generate_serverless_config(self, request: DeploymentRequest, config: Dict) -> str:
        """Generate serverless configuration"""
        serverless_config = config.get("serverless", {})
        return f"""service: {request.project_name}

provider:
  name: aws
  runtime: {serverless_config.get('runtime', 'nodejs18.x')}
  stage: {request.environment}
  region: us-east-1

functions:
  {request.project_name}:
    handler: {serverless_config.get('handler', 'index.handler')}
    timeout: {serverless_config.get('timeout', 30)}
    memorySize: {serverless_config.get('memory', 512)}
    environment:
      NODE_ENV: {request.environment}
    events:
      - http:
          path: /
          method: ANY
"""
    
    def generate_serverless_deploy_script(self, request: DeploymentRequest) -> str:
        """Generate serverless deployment script"""
        return f"""#!/bin/bash

set -e

echo "Deploying {request.project_name} to AWS Lambda..."

# Deploy using serverless framework
npx serverless deploy --stage {request.environment}

echo "Serverless deployment completed successfully!"
"""
