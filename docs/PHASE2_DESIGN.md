# Phase 2: Normalize & Template - Design Document

**Status:** Design Approved ✅  
**Ready for Implementation:** Pending  
**Last Updated:** December 23, 2025

---

## Design Decisions (APPROVED)

### 1. AI Provider
**Decision:** OpenAI GPT-4  
**Rationale:** Native JSON mode, excellent at structured output, well-documented API

### 2. AI Call Granularity
**Decision:** One AI call per module path (batch all instances)  
**Fallback:** Split into multiple calls if instances >20 or token limit reached  
**Rationale:** Fewer API calls, better pattern recognition across examples

### 3. Placeholder Naming Convention
**Decision:** Descriptive names - `{{management_ip_address}}`  
**Examples:**
- `{{management_ip_address}}` not `{{mgmt_ip}}`
- `{{virtual_server_ip}}` not `{{vip}}`
- `{{real_server_name}}` not `{{rs_name}}`

**Rationale:** Most readable, AI-friendly, self-documenting

### 4. Template Variation Strategy
**Decision:** One template with all optional parameters  
**Approach:**
- Single template per module path
- Mark optional parameters with `required: false`
- Track variation patterns in metadata

**Rationale:** Simpler, more flexible, easier to maintain

### 5. Default Value Threshold
**Decision:** 70% occurrence threshold  
**Rules:**
- Value appears in ≥70% of instances → Set as default
- 50-69% → Mark as "common" but no default
- <50% → No default, user must provide

**Rationale:** Balance between convenience and accuracy

### 6. Special Module Handling

#### Certificates & Keys
```json
{
  "template": {
    "header": "/c/slb/ssl/certs/import cert \"{{certificate_name}}\" text",
    "body": "{{certificate_content}}"
  },
  "parameters": {
    "certificate_name": {
      "type": "string",
      "required": true
    },
    "certificate_content": {
      "type": "pem_certificate",
      "required": true,
      "description": "PEM-encoded certificate content (preserve exact formatting)"
    }
  }
}
```

#### Scripts
```json
{
  "template": {
    "header": "/c/slb/appshape/script {{script_id}}",
    "body": [
      "{{status}}",
      "import text",
      "{{script_content}}",
      "-----END"
    ]
  },
  "parameters": {
    "script_id": {
      "type": "integer",
      "required": true
    },
    "script_content": {
      "type": "tcl_script",
      "required": true,
      "description": "TCL script body (preserve exact formatting)"
    }
  }
}
```

#### Action Commands
```json
{
  "module_path": "/c/l2/stg",
  "template": {
    "header": "/c/l2/stg {{stg_id}}/add {{port_range}} {{vlan_list}}"
  },
  "parameters": {
    "stg_id": {"type": "integer", "required": true},
    "port_range": {"type": "string", "required": true, "example": "1-2"},
    "vlan_list": {"type": "string", "required": true, "example": "818 820"}
  }
}
```

---

## Phase 2 Architecture

### Component Structure

```
phase2/
├── __init__.py
├── value_extractor.py      # Python: Extract values from sub-lines
├── pattern_analyzer.py     # Python: Detect types, group patterns
├── ai_analyzer.py          # AI: OpenAI integration
├── template_generator.py   # Python: Build templates with placeholders
├── metadata_generator.py   # AI: Generate descriptions, tags
├── default_calculator.py   # Python: Calculate statistical defaults
└── template_storage.py     # Python: Save templates to JSON
```

### Main Script
```
normalize_configs.py        # Phase 2 orchestrator
```

---

## Data Flow

```
Phase 1 JSON (parsed_modules_*.json)
           ↓
    [Load & Group]
           ↓
┌──────────────────────────┐
│ Group by Module Path     │
│ /c/l3/if: [15 instances] │
└──────────────────────────┘
           ↓
    For each group:
           ↓
┌──────────────────────────────────────────┐
│ 1. Python: Extract Value Patterns        │
│    - Key-value pairs                     │
│    - Type detection                      │
│    - Frequency analysis                  │
└──────────────────────────────────────────┘
           ↓
┌──────────────────────────────────────────┐
│ 2. AI: Semantic Analysis (GPT-4)         │
│    Input: Module examples + patterns     │
│    Output: JSON with:                    │
│    - Parameter names                     │
│    - Descriptions                        │
│    - Category                            │
│    - Tags                                │
│    - Dependencies                        │
└──────────────────────────────────────────┘
           ↓
┌──────────────────────────────────────────┐
│ 3. Python: Generate Template             │
│    - Replace values with placeholders    │
│    - Build parameter schemas             │
│    - Calculate defaults (70% threshold)  │
└──────────────────────────────────────────┘
           ↓
┌──────────────────────────────────────────┐
│ 4. Python: Store Template                │
│    Output: templated_modules_*.json      │
└──────────────────────────────────────────┘
```

