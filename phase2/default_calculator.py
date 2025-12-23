"""
Default Calculator - Phase 2 Component

Calculates statistical defaults from multiple module instances.
Applies 70% threshold to determine default values.
"""

from typing import Dict, List, Any
from collections import Counter


class DefaultCalculator:
    """Calculates default values based on statistical analysis"""
    
    DEFAULT_THRESHOLD = 0.70  # 70% occurrence threshold
    
    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        """
        Initialize calculator
        
        Args:
            threshold: Minimum occurrence rate to set a default (0.0-1.0)
        """
        self.threshold = threshold
        self.stats = {
            'parameters_analyzed': 0,
            'defaults_set': 0,
            'no_default': 0
        }
    
    def calculate_defaults(self, patterns: Dict) -> Dict[str, Dict]:
        """
        Calculate defaults for all parameters
        
        Args:
            patterns: Patterns dictionary from ValueExtractor
            
        Returns:
            Dictionary mapping parameter keys to default info:
            {
                "key": {
                    "default": value (or None),
                    "confidence": float,
                    "distribution": {value: percentage},
                    "total_samples": int
                }
            }
        """
        defaults = {}
        
        for key, pattern in patterns.get('patterns', {}).items():
            default_info = self._calculate_parameter_default(pattern.values)
            defaults[key] = default_info
            
            self.stats['parameters_analyzed'] += 1
            if default_info['default'] is not None:
                self.stats['defaults_set'] += 1
            else:
                self.stats['no_default'] += 1
        
        return defaults
    
    def _calculate_parameter_default(self, values: List[str]) -> Dict[str, Any]:
        """
        Calculate default for a single parameter
        
        Args:
            values: List of all values seen for this parameter
            
        Returns:
            Dictionary with default info
        """
        if not values:
            return {
                'default': None,
                'confidence': 0.0,
                'distribution': {},
                'total_samples': 0
            }
        
        # Count value frequencies
        counter = Counter(values)
        total = len(values)
        
        # Get most common value
        most_common_value, most_common_count = counter.most_common(1)[0]
        confidence = most_common_count / total
        
        # Build distribution
        distribution = {value: count / total for value, count in counter.items()}
        
        # Apply threshold
        result = {
            'confidence': confidence,
            'distribution': distribution,
            'total_samples': total
        }
        
        if confidence >= self.threshold:
            result['default'] = most_common_value
        else:
            result['default'] = None
        
        return result
    
    def apply_defaults_to_template(
        self,
        template: Any,
        defaults: Dict[str, Dict]
    ) -> None:
        """
        Apply calculated defaults to a TemplatedModule
        
        Args:
            template: TemplatedModule object
            defaults: Default info from calculate_defaults()
        """
        # Update learned_defaults field
        template.learned_defaults = defaults
        
        # Update parameter schemas with default values
        for param_name, param_schema in template.parameters.items():
            original_key = param_schema.original_key
            
            if original_key in defaults:
                default_info = defaults[original_key]
                
                param_schema.default = default_info['default']
                param_schema.default_confidence = default_info['confidence']
    
    def get_stats(self) -> Dict:
        """Get calculation statistics"""
        return self.stats.copy()
    
    def get_summary(self, defaults: Dict[str, Dict]) -> str:
        """Generate human-readable summary"""
        lines = []
        lines.append("Default Value Analysis:")
        lines.append(f"  Threshold: {self.threshold * 100}%")
        lines.append(f"  Parameters analyzed: {self.stats['parameters_analyzed']}")
        lines.append(f"  Defaults set: {self.stats['defaults_set']}")
        lines.append(f"  No default: {self.stats['no_default']}")
        lines.append("")
        
        # Show parameters with defaults
        has_defaults = [(k, v) for k, v in defaults.items() if v['default'] is not None]
        if has_defaults:
            lines.append("Parameters with defaults:")
            for key, info in sorted(has_defaults, key=lambda x: x[1]['confidence'], reverse=True):
                lines.append(
                    f"  {key:15s} = {info['default']:20s} "
                    f"({info['confidence']*100:.1f}% confidence, {info['total_samples']} samples)"
                )
        
        lines.append("")
        
        # Show parameters without defaults
        no_defaults = [(k, v) for k, v in defaults.items() if v['default'] is None]
        if no_defaults:
            lines.append("Parameters without defaults (< 70% threshold):")
            for key, info in sorted(no_defaults, key=lambda x: x[1]['confidence'], reverse=True):
                most_common = max(info['distribution'].items(), key=lambda x: x[1])
                lines.append(
                    f"  {key:15s} - Most common: {most_common[0]} "
                    f"({most_common[1]*100:.1f}%, needs {info['total_samples']} samples)"
                )
        
        return "\n".join(lines)


def test_default_calculator():
    """Test default calculator"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    
    from phase2.value_extractor import ValueExtractor
    
    # Sample modules with varying values
    sample_modules = [
        {"sub_lines": ["ena", "ipver v4", "addr 10.1.1.1", "mask 255.255.255.0"]},
        {"sub_lines": ["ena", "ipver v4", "addr 10.1.1.2", "mask 255.255.255.0"]},
        {"sub_lines": ["ena", "ipver v4", "addr 10.1.1.3", "mask 255.255.255.0"]},
        {"sub_lines": ["ena", "ipver v4", "addr 10.1.1.4", "mask 255.255.248.0"]},  # Different mask
        {"sub_lines": ["ena", "ipver v4", "addr 10.1.1.5", "mask 255.255.255.0"]},
        {"sub_lines": ["dis", "ipver v4", "addr 10.1.1.6", "mask 255.255.255.0"]},  # Disabled
        {"sub_lines": ["ena", "ipver v6", "addr 10.1.1.7", "mask 255.255.255.0"]},  # IPv6
        {"sub_lines": ["ena", "ipver v4", "addr 10.1.1.8", "mask 255.255.255.0"]},
        {"sub_lines": ["ena", "ipver v4", "addr 10.1.1.9", "mask 255.255.255.0"]},
        {"sub_lines": ["ena", "ipver v4", "addr 10.1.1.10", "mask 255.255.255.0"]},
    ]
    
    # Extract patterns
    extractor = ValueExtractor()
    patterns = extractor.extract_patterns(sample_modules)
    
    # Calculate defaults
    calculator = DefaultCalculator(threshold=0.70)
    defaults = calculator.calculate_defaults(patterns)
    
    print("=" * 70)
    print("DEFAULT CALCULATOR TEST")
    print("=" * 70)
    print()
    print(calculator.get_summary(defaults))
    print()
    print("Detailed Results:")
    for key, info in defaults.items():
        print(f"\n{key}:")
        print(f"  Default: {info['default']}")
        print(f"  Confidence: {info['confidence']*100:.1f}%")
        print(f"  Distribution:")
        for value, percentage in sorted(info['distribution'].items(), key=lambda x: x[1], reverse=True):
            print(f"    {value}: {percentage*100:.1f}%")


if __name__ == "__main__":
    test_default_calculator()
