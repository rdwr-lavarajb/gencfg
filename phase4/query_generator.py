"""
Phase 4: Query Generator
Converts parsed requirements into vector queries with filters.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase3.embedding_generator import EmbeddingGenerator
from phase4.requirements_parser import ParsedRequirement


@dataclass
class VectorQuery:
    """Vector query with embedding and filters."""
    embedding: List[float]
    filters: Optional[Dict[str, Any]]
    top_k: int
    query_text: str
    original_requirement: str
    categories: List[str]


class QueryGenerator:
    """Generates vector queries from parsed requirements."""
    
    def __init__(self, embedding_generator: EmbeddingGenerator):
        """
        Initialize query generator.
        
        Args:
            embedding_generator: EmbeddingGenerator instance for embeddings
        """
        self.embedding_generator = embedding_generator
    
    def generate_query(
        self,
        parsed: ParsedRequirement,
        top_k: int = 5,
        use_filters: bool = True
    ) -> VectorQuery:
        """
        Generate vector query from parsed requirement.
        
        Args:
            parsed: ParsedRequirement object
            top_k: Number of results to retrieve
            use_filters: Whether to apply category filters
            
        Returns:
            VectorQuery object
        """
        # Generate embedding from query text
        embedding = self.embedding_generator.generate_embedding(parsed.query_text)
        
        # Build filters
        filters = None
        if use_filters and parsed.categories:
            filters = self._build_filters(parsed)
        
        return VectorQuery(
            embedding=embedding,
            filters=filters,
            top_k=top_k,
            query_text=parsed.query_text,
            original_requirement=parsed.original_text,
            categories=parsed.categories
        )
    
    def generate_multi_query(
        self,
        parsed: ParsedRequirement,
        top_k: int = 5
    ) -> List[VectorQuery]:
        """
        Generate multiple specialized queries for complex requirements.
        
        For complex requirements mentioning multiple concepts, this creates
        separate queries for each major component.
        
        Args:
            parsed: ParsedRequirement object
            top_k: Number of results per query
            
        Returns:
            List of VectorQuery objects
        """
        queries = []
        
        # Main query (always included)
        main_query = self.generate_query(parsed, top_k=top_k)
        queries.append(main_query)
        
        # If multiple categories, create specialized queries
        if len(parsed.categories) > 1:
            for category in parsed.categories[:3]:  # Max 3 additional queries
                # Build category-specific query text
                category_text = f"{parsed.query_text} | Category: {category}"
                
                # Generate embedding
                embedding = self.embedding_generator.generate_embedding(category_text)
                
                # Build category-specific filter
                filters = {"category": category}
                
                queries.append(VectorQuery(
                    embedding=embedding,
                    filters=filters,
                    top_k=max(3, top_k // 2),  # Fewer results per specialized query
                    query_text=category_text,
                    original_requirement=parsed.original_text,
                    categories=[category]
                ))
        
        return queries
    
    def _build_filters(self, parsed: ParsedRequirement) -> Dict[str, Any]:
        """
        Build ChromaDB filter expression from parsed requirements.
        
        ChromaDB supports filters like:
        - {"category": "load_balancing"}
        - {"$or": [{"category": "load_balancing"}, {"category": "network_layer3"}]}
        
        Note: ChromaDB doesn't support combining $or with other filters at the same level.
        We only use category filters since they're most important.
        
        Args:
            parsed: ParsedRequirement object
            
        Returns:
            ChromaDB filter dict
        """
        filters = {}
        
        # Category filter (OR multiple categories)
        # This is the primary filter - don't combine with others
        if parsed.categories:
            if len(parsed.categories) == 1:
                filters["category"] = parsed.categories[0]
            else:
                # Use $or for multiple categories
                filters["$or"] = [
                    {"category": cat} for cat in parsed.categories[:3]  # Limit to 3
                ]
        
        # Note: We skip param_count filter to avoid ChromaDB filter combination issues
        # Ranking will handle parameter relevance scoring instead
        
        return filters if filters else None
    
    def expand_query(self, query_text: str, expansion_terms: List[str]) -> str:
        """
        Expand query with related terms.
        
        Args:
            query_text: Original query text
            expansion_terms: Additional terms to include
            
        Returns:
            Expanded query text
        """
        return f"{query_text} | {' '.join(expansion_terms)}"
    
    def get_token_stats(self) -> Dict[str, Any]:
        """
        Get token usage statistics from embedding generator.
        
        Returns:
            Dict with token stats
        """
        return self.embedding_generator.get_token_stats()
