# Vision Agent Improvements for Security Analysis

## Problem Summary
The Vision agent has too many tools (22), many of which don't contribute to security analysis. The prompts don't focus on security-relevant information that the CyberSecurity agent needs.

## Recommended Tool Structure (Reduce from 22 to 6-8 tools)

### Core Tools (Keep & Enhance)

1. **run_core_analysis_parallel** ✅ KEEP
   - Analyzes: components, connections, zones in parallel
   - Enhancement: Merge relationship inference into this bundle

2. **run_security_enhancement_parallel** ✅ KEEP (rename from run_enhancement_analysis_parallel)
   - Analyzes: technologies, annotations in parallel
   - Remove: diagram_classification (not security-relevant)

3. **detect_trust_boundaries** ✅ KEEP
   - Critical for security zone analysis

4. **detect_data_flows** ✅ ADD NEW
   - Classify data types flowing through connections
   - Identify PII, credentials, sensitive data paths

5. **detect_external_exposure** ✅ ADD NEW
   - Identify internet-facing components
   - Classify exposure levels (public, semi-public, internal)

6. **detect_auth_points** ✅ ADD NEW
   - Identify authentication/authorization points
   - Map authentication flows

### Tools to Remove (14 tools)

❌ **Export Tools (3)** - Not analysis
- export_to_plantuml
- export_to_mermaid
- export_to_drawio

❌ **Text Extraction (3)** - Redundant, not implemented
- extract_text_from_image (already in component.text_content)
- extract_text_with_paddleocr (not actually implemented)
- extract_text_with_consensus (not actually implemented)

❌ **Meta-Analysis Tools (2)** - Overhead without security value
- enhance_analysis
- validate_visual_analysis

❌ **Quality/Layout Tools (4)** - Not security-relevant
- assess_image_quality
- identify_regions
- analyze_layout
- analyze_styling

❌ **Individual Enhancement Tools (3)** - Use parallel bundle instead
- detect_technologies (keep in bundle)
- classify_diagram_type (remove entirely)
- extract_annotations (keep in bundle)

⚠️ **Optional Removal (2)** - Low security value
- extract_legend_mappings
- detect_line_crossings

⚠️ **Merge into Core (1)**
- infer_relationships → merge into run_core_analysis_parallel

## Prompt Improvements

### Component Analysis Prompt - Add Security Questions

**Current:** Asks for name, type, position, text_content, visual_group, confidence

**Add Security Fields:**
```python
class VisualComponent(BaseModel):
    # ... existing fields ...

    # NEW: Security-relevant fields
    exposure_level: Literal["internet_facing", "semi_public", "internal", "private", "unknown"] = Field(
        default="unknown",
        description="Whether this component is exposed to the internet, semi-public (partner access), internal, or private"
    )

    has_authentication: bool = Field(
        default=False,
        description="Whether this component implements authentication/authorization"
    )

    data_sensitivity: Literal["public", "internal", "confidential", "pii", "credentials", "unknown"] = Field(
        default="unknown",
        description="Sensitivity level of data stored or processed by this component"
    )

    security_controls: List[str] = Field(
        default_factory=list,
        description="Visible security controls (WAF, Firewall, MFA, Encryption, etc.)"
    )
```

**Updated Prompt:**
```
In addition to basic component information, identify:

SECURITY ANALYSIS:
- exposure_level: Is this component internet-facing, semi-public (partner/customer access),
  internal (corporate network), or private (backend only)?
  Look for indicators like "Public", "Internet", "External", "DMZ" vs "Internal", "Private", "Backend"

- has_authentication: Does this component handle authentication or authorization?
  Look for: Login, Auth, SSO, Identity, IAM, AD, OAuth, JWT, API Key

- data_sensitivity: What level of sensitive data does it handle?
  - "pii" if handles personal data (user info, emails, names)
  - "credentials" if handles passwords, tokens, keys, secrets
  - "confidential" if handles business-critical data
  - "internal" if handles internal business data
  - "public" if only public/non-sensitive data

- security_controls: List any visible security mechanisms
  Examples: "WAF", "Firewall", "TLS/HTTPS", "MFA", "Encryption at Rest", "VPN", "API Gateway"
```

### Connection Analysis Prompt - Add Security Questions

**Add Security Fields:**
```python
class VisualConnection(BaseModel):
    # ... existing fields ...

    # NEW: Security-relevant fields
    protocol_security: Literal["encrypted", "plaintext", "unknown"] = Field(
        default="unknown",
        description="Whether connection uses encryption (HTTPS, TLS, SSH) or plaintext (HTTP, FTP)"
    )

    data_type: Literal["public", "internal", "pii", "credentials", "sensitive", "unknown"] = Field(
        default="unknown",
        description="Type of data flowing through this connection"
    )

    crosses_trust_boundary: bool = Field(
        default=False,
        description="Whether this connection crosses a security/trust boundary (e.g., DMZ to internal, public to private)"
    )

    authentication_method: str = Field(
        default="",
        description="Authentication method if shown (API Key, OAuth, JWT, Basic Auth, etc.)"
    )
```

