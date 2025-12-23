"""
Phase 5: Template Assembler
Fills template placeholders with actual values.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import re


@dataclass
class AssembledModule:
    """A module with filled template."""
    module_path: str
    config_lines: List[str]
    parameter_assignments: List[Any]  # ValueAssignment objects
    missing_required: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class TemplateAssembler:
    """Assembles configuration modules from templates and values."""
    
    def assemble(
        self,
        template: Dict[str, Any],
        assignments: List[Any],  # ValueAssignment objects
        index: Optional[int] = None
    ) -> AssembledModule:
        """
        Assemble a configuration module from template and assignments.
        
        Args:
            template: Template dict from Phase 2/4
            assignments: List of ValueAssignment objects
            index: Optional index for indexed modules
            
        Returns:
            AssembledModule with filled configuration
        """
        module_path = template.get('module_path', '')
        template_obj = template.get('template', {})
        parameters = template.get('parameters', {})
        
        # Build assignment map
        assignment_map = {a.parameter_name: a for a in assignments}
        
        # Check for missing required parameters
        missing_required = []
        for param_name, param_info in parameters.items():
            if param_info.get('required', False) and param_name not in assignment_map:
                missing_required.append(param_name)
        
        # Fill template
        header = template_obj.get('header', '')
        body_lines = template_obj.get('body', [])
        
        # Fill header (handle index if present)
        if index is not None:
            filled_header = header.replace('{{index}}', str(index))
        else:
            filled_header = header
        
        # Fill body lines
        filled_lines = []
        warnings = []
        
        for line in body_lines:
            filled_line, line_warnings = self._fill_line(
                line,
                assignment_map,
                parameters
            )
            
            if filled_line is not None:
                filled_lines.append(filled_line)
            
            warnings.extend(line_warnings)
        
        # Build config lines (header + body)
        config_lines = [filled_header] + filled_lines
        
        return AssembledModule(
            module_path=module_path,
            config_lines=config_lines,
            parameter_assignments=assignments,
            missing_required=missing_required,
            warnings=warnings,
            metadata={
                'template': template,
                'index': index,
                'category': template.get('category', 'unknown'),
                'module_type': template.get('module_type', 'standard')
            }
        )
    
    def assemble_multiple(
        self,
        template: Dict[str, Any],
        assignments_list: List[List[Any]],
        start_index: int = 1
    ) -> List[AssembledModule]:
        """
        Assemble multiple instances of an indexed module.
        
        Args:
            template: Template dict
            assignments_list: List of assignment lists (one per instance)
            start_index: Starting index number
            
        Returns:
            List of AssembledModule objects
        """
        modules = []
        
        for i, assignments in enumerate(assignments_list, start=start_index):
            module = self.assemble(template, assignments, index=i)
            modules.append(module)
        
        return modules
    
    def _fill_line(
        self,
        line: str,
        assignment_map: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> tuple[Optional[str], List[str]]:
        """
        Fill a single template line with values.
        
        Returns:
            (filled_line, warnings) - filled_line is None if line should be skipped
        """
        warnings = []
        
        # Find all placeholders
        placeholders = re.findall(r'{{(\w+)}}', line)
        
        if not placeholders:
            # No placeholders - return as-is
            return line, warnings
        
        # Fill each placeholder
        filled_line = line
        all_filled = True
        
        for placeholder in placeholders:
            if placeholder in assignment_map:
                assignment = assignment_map[placeholder]
                value = self._format_value(assignment.value, assignment.parameter_type)
                filled_line = filled_line.replace(f'{{{{{placeholder}}}}}', value)
            else:
                # Placeholder not filled
                param_info = parameters.get(placeholder, {})
                required = param_info.get('required', False)
                
                if required:
                    warnings.append(f"Missing required parameter: {placeholder}")
                    all_filled = False
                else:
                    # Optional parameter - skip line
                    return None, []
        
        # Only return line if all required placeholders were filled
        if all_filled:
            return filled_line, warnings
        else:
            return None, warnings
    
    def _format_value(self, value: Any, param_type: str) -> str:
        """Format value according to parameter type."""
        if value is None:
            return ""
        
        # Quoted strings
        if param_type in ['quoted_string', 'string'] and not str(value).startswith('"'):
            # Add quotes if not present and contains spaces or special chars
            if ' ' in str(value) or any(c in str(value) for c in ['-', '/', '\\']):
                return f'"{value}"'
        
        # Remove quotes if already present
        if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
            return value  # Already quoted
        
        return str(value)
    
    def validate_assembly(self, module: AssembledModule) -> bool:
        """
        Validate assembled module.
        
        Returns:
            True if module is valid (no missing required parameters)
        """
        return len(module.missing_required) == 0
    
    def get_summary(self, modules: List[AssembledModule]) -> Dict[str, Any]:
        """Get summary statistics for assembled modules."""
        total_modules = len(modules)
        valid_modules = sum(1 for m in modules if self.validate_assembly(m))
        total_warnings = sum(len(m.warnings) for m in modules)
        total_lines = sum(len(m.config_lines) for m in modules)
        
        return {
            'total_modules': total_modules,
            'valid_modules': valid_modules,
            'invalid_modules': total_modules - valid_modules,
            'total_warnings': total_warnings,
            'total_lines': total_lines
        }
