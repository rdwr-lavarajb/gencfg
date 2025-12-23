"""
AI Analyzer - Phase 2 Component

Integrates with OpenAI GPT-4 for semantic analysis and metadata generation.
"""

import json
import os
from typing import Dict, List, Any
from dataclasses import dataclass
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from project root
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass  # python-dotenv not installed, will rely on system env vars


@dataclass
class AIAnalysisResult:
    """Result from AI analysis"""
    description: str
    category: str
    tags: List[str]
    parameter_mappings: Dict[str, Dict[str, str]]  # original_key -> {placeholder_name, description}
    dependencies: Dict[str, List[str]]  # {requires: [...], required_by: [...]}
    raw_response: Dict  # Full AI response


class AIAnalyzer:
    """OpenAI GPT-4 integration for semantic analysis"""
    
    # Module categories for AI prompts
    VALID_CATEGORIES = [
        'system_management',
        'network_layer2',
        'network_layer3',
        'load_balancing',
        'security_ssl',
        'security_access',
        'monitoring',
        'high_availability',
        'application'
    ]
    
    def __init__(self, api_key: str = None):
        """
        Initialize AI Analyzer
        
        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key parameter")
        
        # Initialize OpenAI client
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        self.stats = {
            'calls_made': 0,
            'tokens_used': 0,
            'errors': 0
        }
    
    def analyze_module_group(
        self,
        module_path: str,
        modules: List[Dict],
        patterns: Dict[str, Any]
    ) -> AIAnalysisResult:
        """
        Analyze a group of modules with the same path
        
        Args:
            module_path: Module path (e.g., "/c/l3/if")
            modules: List of module instances
            patterns: Detected patterns from ValueExtractor
            
        Returns:
            AIAnalysisResult with metadata
        """
        prompt = self._build_prompt(module_path, modules, patterns)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are a network configuration expert specializing in Alteon/Radware load balancers."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3  # Lower temperature for consistent output
            )
            
            self.stats['calls_made'] += 1
            self.stats['tokens_used'] += response.usage.total_tokens
            
            # Parse response
            content = response.choices[0].message.content
            ai_data = json.loads(content)
            
            # Validate and extract
            return AIAnalysisResult(
                description=ai_data.get('description', ''),
                category=ai_data.get('category', 'system_management'),
                tags=ai_data.get('tags', []),
                parameter_mappings=ai_data.get('parameters', {}),
                dependencies=ai_data.get('dependencies', {'requires': [], 'required_by': []}),
                raw_response=ai_data
            )
            
        except Exception as e:
            self.stats['errors'] += 1
            print(f"AI Analysis Error for {module_path}: {e}")
            # Return fallback result
            return self._fallback_result(module_path, patterns)
    
    def _build_prompt(self, module_path: str, modules: List[Dict], patterns: Dict) -> str:
        """Build the prompt for AI analysis"""
        
        # Get first 3 examples
        examples = []
        for i, module in enumerate(modules[:3], 1):
            example_lines = [f"Example {i}:"]
            example_lines.append(f"{module_path} {module.get('index', '')}")
            for line in module.get('sub_lines', [])[:10]:  # Limit lines
                example_lines.append(f"  {line}")
            examples.append("\n".join(example_lines))
        
        examples_text = "\n\n".join(examples)
        
        # Build pattern summary
        pattern_summary = []
        for key, pattern in patterns.get('patterns', {}).items():
            pattern_summary.append(
                f"  - {key}: {pattern.detected_type} "
                f"(occurs in {pattern.frequency}/{patterns['total_modules']} instances)"
            )
        patterns_text = "\n".join(pattern_summary)
        
        prompt = f"""
You are a network configuration expert analyzing Alteon/Radware load balancer modules.

Module Path: {module_path}
Module Type: {modules[0].get('module_type', 'standard')}
Instances Analyzed: {len(modules)}

Example Instances:
{examples_text}

Detected Patterns:
{patterns_text}

Tasks:
1. Provide a clear, concise description of what this module does (1-2 sentences)

2. Categorize this module using ONE of these categories:
   - system_management: Management interface, users, access control
   - network_layer2: VLANs, ports, spanning tree, switching
   - network_layer3: Interfaces, routing, gateways, IP configuration
   - load_balancing: Virtual servers, real servers, groups, services
   - security_ssl: Certificates, SSL policies, encryption
   - security_access: SNMP, SSH, authentication, authorization
   - monitoring: Syslog, NTP, health checks, logging
   - high_availability: Sync, floating IPs, peer configuration
   - application: Scripts, caching, compression, application logic

