"""
Pattern retriever for finding similar crawling patterns.

Retrieves and ranks patterns from the vector store based on
similarity to the target URL and context.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import json

from .vector_store import VectorStore
from .embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class PatternRetriever:
    """
    Retrieve similar crawling patterns from knowledge base.

    Uses vector similarity search to find patterns that worked well
    on similar URLs in the past.

    Example:
        >>> retriever = PatternRetriever(vector_store, embedding_generator)
        >>> patterns = retriever.retrieve_patterns(
        ...     url="https://example.com/news",
        ...     n_results=5,
        ...     min_similarity=0.7
        ... )
        >>> best_pattern = patterns[0]["pattern"]
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_generator: EmbeddingGenerator
    ):
        """
        Initialize pattern retriever.

        Args:
            vector_store: Vector database instance
            embedding_generator: Embedding generator instance
        """
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator

    def retrieve_patterns(
        self,
        url: str,
        n_results: int = 5,
        min_similarity: float = 0.0,
        min_success_rate: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar patterns for a URL.

        Args:
            url: Target URL
            n_results: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0-1)
            min_success_rate: Minimum success rate threshold (0-1)
            filters: Additional metadata filters

        Returns:
            List of similar patterns with metadata, sorted by similarity

        Example:
            >>> patterns = retriever.retrieve_patterns(
            ...     url="https://example.com/news",
            ...     n_results=5,
            ...     min_success_rate=0.8
            ... )
        """
        # 1. Generate query embedding
        query_embedding = self.embedding_generator.generate_url_embedding(url)

        # 2. Build metadata filters
        where_filters = {}
        if min_success_rate > 0:
            where_filters["success_rate"] = {"$gte": min_success_rate}

        if filters:
            where_filters.update(filters)

        # 3. Search vector store
        results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=n_results * 2,  # Get more, then filter
            where=where_filters if where_filters else None
        )

        # 4. Filter by similarity and sort
        filtered_results = []
        for result in results:
            similarity = result.get("similarity", 0.0)

            if similarity >= min_similarity:
                # Parse pattern from metadata
                metadata = result["metadata"]
                pattern_str = metadata.get("pattern", "{}")

                try:
                    pattern = json.loads(pattern_str)
                except:
                    pattern = {}

                filtered_results.append({
                    "id": result["id"],
                    "url": metadata.get("url", ""),
                    "pattern": pattern,
                    "similarity": similarity,
                    "success_rate": metadata.get("success_rate", 0.0),
                    "items_count": metadata.get("items_count", 0),
                    "timestamp": metadata.get("timestamp", ""),
                    "metadata": metadata
                })

        # 5. Sort by similarity (descending) and limit
        filtered_results.sort(key=lambda x: x["similarity"], reverse=True)
        return filtered_results[:n_results]

    def retrieve_by_domain(
        self,
        domain: str,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve patterns for a specific domain.

        Args:
            domain: Domain name (e.g., "example.com")
            n_results: Maximum number of results

        Returns:
            List of patterns for the domain
        """
        # Filter by domain in metadata
        results = self.vector_store.search(
            query_embedding=self.embedding_generator.generate_embedding(domain),
            n_results=n_results * 2,
            where={"domain": domain}
        )

        return results[:n_results]

    def retrieve_best_pattern(
        self,
        url: str,
        min_success_rate: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve the single best pattern for a URL.

        Selects the pattern with the highest combination of
        similarity and success rate.

        Args:
            url: Target URL
            min_success_rate: Minimum success rate threshold

        Returns:
            Best pattern or None if no suitable pattern found
        """
        patterns = self.retrieve_patterns(
            url=url,
            n_results=10,
            min_success_rate=min_success_rate
        )

        if not patterns:
            return None

        # Score by combined metric
        def score_pattern(p):
            # Weight similarity 60%, success rate 40%
            return p["similarity"] * 0.6 + p["success_rate"] * 0.4

        # Return highest scored pattern
        best = max(patterns, key=score_pattern)
        return best

    def retrieve_with_adaptation(
        self,
        url: str,
        current_context: Optional[Dict[str, Any]] = None,
        n_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve patterns and adapt them to current context.

        Args:
            url: Target URL
            current_context: Current crawling context
            n_results: Number of results to return

        Returns:
            Adapted patterns
        """
        # Retrieve similar patterns
        patterns = self.retrieve_patterns(url, n_results=n_results)

        # Adapt each pattern to current context
        adapted = []
        for pattern_info in patterns:
            adapted_pattern = self._adapt_pattern(
                pattern_info["pattern"],
                current_context
            )

            adapted.append({
                **pattern_info,
                "pattern": adapted_pattern,
                "adapted": True
            })

        return adapted

    def _adapt_pattern(
        self,
        pattern: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Adapt a pattern to current context.

        Args:
            pattern: Original pattern
            context: Current crawling context

        Returns:
            Adapted pattern
        """
        if not context:
            return pattern

        adapted = pattern.copy()

        # Adjust based on context
        if context.get("javascript_heavy", False):
            adapted["use_playwright"] = True
            adapted["wait_for_selector"] = True

        if context.get("pagination_detected", False):
            adapted["handle_pagination"] = True

        if context.get("rate_limited", False):
            adapted["delay"] = adapted.get("delay", 1) * 2
            adapted["use_proxy"] = True

        return adapted

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about patterns in the knowledge base.

        Returns:
            Statistics dictionary
        """
        stats = self.vector_store.get_statistics()

        # Additional retriever-specific stats
        stats["embedding_dimension"] = self.embedding_generator.get_embedding_dimension()
        stats["embedding_model"] = self.embedding_generator.model_name

        return stats

    def find_failing_patterns(
        self,
        url: str,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Find patterns that previously failed for similar URLs.

        Useful for avoiding known bad patterns.

        Args:
            url: Target URL
            threshold: Maximum success rate to consider as "failing"

        Returns:
            List of failing patterns
        """
        results = self.vector_store.search(
            query_embedding=self.embedding_generator.generate_url_embedding(url),
            n_results=10
        )

        failing = []
        for result in results:
            metadata = result["metadata"]
            success_rate = metadata.get("success_rate", 1.0)

            if success_rate < threshold:
                failing.append({
                    "url": metadata.get("url", ""),
                    "pattern": json.loads(metadata.get("pattern", "{}")),
                    "success_rate": success_rate,
                    "failure_reason": metadata.get("failure_reason", "Unknown")
                })

        return failing

    def recommend_from_similar_domains(
        self,
        url: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recommend patterns from domains with similar structures.

        Args:
            url: Target URL
            n_results: Number of recommendations

        Returns:
            Recommended patterns from similar domains
        """
        from urllib.parse import urlparse

        target_domain = urlparse(url).netloc
        target_parts = target_domain.split(".")

        # Find similar domains (same TLD, similar structure)
        similar_domains = []
        for i in range(len(target_parts)):
            # Create domain variations
            if i > 0:
                similar_domain = ".".join(target_parts[i:])
                similar_domains.append(similar_domain)

        # Retrieve patterns for similar domains
        recommendations = []
        for domain in similar_domains:
            patterns = self.retrieve_by_domain(domain, n_results=2)
            recommendations.extend(patterns)

        return recommendations[:n_results]
