"""
Phase 5: Relationship Manager
Manages inter-module relationships and ensures consistency.
"""

from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass


@dataclass
class ModuleRelationship:
    """Represents a relationship between two modules."""
    source_module: str  # e.g., "/c/slb/group"
    source_param: str   # e.g., "add" (real server index)
    target_module: str  # e.g., "/c/slb/real"
    target_param: str   # e.g., "index"
    relationship_type: str  # "references", "requires", "uses"


class RelationshipManager:
    """Manages relationships between configuration modules."""
    
    # Define known relationships between modules
    RELATIONSHIPS = [
        # Group references real servers
        ModuleRelationship(
            source_module="/c/slb/group",
            source_param="group_member",  # The "add {{group_member}}" parameter in group config
            target_module="/c/slb/real",
            target_param="index",
            relationship_type="references"
        ),
        # Virt references groups
        ModuleRelationship(
            source_module="/c/slb/virt",
            source_param="service_group_id",  # The "service_group_id" parameter in virt config
            target_module="/c/slb/group",
            target_param="index",
            relationship_type="references"
        ),
    ]
    
    def __init__(self):
        """Initialize relationship manager."""
        self.relationships = self.RELATIONSHIPS
        
    def suggest_missing_modules(
        self,
        modules: List[Any]  # AssembledModule objects
    ) -> List[str]:
        """
        Suggest missing modules based on relationships.
        
        For example, if /c/slb/virt is present but /c/slb/group is missing,
        suggest adding /c/slb/group and /c/slb/real.
        
        Args:
            modules: List of AssembledModule objects
            
        Returns:
            List of module paths that should be added
        """
        present_modules = {m.module_path for m in modules}
        suggestions = set()
        
        for module in modules:
            module_path = module.module_path
            
            # Check if this module requires other modules
            for rel in self.relationships:
                if module_path == rel.source_module:
                    # This module references another - check if target exists
                    if rel.target_module not in present_modules:
                        suggestions.add(rel.target_module)
        
        return sorted(list(suggestions))
        """
        Resolve inter-module references.
        
        Updates parameter values to maintain consistency between modules.
        For example, if group "add" should reference real server index.
        
        Args:
            modules: List of AssembledModule objects
            
        Returns:
            List of updated AssembledModule objects
        """
        # Build index tracking
        module_indices = self._build_index_map(modules)
        
        # Process each module
        for module in modules:
            module_path = module.module_path
            
            # Check if this module has relationships
            for rel in self.relationships:
                if module_path == rel.source_module:
                    # This module references another
                    self._resolve_reference(module, rel, module_indices)
        
        return modules
    
    def _build_index_map(self, modules: List[Any]) -> Dict[str, List[int]]:
        """
        Build a map of module paths to their indices.
        
        Args:
            modules: List of AssembledModule objects
            
        Returns:
            Dict mapping module_path to list of indices
        """
        index_map = {}
        
        for module in modules:
            path = module.module_path
            
            if path not in index_map:
                index_map[path] = []
            
            # Extract index from metadata or infer from position
            metadata = module.metadata or {}
            index = metadata.get('index')
            
            if index is not None:
                index_map[path].append(index)
            else:
                # Use sequential numbering
                index_map[path].append(len(index_map[path]) + 1)
        
        return index_map
    
    def _resolve_reference(
        self,
        module: Any,
        relationship: ModuleRelationship,
        index_map: Dict[str, List[int]]
    ):
        """
        Resolve a specific reference in a module.
        
        Args:
            module: AssembledModule object
            relationship: ModuleRelationship definition
            index_map: Map of module paths to indices
        """
        target_indices = index_map.get(relationship.target_module, [])
        
        if not target_indices:
            # No target modules found
            return
        
        # Find the parameter assignment that needs updating
        for assignment in module.parameter_assignments:
            if assignment.parameter_name == relationship.source_param:
                # Update value to reference target
                # Use the first available target index
                if target_indices:
                    assignment.value = str(target_indices[0])
                    assignment.confidence = 0.9
                    assignment.source = 'relationship'
                break
    
    def suggest_missing_modules(
        self,
        modules: List[Any]
    ) -> List[str]:
        """
        Suggest modules that might be missing based on relationships.
        
        Args:
            modules: List of AssembledModule objects
            
        Returns:
            List of suggested module paths
        """
        present_modules = {m.module_path for m in modules}
        suggestions = set()
        
        for module in modules:
            module_path = module.module_path
            
            # Check if this module requires others
            for rel in self.relationships:
                if module_path == rel.source_module:
                    # This module references target - is target present?
                    if rel.target_module not in present_modules:
                        suggestions.add(rel.target_module)
                        
                elif module_path == rel.target_module:
                    # This is a target - suggest the source if relevant
                    # (e.g., if we have real servers, suggest groups/virts)
                    pass  # Could add reverse suggestions here
        
        return list(suggestions)
    
    def assign_consistent_indices(
        self,
        modules: List[Any],
        start_index: int = 1
    ) -> List[Any]:
        """
        Assign consistent indices across related modules.
        
        For example:
        - real server 1 → group 1 adds real 1 → virt 1 uses group 1
        
        Args:
            modules: List of AssembledModule objects
            start_index: Starting index number
            
        Returns:
            List of modules with updated indices
        """
        # Group modules by type
        by_type = {}
        for module in modules:
            path = module.module_path
            if path not in by_type:
                by_type[path] = []
            by_type[path].append(module)
        
        # Assign sequential indices per type
        for path, module_list in by_type.items():
            for i, module in enumerate(module_list, start=start_index):
                # Update metadata
                if module.metadata is None:
                    module.metadata = {}
                module.metadata['index'] = i
        
        return modules
    
    def validate_relationships(
        self,
        modules: List[Any]
    ) -> List[str]:
        """
        Validate that all relationships are satisfied.
        
        Args:
            modules: List of AssembledModule objects
            
        Returns:
            List of validation errors
        """
        errors = []
        module_indices = self._build_index_map(modules)
        
        for module in modules:
            module_path = module.module_path
            
            # Check relationships
            for rel in self.relationships:
                if module_path == rel.source_module:
                    # Verify target exists
                    if rel.target_module not in module_indices:
                        errors.append(
                            f"{module_path} references {rel.target_module} "
                            f"but target not found in configuration"
                        )
                    
                    # Check if reference value is valid
                    for assignment in module.parameter_assignments:
                        if assignment.parameter_name == rel.source_param:
                            ref_value = str(assignment.value)
                            target_indices = module_indices.get(rel.target_module, [])
                            
                            # Convert to string for comparison
                            target_indices_str = [str(idx) for idx in target_indices]
                            
                            if ref_value not in target_indices_str:
                                errors.append(
                                    f"{module_path}.{rel.source_param}={ref_value} "
                                    f"references non-existent {rel.target_module} "
                                    f"(available: {', '.join(target_indices_str)})"
                                )
        
        return errors
