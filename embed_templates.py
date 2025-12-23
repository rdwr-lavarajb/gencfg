"""
Phase 3 Main Script: Embed Templates
Load Phase 2 templates, generate embeddings, and store in ChromaDB.

Usage:
    python embed_templates.py [template_file]
    
    If no template file specified, uses the most recent from data/templates/
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from phase3.embedding_generator import EmbeddingGenerator
from phase3.vector_store import VectorStore


class TemplateEmbedder:
    """Orchestrates the template embedding pipeline."""
    
    def __init__(self):
        """Initialize embedding generator and vector store."""
        # Load environment variables
        load_dotenv()
        
        print("🚀 Phase 3: Embedding & Storage")
        print("=" * 60)
        
        # Initialize components
        print("\n📦 Initializing components...")
        self.generator = EmbeddingGenerator()
        self.store = VectorStore()
        
        print(f"✅ Embedding model: {self.generator.EMBEDDING_MODEL}")
        print(f"✅ Vector store: {self.store.COLLECTION_NAME}")
        print(f"✅ Storage location: {self.store.persist_directory}")
    
    def find_latest_template_file(self) -> Path:
        """
        Find the most recent templated_modules_*.json file.
        
        Returns:
            Path to latest template file
        """
        templates_dir = Path("data/templates")
        if not templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {templates_dir}")
        
        # Find all template files
        template_files = list(templates_dir.glob("templated_modules_*.json"))
        
        if not template_files:
            raise FileNotFoundError(f"No template files found in {templates_dir}")
        
        # Sort by modification time, most recent first
        latest = sorted(template_files, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        
        return latest
    
    def load_templates(self, file_path: Path) -> dict:
        """
        Load templates from JSON file.
        
        Args:
            file_path: Path to templated_modules_*.json
            
        Returns:
            Dict with metadata and templates
        """
        print(f"\n📂 Loading templates from: {file_path.name}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metadata = data.get('metadata', {})
        templates = data.get('templates', [])
        
        print(f"✅ Loaded {len(templates)} templates")
        print(f"   Phase: {metadata.get('phase', 'unknown')}")
        print(f"   Created: {metadata.get('timestamp', 'unknown')}")
        
        return data
    
    def embed_and_store(self, templates: list) -> dict:
        """
        Generate embeddings and store in ChromaDB.
        
        Args:
            templates: List of template dicts from Phase 2
            
        Returns:
            Dict with processing statistics
        """
        print(f"\n🔮 Generating embeddings...")
        print(f"   Model: {self.generator.EMBEDDING_MODEL}")
        print(f"   Batch processing: {len(templates)} templates")
        
        start_time = datetime.now()
        
        # Generate embeddings in batch
        embedded_templates = self.generator.embed_templates_batch(templates)
        
        embedding_time = (datetime.now() - start_time).total_seconds()
        
        print(f"✅ Generated {len(embedded_templates)} embeddings in {embedding_time:.2f}s")
        
        # Store in ChromaDB
        print(f"\n💾 Storing in ChromaDB...")
        
        module_paths = [t.module_path for t in embedded_templates]
        embeddings = [t.embedding for t in embedded_templates]
        documents = [t.document_text for t in embedded_templates]
        metadatas = [t.metadata for t in embedded_templates]
        
        template_ids = self.store.add_templates(
            module_paths=module_paths,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        print(f"✅ Stored {len(template_ids)} templates")
        
        # Get statistics
        token_stats = self.generator.get_token_stats()
        collection_stats = self.store.get_collection_stats()
        
        return {
            'templates_embedded': len(embedded_templates),
            'embedding_time_seconds': embedding_time,
            'tokens_used': token_stats['tokens_used'],
            'estimated_cost_usd': token_stats['estimated_cost_usd'],
            'embedding_model': token_stats['model'],
            'collection_name': collection_stats['collection_name'],
            'total_templates_in_db': collection_stats['total_templates'],
            'storage_location': collection_stats['persist_directory']
        }
    
    def display_sample_results(self):
        """Display sample templates and search test."""
        print(f"\n📊 Sample Templates in ChromaDB:")
        print("=" * 60)
        
        templates = self.store.list_all_templates()
        
        for i, template in enumerate(templates[:5], 1):
            print(f"\n{i}. {template['module_path']}")
            print(f"   Category: {template['category']}")
            print(f"   Parameters: {template['param_count']}")
            print(f"   Examples: {template['examples_seen']}")
    
    def run(self, template_file: Path = None):
        """
        Execute the complete embedding pipeline.
        
        Args:
            template_file: Optional path to template file (auto-detect if None)
        """
        try:
            # Find or use provided template file
            if template_file is None:
                template_file = self.find_latest_template_file()
            
            # Load templates
            data = self.load_templates(template_file)
            templates = data['templates']
            
            if not templates:
                print("❌ No templates found in file")
                return
            
            # Embed and store
            stats = self.embed_and_store(templates)
            
            # Display results
            print(f"\n" + "=" * 60)
            print("✅ PHASE 3 COMPLETE")
            print("=" * 60)
            print(f"\n📈 Statistics:")
            print(f"   Templates embedded: {stats['templates_embedded']}")
            print(f"   Embedding time: {stats['embedding_time_seconds']:.2f}s")
            print(f"   Tokens used: {stats['tokens_used']:,}")
            print(f"   Estimated cost: ${stats['estimated_cost_usd']:.6f}")
            print(f"   Model: {stats['embedding_model']}")
            print(f"\n💾 ChromaDB Storage:")
            print(f"   Collection: {stats['collection_name']}")
            print(f"   Total templates: {stats['total_templates_in_db']}")
            print(f"   Location: {stats['storage_location']}")
            
            # Show sample results
            self.display_sample_results()
            
            print(f"\n🎯 Next Steps:")
            print(f"   - Test search: See sample queries below")
            print(f"   - Phase 4: Implement retrieval system")
            print(f"   - Add more configs to improve templates")
            
        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """Main entry point."""
    # Parse command line arguments
    template_file = None
    if len(sys.argv) > 1:
        template_file = Path(sys.argv[1])
        if not template_file.exists():
            print(f"❌ Error: File not found: {template_file}")
            sys.exit(1)
    
    # Run embedder
    embedder = TemplateEmbedder()
    embedder.run(template_file)


if __name__ == "__main__":
    main()
