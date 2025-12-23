"""
Phase 4: Template Retriever
Executes queries against ChromaDB and retrieves relevant templates.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase3.vector_store import VectorStore
from phase4.query_generator import VectorQuery


@dataclass
class RetrievedTemplate:
    """Template retrieved from vector store with metadata."""
    module_path: str
    similarity_score: float  # Cosine similarity from ChromaDB
    template: Dict[str, Any]
    parameters: Dict[str, Any]
    defaults: Dict[str, Any]
    metadata: Dict[str, Any]
    document_text: str


class TemplateRetriever:
    """Retrieves templates from ChromaDB based on queries."""
    
    def __init__(self, vector_store: VectorStore):
        """
        Initialize template retriever.
        
        Args:
            vector_store: VectorStore instance
        """
        self.vector_store = vector_store
    
    def retrieve(self, query: VectorQuery) -> List[RetrievedTemplate]:
        """
        Retrieve templates matching query.
        
        Args:
            query: VectorQuery with embedding and filters
            
        Returns:
            List of RetrievedTemplate objects
        """
        # Query ChromaDB
        results = self.vector_store.search_similar(
            query_embedding=query.embedding,
            top_k=query.top_k,
            filter_dict=query.filters
        )
        
        # Convert to RetrievedTemplate objects
        templates = []
        for i, (template_id, distance, metadata, document) in enumerate(zip(
            results['ids'],
            results['distances'],
            results['metadatas'],
            results['documents']
        )):
            # Convert distance to similarity (1 - distance for cosine distance)
            similarity = 1.0 - distance
            
            templates.append(RetrievedTemplate(
                module_path=metadata.get('module_path', ''),
                similarity_score=similarity,
                template=metadata.get('template', {}),
                parameters=metadata.get('parameters', {}),
                defaults=metadata.get('learned_defaults', {}),
                metadata=metadata,
                document_text=document
            ))
        
        return templates
    
    def retrieve_multi(self, queries: List[VectorQuery]) -> List[RetrievedTemplate]:
        """
        Retrieve templates for multiple queries and merge results.
        
        Args:
            queries: List of VectorQuery objects
            
        Returns:
            List of unique RetrievedTemplate objects (deduplicated)
        """
        all_templates = []
        seen_paths = set()
        
        for query in queries:
            templates = self.retrieve(query)
            
            # Add only unique templates (by module_path)
            for template in templates:
                if template.module_path not in seen_paths:
                    all_templates.append(template)
                    seen_paths.add(template.module_path)
        
        return all_templates
    
    def retrieve_by_category(
        self,
        query: VectorQuery,
        category: str
    ) -> List[RetrievedTemplate]:
        """
        Retrieve templates filtered by specific category.
        
        Args:
            query: VectorQuery object
            category: Category to filter by
            
        Returns:
            List of RetrievedTemplate objects
        """
        # Override filters with specific category
        category_query = VectorQuery(
            embedding=query.embedding,
            filters={"category": category},
            top_k=query.top_k,
            query_text=query.query_text,
            original_requirement=query.original_requirement,
            categories=[category]
        )
        
        return self.retrieve(category_query)
    
    def retrieve_with_dependencies(
        self,
        query: VectorQuery,
        include_dependencies: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve templates and optionally their dependencies.
        
        Args:
            query: VectorQuery object
            include_dependencies: Whether to fetch dependency templates
            
        Returns:
            Dict with 'primary' templates and optional 'dependencies'
        """
        # Get primary templates
        primary_templates = self.retrieve(query)
        
        result = {
            'primary': primary_templates,
            'dependencies': []
        }
        
        if include_dependencies:
            # Collect all dependency paths
            dep_paths = set()
            for template in primary_templates:
                deps = template.metadata.get('dependencies', {})
                requires = deps.get('requires', [])
                dep_paths.update(requires)
            
            # Fetch dependency templates
            dependencies = []
            for path in dep_paths:
                dep_template = self.vector_store.get_by_path(path)
                if dep_template:
                    # Convert to RetrievedTemplate
                    metadata = dep_template['metadata']
                    dependencies.append(RetrievedTemplate(
                        module_path=metadata.get('module_path', ''),
                        similarity_score=0.0,  # Not from similarity search
                        template=metadata.get('template', {}),
                        parameters=metadata.get('parameters', {}),
                        defaults=metadata.get('learned_defaults', {}),
                        metadata=metadata,
                        document_text=dep_template['document']
                    ))
            
            result['dependencies'] = dependencies
        
        return result
    
    def get_template_by_path(self, module_path: str) -> Optional[RetrievedTemplate]:
        """
        Get specific template by exact module path.
        
        Args:
            module_path: Module path (e.g., "/c/sys/mmgmt")
            
        Returns:
            RetrievedTemplate or None if not found
        """
        template_data = self.vector_store.get_by_path(module_path)
        
        if not template_data:
            return None
        
        metadata = template_data['metadata']
        
        return RetrievedTemplate(
            module_path=metadata.get('module_path', ''),
            similarity_score=1.0,  # Exact match
            template=metadata.get('template', {}),
            parameters=metadata.get('parameters', {}),
            defaults=metadata.get('learned_defaults', {}),
            metadata=metadata,
            document_text=template_data['document']
        )
    
    def get_all_templates(self) -> List[RetrievedTemplate]:
        """
        Get all templates from the vector store.
        
        Returns:
            List of all RetrievedTemplate objects
        """
        all_template_info = self.vector_store.list_all_templates()
        
        templates = []
        for info in all_template_info:
            template = self.get_template_by_path(info['module_path'])
            if template:
                templates.append(template)
        
        return templates
    
    def count_templates(self) -> int:
        """
        Get total number of templates in store.
        
        Returns:
            Template count
        """
        stats = self.vector_store.get_collection_stats()
        return stats['total_templates']
