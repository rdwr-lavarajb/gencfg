"""
Test script for Phase 3 vector search functionality.
Tests semantic search with various queries.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from phase3.embedding_generator import EmbeddingGenerator
from phase3.vector_store import VectorStore


def test_search():
    """Test semantic search with sample queries."""
    print("🔍 Testing Vector Search")
    print("=" * 60)
    
    # Load environment
    load_dotenv()
    
    # Initialize components
    generator = EmbeddingGenerator()
    store = VectorStore()
    
    # Get collection stats
    stats = store.get_collection_stats()
    print(f"\n📊 Collection: {stats['collection_name']}")
    print(f"   Total templates: {stats['total_templates']}")
    
    # Test queries
    test_queries = [
        "Configure management IP address and network settings",
        "Setup NTP time synchronization",
        "Create virtual server for load balancing",
        "Configure VLAN and layer 2 settings",
        "Setup SSL certificates",
        "Configure real servers"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 60}")
        print(f"Query {i}: {query}")
        print("=" * 60)
        
        # Generate query embedding
        query_embedding = generator.generate_embedding(query)
        
        # Search
        results = store.search_similar(
            query_embedding=query_embedding,
            top_k=3
        )
        
        # Display results
        print(f"\nTop 3 Results:")
        for j, (module_path, distance, metadata) in enumerate(
            zip(results['ids'], results['distances'], results['metadatas']), 1
        ):
            print(f"\n{j}. {metadata['module_path']}")
            print(f"   Similarity: {1 - distance:.4f}")  # Convert distance to similarity
            print(f"   Category: {metadata.get('category', 'unknown')}")
            print(f"   Description: {metadata.get('description', 'N/A')[:100]}...")
            print(f"   Parameters: {metadata.get('param_count', 0)}")
    
    # Display token usage
    print(f"\n{'=' * 60}")
    print(f"Token Usage:")
    token_stats = generator.get_token_stats()
    print(f"   Tokens: {token_stats['tokens_used']}")
    print(f"   Cost: ${token_stats['estimated_cost_usd']:.6f}")
    print(f"   Model: {token_stats['model']}")


if __name__ == "__main__":
    test_search()
