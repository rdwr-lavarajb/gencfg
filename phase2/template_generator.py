"""
Template Generator - Phase 2 Component

Generates templates with placeholders from parsed modules and AI analysis.
Builds ParameterSchema for each parameter.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
import re


@dataclass
class ParameterSchema:
    """Schema for a single parameter"""
    name: str                          # Placeholder name (e.g., "management_ip_address")
    original_key: str                  # Original key from config (e.g., "addr")
    type: str                          # Parameter type (ipv4, integer, etc.)
    required: bool                     # Is this parameter mandatory?
    validation: Optional[str] = None   # Validation rule name
    options: Optional[List] = None     # For enum/flag types
    range: Optional[Tuple] = None      # For numeric types (min, max)
    pattern: Optional[str] = None      # Regex pattern
    default: Optional[Any] = None      # Most common value (if ≥70%)
    default_confidence: float = 0.0    # Percentage (0.0-1.0)
    description: str = ""              # Human-readable explanation
    example_values: List[str] = field(default_factory=list)  # Actual values seen


@dataclass
class TemplatedModule:
    """Complete template representation of a module"""
    # Identity
    module_path: str
    index_required: bool
    module_type: str  # standard, action, multiline_cert, etc.
    
    # AI-Generated Metadata
    category: str
    description: str
    tags: List[str]
    
    # Template Definition
    template: Dict[str, Any]  # {header: str, body: List[str] or str}
    parameters: Dict[str, ParameterSchema]
    
    # Statistical Data
    learned_defaults: Dict[str, Dict] = field(default_factory=dict)
    examples_seen: int = 0
    variations: List[str] = field(default_factory=list)
    
    # Dependencies
    dependencies: Dict[str, List[str]] = field(default_factory=lambda: {'requires': [], 'required_by': []})
    
    # Metadata
    created_at: str = ""
    ai_model: str = "gpt-4-turbo"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert ParameterSchema objects to dicts
        result['parameters'] = {
            k: asdict(v) for k, v in self.parameters.items()
        }
        return result


class TemplateGenerator:
    """Generates templates from parsed modules and AI analysis"""
    
    def __init__(self):
        self.stats = {
            'templates_generated': 0,
            'parameters_processed': 0,
            'multiline_modules': 0
        }
    
    def generate_template(
        self,
        module_path: str,
        modules: List[Dict],
        patterns: Dict,
        ai_analysis: Any
    ) -> TemplatedModule:
        """
        Generate a complete template from analysis results
        
        Args:
            module_path: Module path (e.g., "/c/l3/if")
            modules: List of module instances
            patterns: Value patterns from ValueExtractor
            ai_analysis: AIAnalysisResult from AIAnalyzer
            
        Returns:
            TemplatedModule ready for storage
        """
        first_module = modules[0]
        module_type = first_module.get('module_type', 'standard')
        
        # Determine if index is required
        index_required = first_module.get('index') is not None
        
        # Build parameter schemas
        parameters = self._build_parameter_schemas(patterns, ai_analysis)
        
        # Generate template structure
        if module_type == 'multiline_cert':
            template = self._generate_cert_template(first_module, parameters)
        elif module_type == 'multiline_script':
            template = self._generate_script_template(first_module, parameters)
        elif module_type == 'action':
            template = self._generate_action_template(first_module, parameters)
        else:
            template = self._generate_standard_template(module_path, first_module, parameters, index_required)
        
        # Detect variations
        variations = self._detect_variations(modules)
        
        # Create templated module
        templated = TemplatedModule(
            module_path=module_path,
            index_required=index_required,
            module_type=module_type,
            category=ai_analysis.category,
            description=ai_analysis.description,
            tags=ai_analysis.tags,
            template=template,
            parameters=parameters,
            examples_seen=len(modules),
            variations=variations,
            dependencies=ai_analysis.dependencies
        )
        
        self.stats['templates_generated'] += 1
        self.stats['parameters_processed'] += len(parameters)
        if module_type in ['multiline_cert', 'multiline_script']:
            self.stats['multiline_modules'] += 1
        
        return templated
    
    def _build_parameter_schemas(self, patterns: Dict, ai_analysis: Any) -> Dict[str, ParameterSchema]:
        """Build parameter schemas from patterns and AI analysis"""
        schemas = {}
        
        for key, pattern in patterns.get('patterns', {}).items():
            # Get AI mapping for this key
            ai_param = ai_analysis.parameter_mappings.get(key, {})
            placeholder_name = ai_param.get('placeholder_name', f"{key}_value")
            param_description = ai_param.get('description', f"Value for {key}")
            
            # Determine validation rule based on type
            validation = self._get_validation_rule(pattern.detected_type)
            
            # Build schema
            schema = ParameterSchema(
                name=placeholder_name,
                original_key=key,
                type=pattern.detected_type,
                required=pattern.is_required,
                validation=validation,
                description=param_description,
                example_values=pattern.example_values
            )
            
            # Add type-specific attributes
            if pattern.detected_type == 'flag':
                schema.options = list(set(pattern.values))
            elif pattern.detected_type == 'ip_version':
                schema.options = list(set(pattern.values))
            elif pattern.detected_type == 'vlan_id':
                schema.range = (1, 4094)
            elif pattern.detected_type == 'port':
                schema.range = (1, 65535)
            
            schemas[placeholder_name] = schema
        
        return schemas
    
    def _get_validation_rule(self, param_type: str) -> str:
        """Get validation rule name for parameter type"""
        validation_map = {
            'ipv4_address': 'ipv4_address',
            'ipv4_netmask': 'ipv4_netmask',
            'ipv6_address': 'ipv6_address',
            'port': 'port_number',
            'vlan_id': 'vlan_id',
            'integer': 'positive_integer',
            'mac_address': 'mac_address'
        }
        return validation_map.get(param_type, 'none')
    
    def _generate_standard_template(
        self,
        module_path: str,
        module: Dict,
        parameters: Dict[str, ParameterSchema],
        index_required: bool
    ) -> Dict:
        """Generate template for standard module"""
        # Build header
        if index_required:
            header = f"{module_path} {{{{interface_index}}}}" if 'interface' in module_path else f"{module_path} {{{{index}}}}"
        else:
            header = module_path
        
        # Build body with placeholders
        body = []
        sub_lines = module.get('sub_lines', [])
        
        for line in sub_lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse the line
            parts = line.split(None, 1)
            if len(parts) == 1:
                # Flag without value
                key = parts[0]
                placeholder = self._find_placeholder_for_key(key, parameters)
                if placeholder:
                    body.append(f"{{{{{placeholder}}}}}")
                else:
                    body.append(line)
            else:
                # Key-value pair
                key, value = parts
                placeholder = self._find_placeholder_for_key(key, parameters)
                if placeholder:
                    body.append(f"{key} {{{{{placeholder}}}}}")
                else:
                    body.append(line)
        
        return {
            'header': header,
            'body': body
        }
    
    def _generate_cert_template(self, module: Dict, parameters: Dict) -> Dict:
        """Generate template for certificate module"""
        module_path = module.get('module_path', '')
        metadata = module.get('multiline_metadata', {})
        cert_name = metadata.get('cert_name', 'certificate_name')
        
        return {
            'header': f'{module_path} "{{{{certificate_name}}}}" text',
            'body': '{{certificate_content}}'
        }
    
    def _generate_script_template(self, module: Dict, parameters: Dict) -> Dict:
        """Generate template for script module"""
        module_path = module.get('module_path', '')
        index = module.get('index', '')
        
        body = [
            '{{script_status}}',
            'import text',
            '{{script_content}}',
            '-----END'
        ]
        
        return {
            'header': f'{module_path} {{{{script_id}}}}',
            'body': body
        }
    
    def _generate_action_template(self, module: Dict, parameters: Dict) -> Dict:
        """Generate template for action command module"""
        raw_lines = module.get('raw_lines', [])
        if raw_lines:
            header_line = raw_lines[0]
            # Replace values with placeholders based on parameters
            for param_name, param in parameters.items():
                # Simple replacement (can be enhanced)
                for example in param.example_values:
                    header_line = header_line.replace(example, f"{{{{{param_name}}}}}")
            return {'header': header_line}
        
        return {'header': module.get('module_path', '')}
    
    def _find_placeholder_for_key(self, key: str, parameters: Dict[str, ParameterSchema]) -> Optional[str]:
        """Find placeholder name for original key"""
        for placeholder_name, param in parameters.items():
            if param.original_key == key:
                return placeholder_name
        return None
    
    def _detect_variations(self, modules: List[Dict]) -> List[str]:
        """Detect configuration variations across modules"""
        variations = set()
        
        # Collect all keys across modules
        all_keys = set()
        for module in modules:
            for line in module.get('sub_lines', []):
                parts = line.strip().split(None, 1)
                if parts:
                    all_keys.add(parts[0])
        
        # Check for optional parameters
        for module in modules:
            module_keys = set()
            for line in module.get('sub_lines', []):
                parts = line.strip().split(None, 1)
                if parts:
                    module_keys.add(parts[0])
            
            # Determine variation type
            if 'peer' in module_keys:
                variations.add('with_peer')
            if 'broad' in module_keys:
                variations.add('with_broadcast')
            if len(module_keys) < len(all_keys) * 0.5:
                variations.add('minimal')
            elif len(module_keys) > len(all_keys) * 0.8:
                variations.add('full')
        
        return sorted(list(variations)) if variations else ['standard']
    
    def get_stats(self) -> Dict:
        """Get generation statistics"""
        return self.stats.copy()


def test_template_generator():
    """Test template generator"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    
    from phase2.value_extractor import ValueExtractor
    from phase2.ai_analyzer import AIAnalyzer, AIAnalysisResult
    
    # Sample data
    sample_modules = [
        {
            "module_path": "/c/l3/if",
            "index": "1",
            "module_type": "standard",
            "sub_lines": ["ena", "ipver v4", "addr 10.250.18.26", "mask 255.255.255.0", "vlan 818"]
        },
        {
            "module_path": "/c/l3/if",
            "index": "2",
            "module_type": "standard",
            "sub_lines": ["ena", "ipver v4", "addr 10.250.20.26", "mask 255.255.255.0", "vlan 820", "peer 10.250.20.27"]
        }
    ]
    
    # Extract patterns
    extractor = ValueExtractor()
    patterns = extractor.extract_patterns(sample_modules)
    
    # Mock AI analysis
    ai_analysis = AIAnalysisResult(
        description="Layer 3 interface configuration",
        category="network_layer3",
        tags=["layer3", "ip", "vlan"],
        parameter_mappings={
            "ena": {"placeholder_name": "interface_enabled", "description": "Enable interface"},
            "ipver": {"placeholder_name": "ip_version", "description": "IP version"},
            "addr": {"placeholder_name": "ip_address", "description": "IP address"},
            "mask": {"placeholder_name": "subnet_mask", "description": "Subnet mask"},
            "vlan": {"placeholder_name": "vlan_id", "description": "VLAN ID"},
            "peer": {"placeholder_name": "peer_ip_address", "description": "Peer IP"}
        },
        dependencies={'requires': ['/c/l2/vlan'], 'required_by': []},
        raw_response={}
    )
    
    # Generate template
    generator = TemplateGenerator()
    template = generator.generate_template(
        module_path="/c/l3/if",
        modules=sample_modules,
        patterns=patterns,
        ai_analysis=ai_analysis
    )
    
    print("=" * 70)
    print("TEMPLATE GENERATOR TEST")
    print("=" * 70)
    print()
    print(f"Module: {template.module_path}")
    print(f"Category: {template.category}")
    print(f"Description: {template.description}")
    print()
    print("Template:")
    print(f"  Header: {template.template['header']}")
    print(f"  Body:")
    for line in template.template['body']:
        print(f"    {line}")
    print()
    print("Parameters:")
    for name, param in template.parameters.items():
        req = "REQUIRED" if param.required else "optional"
        print(f"  {name:20s} ({param.type:15s}) [{req}]")
        print(f"                       Original: {param.original_key}")
        print(f"                       {param.description}")
    print()
    print(f"Variations: {template.variations}")
    print(f"Examples Seen: {template.examples_seen}")
    print()
    print(f"Stats: {generator.get_stats()}")


if __name__ == "__main__":
    test_template_generator()