**Updated Prompt:**
```
For each connection, identify:

SECURITY ANALYSIS:
- protocol_security: Does the connection use encryption?
  - "encrypted" if shows HTTPS, TLS, SSL, SSH, VPN, Secure, Encrypted
  - "plaintext" if shows HTTP, FTP, Telnet, or no security indicator
  - "unknown" if not specified

- data_type: What kind of data flows through this connection?
  Look at labels and context:
  - "credentials" for login, auth, tokens, passwords
  - "pii" for user data, personal info, emails
  - "sensitive" for financial, health, confidential business data
  - "internal" for internal business data
  - "public" for publicly available data

- crosses_trust_boundary: Does this connection go between security zones?
  Examples: Internet → DMZ, DMZ → Internal, Public → Private, External → VPC

- authentication_method: What auth method is shown (if any)?
  Look for labels: "API Key", "OAuth 2.0", "JWT", "Basic Auth", "mTLS", "SAML", etc.
```

### Zone Analysis Prompt - Emphasize Security

**Updated Prompt:**
```
For each visual zone, identify:

SECURITY EMPHASIS:
- If the zone represents a security boundary (DMZ, Public Zone, Private Subnet, VPC, etc.),
  prioritize detecting it

- For security zones, note:
  * Trust level (public, semi-trusted, trusted, highly-trusted)
  * Network isolation mechanisms (firewall, security group, VLAN)
  * Components that belong to this security zone

- Look for visual indicators:
  * Red/orange borders → exposed/public zones
  * Green/blue borders → protected/private zones
  * Dashed lines → security boundaries
  * Labels: "DMZ", "Public Subnet", "Private Network", "VPC", "Security Zone"
```

## Implementation Priority

### Immediate (Week 1)
1. ✅ Remove 14 low-value tools
2. ✅ Update component analysis prompt with security fields
3. ✅ Update connection analysis prompt with security fields
4. ✅ Update zone analysis prompt with security emphasis

### Short-term (Week 2)
5. ✅ Add `detect_data_flows` tool
6. ✅ Add `detect_external_exposure` tool
7. ✅ Add `detect_auth_points` tool
8. ✅ Merge `infer_relationships` into `run_core_analysis_parallel`

### Medium-term (Week 3-4)
9. ✅ Update Pydantic models with new security fields
10. ✅ Test with real architecture diagrams
11. ✅ Validate CyberSecurity agent receives useful data

## Expected Improvements

### Before (Current State)
- 22 tools → LLM confused about which to use
- Generic component/connection data → CyberSec agent must infer security implications
- Missing critical security context → Incomplete threat analysis
- Text extraction overhead → Wasted tokens and cost

### After (Improved State)
- 6-8 focused tools → Clear workflow
- Security-rich component/connection data → CyberSec agent gets direct security context
- Complete security context → Comprehensive threat analysis
- No redundant analysis → Lower cost and latency

## Example: Before vs After

### Before - Component Analysis
```json
{
  "name": "User Service",
  "component_type": "application",
  "visual_type": "box",
  "position": {...},
  "text_content": "User Service\nHTTPS API",
  "visual_group": "Backend",
  "confidence": 0.94
}
```

### After - Component Analysis
```json
{
  "name": "User Service",
  "component_type": "application",
  "visual_type": "box",
  "position": {...},
  "text_content": "User Service\nHTTPS API",
  "visual_group": "Backend",
  "confidence": 0.94,

  // NEW SECURITY FIELDS
  "exposure_level": "internal",
  "has_authentication": true,
  "data_sensitivity": "pii",
  "security_controls": ["HTTPS", "JWT Authentication", "API Gateway"]
}
```

This gives the CyberSecurity agent immediate context that:
- Component is internal (not internet-facing)
- Handles authentication
- Processes PII (requires compliance checks)
- Uses HTTPS and JWT (good security posture)

## Success Metrics

1. **Tool count**: 22 → 6-8 tools
2. **Security field coverage**: 0% → 90%+ of components/connections have security metadata
3. **CyberSec agent quality**: Measure threat detection accuracy before/after
4. **Cost reduction**: ~30-40% fewer LLM calls (removing text extraction, validation, enhancement)
5. **Latency improvement**: Faster analysis with fewer sequential tool calls