---

## Python Value Extraction

### ValueExtractor Class

```python
class ValueExtractor:
    """Extracts values and patterns from module sub-lines"""
    
    def extract_patterns(self, modules: List[ModuleBlock]) -> Dict:
        """
        Input: All instances of same module path
        Output: {
            "key_frequencies": {"addr": 15, "mask": 15, "vlan": 15},
            "value_by_key": {
                "addr": ["10.250.18.26", "10.250.20.26", ...],
                "mask": ["255.255.255.0", "255.255.255.0", ...],
            },
            "detected_types": {
                "addr": "ipv4",
                "mask": "ipv4",
                "vlan": "integer"
            }
        }
        """
```

### Type Detection Rules

```python
TYPE_PATTERNS = {
    "ipv4_address": r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',
    "ipv4_netmask": r'^(255\.\d{1,3}\.\d{1,3}\.\d{1,3})$',
    "integer": r'^\d+$',
    "port": r'^([1-9]\d{0,4}|[1-5]\d{4}|6[0-4]\d{3}|65[0-4]\d{2}|655[0-2]\d|6553[0-5])$',
    "quoted_string": r'^"[^"]*"$',
    "flag": ["ena", "dis", "on", "off"],
    "vlan_id": lambda v: v.isdigit() and 1 <= int(v) <= 4094,
    "mac_address": r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
}
```

---

## AI Integration

### OpenAI Prompt Template

```python
ANALYSIS_PROMPT = """
You are a network configuration expert analyzing Alteon/Radware load balancer modules.

Module Path: {module_path}
Module Type: {module_type}
Instances Analyzed: {count}

Example Instances:
{examples}

Detected Patterns:
{patterns}

Tasks:
1. Provide a clear, concise description of what this module does (1-2 sentences)
2. Categorize this module using ONE of these categories:
   - system_management
   - network_layer2
   - network_layer3
   - load_balancing
   - security_ssl
   - security_access
   - monitoring
   - high_availability
   - application
   
3. Generate 5-8 relevant tags (lowercase, underscore-separated)

4. For each detected parameter, suggest a semantic placeholder name and description

5. Suggest dependencies:
   - What modules must exist BEFORE this one?
   - What modules might depend ON this one?

Respond ONLY with valid JSON in this format:
{{
  "description": "...",
  "category": "...",
  "tags": ["...", "..."],
  "parameters": {{
    "original_key": {{
      "placeholder_name": "semantic_name",
      "description": "..."
    }}
  }},
  "dependencies": {{
    "requires": ["/c/path/to/module"],
    "required_by": ["/c/path/to/module"]
  }}
}}
"""
```

### AI Client Wrapper

```python
class AIAnalyzer:
    """OpenAI GPT-4 integration for semantic analysis"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        
    def analyze_module_group(
        self, 
        module_path: str,
        modules: List[ModuleBlock],
        patterns: Dict
    ) -> Dict:
        """
        Analyze a group of modules with same path
        Returns AI-generated metadata
        """
        
        prompt = self._build_prompt(module_path, modules, patterns)
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a network configuration expert."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3  # Lower for more consistent output
        )
        
        return json.loads(response.choices[0].message.content)
```

---

## Template Generation

### Template Structure

```python
@dataclass
class TemplatedModule:
    # Identity
    module_path: str
    index_required: bool
    module_type: str  # standard, action, multiline_cert, etc.
    
    # AI-Generated Metadata
    category: str
    description: str
    tags: List[str]
    
    # Template Definition
    template: Dict[str, Any]  # {header: str, body: List[str]}
    parameters: Dict[str, ParameterSchema]
    
    # Statistical Data
    learned_defaults: Dict[str, Dict]
    examples_seen: int
    variations: List[str]
    
    # Dependencies
    dependencies: Dict[str, List[str]]  # {requires: [...], required_by: [...]}
    
    # Metadata
    created_at: str
    ai_model: str = "gpt-4"
```

### ParameterSchema

