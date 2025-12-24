"""
Phase 5: Dependency Resolver
Orders modules based on dependencies and validates references.
"""

from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass


@dataclass
class DependencyInfo:
    """Dependency information for a module."""
    module_path: str
    requires: List[str]
    required_by: List[str]


class DependencyResolver:
    """Resolves and orders modules based on dependencies."""
    
    def order_modules(
        self,
        modules: List[Any],  # AssembledModule objects
        all_templates: Dict[str, Any] = None
    ) -> List[Any]:
        """
        Order modules based on dependencies.
        
        Args:
            modules: List of AssembledModule objects
            all_templates: Optional dict of all available templates
            
        Returns:
            Ordered list of modules
        """
        if not modules:
            return []
        
        # Build dependency graph
        dep_graph = self._build_dependency_graph(modules)
        
        # Topological sort
        try:
            ordered = self._topological_sort(dep_graph)
        except ValueError as e:
            # Circular dependency detected - use best-effort ordering
            print(f"Warning: {e}. Using best-effort ordering.")
            ordered = self._best_effort_order(dep_graph)
        
        # Map back to modules
        module_map = {m.module_path: m for m in modules}
        ordered_modules = [module_map[path] for path in ordered if path in module_map]
        
        return ordered_modules
    
    def _build_dependency_graph(self, modules: List[Any]) -> Dict[str, DependencyInfo]:
        """Build dependency graph from modules."""
        graph = {}
        
        for module in modules:
            path = module.module_path
            metadata = module.metadata
            
            # Get dependencies from template metadata
            template = metadata.get('template', {})
            deps = template.get('dependencies', {})
            
            requires = deps.get('requires', [])
            required_by = deps.get('required_by', [])
            
            graph[path] = DependencyInfo(
                module_path=path,
                requires=requires,
                required_by=required_by
            )
        
        return graph
    
    def _get_module_order_priority(self, module_path: str) -> int:
        """Get ordering priority for module (lower number = earlier)."""
        # Define logical ordering based on module types
        if '/l2/vlan' in module_path:
            return 1  # VLANs first
        elif '/slb/real' in module_path:
            return 2  # Real servers before groups
        elif '/slb/group' in module_path:
            return 3  # Groups after real servers
        elif '/slb/virt' in module_path and '/service' not in module_path:
            return 4  # VIP after groups
        elif '/slb/virt' in module_path and '/service' in module_path:
            return 5  # Service submodules after VIP
        elif '/slb/ssl' in module_path:
            return 3  # SSL with groups
        elif '/l3/' in module_path:
            return 1  # Layer 3 with VLANs
        else:
            return 10  # Other modules last
    
    def _topological_sort(self, graph: Dict[str, DependencyInfo]) -> List[str]:
        """
        Topological sort of dependency graph with logical ordering.
        
        Returns modules in dependency order (dependencies first).
        """
        # Calculate in-degree for each node
        in_degree = {path: 0 for path in graph}
        
        for info in graph.values():
            for dep in info.requires:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        # Find nodes with no incoming edges and sort by priority
        queue = [path for path, degree in in_degree.items() if degree == 0]
        queue.sort(key=lambda p: (self._get_module_order_priority(p), p))
        result = []
        
        while queue:
            # Sort queue by priority and then alphabetically
            queue.sort(key=lambda p: (self._get_module_order_priority(p), p))
            node = queue.pop(0)
            result.append(node)
            
            # Remove node and update in-degrees
            if node in graph:
                for required_by in graph[node].required_by:
                    if required_by in in_degree:
                        in_degree[required_by] -= 1
                        if in_degree[required_by] == 0:
                            queue.append(required_by)
        
        # Check for cycles
        if len(result) != len(graph):
            raise ValueError("Circular dependency detected")
        
        return result
    
    def _best_effort_order(self, graph: Dict[str, DependencyInfo]) -> List[str]:
        """Best-effort ordering when topological sort fails."""
        # Group by category and order by path
        paths = sorted(graph.keys())
        return paths
    
    def find_missing_dependencies(
        self,
        modules: List[Any],
        all_templates: Dict[str, Any]
    ) -> List[str]:
        """
        Find dependencies that are required but not included.
        
        Args:
            modules: List of AssembledModule objects
            all_templates: Dict of all available templates
            
        Returns:
            List of missing module paths
        """
        included = {m.module_path for m in modules}
        missing = set()
        
        for module in modules:
            template = module.metadata.get('template', {})
            deps = template.get('dependencies', {})
            requires = deps.get('requires', [])
            
            for dep in requires:
                if dep not in included and dep in all_templates:
                    missing.add(dep)
        
        return sorted(missing)
    
    def validate_dependencies(
        self,
        modules: List[Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate that all dependencies are satisfied.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        included = {m.module_path for m in modules}
        
        for module in modules:
            template = module.metadata.get('template', {})
            deps = template.get('dependencies', {})
            requires = deps.get('requires', [])
            
            for dep in requires:
                if dep not in included:
                    errors.append(
                        f"Module {module.module_path} requires {dep} which is not included"
                    )
        
        return len(errors) == 0, errors
    
    def suggest_additions(
        self,
        modules: List[Any],
        all_templates: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Suggest additional modules that might be needed.
        
        Returns:
            List of suggested templates with reasons
        """
        suggestions = []
        included = {m.module_path for m in modules}
        
        # Find missing dependencies
        missing_deps = self.find_missing_dependencies(modules, all_templates)
        
        for dep_path in missing_deps:
            if dep_path in all_templates:
                suggestions.append({
                    'module_path': dep_path,
                    'template': all_templates[dep_path],
                    'reason': 'Required by existing modules',
                    'priority': 'high'
                })
        
        # Suggest commonly paired modules
        included_categories = {m.metadata.get('category') for m in modules}
        
        # If load_balancing modules present, suggest related modules
        if 'load_balancing' in included_categories:
            # Check if we have virt but not real/group
            has_virt = any('/slb/virt' in m.module_path for m in modules)
            has_real = any('/slb/real' in m.module_path for m in modules)
            has_group = any('/slb/group' in m.module_path for m in modules)
            
            if has_virt and not has_real:
                suggestions.append({
                    'module_path': '/c/slb/real',
                    'reason': 'Virtual server typically needs real servers',
                    'priority': 'medium'
                })
            
            if has_virt and not has_group:
                suggestions.append({
                    'module_path': '/c/slb/group',
                    'reason': 'Virtual server typically uses server groups',
                    'priority': 'medium'
                })
        
        return suggestions
