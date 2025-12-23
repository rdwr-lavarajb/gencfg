"""
Phase 3: Vector Store
ChromaDB wrapper for storing and retrieving template embeddings.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import hashlib
import json
from datetime import datetime
from pathlib import Path


class VectorStore:
    """ChromaDB wrapper for configuration template storage."""
    
    COLLECTION_NAME = "config_templates"
    
    def __init__(self, persist_directory: str = "data/vectordb"):
        """
        Initialize ChromaDB vector store.
        
        Args:
            persist_directory: Directory for persistent storage
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "Configuration templates with embeddings"}
        )
    
    def _generate_id(self, module_path: str) -> str:
        """
        Generate deterministic ID from module path.
        
        Args:
            module_path: Module path (e.g., "/c/sys/mmgmt")
            
        Returns:
            Hash-based ID
        """
        # Use SHA256 hash for deterministic IDs
        hash_obj = hashlib.sha256(module_path.encode('utf-8'))
        return f"tpl_{hash_obj.hexdigest()[:16]}"
    
    def add_template(
        self,
        module_path: str,
        embedding: List[float],
        document: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Add a single template to the vector store.
        
        Args:
            module_path: Module path identifier
            embedding: Embedding vector (1536 dims)
            document: Searchable text
            metadata: Template metadata
            
        Returns:
            Generated ID
        """
        template_id = self._generate_id(module_path)
        
        # ChromaDB requires metadata values to be strings, ints, floats, or bools
        # Convert complex types to JSON strings
        clean_metadata = self._serialize_metadata(metadata)
        
        self.collection.upsert(
            ids=[template_id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[clean_metadata]
        )
        
        return template_id
    
    def add_templates(
        self,
        module_paths: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add multiple templates in batch (more efficient).
        
        Args:
            module_paths: List of module path identifiers
            embeddings: List of embedding vectors
            documents: List of searchable texts
            metadatas: List of metadata dicts
            
        Returns:
            List of generated IDs
        """
        if not (len(module_paths) == len(embeddings) == len(documents) == len(metadatas)):
            raise ValueError("All input lists must have the same length")
        
        template_ids = [self._generate_id(path) for path in module_paths]
        
        # Serialize all metadata
        clean_metadatas = [self._serialize_metadata(m) for m in metadatas]
        
        self.collection.upsert(
            ids=template_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=clean_metadatas
        )
        
        return template_ids
    
    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for similar templates using cosine similarity.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filters (e.g., {"category": "network_layer3"})
            
        Returns:
            Dict with ids, distances, metadatas, documents
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_dict
        )
        
        # Deserialize metadata
        if results['metadatas'] and results['metadatas'][0]:
            results['metadatas'][0] = [
                self._deserialize_metadata(m) for m in results['metadatas'][0]
            ]
        
        return {
            'ids': results['ids'][0] if results['ids'] else [],
            'distances': results['distances'][0] if results['distances'] else [],
            'metadatas': results['metadatas'][0] if results['metadatas'] else [],
            'documents': results['documents'][0] if results['documents'] else []
        }
    
    def get_by_path(self, module_path: str) -> Optional[Dict[str, Any]]:
        """
        Get template by exact module path.
        
        Args:
            module_path: Module path to retrieve
            
        Returns:
            Template data or None if not found
        """
        template_id = self._generate_id(module_path)
        
        try:
            result = self.collection.get(
                ids=[template_id],
                include=["embeddings", "documents", "metadatas"]
            )
            
            if not result['ids']:
                return None
            
            # Deserialize metadata
            metadata = self._deserialize_metadata(result['metadatas'][0])
            
            return {
                'id': result['ids'][0],
                'embedding': result['embeddings'][0],
                'document': result['documents'][0],
                'metadata': metadata
            }
        except Exception:
            return None
    
    def delete_template(self, module_path: str) -> bool:
        """
        Delete template by module path.
        
        Args:
            module_path: Module path to delete
            
        Returns:
            True if deleted, False if not found
        """
        template_id = self._generate_id(module_path)
        
        try:
            self.collection.delete(ids=[template_id])
            return True
        except Exception:
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.
        
        Returns:
            Dict with count and metadata
        """
        count = self.collection.count()
        
        return {
            'collection_name': self.COLLECTION_NAME,
            'total_templates': count,
            'persist_directory': str(self.persist_directory),
            'collection_metadata': self.collection.metadata
        }
    
    def list_all_templates(self) -> List[Dict[str, Any]]:
        """
        List all templates in the collection.
        
        Returns:
            List of template metadata
        """
        result = self.collection.get(
            include=["metadatas"]
        )
        
        templates = []
        for i, template_id in enumerate(result['ids']):
            metadata = self._deserialize_metadata(result['metadatas'][i])
            templates.append({
                'id': template_id,
                'module_path': metadata.get('module_path'),
                'category': metadata.get('category'),
                'param_count': metadata.get('param_count'),
                'examples_seen': metadata.get('examples_seen')
            })
        
        return templates
    
    def _serialize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert metadata to ChromaDB-compatible format.
        
        ChromaDB only supports: str, int, float, bool
        Complex types are converted to JSON strings.
        
        Args:
            metadata: Original metadata dict
            
        Returns:
            Serialized metadata
        """
        clean = {}
        
        for key, value in metadata.items():
            if value is None:
                continue
            elif isinstance(value, (str, int, float, bool)):
                clean[key] = value
            elif isinstance(value, (list, dict)):
                # Serialize complex types as JSON
                clean[f"{key}_json"] = json.dumps(value)
            else:
                # Convert other types to string
                clean[key] = str(value)
        
        return clean
    
    def _deserialize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert ChromaDB metadata back to original format.
        
        Args:
            metadata: Serialized metadata from ChromaDB
            
        Returns:
            Deserialized metadata
        """
        clean = {}
        
        for key, value in metadata.items():
            if key.endswith('_json'):
                # Deserialize JSON strings
                original_key = key[:-5]  # Remove '_json' suffix
                try:
                    clean[original_key] = json.loads(value)
                except json.JSONDecodeError:
                    clean[original_key] = value
            else:
                clean[key] = value
        
        return clean
    
    def clear_collection(self):
        """
        Delete all templates from the collection.
        
        WARNING: This is destructive and cannot be undone.
        """
        # Delete the collection
        self.client.delete_collection(name=self.COLLECTION_NAME)
        
        # Recreate empty collection
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "Configuration templates with embeddings"}
        )
