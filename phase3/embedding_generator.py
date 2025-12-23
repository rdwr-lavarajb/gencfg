"""
Phase 3: Embedding Generator
Converts templates into vector embeddings using OpenAI text-embedding-3-small.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import openai
from openai import OpenAI
import os
from datetime import datetime


@dataclass
class EmbeddedTemplate:
    """Template with its vector embedding."""
    module_path: str
    embedding: List[float]
    document_text: str
    metadata: Dict[str, Any]
    embedding_model: str
    created_at: str


class EmbeddingGenerator:
    """Generates embeddings for configuration templates."""
    
    # Model configuration
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536
    BATCH_SIZE = 100  # OpenAI limit
    
    def __init__(self, api_key: str = None):
        """
        Initialize the embedding generator.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required (OPENAI_API_KEY env var or api_key parameter)")
        
        self.client = OpenAI(api_key=self.api_key)
        self.tokens_used = 0
    
    def build_document_text(self, template: Dict[str, Any]) -> str:
        """
        Build searchable text from template for embedding.
        
        The document text combines:
        - Module path and category
        - Description
        - Parameter names and descriptions
        - Template preview (first 200 chars)
        
        Args:
            template: Template dict from Phase 2
            
        Returns:
            Formatted text string for embedding
        """
        parts = []
        
        # Module identification
        parts.append(f"Module: {template['module_path']}")
        parts.append(f"Category: {template.get('category', 'unknown')}")
        
        # Description
        if template.get('description'):
            parts.append(f"Description: {template['description']}")
        
        # Tags
        if template.get('tags'):
            tags_str = ", ".join(template['tags'])
            parts.append(f"Tags: {tags_str}")
        
        # Parameters
        params = template.get('parameters', {})
        if params:
            param_details = []
            for param_name, param_info in params.items():
                desc = param_info.get('description', '')
                param_type = param_info.get('type', 'unknown')
                param_details.append(f"{param_name} ({param_type}): {desc}")
            parts.append(f"Parameters: {'; '.join(param_details)}")
        
        # Template preview
        template_obj = template.get('template', {})
        if template_obj:
            header = template_obj.get('header', '')
            body = template_obj.get('body', [])
            template_lines = [header] + body[:5]  # First 5 lines
            template_preview = '\n'.join(template_lines)[:200]
            parts.append(f"Template: {template_preview}")
        
        return '\n'.join(parts)
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (1536 dimensions)
        """
        response = self.client.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=text,
            encoding_format="float"
        )
        
        # Track token usage
        self.tokens_used += response.usage.total_tokens
        
        return response.data[0].embedding
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to embed (max 100)
            
        Returns:
            List of embedding vectors
        """
        if len(texts) > self.BATCH_SIZE:
            raise ValueError(f"Batch size exceeds limit: {len(texts)} > {self.BATCH_SIZE}")
        
        response = self.client.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=texts,
            encoding_format="float"
        )
        
        # Track token usage
        self.tokens_used += response.usage.total_tokens
        
        # Sort by index to maintain order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]
    
    def embed_template(self, template: Dict[str, Any]) -> EmbeddedTemplate:
        """
        Generate embedding for a single template.
        
        Args:
            template: Template dict from Phase 2
            
        Returns:
            EmbeddedTemplate with vector and metadata
        """
        # Build document text
        doc_text = self.build_document_text(template)
        
        # Generate embedding
        embedding = self.generate_embedding(doc_text)
        
        # Extract key metadata
        metadata = {
            'module_path': template['module_path'],
            'category': template.get('category', 'unknown'),
            'module_type': template.get('module_type', 'standard'),
            'index_required': template.get('index_required', False),
            'param_count': len(template.get('parameters', {})),
            'has_defaults': bool(template.get('learned_defaults', {})),
            'examples_seen': template.get('examples_seen', 0),
            'tags': template.get('tags', []),
            'description': template.get('description', ''),
            # Store full template and parameters for retrieval
            'template': template.get('template', {}),
            'parameters': template.get('parameters', {}),
            'learned_defaults': template.get('learned_defaults', {}),
            'dependencies': template.get('dependencies', {}),
        }
        
        return EmbeddedTemplate(
            module_path=template['module_path'],
            embedding=embedding,
            document_text=doc_text,
            metadata=metadata,
            embedding_model=self.EMBEDDING_MODEL,
            created_at=datetime.now().isoformat()
        )
    
    def embed_templates_batch(self, templates: List[Dict[str, Any]]) -> List[EmbeddedTemplate]:
        """
        Generate embeddings for multiple templates efficiently.
        
        Args:
            templates: List of template dicts from Phase 2
            
        Returns:
            List of EmbeddedTemplates
        """
        # Build document texts
        doc_texts = [self.build_document_text(t) for t in templates]
        
        # Generate embeddings in batches
        all_embeddings = []
        for i in range(0, len(doc_texts), self.BATCH_SIZE):
            batch = doc_texts[i:i + self.BATCH_SIZE]
            embeddings = self.generate_embeddings_batch(batch)
            all_embeddings.extend(embeddings)
        
        # Create EmbeddedTemplate objects
        results = []
        for template, embedding, doc_text in zip(templates, all_embeddings, doc_texts):
            metadata = {
                'module_path': template['module_path'],
                'category': template.get('category', 'unknown'),
                'module_type': template.get('module_type', 'standard'),
                'index_required': template.get('index_required', False),
                'param_count': len(template.get('parameters', {})),
                'has_defaults': bool(template.get('learned_defaults', {})),
                'examples_seen': template.get('examples_seen', 0),
                'tags': template.get('tags', []),
                'description': template.get('description', ''),
                'template': template.get('template', {}),
                'parameters': template.get('parameters', {}),
                'learned_defaults': template.get('learned_defaults', {}),
                'dependencies': template.get('dependencies', {}),
            }
            
            results.append(EmbeddedTemplate(
                module_path=template['module_path'],
                embedding=embedding,
                document_text=doc_text,
                metadata=metadata,
                embedding_model=self.EMBEDDING_MODEL,
                created_at=datetime.now().isoformat()
            ))
        
        return results
    
    def get_token_stats(self) -> Dict[str, Any]:
        """
        Get token usage statistics.
        
        Returns:
            Dict with tokens used and estimated cost
        """
        # text-embedding-3-small: $0.02 per 1M tokens
        cost = (self.tokens_used / 1_000_000) * 0.02
        
        return {
            'tokens_used': self.tokens_used,
            'estimated_cost_usd': round(cost, 6),
            'model': self.EMBEDDING_MODEL
        }
