"""
Phase 4 Main Script: Retrieve Templates
Intelligent template retrieval based on user requirements.

Usage:
    python retrieve_templates.py "Configure management IP address"
    python retrieve_templates.py --interactive
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from phase3.embedding_generator import EmbeddingGenerator
from phase3.vector_store import VectorStore
from phase4.requirements_parser import RequirementsParser
from phase4.query_generator import QueryGenerator
from phase4.template_retriever import TemplateRetriever
from phase4.relevance_ranker import RelevanceRanker


class TemplateRetrievalSystem:
    """Complete template retrieval pipeline."""
    
    def __init__(self):
        """Initialize all components."""
        # Load environment
        load_dotenv()
        
        print("🚀 Phase 4: Template Retrieval System")
        print("=" * 60)
        
        # Initialize components
        print("\n📦 Initializing components...")
        self.embedding_generator = EmbeddingGenerator()
        self.vector_store = VectorStore()
        self.parser = RequirementsParser()
        self.query_generator = QueryGenerator(self.embedding_generator)
        self.retriever = TemplateRetriever(self.vector_store)
        self.ranker = RelevanceRanker()
        
        # Check if vector store has data
        stats = self.vector_store.get_collection_stats()
        template_count = stats['total_templates']
        
        if template_count == 0:
            print("\n⚠️  Warning: Vector store is empty!")
            print("   Run 'python embed_templates.py' first to populate the database.")
            sys.exit(1)
        
        print(f"✅ Vector store ready ({template_count} templates)")
    
    def retrieve(
        self,
        requirement: str,
        top_k: int = 5,
        show_details: bool = True
    ) -> dict:
        """
        Retrieve templates for a requirement.
        
        Args:
            requirement: Natural language requirement
            top_k: Number of results to return
            show_details: Whether to display detailed results
            
        Returns:
            Dict with results and metadata
        """
        print(f"\n{'=' * 60}")
        print(f"📝 Requirement: {requirement}")
        print("=" * 60)
        
        # 1. Parse requirement
        print("\n🔍 Parsing requirement...")
        parsed = self.parser.parse(requirement)
        
        if show_details:
            print(f"   Intent: {parsed.intent}")
            print(f"   Categories: {', '.join(parsed.categories[:3])}")
            if parsed.entities:
                entities_str = ', '.join(
                    f"{k}={v[:2]}" for k, v in list(parsed.entities.items())[:3]
                )
                print(f"   Entities: {entities_str}")
        
        # 2. Generate query
        print("\n🔮 Generating query...")
        query = self.query_generator.generate_query(parsed, top_k=top_k)
        
        # 3. Retrieve templates
        print("\n🔎 Searching vector database...")
        templates = self.retriever.retrieve(query)
        print(f"   Found {len(templates)} candidates")
        
        # 4. Rank templates
        print("\n⚖️  Ranking by relevance...")
        ranked = self.ranker.rank(templates, parsed)
        
        # 5. Display results
        if show_details:
            self._display_results(ranked, parsed)
        
        # Return structured data
        return {
            'requirement': requirement,
            'parsed': parsed,
            'results': ranked,
            'timestamp': datetime.now().isoformat()
        }
    
    def _display_results(self, ranked, parsed):
        """Display ranked results."""
        print(f"\n{'=' * 60}")
        print("📊 RESULTS")
        print("=" * 60)
        
        if not ranked:
            print("\n❌ No relevant templates found")
            return
        
        for i, rt in enumerate(ranked[:10], 1):  # Show top 10
            template = rt.template
            
            print(f"\n{i}. {template.module_path}")
            print(f"   Relevance: {rt.relevance_score:.3f} (Similarity: {template.similarity_score:.3f})")
            print(f"   {rt.explanation}")
            
            # Show parameter summary
            param_count = template.metadata.get('param_count', 0)
            if param_count > 0:
                print(f"   Parameters ({param_count}):", end=" ")
                params = list(template.parameters.keys())[:3]
                print(', '.join(params), end="")
                if len(template.parameters) > 3:
                    print(f", ... (+{len(template.parameters) - 3} more)")
                else:
                    print()
            
            # Show description
            desc = template.metadata.get('description', '')
            if desc:
                print(f"   📄 {desc[:100]}{'...' if len(desc) > 100 else ''}")
    
    def interactive_mode(self):
        """Run in interactive mode."""
        print("\n🎯 Interactive Mode")
        print("=" * 60)
        print("Enter requirements (or 'quit' to exit)")
        print("Example: 'Setup virtual server for load balancing'")
        print()
        
        while True:
            try:
                requirement = input("\n📝 Requirement: ").strip()
                
                if requirement.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                if not requirement:
                    continue
                
                # Retrieve and display
                self.retrieve(requirement, top_k=5, show_details=True)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    def batch_mode(self, requirements: list, output_file: str = None):
        """
        Process multiple requirements in batch.
        
        Args:
            requirements: List of requirement strings
            output_file: Optional JSON output file
        """
        print(f"\n📦 Batch Mode: Processing {len(requirements)} requirements")
        print("=" * 60)
        
        all_results = []
        
        for i, req in enumerate(requirements, 1):
            print(f"\n[{i}/{len(requirements)}]")
            result = self.retrieve(req, top_k=3, show_details=True)
            all_results.append(result)
        
        # Save to file if specified
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert results to serializable format
            serializable = []
            for result in all_results:
                serializable.append({
                    'requirement': result['requirement'],
                    'timestamp': result['timestamp'],
                    'results': [
                        {
                            'rank': rt.rank,
                            'module_path': rt.template.module_path,
                            'relevance_score': rt.relevance_score,
                            'similarity_score': rt.template.similarity_score,
                            'explanation': rt.explanation,
                            'parameters': list(rt.template.parameters.keys()),
                            'category': rt.template.metadata.get('category', 'unknown')
                        }
                        for rt in result['results'][:5]
                    ]
                })
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(serializable, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Results saved to: {output_path}")
        
        # Display summary statistics
        print(f"\n{'=' * 60}")
        print("📈 SUMMARY")
        print("=" * 60)
        print(f"   Total requirements: {len(requirements)}")
        print(f"   Total results: {sum(len(r['results']) for r in all_results)}")
        
        # Token usage
        token_stats = self.query_generator.get_token_stats()
        print(f"\n💰 Token Usage:")
        print(f"   Tokens: {token_stats['tokens_used']}")
        print(f"   Cost: ${token_stats['estimated_cost_usd']:.6f}")


def main():
    """Main entry point."""
    # Initialize system
    try:
        system = TemplateRetrievalSystem()
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        sys.exit(1)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--interactive', '-i']:
            # Interactive mode
            system.interactive_mode()
        elif sys.argv[1] in ['--batch', '-b']:
            # Batch mode from file
            if len(sys.argv) < 3:
                print("Usage: python retrieve_templates.py --batch <requirements_file>")
                sys.exit(1)
            
            req_file = Path(sys.argv[2])
            if not req_file.exists():
                print(f"❌ File not found: {req_file}")
                sys.exit(1)
            
            # Read requirements (one per line)
            with open(req_file, 'r', encoding='utf-8') as f:
                requirements = [line.strip() for line in f if line.strip()]
            
            output_file = sys.argv[3] if len(sys.argv) > 3 else "data/results/retrieval_results.json"
            system.batch_mode(requirements, output_file)
        else:
            # Single requirement from command line
            requirement = ' '.join(sys.argv[1:])
            system.retrieve(requirement, top_k=5, show_details=True)
    else:
        # Default: Interactive mode
        system.interactive_mode()


if __name__ == "__main__":
    main()
