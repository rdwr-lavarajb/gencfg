"""
Phase 5: Parameter Matcher
Matches extracted values to template parameters.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import re


@dataclass
class ValueAssignment:
    """Assignment of a value to a parameter."""
    parameter_name: str
    parameter_type: str
    value: Any
    source: str  # 'user', 'default', 'inferred'
    confidence: float
    original_param_key: str


class ParameterMatcher:
    """Matches extracted values to template parameters intelligently."""
    
    # Type compatibility mappings
    TYPE_COMPATIBILITY = {
        'ipv4_address': ['ipv4', 'ipv4_address'],
        'ipv4_netmask': ['ipv4', 'ipv4_netmask'],
        'port': ['port', 'integer'],
        'vlan_id': ['vlan', 'vlan_id', 'integer'],
        'integer': ['integer', 'port', 'vlan_id'],
        'string': ['string', 'quoted_string'],
        'flag': ['flag'],
    }
    
    def match(
        self,
        template_parameters: Dict[str, Any],
        extracted_values: Dict[str, List[Any]],
        defaults: Dict[str, Any] = None,
        use_defaults: bool = True,
        auto_fill_high_confidence: bool = True
    ) -> List[ValueAssignment]:
        """
        Match extracted values to template parameters.
        
        Args:
            template_parameters: Template parameter definitions
            extracted_values: Values extracted from requirements
            defaults: Learned defaults from template
            use_defaults: Whether to use defaults for missing values
            auto_fill_high_confidence: Auto-fill parameters with >90% confidence defaults
            
        Returns:
            List of ValueAssignment objects
        """
        assignments = []
        defaults = defaults or {}
        
        # Track which values have been used
        used_values = {vtype: set() for vtype in extracted_values.keys()}
        
        # First pass: Exact type matches with keyword hints
        for param_name, param_info in template_parameters.items():
            param_type = param_info.get('type', 'string')
            
            # Check if this parameter has a very high confidence default
            # that should be auto-filled even if user didn't specify
            if auto_fill_high_confidence and param_name in defaults:
                default_info = defaults[param_name]
                confidence = default_info.get('confidence', 0.0)
                
                # Auto-fill parameters with very high confidence (>90%)
                # Common examples: ip_version=v4, enabled_status=ena
                if confidence >= 0.9:
                    assignments.append(ValueAssignment(
                        parameter_name=param_name,
                        parameter_type=param_type,
                        value=default_info.get('default'),
                        source='default',
                        confidence=confidence,
                        original_param_key=param_info.get('original_key', param_name)
                    ))
                    continue
            
            # Try to match with extracted values
            assignment = self._match_parameter(
                param_name,
                param_info,
                extracted_values,
                used_values
            )
            
            if assignment:
                assignments.append(assignment)
                continue
            
            # No user value found - try defaults with lower confidence
            if use_defaults and param_name in defaults:
                default_info = defaults[param_name]
                confidence = default_info.get('confidence', 0.5)
                
                # Use defaults with reasonable confidence for optional params
                if confidence >= 0.7 or not param_info.get('required', False):
                    assignments.append(ValueAssignment(
                        parameter_name=param_name,
                        parameter_type=param_type,
                        value=default_info.get('default'),
                        source='default',
                        confidence=confidence,
                        original_param_key=param_info.get('original_key', param_name)
                    ))
        
        return assignments
    
    def _match_parameter(
        self,
        param_name: str,
        param_info: Dict[str, Any],
        extracted_values: Dict[str, List[Any]],
        used_values: Dict[str, set]
    ) -> Optional[ValueAssignment]:
        """Match a single parameter to extracted values."""
        param_type = param_info.get('type', 'string')
        
        # Find compatible value types
        compatible_types = self._get_compatible_types(param_type)
        
        # Score all available values
        best_match = None
        best_score = 0.0
        best_value_type = None
        best_value_idx = None
        
        for value_type in compatible_types:
            if value_type not in extracted_values:
                continue
            
            for idx, extracted in enumerate(extracted_values[value_type]):
                # Skip if already used
                if idx in used_values[value_type]:
                    continue
                
                # Get the actual value
                value = extracted.value if hasattr(extracted, 'value') else extracted
                
                # Calculate match score
                score = self._calculate_match_score(
                    param_name,
                    param_info,
                    value,
                    value_type,
                    extracted
                )
                
                if score > best_score:
                    best_score = score
                    best_match = value
                    best_value_type = value_type
                    best_value_idx = idx
        
        # If we found a good match, create assignment
        if best_match and best_score >= 0.5:
            # Mark value as used
            if best_value_type and best_value_idx is not None:
                used_values[best_value_type].add(best_value_idx)
            
            return ValueAssignment(
                parameter_name=param_name,
                parameter_type=param_type,
                value=best_match,
                source='user',
                confidence=best_score,
                original_param_key=param_info.get('original_key', param_name)
            )
        
        return None
    
    def _get_compatible_types(self, param_type: str) -> List[str]:
        """Get list of value types compatible with parameter type."""
        return self.TYPE_COMPATIBILITY.get(param_type, [param_type, 'string'])
    
    def _calculate_match_score(
        self,
        param_name: str,
        param_info: Dict[str, Any],
        value: Any,
        value_type: str,
        extracted: Any
    ) -> float:
        """
        Calculate how well a value matches a parameter.
        
        Scoring factors:
        - Type compatibility (0.3)
        - Keyword matching in parameter name (0.4)
        - Context from extraction (0.2)
        - Value validation (0.1)
        """
        score = 0.0
        
        # Extract keywords from parameter name first (needed for semantic matching)
        param_keywords = self._extract_keywords(param_name)
        
        # 1. Type compatibility (base score)
        param_type = param_info.get('type', 'string')
        if value_type == param_type:
            score += 0.3  # Exact type match
        elif value_type in self.TYPE_COMPATIBILITY.get(param_type, []):
            # Check if value type semantically matches parameter name
            # E.g., 'port' value type for 'real_port' parameter should score higher
            if value_type in param_keywords:
                score += 0.35  # Semantic match - boost compatible type
            else:
                score += 0.2  # Regular compatible type
        else:
            score += 0.1  # Generic match
        
        # 2. Keyword matching in parameter name
        # Check context if available
        context = ""
        if hasattr(extracted, 'context'):
            context = extracted.context.lower()
        
        # Score based on keyword overlap
        keyword_score = 0.0
        for keyword in param_keywords:
            if keyword in context or keyword in str(value).lower():
                keyword_score += 0.1
        
        score += min(keyword_score, 0.4)
        
        # 3. Context relevance
        if hasattr(extracted, 'confidence'):
            # Use extraction confidence as context score
            score += extracted.confidence * 0.2
        else:
            score += 0.1
        
        # 4. Value validation
        if self._validate_value(value, param_info):
            score += 0.1
        
        return min(score, 1.0)
    
    def _extract_keywords(self, param_name: str) -> List[str]:
        """Extract keywords from parameter name."""
        # First split on underscores
        parts = param_name.split('_')
        keywords = []
        
        # Then split each part on camelCase
        for part in parts:
            camel_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', part)
            keywords.extend([p.lower() for p in camel_parts if len(p) > 2])
        
        return keywords
    
    def _validate_value(self, value: Any, param_info: Dict[str, Any]) -> bool:
        """Validate value against parameter constraints."""
        param_type = param_info.get('type', 'string')
        
        # Range validation
        if param_type in ['port', 'integer', 'vlan_id']:
            try:
                num_value = int(value)
                value_range = param_info.get('range')
                if value_range:
                    return value_range[0] <= num_value <= value_range[1]
                return True
            except (ValueError, TypeError):
                return False
        
        # IP validation
        if param_type in ['ipv4_address', 'ipv4_netmask']:
            parts = str(value).split('.')
            if len(parts) != 4:
                return False
            try:
                return all(0 <= int(p) <= 255 for p in parts)
            except (ValueError, TypeError):
                return False
        
        # Options validation
        options = param_info.get('options')
        if options:
            return value in options
        
        return True
    
    def assign_indexed_values(
        self,
        template_parameters: Dict[str, Any],
        value_lists: Dict[str, List[Any]],
        index_count: int
    ) -> List[List[ValueAssignment]]:
        """
        Create assignments for indexed modules (multiple instances).
        
        Args:
            template_parameters: Template parameter definitions
            value_lists: Lists of values for each parameter type
            index_count: Number of instances to create
            
        Returns:
            List of assignment lists (one per instance)
        """
        all_assignments = []
        
        for index in range(index_count):
            assignments = []
            
            for param_name, param_info in template_parameters.items():
                param_type = param_info.get('type', 'string')
                
                # Try to get value from appropriate list
                value = None
                compatible_types = self._get_compatible_types(param_type)
                
                for value_type in compatible_types:
                    if value_type in value_lists:
                        values = value_lists[value_type]
                        if index < len(values):
                            value = values[index]
                            break
                
                if value:
                    assignments.append(ValueAssignment(
                        parameter_name=param_name,
                        parameter_type=param_type,
                        value=value,
                        source='user',
                        confidence=0.9,
                        original_param_key=param_info.get('original_key', param_name)
                    ))
            
            all_assignments.append(assignments)
        
        return all_assignments
