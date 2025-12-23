"""
Phase 6: Type Checker
Validates parameter types and value constraints.
"""

from typing import List, Dict, Any
from .syntax_validator import ValidationError


class TypeChecker:
    """Validates parameter types and constraints."""
    
    # Type definitions
    TYPE_VALIDATORS = {
        'ipv4_address': lambda v: TypeChecker._validate_ipv4(v),
        'port': lambda v: TypeChecker._validate_port(v),
        'integer': lambda v: TypeChecker._validate_integer(v),
        'boolean': lambda v: v.lower() in ['true', 'false', 'ena', 'dis', '0', '1', 'on', 'off'],
        'string': lambda v: True,  # Always valid
    }
    
    # Parameter type mappings (learned from templates)
    PARAM_TYPES = {
        'vip': 'ipv4_address',
        'rip': 'ipv4_address',
        'ip': 'ipv4_address',
        'virtual_ip_address': 'ipv4_address',
        'real_ip': 'ipv4_address',
        'port': 'port',
        'rport': 'port',
        'sport': 'port',
        'real_port': 'port',
        'group': 'integer',
        'add': 'integer',
        'index': 'integer',
        'service_group_id': 'integer',
        'group_member': 'integer',
        'enable_status': 'boolean',
        'ena': 'boolean',
        'dis': 'boolean',
    }
    
    def __init__(self):
        """Initialize type checker."""
        self.errors: List[ValidationError] = []
    
    def validate_types(
        self,
        module_path: str,
        parameters: Dict[str, Any],
        line_offset: int = 0
    ) -> List[ValidationError]:
        """
        Validate parameter types.
        
        Args:
            module_path: Module path for error reporting
            parameters: Dict of parameter_name -> value
            line_offset: Line number offset for error reporting
            
        Returns:
            List of validation errors
        """
        self.errors = []
        
        for param_name, value in parameters.items():
            param_type = self.PARAM_TYPES.get(param_name)
            
            if not param_type:
                # Unknown parameter - just warning
                self.errors.append(ValidationError(
                    line_number=line_offset,
                    module_path=module_path,
                    error_type='type',
                    severity='info',
                    message=f'Unknown parameter type for: {param_name}',
                    suggestion='This parameter may not be validated'
                ))
                continue
            
            # Validate type
            validator = self.TYPE_VALIDATORS.get(param_type)
            if validator and not validator(str(value)):
                self.errors.append(ValidationError(
                    line_number=line_offset,
                    module_path=module_path,
                    error_type='type',
                    severity='error',
                    message=f'Invalid {param_type} for {param_name}: {value}',
                    suggestion=f'Expected {param_type} format'
                ))
        
        return self.errors
    
    @staticmethod
    def _validate_ipv4(value: str) -> bool:
        """Validate IPv4 address."""
        try:
            parts = value.split('.')
            if len(parts) != 4:
                return False
            return all(0 <= int(part) <= 255 for part in parts)
        except (ValueError, AttributeError):
            return False
    
    @staticmethod
    def _validate_port(value: str) -> bool:
        """Validate port number."""
        try:
            port = int(value)
            return 1 <= port <= 65535
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def _validate_integer(value: str) -> bool:
        """Validate integer."""
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            return False
