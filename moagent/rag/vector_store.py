"""
Vector store implementation using ChromaDB.

Provides persistent storage for crawling patterns with semantic search capabilities.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from ..config.settings import Config

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector database wrapper for storing and retrieving crawling patterns.

    Uses ChromaDB for persistent vector storage with:
    - Automatic persistence
    - Fast similarity search (HNSW index)
    - Metadata filtering
    - Collection management

    Example:
        >>> store = VectorStore(collection_name="crawling_patterns")
        >>> store.add_pattern(
        ...     url="https://example.com/news",
        ...     pattern={"selector": ".news-item"},
        ...     metadata={"success_rate": 0.95}
        ... )
        >>> results = store.search("https://similar-site.com/news", n_results=5)
    """

    def __init__(
        self,
        collection_name: str = "crawling_patterns",
        persist_directory: Optional[str] = None,
        embedding_function: Optional[Any] = None
    ):
        """
        Initialize vector store.

        Args:
            collection_name: Name of the collection
            persist_directory: Directory for persistence (default: ./data/vector_db)
            embedding_function: Custom embedding function (optional)
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "ChromaDB is required for VectorStore. "
                "Install it with: pip install chromadb"
            )

        self.collection_name = collection_name
        self.persist_directory = persist_directory or "./data/vector_db"

        # Ensure directory exists
        os.makedirs(self.persist_directory, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection: {collection_name}")

        self.embedding_function = embedding_function

    def add_pattern(
        self,
        url: str,
        pattern: Dict[str, Any],
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a crawling pattern to the vector store.

        Args:
            url: URL that was crawled
            pattern: Crawling pattern (selectors, xpath, etc.)
            embedding: Vector embedding of the pattern
            metadata: Additional metadata (success rate, items count, etc.)

        Returns:
            ID of the added pattern

        Example:
            >>> store.add_pattern(
            ...     url="https://example.com",
            ...     pattern={"css": ".content"},
            ...     embedding=[0.1, 0.2, ...],
            ...     metadata={"success": True, "items": 10}
            ... )
        """
        # Prepare document text
        document_text = self._prepare_document(url, pattern, metadata)

        # Prepare metadata
        metadata_dict = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {}),
            "pattern": json.dumps(pattern)
        }

        # Generate unique ID
        pattern_id = f"{url}_{datetime.now().isoformat()}"

        # Add to collection
        self.collection.add(
            embeddings=[embedding],
            documents=[document_text],
            metadatas=[metadata_dict],
            ids=[pattern_id]
        )

        logger.info(f"Added pattern {pattern_id} for {url}")
        return pattern_id

    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar patterns using vector similarity.

        Args:
            query_embedding: Query vector embedding
            n_results: Number of results to return
            where: Metadata filter conditions
            where_document: Document filter conditions

        Returns:
            List of similar patterns with metadata

        Example:
            >>> results = store.search(
            ...     query_embedding=[0.1, 0.2, ...],
            ...     n_results=5,
            ...     where={"success_rate": {"$gt": 0.8}}
            ... )
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document
        )

        # Format results
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i, pattern_id in enumerate(results["ids"][0]):
                formatted_results.append({
                    "id": pattern_id,
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None,
                    "similarity": 1 - results["distances"][0][i] if "distances" in results else None
                })

        return formatted_results

    def get_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific pattern by ID.

        Args:
            pattern_id: Pattern ID

        Returns:
            Pattern data or None if not found
        """
        try:
            results = self.collection.get(
                ids=[pattern_id],
                include=["embeddings", "documents", "metadatas"]
            )

            if results["ids"]:
                return {
                    "id": results["ids"][0],
                    "document": results["documents"][0] if results["documents"] else None,
                    "metadata": results["metadatas"][0] if results["metadatas"] else None,
                    "embedding": results["embeddings"][0] if results["embeddings"] else None
                }
        except Exception as e:
            logger.error(f"Error retrieving pattern {pattern_id}: {e}")

        return None

    def update_pattern(
        self,
        pattern_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update pattern metadata.

        Args:
            pattern_id: Pattern ID to update
            metadata: New metadata to merge

        Returns:
            True if updated successfully
        """
        try:
            current = self.get_pattern(pattern_id)
            if not current:
                logger.warning(f"Pattern {pattern_id} not found")
                return False

            # Merge metadata
            updated_metadata = {**(current["metadata"] or {}), **(metadata or {})}

            # Update in collection
            self.collection.update(
                ids=[pattern_id],
                metadatas=[updated_metadata]
            )

            logger.info(f"Updated pattern {pattern_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating pattern {pattern_id}: {e}")
            return False

    def delete_pattern(self, pattern_id: str) -> bool:
        """
        Delete a pattern from the store.

        Args:
            pattern_id: Pattern ID to delete

        Returns:
            True if deleted successfully
        """
        try:
            self.collection.delete(ids=[pattern_id])
            logger.info(f"Deleted pattern {pattern_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting pattern {pattern_id}: {e}")
            return False

    def count_patterns(self) -> int:
        """Get total number of patterns in the store."""
        return self.collection.count()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.

        Returns:
            Dictionary with statistics
        """
        total_patterns = self.count_patterns()

        # Sample some patterns to calculate stats
        sample_size = min(100, total_patterns)
        stats = {
            "total_patterns": total_patterns,
            "collection_name": self.collection_name,
            "persist_directory": self.persist_directory
        }

        if total_patterns > 0:
            # Get recent patterns
            try:
                recent = self.collection.get(
                    limit=sample_size,
                    include=["metadatas"]
                )

                if recent["metadatas"]:
                    success_rates = [
                        m.get("success_rate", 0)
                        for m in recent["metadatas"]
                        if "success_rate" in m
                    ]

                    if success_rates:
                        stats["avg_success_rate"] = sum(success_rates) / len(success_rates)
                        stats["min_success_rate"] = min(success_rates)
                        stats["max_success_rate"] = max(success_rates)

            except Exception as e:
                logger.warning(f"Could not calculate statistics: {e}")

        return stats

    def clear_collection(self) -> bool:
        """
        Clear all patterns from the collection.

        Warning: This is irreversible!

        Returns:
            True if cleared successfully
        """
        try:
            # Delete and recreate collection
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Cleared collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            return False

    def _prepare_document(
        self,
        url: str,
        pattern: Dict[str, Any],
        metadata: Optional[Dict[str, Any]]
    ) -> str:
        """
        Prepare document text for embedding.

        Creates a searchable text representation of the pattern.

        Args:
            url: Target URL
            pattern: Crawling pattern
            metadata: Additional metadata

        Returns:
            Text description of the pattern
        """
        parts = [
            f"URL: {url}",
            f"Domain: {self._extract_domain(url)}",
            f"Path: {self._extract_path(url)}"
        ]

        # Add pattern information
        if pattern:
            if "css_selectors" in pattern:
                parts.append(f"CSS Selectors: {', '.join(pattern['css_selectors'])}")
            if "xpath" in pattern:
                parts.append(f"XPath: {pattern['xpath']}")
            if "list_container" in pattern:
                parts.append(f"List Container: {pattern['list_container']}")
            if "item_selector" in pattern:
                parts.append(f"Item Selector: {pattern['item_selector']}")

        # Add metadata
        if metadata:
            if "crawl_mode" in metadata:
                parts.append(f"Crawl Mode: {metadata['crawl_mode']}")
            if "content_type" in metadata:
                parts.append(f"Content Type: {metadata['content_type']}")

        return " | ".join(parts)

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        try:
            return urlparse(url).netloc
        except:
            return "unknown"

    def _extract_path(self, url: str) -> str:
        """Extract path from URL."""
        from urllib.parse import urlparse
        try:
            return urlparse(url).path
        except:
            return "/"

    def __repr__(self) -> str:
        """String representation."""
        return f"VectorStore(collection={self.collection_name}, patterns={self.count_patterns()})"
