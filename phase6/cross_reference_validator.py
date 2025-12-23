"""
Phase 6: Cross-Reference Validator
Validates references between modules (e.g., group references real server).
"""

from typing import List, Dict, Any, Set
from .syntax_validator import ValidationError


class CrossReferenceValidator:
    """Validates cross-references between modules."""
    
    def __init__(self):
        """Initialize cross-reference validator."""
        self.errors: List[ValidationError] = []
    
    def validate_references(
        self,
        modules: List[Any]  # AssembledModule objects
    ) -> List[ValidationError]:
        """
        Validate cross-references between modules.
        
        Args:
            modules: List of AssembledModule objects
            
        Returns:
            List of validation errors
        """
        self.errors = []
        
        # Build index of available modules and their indices
        module_indices = self._build_module_index(modules)
        
        # Validate references
        for module in modules:
            self._validate_module_references(module, module_indices)
        
        return self.errors
    
    def _build_module_index(self, modules: List[Any]) -> Dict[str, Set[int]]:
        """Build index of module paths to their indices."""
        index = {}
        
        for module in modules:
            module_path = module.module_path
            module_index = module.metadata.get('index')
            
            if module_path not in index:
                index[module_path] = set()
            
            if module_index is not None:
                index[module_path].add(module_index)
        
        return index
    
    def _validate_module_references(
        self,
        module: Any,
        module_indices: Dict[str, Set[int]]
    ) -> None:
        """Validate references in a single module."""
        module_path = module.module_path
        
        # Check group -> real references
        if module_path == '/c/slb/group':
            self._validate_group_references(module, module_indices)
        
        # Check virt -> group references
        elif module_path == '/c/slb/virt':
            self._validate_virt_references(module, module_indices)
    
    def _validate_group_references(
        self,
        module: Any,
        module_indices: Dict[str, Set[int]]
    ) -> None:
        """Validate that group references valid real servers."""
        # Find group_member (add) parameter
        for assignment in module.parameter_assignments:
            if assignment.parameter_name == 'group_member':
                try:
                    real_index = int(assignment.value)
                    
                    # Check if real server with this index exists
                    real_indices = module_indices.get('/c/slb/real', set())
                    
                    if real_index not in real_indices:
                        self.errors.append(ValidationError(
                            line_number=0,
                            module_path=module.module_path,
                            error_type='reference',
                            severity='error',
                            message=f'Group references non-existent real server: {real_index}',
                            suggestion=f'Ensure /c/slb/real {real_index} is defined'
                        ))
                except (ValueError, AttributeError):
                    pass
    
    def _validate_virt_references(
        self,
        module: Any,
        module_indices: Dict[str, Set[int]]
    ) -> None:
        """Validate that virt references valid groups."""
        # Find service_group_id parameter
        for assignment in module.parameter_assignments:
            if assignment.parameter_name == 'service_group_id':
                try:
                    group_index = int(assignment.value)
                    
                    # Check if group with this index exists
                    group_indices = module_indices.get('/c/slb/group', set())
                    
                    if group_index not in group_indices:
                        self.errors.append(ValidationError(
                            line_number=0,
                            module_path=module.module_path,
                            error_type='reference',
                            severity='error',
                            message=f'VIP references non-existent group: {group_index}',
                            suggestion=f'Ensure /c/slb/group {group_index} is defined'
                        ))
                except (ValueError, AttributeError):
                    pass