3. Generate 5-8 relevant tags (lowercase, underscore-separated)

4. For each detected parameter, suggest a semantic placeholder name and description.
   Use descriptive names like "management_ip_address" not "mgmt_ip".
   Example: For key "addr" suggest "ip_address" or "management_ip_address"

5. Suggest dependencies (module paths that must exist before/after this one):
   - What modules must exist BEFORE this one can be configured?
   - What modules might depend ON this one?

Respond ONLY with valid JSON in this EXACT format:
{{
  "description": "Brief description here",
  "category": "one_of_the_valid_categories",
  "tags": ["tag1", "tag2", "tag3"],
  "parameters": {{
    "original_key": {{
      "placeholder_name": "semantic_name",
      "description": "What this parameter controls"
    }}
  }},
  "dependencies": {{
    "requires": ["/c/path/to/required/module"],
    "required_by": ["/c/path/to/dependent/module"]
  }}
}}
"""
        return prompt
    
    def _fallback_result(self, module_path: str, patterns: Dict) -> AIAnalysisResult:
        """Generate fallback result if AI fails"""
        # Simple fallback based on path
        path_parts = module_path.split('/')
        
        category = 'system_management'
        if 'l3' in path_parts:
            category = 'network_layer3'
        elif 'l2' in path_parts:
            category = 'network_layer2'
        elif 'slb' in path_parts:
            category = 'load_balancing'
        elif 'ssl' in path_parts:
            category = 'security_ssl'
        
        # Create basic parameter mappings
        param_mappings = {}
        for key, pattern in patterns.get('patterns', {}).items():
            param_mappings[key] = {
                "placeholder_name": f"{key}_value",
                "description": f"Value for {key}"
            }
        
        return AIAnalysisResult(
            description=f"Configuration module for {module_path}",
            category=category,
            tags=path_parts[2:],  # Use path parts as tags
            parameter_mappings=param_mappings,
            dependencies={'requires': [], 'required_by': []},
            raw_response={}
        )
    
    def get_stats(self) -> Dict:
        """Get statistics about AI usage"""
        return self.stats.copy()


def test_ai_analyzer():
    """Test AI analyzer with sample data"""
    import os
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set. Skipping AI test.")
        print("   To test AI integration, set your API key:")
        print("   export OPENAI_API_KEY='your-key-here'  # Linux/Mac")
        print("   $env:OPENAI_API_KEY='your-key-here'  # PowerShell")
        return
    
    # Sample data
    sample_modules = [
        {
            "module_path": "/c/l3/if",
            "index": "1",
            "module_type": "standard",
            "sub_lines": [
                "ena",
                "ipver v4",
                "addr 10.250.18.26",
                "mask 255.255.255.0",
                "vlan 818"
            ]
        },
        {
            "module_path": "/c/l3/if",
            "index": "2",
            "module_type": "standard",
            "sub_lines": [
                "ena",
                "ipver v4",
                "addr 10.250.20.26",
                "mask 255.255.255.0",
                "vlan 820",
                "peer 10.250.20.27"
            ]
        }
    ]
    
    # Mock patterns (would come from ValueExtractor)
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from phase2.value_extractor import ValueExtractor
    extractor = ValueExtractor()
    result = extractor.extract_patterns(sample_modules)
    
    print("=" * 70)
    print("AI ANALYZER TEST")
    print("=" * 70)
    print()
    
    try:
        analyzer = AIAnalyzer(api_key)
        ai_result = analyzer.analyze_module_group(
            module_path="/c/l3/if",
            modules=sample_modules,
            patterns=result
        )
        
        print("✅ AI Analysis Successful!")
        print()
        print(f"Description: {ai_result.description}")
        print(f"Category: {ai_result.category}")
        print(f"Tags: {', '.join(ai_result.tags)}")
        print()
        print("Parameter Mappings:")
        for orig_key, mapping in ai_result.parameter_mappings.items():
            print(f"  {orig_key:15s} -> {mapping['placeholder_name']}")
            print(f"                     {mapping['description']}")
        print()
        print(f"Dependencies: {ai_result.dependencies}")
        print()
        print(f"Stats: {analyzer.get_stats()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_ai_analyzer()
