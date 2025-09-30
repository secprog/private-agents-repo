"""
ADK-based security analysis tools
"""

import re
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

# Google ADK SDK imports
from google.adk.tools import FunctionTool
from google.adk.tools import ToolContext

from modules.models import SecurityAnalysisRequest

logger = logging.getLogger(__name__)


def security_analysis_function(content: str, analysis_type: str = "code") -> dict:
    """Analyze code, URLs, or files for security vulnerabilities including OWASP Top 10 issues"""
    # This will be implemented by the SecurityAnalysisTool class
    pass

class SecurityAnalysisTool(FunctionTool):
    """Tool for analyzing security vulnerabilities in code"""
    
    def __init__(self):
        super().__init__(security_analysis_function)
        
        # OWASP patterns for vulnerability detection
        self.owasp_patterns = {
            "sql_injection": [
                r"(?i)(union\s+select|drop\s+table|insert\s+into|delete\s+from)",
                r"(?i)(or\s+1\s*=\s*1|and\s+1\s*=\s*1)",
                r"(?i)(';|\"|\s*;\s*--)",
            ],
            "xss": [
                r"(?i)<script[^>]*>.*?</script>",
                r"(?i)javascript:",
                r"(?i)on\w+\s*=",
                r"(?i)alert\s*\(",
            ],
            "path_traversal": [
                r"(?i)\.\./",
                r"(?i)\.\.\\",
                r"(?i)%2e%2e%2f",
                r"(?i)%2e%2e%5c",
            ],
            "command_injection": [
                r"(?i)(\||&|;|\$\(|\`|\$\{)",
                r"(?i)(cat\s+|ls\s+|pwd\s+|whoami\s+)",
                r"(?i)(rm\s+-rf|del\s+|format\s+)",
            ],
            "weak_crypto": [
                r"(?i)(md5\s*\(|sha1\s*\()",
                r"(?i)(des\s|rc4\s|md4\s)",
                r"(?i)(password\s*=\s*['\"][^'\"]{1,7}['\"])",
            ],
            "hardcoded_secrets": [
                r"(?i)(api[_-]?key\s*=\s*['\"][^'\"]+['\"])",
                r"(?i)(secret\s*=\s*['\"][^'\"]+['\"])",
                r"(?i)(password\s*=\s*['\"][^'\"]+['\"])",
                r"(?i)(token\s*=\s*['\"][^'\"]+['\"])",
            ],
        }
    
    async def execute(self, context: ToolContext, **kwargs) -> Dict[str, Any]:
        """Execute security analysis"""
        try:
            # Extract parameters
            code = kwargs.get("code", "")
            url = kwargs.get("url", "")
            file_content = kwargs.get("file_content", "")
            analysis_type = kwargs.get("analysis_type", "comprehensive")
            
            threats = []
            vulnerabilities = []
            
            # Analyze based on input type
            if code:
                threats, vulnerabilities = await self._analyze_code(code)
            elif url:
                threats, vulnerabilities = await self._analyze_url(url)
            elif file_content:
                threats, vulnerabilities = await self._analyze_code(file_content)
            else:
                return {
                    "status": "error",
                    "message": "No content provided for analysis. Please provide 'code', 'url', or 'file_content' parameter."
                }
            
            # Generate security score
            security_score = self._calculate_security_score(threats, vulnerabilities)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(threats, vulnerabilities)
            
            return {
                "status": "completed",
                "threats": threats,
                "vulnerabilities": vulnerabilities,
                "security_score": security_score,
                "recommendations": recommendations,
                "analysis_type": analysis_type
            }
            
        except Exception as e:
            logger.error(f"Security analysis error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _analyze_code(self, code: str) -> tuple[List[Dict], List[Dict]]:
        """Analyze code for security issues"""
        threats = []
        vulnerabilities = []
        
        # Check for OWASP patterns
        for category, patterns in self.owasp_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, code, re.MULTILINE)
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    
                    if category in ["sql_injection", "command_injection"]:
                        threats.append({
                            "type": category,
                            "severity": "high",
                            "line": line_num,
                            "description": f"Potential {category.replace('_', ' ')} vulnerability detected",
                            "code_snippet": match.group(),
                            "recommendation": self._get_recommendation(category)
                        })
                    else:
                        vulnerabilities.append({
                            "type": category,
                            "severity": "medium" if category == "xss" else "low",
                            "line": line_num,
                            "description": f"{category.replace('_', ' ')} issue detected",
                            "code_snippet": match.group(),
                            "recommendation": self._get_recommendation(category)
                        })
        
        return threats, vulnerabilities
    
    async def _analyze_url(self, url: str) -> tuple[List[Dict], List[Dict]]:
        """Analyze URL for security issues"""
        threats = []
        vulnerabilities = []
        
        try:
            parsed = urlparse(url)
            
            # Check for suspicious patterns
            if not parsed.scheme or parsed.scheme not in ['http', 'https']:
                vulnerabilities.append({
                    "type": "insecure_protocol",
                    "severity": "medium",
                    "description": "URL uses insecure or unknown protocol",
                    "recommendation": "Use HTTPS protocol"
                })
            
            # Check for suspicious domains
            suspicious_domains = ['bit.ly', 'tinyurl.com', 'goo.gl']
            if any(domain in parsed.netloc for domain in suspicious_domains):
                threats.append({
                    "type": "suspicious_shortener",
                    "severity": "medium",
                    "description": "URL uses suspicious URL shortener",
                    "recommendation": "Verify the actual destination before accessing"
                })
            
            # Check for suspicious parameters
            if parsed.query:
                if 'redirect' in parsed.query.lower() or 'url' in parsed.query.lower():
                    threats.append({
                        "type": "open_redirect",
                        "severity": "high",
                        "description": "Potential open redirect vulnerability",
                        "recommendation": "Validate and sanitize redirect URLs"
                    })
        
        except Exception as e:
            logger.error(f"URL analysis error: {e}")
        
        return threats, vulnerabilities
    
    def _calculate_security_score(self, threats: List[Dict], vulnerabilities: List[Dict]) -> int:
        """Calculate security score (0-100)"""
        score = 100
        
        # Deduct points for threats
        for threat in threats:
            if threat["severity"] == "critical":
                score -= 25
            elif threat["severity"] == "high":
                score -= 15
            elif threat["severity"] == "medium":
                score -= 10
            else:
                score -= 5
        
        # Deduct points for vulnerabilities
        for vuln in vulnerabilities:
            if vuln["severity"] == "high":
                score -= 10
            elif vuln["severity"] == "medium":
                score -= 5
            else:
                score -= 2
        
        return max(0, score)
    
    def _generate_recommendations(self, threats: List[Dict], vulnerabilities: List[Dict]) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        # Collect unique recommendations
        all_issues = threats + vulnerabilities
        seen_recommendations = set()
        
        for issue in all_issues:
            rec = issue.get("recommendation", "")
            if rec and rec not in seen_recommendations:
                recommendations.append(rec)
                seen_recommendations.add(rec)
        
        # Add general recommendations
        if threats:
            recommendations.append("Implement input validation and sanitization")
            recommendations.append("Use parameterized queries to prevent SQL injection")
            recommendations.append("Implement proper authentication and authorization")
        
        if vulnerabilities:
            recommendations.append("Regular security code reviews")
            recommendations.append("Implement automated security testing")
            recommendations.append("Keep dependencies updated")
        
        return recommendations
    
    def _get_recommendation(self, category: str) -> str:
        """Get specific recommendation for security category"""
        recommendations = {
            "sql_injection": "Use parameterized queries and input validation",
            "xss": "Implement output encoding and Content Security Policy",
            "path_traversal": "Validate and sanitize file paths",
            "command_injection": "Avoid system commands, use safe alternatives",
            "weak_crypto": "Use strong cryptographic algorithms (AES-256, SHA-256+)",
            "hardcoded_secrets": "Use environment variables or secure secret management"
        }
        return recommendations.get(category, "Review and fix security issue")


def threat_detection_function(content: str, threat_type: str = "general") -> dict:
    """Detect and analyze security threats in various formats"""
    # This will be implemented by the ThreatDetectionTool class
    pass

class ThreatDetectionTool(FunctionTool):
    """Tool for detecting security threats"""
    
    def __init__(self):
        super().__init__(threat_detection_function)
    
    async def execute(self, context: ToolContext, **kwargs) -> Dict[str, Any]:
        """Execute threat detection"""
        try:
            content = kwargs.get("content", "")
            threat_type = kwargs.get("threat_type", "general")
            
            # Basic threat detection logic
            threats = []
            
            # Check for common threat patterns
            if "malware" in content.lower():
                threats.append({
                    "type": "malware",
                    "severity": "high",
                    "description": "Potential malware reference detected",
                    "recommendation": "Scan system for malware and update antivirus"
                })
            
            if "phishing" in content.lower():
                threats.append({
                    "type": "phishing",
                    "severity": "medium",
                    "description": "Potential phishing attempt detected",
                    "recommendation": "Verify sender authenticity and avoid clicking suspicious links"
                })
            
            return {
                "status": "completed",
                "threats": threats,
                "threat_type": threat_type
            }
            
        except Exception as e:
            logger.error(f"Threat detection error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
