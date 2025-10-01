"""
ADK-based cybersecurity agent core functionality
"""

import os
import uuid
import logging
import httpx
import base64
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

# Google ADK SDK imports - temporarily disabled due to import issues
# from google.adk.agents.context import InvocationContext
# from google.adk.agents.events import Event, EventActions

from modules.models import A2AMessage, SecurityAnalysisRequest, ArtifactData
from modules.session_service import AgentSessionService
from modules.artifact_service import create_artifact_service
from google.adk.agents import Agent
from modules.security_tools import SecurityAnalysisTool, ThreatDetectionTool

logger = logging.getLogger(__name__)


class CyberSecurityCore:
    """ADK-based cybersecurity agent core functionality"""
    
    def __init__(self):
        self.agent_id = "cybersecurity-agent-01"
        self.endpoint = os.getenv('CYBERSECURITY_AGENT_ENDPOINT', 'https://cybersecurity-agent:8001')
        
        # Initialize ADK LLM agent directly
        valid_name = self.agent_id.replace("-", "_")
        self.agent = Agent(
            name=valid_name,
            description="Specialized agent for cybersecurity analysis, threat detection, and vulnerability assessment",
            model="gemini-2.0-flash"
        )
        
        # Add security tools
        self.security_analysis_tool = SecurityAnalysisTool()
        self.threat_detection_tool = ThreatDetectionTool()
        
        # Set capabilities
        self.capabilities = [
            "security_analysis",
            "threat_detection", 
            "vulnerability_scan",
            "security_policy",
            "incident_response",
            "owasp_analysis",
            "pattern_detection",
            "security_recommendations",
            "sbom_analysis",
            "dependency_scanning",
            "vulnerability_database_lookup"
        ]
        
        # Initialize components
        self.session_service = AgentSessionService()  # New Google ADK session service
        self.artifact_service = create_artifact_service()
    
    async def initialize(self):
        """Initialize cybersecurity agent"""
        try:
            # Register with orchestrator
            await self.register_with_orchestrator()
            
            logger.info("CyberSecurity agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise
    
    async def register_with_orchestrator(self):
        """Register this agent with the orchestrator"""
        try:
            orchestrator_endpoint = os.getenv('ORCHESTRATOR_ENDPOINT', 'https://orchestrator:8000')
            
            registration_message = A2AMessage(
                id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id="orchestrator-main",
                message_type="agent_registration",
                content={
                    "agent_id": self.agent_id,
                    "endpoint": self.endpoint,
                    "capabilities": self.capabilities,
                    "description": "Cybersecurity agent for security analysis, vulnerability scanning, and threat detection"
                }
            )
            
            # Send registration to orchestrator
            verify_ssl = os.getenv('VERIFY_SSL', 'true').lower() == 'true'
            async with httpx.AsyncClient(verify=verify_ssl) as client:
                response = await client.post(
                    f"{orchestrator_endpoint}",
                    json=registration_message.dict(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Successfully registered {self.agent_id} with orchestrator")
                else:
                    logger.warning(f"⚠️ Registration response: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Failed to register with orchestrator: {e}")
    
    
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return [
            "security_analysis",
            "threat_detection", 
            "vulnerability_scan",
            "security_policy",
            "incident_response",
            "owasp_analysis",
            "pattern_detection",
            "security_recommendations"
        ]
    
    async def analyze_sbom_artifact(self, artifact: ArtifactData, analysis: Dict) -> Dict:
        """Analyze SBOM (Software Bill of Materials) for vulnerabilities"""
        try:
            
            # Decode artifact data
            artifact_content = base64.b64decode(artifact.data).decode('utf-8')
            
            # Parse SBOM (assuming JSON format like SPDX or CycloneDX)
            try:
                sbom_data = json.loads(artifact_content)
            except json.JSONDecodeError:
                return {"error": "Invalid JSON format in SBOM file"}
            
            # Analyze SBOM structure and components
            analysis_prompt = f"""Analyze this Software Bill of Materials (SBOM) for security vulnerabilities.
            
            SBOM Data: {json.dumps(sbom_data, indent=2)[:2000]}...
            
            Please provide:
            1. List of all components/packages with versions
            2. Known vulnerabilities for each component
            3. Risk assessment (High/Medium/Low)
            4. Remediation recommendations
            5. Compliance status (if applicable)
            
            Format as JSON with structure:
            {{
                "components": [{{"name": "package", "version": "1.0.0", "vulnerabilities": [...]}}],
                "risk_summary": {{"high": 0, "medium": 0, "low": 0}},
                "recommendations": ["recommendation1", "recommendation2"],
                "compliance_status": "compliant|non_compliant|partial"
            }}
            """
            
            response = await self.agent.run(
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            try:
                parsed_result = json.loads(result)
            except json.JSONDecodeError:
                parsed_result = {"raw_analysis": result}
            
            return {
                "analysis_type": "sbom_vulnerability_scan",
                "artifact_type": "sbom",
                "components_analyzed": len(sbom_data.get("packages", [])),
                "vulnerability_analysis": parsed_result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing SBOM artifact: {e}")
            return {"error": f"SBOM analysis failed: {str(e)}"}
    
    async def analyze_text_security_file(self, artifact: ArtifactData, analysis: Dict) -> Dict:
        """Analyze text-based security files"""
        try:
            
            # Decode artifact data
            artifact_content = base64.b64decode(artifact.data).decode('utf-8')
            
            analysis_prompt = f"""Analyze this security-related text file for potential issues.
            
            Filename: {artifact.filename}
            Content: {artifact_content[:2000]}...
            
            Look for:
            1. Security vulnerabilities
            2. Configuration issues
            3. Compliance violations
            4. Best practice violations
            
            Provide structured analysis with severity levels and recommendations.
            """
            
            response = await self.agent.run(
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.3
            )
            
            return {
                "analysis_type": "text_security_analysis",
                "artifact_type": "text_file",
                "analysis": response.choices[0].message.content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing text security file: {e}")
            return {"error": f"Text analysis failed: {str(e)}"}
    
    async def analyze_generic_artifact(self, artifact: ArtifactData, analysis: Dict) -> Dict:
        """Analyze generic artifacts"""
        try:
            analysis_prompt = f"""Analyze this file for potential security implications.
            
            Filename: {artifact.filename}
            MIME Type: {artifact.mime_type}
            File Size: {len(artifact.data)} bytes (base64 encoded)
            
            Provide security analysis based on file type and name patterns.
            """
            
            response = await self.agent.run(
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.3
            )
            
            return {
                "analysis_type": "generic_security_analysis",
                "artifact_type": "generic",
                "mime_type": artifact.mime_type,
                "analysis": response.choices[0].message.content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing generic artifact: {e}")
            return {"error": f"Generic analysis failed: {str(e)}"}
    
    
    async def analyze_security_task(self, request: str, attachments: List[Dict]) -> Dict:
        """Analyze security task"""
        try:
            # Determine analysis type based on attachments
            analysis_type = "comprehensive"
            code_content = None
            url_content = None
            file_content = None
            
            for attachment in attachments:
                if attachment.get("type") == "code":
                    code_content = attachment.get("content", "")
                elif attachment.get("type") == "url":
                    url_content = attachment.get("content", "")
                elif attachment.get("type") == "file":
                    file_content = attachment.get("content", "")
            
            # Create security analysis request
            security_request = SecurityAnalysisRequest(
                code=code_content,
                url=url_content,
                file_content=file_content,
                analysis_type=analysis_type
            )
            
            # Perform security analysis
            result = await self.security_analyzer.analyze_security_request(security_request)
            
            # Enhance with LLM analysis if needed
            if result.get("status") == "completed":
                llm_analysis = await self.agent.run(
                    f"Provide additional security insights for this analysis: {result}"
                )
                result["llm_insights"] = llm_analysis
            
            return result
            
        except Exception as e:
            logger.error(f"Security analysis error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
