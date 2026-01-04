"""
Knowledge base management for RAG system.

Provides high-level interface for managing crawling patterns
and learned experiences.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from .vector_store import VectorStore
from .embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    Knowledge base for storing and managing crawling patterns.

    Acts as a high-level interface to the vector store with
    additional functionality like import/export, analytics,
    and pattern management.

    Example:
        >>> kb = KnowledgeBase(vector_store, embedding_generator)
        >>>
        >>> # Store a successful pattern
        >>> kb.store_pattern(
        ...     url="https://example.com/news",
        ...     pattern={"css": ".news-item"},
        ...     metadata={"success_rate": 0.95}
        ... )
        >>>
        >>> # Get statistics
        >>> stats = kb.get_statistics()
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_generator: EmbeddingGenerator
    ):
        """
        Initialize knowledge base.

        Args:
            vector_store: Vector store instance
            embedding_generator: Embedding generator instance
        """
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator

    def store_pattern(
        self,
        url: str,
        pattern: Dict[str, Any],
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a crawling pattern in the knowledge base.

        Args:
            url: URL that was crawled
            pattern: Crawling pattern
            embedding: Vector embedding
            metadata: Additional metadata

        Returns:
            Pattern ID
        """
        return self.vector_store.add_pattern(
            url=url,
            pattern=pattern,
            embedding=embedding,
            metadata=metadata
        )

    def get_best_patterns(
        self,
        domain: Optional[str] = None,
        min_success_rate: float = 0.8,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get best performing patterns.

        Args:
            domain: Filter by domain (optional)
            min_success_rate: Minimum success rate
            limit: Maximum number of results

        Returns:
            List of best patterns
        """
        # Build filters
        where_filters = {"success_rate": {"$gte": min_success_rate}}
        if domain:
            where_filters["domain"] = domain

        # Query with a dummy embedding (will be overridden by filters)
        dummy_embedding = [0.0] * self.embedding_generator.get_embedding_dimension()

        results = self.vector_store.search(
            query_embedding=dummy_embedding,
            n_results=limit * 2,
            where=where_filters
        )

        # Sort by success rate
        sorted_results = sorted(
            results,
            key=lambda x: x["metadata"].get("success_rate", 0.0),
            reverse=True
        )

        return sorted_results[:limit]

    def get_patterns_by_domain(
        self,
        domain: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get all patterns for a specific domain.

        Args:
            domain: Domain name
            limit: Maximum number of results

        Returns:
            List of patterns for the domain
        """
        query_embedding = [0.0] * self.embedding_generator.get_embedding_dimension()

        results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=limit,
            where={"domain": domain}
        )

        return results

    def analyze_domain(self, domain: str) -> Dict[str, Any]:
        """
        Analyze crawling patterns for a domain.

        Args:
            domain: Domain to analyze

        Returns:
            Analysis results
        """
        patterns = self.get_patterns_by_domain(domain, limit=100)

        if not patterns:
            return {
                "domain": domain,
                "total_patterns": 0,
                "avg_success_rate": 0.0,
                "best_pattern": None,
                "recommendation": "No patterns found"
            }

        # Calculate statistics
        success_rates = [
            p["metadata"].get("success_rate", 0.0)
            for p in patterns
        ]

        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0

        # Find best pattern
        best_pattern = max(patterns, key=lambda x: x["metadata"].get("success_rate", 0.0))

        # Generate recommendation
        if avg_success_rate > 0.9:
            recommendation = "Domain works very well with current patterns"
        elif avg_success_rate > 0.7:
            recommendation = "Domain performs adequately"
        else:
            recommendation = "Domain needs pattern optimization"

        return {
            "domain": domain,
            "total_patterns": len(patterns),
            "avg_success_rate": avg_success_rate,
            "best_pattern": {
                "id": best_pattern["id"],
                "success_rate": best_pattern["metadata"].get("success_rate", 0.0),
                "pattern": best_pattern["metadata"].get("pattern", {})
            },
            "recommendation": recommendation
        }

    def export(self, filepath: str) -> None:
        """
        Export knowledge base to JSON file.

        Args:
            filepath: Path to export file
        """
        # Get all patterns
        all_patterns = []
        try:
            # Try to get all patterns (up to 1000)
            dummy_embedding = [0.0] * self.embedding_generator.get_embedding_dimension()
            results = self.vector_store.search(
                query_embedding=dummy_embedding,
                n_results=1000
            )
            all_patterns = results
        except Exception as e:
            logger.warning(f"Could not export all patterns: {e}")

        # Prepare export data
        export_data = {
            "version": "1.0",
            "export_date": datetime.now().isoformat(),
            "total_patterns": len(all_patterns),
            "patterns": []
        }

        for pattern_data in all_patterns:
            export_data["patterns"].append({
                "id": pattern_data["id"],
                "url": pattern_data["metadata"].get("url"),
                "domain": pattern_data["metadata"].get("domain"),
                "pattern": pattern_data["metadata"].get("pattern"),
                "success_rate": pattern_data["metadata"].get("success_rate"),
                "items_count": pattern_data["metadata"].get("items_count"),
                "timestamp": pattern_data["metadata"].get("timestamp")
            })

        # Write to file
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported {len(all_patterns)} patterns to {filepath}")

    def import_kb(self, filepath: str) -> None:
        """
        Import knowledge base from JSON file.

        Args:
            filepath: Path to import file
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Import file not found: {filepath}")

        with open(filepath, 'r') as f:
            import_data = json.load(f)

        logger.info(f"Importing {import_data['total_patterns']} patterns from {filepath}")

        # Import each pattern
        imported_count = 0
        for pattern_data in import_data.get("patterns", []):
            try:
                # Generate new embedding
                url = pattern_data["url"]
                pattern = pattern_data["pattern"]

                embedding = self.embedding_generator.generate_url_embedding(url, pattern)

                # Store pattern
                self.store_pattern(
                    url=url,
                    pattern=pattern,
                    embedding=embedding,
                    metadata=pattern_data
                )

                imported_count += 1

            except Exception as e:
                logger.warning(f"Failed to import pattern {pattern_data.get('id')}: {e}")

        logger.info(f"Successfully imported {imported_count}/{import_data['total_patterns']} patterns")

    def get_insights(self) -> Dict[str, Any]:
        """
        Get insights about the knowledge base.

        Returns:
            Insights and statistics
        """
        stats = self.vector_store.get_statistics()

        # Get top domains
        try:
            dummy_embedding = [0.0] * self.embedding_generator.get_embedding_dimension()
            all_patterns = self.vector_store.search(
                query_embedding=dummy_embedding,
                n_results=1000
            )

            # Count patterns per domain
            domain_counts = {}
            for pattern in all_patterns:
                domain = pattern["metadata"].get("domain", "unknown")
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

            # Sort by count
            top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            stats["top_domains"] = [
                {"domain": domain, "pattern_count": count}
                for domain, count in top_domains
            ]

        except Exception as e:
            logger.warning(f"Could not calculate domain insights: {e}")

        return stats

    def cleanup_old_patterns(
        self,
        days_old: int = 30,
        min_success_rate: float = 0.5
    ) -> int:
        """
        Remove old low-quality patterns.

        Args:
            days_old: Minimum age in days
            min_success_rate: Patterns below this rate are candidates

        Returns:
            Number of patterns removed
        """
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=days_old)

        # Get all patterns
        try:
            dummy_embedding = [0.0] * self.embedding_generator.get_embedding_dimension()
            all_patterns = self.vector_store.search(
                query_embedding=dummy_embedding,
                n_results=1000
            )

            removed_count = 0
            for pattern in all_patterns:
                timestamp_str = pattern["metadata"].get("timestamp", "")
                success_rate = pattern["metadata"].get("success_rate", 1.0)

                if not timestamp_str:
                    continue

                try:
                    timestamp = datetime.fromisoformat(timestamp_str)

                    # Check if old and low quality
                    if timestamp < cutoff_date and success_rate < min_success_rate:
                        if self.vector_store.delete_pattern(pattern["id"]):
                            removed_count += 1

                except:
                    continue

            logger.info(f"Cleaned up {removed_count} old low-quality patterns")
            return removed_count

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0

    def __repr__(self) -> str:
        """String representation."""
        return f"KnowledgeBase(patterns={self.vector_store.count_patterns()})"
