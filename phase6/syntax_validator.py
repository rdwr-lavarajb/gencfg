"""
Phase 6: Syntax Validator
Validates configuration syntax for correctness.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import re


@dataclass
class ValidationError:
    """Represents a validation error."""
    line_number: int
    module_path: str
    error_type: str  # 'syntax', 'type', 'reference', 'dependency'
    severity: str  # 'error', 'warning', 'info'
    message: str
    suggestion: str = ""


class SyntaxValidator:
    """Validates configuration syntax."""
    
    # Module path pattern
    MODULE_PATH_PATTERN = re.compile(r'^/c(/[\w\-]+)+(\s+\d+(/[\w\-]+\s+\d+\s+[\w\-]+)?)?$')
    
    # Parameter patterns
    IP_PATTERN = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    PORT_PATTERN = re.compile(r'^\d{1,5}$')
    
    def __init__(self):
        """Initialize syntax validator."""
        self.errors: List[ValidationError] = []
    
    def validate(self, config_lines: List[str]) -> Tuple[bool, List[ValidationError]]:
        """
        Validate configuration syntax.
        
        Args:
            config_lines: List of configuration lines
            
        Returns:
            Tuple of (is_valid, errors)
        """
        self.errors = []
        current_module = None
        
        for line_num, line in enumerate(config_lines, 1):
            stripped = line.strip()
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith('#'):
                continue
            
            # Check if it's a module path
            if stripped.startswith('/c/'):
                current_module = stripped
                self._validate_module_path(line_num, stripped)
            
            # Check if it's a parameter (indented or starts with keyword)
            elif line.startswith('\t') or line.startswith('    '):
                if not current_module:
                    self.errors.append(ValidationError(
                        line_number=line_num,
                        module_path='',
                        error_type='syntax',
                        severity='error',
                        message='Parameter without module context',
                        suggestion='Ensure parameter is under a module path'
                    ))
                else:
                    self._validate_parameter(line_num, current_module, stripped)
            
            # Check for reserved keywords
            elif stripped in ['apply', 'save', 'exit']:
                continue  # Valid commands
            
            else:
                # Check if it's a valid non-indented parameter
                if ' ' in stripped:
                    self._validate_parameter(line_num, current_module or 'root', stripped)
        
        is_valid = not any(e.severity == 'error' for e in self.errors)
        return is_valid, self.errors
    
    def _validate_module_path(self, line_num: int, module_path: str) -> None:
        """Validate module path syntax."""
        # Basic format check
        if not module_path.startswith('/c/'):
            self.errors.append(ValidationError(
                line_number=line_num,
                module_path=module_path,
                error_type='syntax',
                severity='error',
                message='Module path must start with /c/',
                suggestion='Check module path format'
            ))
            return
        
        # Check for invalid characters
        if any(char in module_path for char in ['\\', '<', '>', '|', '"', "'"]):
            self.errors.append(ValidationError(
                line_number=line_num,
                module_path=module_path,
                error_type='syntax',
                severity='error',
                message='Module path contains invalid characters',
                suggestion='Remove special characters from path'
            ))
    
    def _validate_parameter(self, line_num: int, module_path: str, param_line: str) -> None:
        """Validate parameter syntax."""
        # Split parameter name and value
        parts = param_line.split(None, 1)
        
        if not parts:
            return
        
        param_name = parts[0]
        param_value = parts[1] if len(parts) > 1 else ''
        
        # Check for placeholder that wasn't replaced
        if '{{' in param_line and '}}' in param_line:
            placeholder = re.search(r'\{\{(\w+)\}\}', param_line)
            if placeholder:
                self.errors.append(ValidationError(
                    line_number=line_num,
                    module_path=module_path,
                    error_type='syntax',
                    severity='error',
                    message=f'Unreplaced placeholder: {placeholder.group(1)}',
                    suggestion=f'Provide value for {placeholder.group(1)} parameter'
                ))
        
        # Validate IP addresses
        if param_name in ['vip', 'rip', 'ip', 'gateway', 'mask']:
            if param_value and not self._is_valid_ip(param_value):
                self.errors.append(ValidationError(
                    line_number=line_num,
                    module_path=module_path,
                    error_type='type',
                    severity='error',
                    message=f'Invalid IP address format: {param_value}',
                    suggestion='Use format: xxx.xxx.xxx.xxx'
                ))
        
        # Validate port numbers
        if param_name in ['port', 'rport', 'sport']:
            if param_value and not self._is_valid_port(param_value):
                self.errors.append(ValidationError(
                    line_number=line_num,
                    module_path=module_path,
                    error_type='type',
                    severity='error',
                    message=f'Invalid port number: {param_value}',
                    suggestion='Port must be between 1 and 65535'
                ))
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Check if IP address is valid."""
        if not self.IP_PATTERN.match(ip):
            return False
        
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    
    def _is_valid_port(self, port: str) -> bool:
        """Check if port number is valid."""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except ValueError:
            return False
    
    def format_errors(self, errors: List[ValidationError]) -> str:
        """Format errors for display."""
        if not errors:
            return "✅ No validation errors found"
        
        output = []
        output.append(f"\n⚠️  Found {len(errors)} validation issue(s):\n")
        
        # Group by severity
        errors_by_severity = {'error': [], 'warning': [], 'info': []}
        for error in errors:
            errors_by_severity[error.severity].append(error)
        
        for severity in ['error', 'warning', 'info']:
            severity_errors = errors_by_severity[severity]
            if not severity_errors:
                continue
            
            icon = '❌' if severity == 'error' else '⚠️' if severity == 'warning' else 'ℹ️'
            output.append(f"{icon} {severity.upper()}S ({len(severity_errors)}):")
            
            for error in severity_errors:
                output.append(f"  Line {error.line_number}: {error.message}")
                if error.module_path:
                    output.append(f"    Module: {error.module_path}")
                if error.suggestion:
                    output.append(f"    💡 {error.suggestion}")
                output.append("")
        
        return "\n".join(output)
