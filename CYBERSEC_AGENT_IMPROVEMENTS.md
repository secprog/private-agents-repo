# CyberSecurity Agent Improvements

## Current Status: ✅ Mostly Good

The CyberSecurity agent is well-structured with only 1 focused tool. However, there are some cleanup issues.

---

## Issues to Fix

### 1. Remove Old Vision Prompts from prompts.py

**File:** `agents/cybersecurity/modules/prompts.py`

**Problem:** Lines 1-317 contain vision analysis prompts that belong in the Vision agent, not here.

**Remove These Functions:**
- `get_component_analysis_instructions()` (lines 1-117)
- `get_connection_analysis_instructions()` (lines 120-200)
- `get_zone_analysis_instructions()` (lines 201-276)
- `get_merger_instructions()` (lines 278-317)

**Keep Only:**
- `get_comprehensive_security_analysis_instructions()` (line 320+)

**Why:** The CyberSecurity agent doesn't perform vision analysis - it receives pre-analyzed JSON data from the Vision agent.

---

### 2. Remove Duplicate Visual Models from models.py

**File:** `agents/cybersecurity/modules/models.py`

**Problem:** Lines 6-73 contain OLD vision models that duplicate the Vision agent's models.

**Remove These Classes:**
- `Position` (lines 6-11)
- `VisualComponent` (lines 13-42)
- `VisualConnection` (lines 44-57)
- `VisualZone` (lines 59-65)
- `VisualAnalysisResponse` (lines 67-73)

**Keep Only:** Security models starting from line 75:
- `ComponentSecurity`
- `ConnectionSecurity`
- `SecurityZone`
- `ThreatIdentification`
- `VulnerabilityAssessment`
- `AttackPath`
- `ComplianceCheck`
- `SecurityRecommendation`
- `SecurityPosture`
- `ComprehensiveSecurityAnalysis`

**Why:** The CyberSecurity agent receives JSON strings from the Vision agent - it doesn't need Pydantic models for vision data.

---

### 3. Update Prompt to Reference New Parameter Names

**File:** `agents/cybersecurity/modules/prompts.py`

**Line 331** - Update reference:

**OLD:**
```python
4. **trust_boundaries_json**: Security and trust boundaries (DMZ, VPC, etc.)
```

**NEW:**
```python
4. **boundaries_json**: Visual boundaries and enclosures (zones, regions, groupings)
```

---

### 4. Add Visual Interpretation Guidance to Prompt

**File:** `agents/cybersecurity/modules/prompts.py`

**Add after line 327** (after "Input Data (JSON):"):

```python
Input Data (JSON):
1. **components_json**: Visual components with colors, visual_badges, all_text_labels
2. **connections_json**: Connections with colors, thickness, line_pattern, visual_markers
3. **zones_json**: Logical zones/regions in the architecture
4. **boundaries_json**: Visual boundaries with visual_style, color, line_style, text_labels
5. **technologies_json**: Detected technologies, frameworks, cloud services
6. **relationships_json**: Inferred logical relationships
7. **annotations_json** (optional): Text annotations, notes, warnings
8. **legend_mappings_json** (optional): Symbol-to-meaning mappings
9. **line_crossings_json** (optional): Line crossing analysis

IMPORTANT - VISUAL DATA INTERPRETATION:
The Vision agent provides GENERIC VISUAL FACTS that you must INTERPRET for security meaning:

**Components:**
- primary_color: "red", "orange" → May indicate critical/exposed components
- visual_badges: "lock icon" → Authentication/encryption present
- all_text_labels: ["Public", "Internet-Facing"] → Exposed to internet
- border_style: "dashed" → May indicate temporary or insecure

**Connections:**
- color: "red" → May indicate critical path or insecure
- thickness: "thick" → May indicate high-volume data flow
- visual_markers: "lock icon" → Encrypted connection
- all_text_labels: ["HTTPS", "443"] → Secure protocol

**Boundaries:**
- text_labels: ["DMZ", "Public", "Internet"] → Security zone
- color: "red", "orange" + line_style: "dashed" → Exposed/public zone
- color: "blue", "green" → Protected/internal zone
- visual_style: "thick border" → Strong isolation

**Examples:**
- Boundary with text_labels=["DMZ", "Public Access"], color="red", line_style="dashed"
  → INTERPRET AS: Public-facing DMZ security zone

- Component with visual_badges=["lock icon"], all_text_labels=["HTTPS", "Auth Required"]
  → INTERPRET AS: Secured component with authentication

- Connection with color="red", visual_markers=["warning symbol"], all_text_labels=["HTTP", "Unencrypted"]
  → INTERPRET AS: Insecure connection vulnerability
```

---

## Implementation Priority

### Immediate (High Priority):
1. ✅ Remove old vision prompts from prompts.py
2. ✅ Remove duplicate visual models from models.py
3. ✅ Update prompt parameter reference (trust_boundaries_json → boundaries_json)

### Short-term (Medium Priority):
4. ✅ Add visual interpretation guidance to prompt

---

## Expected Benefits

### Before:
- Confusing file structure (vision code in cybersec agent)
- Old models that don't match Vision agent output
- Missing guidance on interpreting generic visual data

### After:
- Clean separation: CyberSec agent only has security code
- Receives rich visual data from Vision agent
- Knows how to interpret generic visual facts for security meaning
- Clearer, more maintainable codebase

---

## Files to Modify

1. `agents/cybersecurity/modules/prompts.py` - Remove lines 1-317, update line 331, add interpretation guidance
2. `agents/cybersecurity/modules/models.py` - Remove lines 6-73

---

## Testing Checklist

After making changes:

1. [ ] Verify CyberSec agent starts without errors
2. [ ] Test with Vision agent output (check it receives boundaries_json)
3. [ ] Verify security analysis includes interpretation of visual data
4. [ ] Check that threats/vulnerabilities reference visual details (colors, badges, etc.)
5. [ ] Ensure recommendations mention visual indicators

---

## Example Flow After Changes

### Vision Agent Outputs:
```json
{
  "components": [
    {
      "name": "User API",
      "primary_color": "orange",
      "visual_badges": ["warning triangle"],
      "all_text_labels": ["Port 80", "HTTP", "Public"]
    }
  ],
  "boundaries": [
    {
      "boundary_name": "DMZ",
      "color": "red",
      "line_style": "dashed",
      "text_labels": ["DMZ", "Internet-Facing", "0.0.0.0/0"]
    }
  ]
}
```

### CyberSec Agent Interprets:
```json
{
  "threats": [
    {
      "threat_name": "Unencrypted Public API Exposure",
      "severity": "high",
      "affected_components": ["User API"],
      "description": "User API is exposed in DMZ (red dashed boundary labeled 'Internet-Facing') with HTTP (port 80) instead of HTTPS. Orange color and warning triangle indicate criticality.",
      "attack_vector": "Attacker can intercept unencrypted traffic to User API",
      "impact": "Data breach, credential theft, MITM attacks"
    }
  ]
}
```

The CyberSec agent **interprets** the visual facts (orange color, warning triangle, text labels) to understand security implications.