```python
@dataclass
class ParameterSchema:
    # Identity
    name: str                      # Placeholder name (e.g., "management_ip_address")
    original_key: str              # Original key from config (e.g., "addr")
    
    # Type Information
    type: str                      # ipv4, integer, string, enum, flag, etc.
    required: bool
    
    # Validation
    validation: Optional[str]      # Validation rule name
    options: Optional[List]        # For enum/flag types
    range: Optional[Tuple]         # For numeric types (min, max)
    pattern: Optional[str]         # Regex pattern
    
    # Default Handling
    default: Optional[Any]         # Most common value (if ≥70%)
    default_confidence: float      # Percentage (0.0-1.0)
    
    # Documentation
    description: str               # Human-readable explanation
    example_values: List[str]      # Actual values seen (first 5)
```

---

## Default Value Calculation

### Algorithm

```python
def calculate_defaults(values: List[str]) -> Dict:
    """
    Calculate default value based on 70% threshold
    
    Returns:
    {
        "default": "ena",           # Most common value (if ≥70%)
        "confidence": 0.85,         # Percentage
        "distribution": {           # Full distribution
            "ena": 0.85,
            "dis": 0.15
        },
        "total_samples": 20
    }
    """
    
    counter = Counter(values)
    total = len(values)
    most_common_value, most_common_count = counter.most_common(1)[0]
    confidence = most_common_count / total
    
    result = {
        "confidence": confidence,
        "distribution": {k: v/total for k, v in counter.items()},
        "total_samples": total
    }
    
    # Apply 70% threshold
    if confidence >= 0.70:
        result["default"] = most_common_value
    else:
        result["default"] = None
        
    return result
```

---

## Output Format

### Template File Structure

```json
{
  "metadata": {
    "timestamp": "2025-12-23T15:00:00",
    "phase": "2 - Templating & Normalization",
    "total_templates": 27,
    "total_instances_analyzed": 31,
    "ai_model": "gpt-4",
    "ai_calls_made": 27,
    "processing_time_seconds": 45.2
  },
  
  "templates": [
    {
      "module_path": "/c/l3/if",
      "index_required": true,
      "module_type": "standard",
      "category": "network_layer3",
      "description": "Layer 3 network interface configuration with IP addressing and VLAN association",
      "tags": ["network", "layer3", "interface", "ip", "vlan"],
      
      "template": {
        "header": "/c/l3/if {{interface_index}}",
        "body": [
          "{{interface_status}}",
          "ipver {{ip_version}}",
          "addr {{ip_address}}",
          "mask {{subnet_mask}}",
          "broad {{broadcast_address}}",
          "vlan {{vlan_id}}",
          "peer {{peer_ip_address}}"
        ]
      },
      
      "parameters": {
        "interface_index": {
          "name": "interface_index",
          "original_key": "index",
          "type": "integer",
          "required": true,
          "validation": "positive_integer",
          "description": "Unique interface identifier",
          "example_values": ["1", "2"]
        },
        "interface_status": {
          "name": "interface_status",
          "original_key": "ena/dis",
          "type": "flag",
          "required": false,
          "options": ["ena", "dis"],
          "default": "ena",
          "default_confidence": 0.93,
          "description": "Enable or disable the interface",
          "example_values": ["ena", "ena", "ena", "dis"]
        },
        "ip_version": {
          "name": "ip_version",
          "original_key": "ipver",
          "type": "enum",
          "required": true,
          "options": ["v4", "v6"],
          "default": "v4",
          "default_confidence": 0.96,
          "description": "IP protocol version (IPv4 or IPv6)",
          "example_values": ["v4", "v4", "v4"]
        },
        "ip_address": {
          "name": "ip_address",
          "original_key": "addr",
          "type": "ipv4_address",
          "required": true,
          "validation": "ipv4_address",
          "description": "IPv4 address for this interface",
          "example_values": ["10.250.18.26", "10.250.20.26"]
        },
        "subnet_mask": {
          "name": "subnet_mask",
          "original_key": "mask",
          "type": "ipv4_netmask",
          "required": true,
          "validation": "ipv4_netmask",
          "default": "255.255.255.0",
          "default_confidence": 0.85,
          "description": "Subnet mask for the interface",
          "example_values": ["255.255.255.0", "255.255.255.0"]
        },
        "broadcast_address": {
          "name": "broadcast_address",
          "original_key": "broad",
          "type": "ipv4_address",
          "required": false,
          "validation": "ipv4_address",
          "description": "Broadcast address (optional, can be auto-calculated)",
          "example_values": ["10.250.18.255", "10.250.20.255"]
        },
        "vlan_id": {
          "name": "vlan_id",
          "original_key": "vlan",
          "type": "integer",
          "required": true,
          "range": [1, 4094],
          "validation": "vlan_id",
          "description": "VLAN ID to associate with this interface",
          "example_values": ["818", "820"]
        },
        "peer_ip_address": {
          "name": "peer_ip_address",
          "original_key": "peer",
          "type": "ipv4_address",
          "required": false,
          "validation": "ipv4_address",
          "description": "Peer IP address for HA configurations",
          "example_values": ["10.250.18.27", "10.250.20.27"]
        }
      },
      
      "learned_defaults": {
        "interface_status": {
          "default": "ena",
          "confidence": 0.93,
          "distribution": {"ena": 0.93, "dis": 0.07},
          "total_samples": 15
        },
        "ip_version": {
          "default": "v4",
          "confidence": 0.96,
          "distribution": {"v4": 0.96, "v6": 0.04},
          "total_samples": 15
        },
        "subnet_mask": {
          "default": "255.255.255.0",
          "confidence": 0.85,
          "distribution": {
            "255.255.255.0": 0.85,
            "255.255.248.0": 0.15
          },
          "total_samples": 15
        }
      },
      
      "dependencies": {
        "requires": ["/c/l2/vlan"],
        "required_by": ["/c/l3/ha/floatip", "/c/slb/pip"]
      },
      
      "examples_seen": 15,
      "variations": ["basic", "with_peer", "with_broadcast"],
      
      "created_at": "2025-12-23T15:00:00",
      "ai_model": "gpt-4"
    }
  ]
}
```

