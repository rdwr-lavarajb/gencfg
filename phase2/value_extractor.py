"""
Value Extractor - Phase 2 Component

Extracts values and patterns from parsed module blocks.
Detects parameter types and analyzes value frequencies.
"""

import re
from typing import Dict, List, Set, Tuple, Any
from collections import Counter, defaultdict
from dataclasses import dataclass


@dataclass
class ValuePattern:
    """Represents a detected value pattern"""
    key: str                        # Original key from config (e.g., "addr")
    detected_type: str              # Detected type (ipv4, integer, etc.)
    values: List[str]               # All values seen
    frequency: int                  # How many times this key appears
    occurrence_rate: float          # Percentage of modules with this key
    is_required: bool               # Present in >80% of instances
    example_values: List[str]       # First 5 unique values


class ValueExtractor:
    """Extracts values and patterns from parsed module blocks"""
    
    # Type detection patterns
    TYPE_PATTERNS = {
        'ipv4_address': re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'),
        'ipv4_netmask': re.compile(r'^255\.\d{1,3}\.\d{1,3}\.\d{1,3}$'),
        'ipv6_address': re.compile(r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'),
        'integer': re.compile(r'^\d+$'),
        'port': re.compile(r'^([1-9]\d{0,4}|[1-5]\d{4}|6[0-4]\d{3}|65[0-4]\d{2}|655[0-2]\d|6553[0-5])$'),
        'quoted_string': re.compile(r'^"[^"]*"$'),
        'hex_string': re.compile(r'^[0-9a-fA-F]+$'),
        'mac_address': re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'),
    }
    
    # Special value sets
    FLAG_VALUES = {'ena', 'dis', 'on', 'off', 'enabled', 'disabled', 'e', 'd'}
    IP_VERSION_VALUES = {'v4', 'v6', 'ipv4', 'ipv6'}
    
    def __init__(self):
        self.stats = {
            'modules_processed': 0,
            'keys_detected': 0,
            'types_detected': set()
        }
    
    def extract_patterns(self, modules: List[Dict]) -> Dict[str, Any]:
        """
        Extract value patterns from a group of modules with same path
        
        Args:
            modules: List of module dicts from Phase 1 output
            
        Returns:
            Dictionary containing:
            - key_frequencies: How often each key appears
            - value_by_key: All values for each key
            - detected_types: Type detection for each key
            - patterns: ValuePattern objects for each key
        """
        self.stats['modules_processed'] = len(modules)
        
        # Collect all key-value pairs
        key_values = defaultdict(list)  # key -> [values]
        key_frequencies = Counter()      # key -> count
        
        for module in modules:
            sub_lines = module.get('sub_lines', [])
            
            for line in sub_lines:
                parsed = self._parse_sub_line(line)
                if parsed:
                    key, value = parsed
                    key_values[key].append(value)
                    key_frequencies[key] += 1
        
        self.stats['keys_detected'] = len(key_values)
        
        # Detect types for each key
        detected_types = {}
        patterns = {}
        
        for key, values in key_values.items():
            detected_type = self._detect_type(key, values)
            detected_types[key] = detected_type
            self.stats['types_detected'].add(detected_type)
            
            # Create pattern object
            unique_values = list(dict.fromkeys(values))  # Preserve order, remove duplicates
            occurrence_rate = key_frequencies[key] / len(modules)
            
            patterns[key] = ValuePattern(
                key=key,
                detected_type=detected_type,
                values=values,
                frequency=key_frequencies[key],
                occurrence_rate=occurrence_rate,
                is_required=occurrence_rate > 0.8,
                example_values=unique_values[:5]
            )
        
        return {
            'key_frequencies': dict(key_frequencies),
            'value_by_key': dict(key_values),
            'detected_types': detected_types,
            'patterns': patterns,
            'total_modules': len(modules),
            'stats': self.stats
        }
    
    def _parse_sub_line(self, line: str) -> Tuple[str, str] | None:
        """
        Parse a sub-line into key-value pair
        
        Examples:
            "addr 10.250.4.26" -> ("addr", "10.250.4.26")
            "ena" -> ("ena", "ena")  # Flag without value
            "name \"server1\"" -> ("name", "\"server1\"")
        """
        line = line.strip()
        if not line:
            return None
        
        parts = line.split(None, 1)  # Split on first whitespace
        
        if len(parts) == 1:
            # Flag without value (ena, dis, on, off)
            return (parts[0], parts[0])
        else:
            # Key-value pair
            return (parts[0], parts[1])
    
    def _detect_type(self, key: str, values: List[str]) -> str:
        """
        Detect the type of a parameter based on key name and values
        
        Returns type string: ipv4_address, integer, flag, etc.
        """
        # If all values are the same and in FLAG_VALUES, it's a flag
        unique_values = set(values)
        if unique_values.issubset(self.FLAG_VALUES):
            return 'flag'
        
        # Check for IP version
        if unique_values.issubset(self.IP_VERSION_VALUES):
            return 'ip_version'
        
        # Check for VLAN ID (based on key name and range)
        if key == 'vlan' and all(v.isdigit() and 1 <= int(v) <= 4094 for v in values):
            return 'vlan_id'
        
        # Check for port (based on key name or value range)
        if key in ['port', 'dport', 'rport', 'sport'] and all(
            v.isdigit() and 1 <= int(v) <= 65535 for v in values
        ):
            return 'port'
        
        # Special checks based on key name (before regex to override)
        if key in ['mask', 'broad']:
            return 'ipv4_netmask'
        
        if key in ['addr', 'rip', 'vip', 'gw', 'peer', 'prima', 'secon', 'prisrv', 'secsrv']:
            return 'ipv4_address'
        
        if key in ['name', 'uname', 'wcomm', 'rcomm', 'index']:
            return 'string'
        
        # Check patterns against first value (assume consistent types)
        sample_value = values[0]
        
        # Check regex patterns
        for type_name, pattern in self.TYPE_PATTERNS.items():
            if pattern.match(sample_value):
                return type_name
        
        # Check if all values are numeric
        if all(v.isdigit() for v in values):
            return 'integer'
        
        # Default to string
        return 'string'
    
    def get_summary(self, patterns: Dict[str, ValuePattern]) -> str:
        """Generate a human-readable summary of extracted patterns"""
        lines = []
        lines.append(f"Total Keys Detected: {len(patterns)}")
        lines.append(f"Modules Analyzed: {self.stats['modules_processed']}")
        lines.append("")
        lines.append("Parameters:")
        
        for key, pattern in sorted(patterns.items()):
            req_flag = "REQUIRED" if pattern.is_required else "optional"
            lines.append(f"  {key:15s} ({pattern.detected_type:15s}) [{req_flag}] - {pattern.frequency} occurrences")
            lines.append(f"                Examples: {', '.join(pattern.example_values[:3])}")
        
        return "\n".join(lines)


def test_value_extractor():
    """Quick test of value extractor"""
    
    # Sample modules from Phase 1
    sample_modules = [
        {
            "module_path": "/c/l3/if",
            "index": "1",
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
    
    extractor = ValueExtractor()
    result = extractor.extract_patterns(sample_modules)
    
    print("=" * 70)
    print("VALUE EXTRACTOR TEST")
    print("=" * 70)
    print()
    print(extractor.get_summary(result['patterns']))
    print()
    print("Detected Types:", sorted(result['stats']['types_detected']))


if __name__ == "__main__":
    test_value_extractor()
