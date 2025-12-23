"""
Phase 6: Dependency Validator
Validates module dependencies and ordering.
"""

from typing import List, Dict, Any, Set
from .syntax_validator import ValidationError


class DependencyValidator:
    """Validates module dependencies."""
    
    # Known dependencies
    DEPENDENCIES = {
        '/c/slb/virt': ['/c/slb/group'],  # VIP requires group
        '/c/slb/group': ['/c/slb/real'],  # Group requires real servers
        '/c/slb/virt/service': ['/c/slb/virt', '/c/slb/group'],  # Service requires VIP and group
    }
    
    def __init__(self):
        """Initialize dependency validator."""
        self.errors: List[ValidationError] = []
    
    def validate_dependencies(
        self,
        modules: List[Any]  # AssembledModule objects
    ) -> List[ValidationError]:
        """
        Validate module dependencies.
        
        Args:
            modules: List of AssembledModule objects
            
        Returns:
            List of validation errors
        """
        self.errors = []
        
        # Get set of present module paths
        present_modules = {module.module_path for module in modules}
        
        # Check each module's dependencies
        for module in modules:
            required_deps = self.DEPENDENCIES.get(module.module_path, [])
            
            for dep in required_deps:
                if dep not in present_modules:
                    self.errors.append(ValidationError(
                        line_number=0,
                        module_path=module.module_path,
                        error_type='dependency',
                        severity='error',
                        message=f'Missing required dependency: {dep}',
                        suggestion=f'Add {dep} module configuration'
                    ))
        
        # Check ordering - dependencies should come before dependents
        self._validate_ordering(modules)
        
        return self.errors
    
    def _validate_ordering(self, modules: List[Any]) -> None:
        """Validate that dependencies appear before modules that need them."""
        module_positions = {
            module.module_path: idx
            for idx, module in enumerate(modules)
        }
        
        for idx, module in enumerate(modules):
            required_deps = self.DEPENDENCIES.get(module.module_path, [])
            
            for dep in required_deps:
                dep_position = module_positions.get(dep)
                
                if dep_position is not None and dep_position > idx:
                    self.errors.append(ValidationError(
                        line_number=0,
                        module_path=module.module_path,
                        error_type='dependency',
                        severity='warning',
                        message=f'Dependency {dep} appears after {module.module_path}',
                        suggestion=f'Move {dep} before {module.module_path} for better clarity'
                    ))