---

## Error Handling

### AI Failures
- Retry with exponential backoff (3 attempts)
- Log failed modules for manual review
- Continue processing other modules
- Generate statistics on success/failure rates

### Invalid Responses
- Validate AI JSON response against schema
- Fall back to basic template if AI fails
- Log validation errors

### Missing Data
- Handle modules with insufficient instances (<3)
- Flag for manual review
- Create basic template without defaults

---

## Cost Estimation

### OpenAI API Costs (GPT-4)

**Assumptions:**
- 27 unique module paths
- Average 10 instances per path
- Average prompt: 2,000 tokens
- Average response: 500 tokens

**Calculation:**
```
Input:  27 calls × 2,000 tokens = 54,000 tokens
Output: 27 calls × 500 tokens   = 13,500 tokens

GPT-4 Pricing:
Input:  $0.03 / 1K tokens = $1.62
Output: $0.06 / 1K tokens = $0.81

Total: ~$2.50 per full processing run
```

**Optimization:**
- Cache AI responses
- Reprocess only new/changed modules
- Batch similar modules when possible

---

## Testing Strategy

### Unit Tests
- `test_value_extractor.py`: Pattern extraction logic
- `test_type_detection.py`: Type detection rules
- `test_placeholder_generation.py`: Placeholder naming
- `test_default_calculator.py`: Statistical calculations

### Integration Tests
- `test_ai_integration.py`: OpenAI API calls (mocked)
- `test_template_generation.py`: End-to-end template creation
- `test_output_format.py`: JSON schema validation

### Validation Tests
- Parse output templates
- Verify placeholder consistency
- Check required parameters
- Validate dependency references

---

## Implementation Checklist

### Prerequisites
- [ ] OpenAI API key configured
- [ ] Phase 1 output available
- [ ] Python dependencies installed

### Core Components
- [ ] `value_extractor.py` - Pattern extraction
- [ ] `ai_analyzer.py` - OpenAI integration
- [ ] `template_generator.py` - Template building
- [ ] `default_calculator.py` - Statistics
- [ ] `template_storage.py` - Output handling

### Testing
- [ ] Unit tests for each component
- [ ] Integration tests
- [ ] Validation tests
- [ ] Manual review of samples

### Documentation
- [ ] Update README with Phase 2 status
- [ ] API documentation
- [ ] Example templates
- [ ] Troubleshooting guide

---

## Success Metrics

Phase 2 is successful when:
- ✅ 100% of parsed modules converted to templates
- ✅ All parameters have semantic names
- ✅ Defaults calculated with confidence scores
- ✅ AI-generated metadata for all templates
- ✅ Dependencies suggested
- ✅ Output validates against schema
- ✅ Ready for Phase 3 (embedding)

---

## Next Phase Preview

**Phase 3: Embed & Store**
- Use template descriptions/tags for embedding
- Store in ChromaDB
- NOT raw configuration syntax
- Enable semantic search

