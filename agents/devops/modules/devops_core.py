"""
ADK-based DevOps agent core functionality
"""

import os
import json
import uuid
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Google ADK SDK imports - temporarily disabled due to import issues
# from google.adk.agents.context import InvocationContext
# from google.adk.agents.events import Event, EventActions

from modules.models import A2AMessage, DeploymentRequest, InfrastructureRequest
from modules.session_service import AgentSessionService
from google.adk.agents import Agent
from modules.devops_tools import DeploymentTool, InfrastructureTool

logger = logging.getLogger(__name__)


class DevOpsCore:
    """ADK-based DevOps agent core functionality"""
    
    def __init__(self):
        self.agent_id = "devops-agent-01"
        self.endpoint = os.getenv('DEVOPS_AGENT_ENDPOINT', 'https://devops-agent:8002')
        
        # Initialize ADK LLM agent directly
        valid_name = self.agent_id.replace("-", "_")
        self.agent = Agent(
            name=valid_name,
            description="Specialized agent for DevOps operations, deployment automation, and infrastructure management",
            model="gemini-2.0-flash"
        )
        
        # Add DevOps tools
        self.deployment_tool = DeploymentTool()
        self.infrastructure_tool = InfrastructureTool()
        
        # Set capabilities
        self.capabilities = [
            "deployment",
            "ci_cd",
            "infrastructure",
            "monitoring",
            "automation",
            "containerization",
            "docker_configuration",
            "kubernetes_configuration",
            "pipeline_generation",
            "infrastructure_as_code",
            "terraform_templates",
            "ansible_playbooks"
        ]
        
        # Initialize components
        self.session_service = AgentSessionService()  # New Google ADK session service
    
    async def initialize(self):
        """Initialize DevOps agent"""
        try:
            # A2A client is now handled directly by the SDK
            
            # Setup message handlers
            self.setup_message_handlers()
            
            logger.info("DevOps agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise
    
    def setup_message_handlers(self):
        """Setup A2A message handlers"""
        # Message handlers are now handled directly by the ADK SDK
        pass
    
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return [
            "deployment",
            "ci_cd",
            "infrastructure",
            "monitoring",
            "automation",
            "containerization",
            "docker_configuration",
            "kubernetes_configuration",
            "pipeline_generation",
            "infrastructure_as_code",
            "terraform_templates",
            "ansible_playbooks"
        ]
    
    async def handle_task_assignment(self, message: A2AMessage):
        """Handle task assignment from orchestrator"""
        try:
            task_id = message.content.get("task_id")
            description = message.content.get("description", "")
            attachments = message.content.get("attachments", [])
            
            logger.info(f"Processing DevOps task {task_id}: {description}")
            
            # Analyze the request
            result = await self.process_devops_task(description, attachments)
            
            # Send result back to orchestrator
            response = A2AMessage(
                id=f"result_{task_id}",
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type="task_result",
                content={
                    "task_id": task_id,
                    "result": result,
                    "status": "completed"
                }
            )
            # Send message - handled by ADK SDK
            pass
            
        except Exception as e:
            logger.error(f"Error processing task: {e}")
            # Send error response
            error_response = A2AMessage(
                id=f"error_{message.content.get('task_id', 'unknown')}",
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type="task_error",
                content={"error": str(e)},
                metadata={"task_id": message.content.get("task_id")}
            )
            # Send error message - handled by ADK SDK
            pass
    
    async def handle_health_check(self, message: A2AMessage):
        """Handle health check from orchestrator"""
        response = A2AMessage(
            id=f"health_{datetime.utcnow().isoformat()}",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="health_response",
            content={
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": {
                    "deployments": 0,
                    "active_pipelines": 0
                }
            }
        )
        # Send message - handled by ADK SDK
        pass
    
    async def handle_capability_query(self, message: A2AMessage):
        """Handle capability query from orchestrator"""
        response = A2AMessage(
            id=f"cap_{datetime.utcnow().isoformat()}",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="capability_response",
            content={
                "agent_id": self.agent_id,
                "capabilities": self.get_capabilities(),
                "description": "Specialized agent for DevOps operations, deployment automation, and infrastructure management",
                "version": "1.0.0",
                "status": "online"
            }
        )
        # Send message - handled by ADK SDK
        pass
    
    async def handle_agent_card_query(self, message: A2AMessage):
        """Handle agent card query from orchestrator"""
        # Get agent card using ADK SDK's to_a2a() function which auto-generates agent cards
        agent_card = self.agent.get_agent_card()
        
        response = A2AMessage(
            id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="agent_card_response",
            content=agent_card
        )
        # Send message - handled by ADK SDK
        pass
    
    async def process_devops_task(self, request: str, attachments: List[Dict]) -> Dict:
        """Process DevOps task"""
        try:
            # Analyze request with LLM
            task_analysis = await self.agent.run(f"Analyze this DevOps request: {request}")
            
            # Determine task type
            task_type = task_analysis.get("task_type", "general")
            
            if "deployment" in task_type.lower() or "deploy" in request.lower():
                return await self.handle_deployment_request(request, attachments)
            elif "infrastructure" in task_type.lower() or "infra" in request.lower():
                return await self.handle_infrastructure_request(request, attachments)
            elif "pipeline" in task_type.lower() or "ci" in request.lower():
                return await self.handle_pipeline_request(request, attachments)
            else:
                return await self.handle_general_devops_request(request, attachments)
                
        except Exception as e:
            logger.error(f"DevOps task processing error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def handle_deployment_request(self, request: str, attachments: List[Dict]) -> Dict:
        """Handle deployment request"""
        try:
            # Extract deployment parameters from request
            deployment_request = DeploymentRequest(
                project_name="sample-project",  # Would extract from request
                environment="development",      # Would extract from request
                deployment_type="docker"        # Would extract from request
            )
            
            # Process deployment
            result = await self.deployment_engine.process_deployment_request(deployment_request)
            
            return {
                "status": "completed",
                "task_type": "deployment",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Deployment handling error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def handle_infrastructure_request(self, request: str, attachments: List[Dict]) -> Dict:
        """Handle infrastructure request"""
        try:
            # Generate infrastructure configuration
            infrastructure_config = {
                "type": "terraform",
                "resources": [
                    {
                        "type": "aws_instance",
                        "name": "web_server",
                        "instance_type": "t3.micro",
                        "ami": "ami-0c02fb55956c7d316"
                    }
                ]
            }
            
            return {
                "status": "completed",
                "task_type": "infrastructure",
                "result": {
                    "infrastructure_config": infrastructure_config,
                    "terraform_files": self.generate_terraform_files(infrastructure_config)
                }
            }
            
        except Exception as e:
            logger.error(f"Infrastructure handling error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def handle_pipeline_request(self, request: str, attachments: List[Dict]) -> Dict:
        """Handle CI/CD pipeline request"""
        try:
            # Generate pipeline configuration
            pipeline_config = {
                "type": "github_actions",
                "name": "CI/CD Pipeline",
                "stages": [
                    {
                        "name": "build",
                        "steps": [
                            "Checkout code",
                            "Setup Node.js",
                            "Install dependencies",
                            "Run tests",
                            "Build application"
                        ]
                    },
                    {
                        "name": "deploy",
                        "steps": [
                            "Deploy to staging",
                            "Run integration tests",
                            "Deploy to production"
                        ]
                    }
                ]
            }
            
            return {
                "status": "completed",
                "task_type": "pipeline",
                "result": {
                    "pipeline_config": pipeline_config,
                    "pipeline_files": self.generate_pipeline_files(pipeline_config)
                }
            }
            
        except Exception as e:
            logger.error(f"Pipeline handling error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def handle_general_devops_request(self, request: str, attachments: List[Dict]) -> Dict:
        """Handle general DevOps request"""
        try:
            # Use LLM to generate response
            response = await self.agent.run(
                f"Provide DevOps guidance for: {request}"
            )
            
            return {
                "status": "completed",
                "task_type": "general",
                "result": {
                    "response": response,
                    "recommendations": [
                        "Implement automated testing",
                        "Use infrastructure as code",
                        "Set up monitoring and logging",
                        "Implement security best practices"
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"General DevOps handling error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def generate_terraform_files(self, config: Dict) -> Dict[str, str]:
        """Generate Terraform configuration files"""
        return {
            "main.tf": f"""provider "aws" {{
  region = "us-east-1"
}}

resource "aws_instance" "web_server" {{
  ami           = "{config['resources'][0]['ami']}"
  instance_type = "{config['resources'][0]['instance_type']}"
  
  tags = {{
    Name = "{config['resources'][0]['name']}"
  }}
}}
""",
            "variables.tf": """variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
""",
            "outputs.tf": """output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.web_server.id
}
"""
        }
    
    def generate_pipeline_files(self, config: Dict) -> Dict[str, str]:
        """Generate CI/CD pipeline files"""
        return {
            ".github/workflows/ci-cd.yml": f"""name: {config['name']}

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        
    - name: Install dependencies
      run: npm ci
      
    - name: Run tests
      run: npm test
      
    - name: Build application
      run: npm run build
      
  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Deploy to production
      run: echo "Deploying to production..."
"""
        }
