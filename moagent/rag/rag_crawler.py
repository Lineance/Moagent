"""
Main RAG-enhanced crawler.

Integrates vector storage, embeddings, and pattern retrieval
to provide intelligent crawling with continuous learning.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import urlparse

from .vector_store import VectorStore
from .embeddings import EmbeddingGenerator
from .retriever import PatternRetriever
from .knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


class RAGCrawler:
    """
    RAG-enhanced crawler with continuous learning.

    Combines:
    - Vector database for pattern storage
    - Semantic similarity for pattern retrieval
    - LLM-assisted pattern adaptation
    - Continuous learning from results

    Example:
        >>> rag_crawler = RAGCrawler()
        >>>
        >>> # Crawl with RAG enhancement
        >>> result = rag_crawler.crawl(url="https://example.com/news")
        >>>
        >>> # Result includes RAG-recommended pattern
        >>> print(result["pattern_source"])
        'rag_recommended'
        >>> print(result["similarity_score"])
        0.89
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        auto_learn: bool = True,
        min_quality_threshold: float = 0.7
    ):
        """
        Initialize RAG crawler.

        Args:
            vector_store: Vector store instance (created if None)
            embedding_generator: Embedding generator (created if None)
            auto_learn: Automatically learn from successful crawls
            min_quality_threshold: Minimum quality to store pattern
        """
        # Initialize components
        self.vector_store = vector_store or VectorStore()
        self.embedding_generator = embedding_generator or EmbeddingGenerator()

        # Initialize retriever and knowledge base
        self.retriever = PatternRetriever(
            self.vector_store,
            self.embedding_generator
        )
        self.knowledge_base = KnowledgeBase(
            self.vector_store,
            self.embedding_generator
        )

        # Configuration
        self.auto_learn = auto_learn
        self.min_quality_threshold = min_quality_threshold

        logger.info(f"RAGCrawler initialized with {self.vector_store.count_patterns()} patterns")

    def crawl(
        self,
        url: str,
        crawler_func: callable,
        context: Optional[Dict[str, Any]] = None,
        force_rerun: bool = False
    ) -> Dict[str, Any]:
        """
        Crawl a URL with RAG enhancement.

        Args:
            url: URL to crawl
            crawler_func: Function to perform actual crawling
            context: Additional context about the crawl
            force_rerun: Force crawling even if similar URL exists

        Returns:
            Crawl result with metadata

        Example:
            >>> def my_crawler(url, pattern):
            ...     # Actual crawling logic
            ...     return {"items": [...], "success": True}
            >>>
            >>> result = rag_crawler.crawl(
            ...     url="https://example.com",
            ...     crawler_func=my_crawler
            ... )
        """
        result = {
            "url": url,
            "timestamp": datetime.now().isoformat()
        }

        # 1. Check if we have a good pattern for this URL
        best_pattern = self.retriever.retrieve_best_pattern(
            url=url,
            min_success_rate=self.min_quality_threshold
        )

        # 2. Decide on strategy
        if best_pattern and not force_rerun:
            # Use RAG-recommended pattern
            logger.info(f"Using RAG pattern for {url} (similarity: {best_pattern['similarity']:.2f})")

            pattern = best_pattern["pattern"]
            result["pattern_source"] = "rag_recommended"
            result["similarity_score"] = best_pattern["similarity"]
            result["success_rate"] = best_pattern["success_rate"]

        else:
            # Use default/fallback pattern
            logger.info(f"Using default pattern for {url}")
            pattern = self._get_default_pattern(url, context)
            result["pattern_source"] = "default"

        # 3. Execute crawl
        try:
            crawl_result = crawler_func(url, pattern)
            result.update(crawl_result)

            # 4. Learn from result (if enabled and successful)
            if self.auto_learn and self._is_high_quality_result(result):
                self._learn_from_result(url, pattern, result)

            result["rag_used"] = (best_pattern is not None)

        except Exception as e:
            logger.error(f"Crawl failed for {url}: {e}")
            result["error"] = str(e)
            result["success"] = False

            # Learn from failure
            if self.auto_learn:
                self._learn_from_failure(url, pattern, e)

        return result

    def batch_crawl(
        self,
        urls: List[str],
        crawler_func: callable,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Crawl multiple URLs with RAG enhancement.

        Args:
            urls: List of URLs to crawl
            crawler_func: Function to perform actual crawling
            context: Additional context

        Returns:
            List of crawl results

        Example:
            >>> results = rag_crawler.batch_crawl(
            ...     urls=["https://example.com/1", "https://example.com/2"],
            ...     crawler_func=my_crawler
            ... )
            >>> success_count = sum(1 for r in results if r.get("success"))
        """
        results = []

        for i, url in enumerate(urls):
            logger.info(f"Crawling {i+1}/{len(urls)}: {url}")

            result = self.crawl(url, crawler_func, context)
            results.append(result)

        # Summary statistics
        success_count = sum(1 for r in results if r.get("success", False))
        rag_used_count = sum(1 for r in results if r.get("rag_used", False))

        logger.info(f"Batch crawl complete: {success_count}/{len(urls)} successful")
        logger.info(f"RAG patterns used: {rag_used_count}/{len(urls)}")

        return results

    def get_suggested_pattern(
        self,
        url: str,
        n_options: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get suggested patterns for a URL (without crawling).

        Useful for preview and debugging.

        Args:
            url: URL to get suggestions for
            n_options: Number of pattern options to return

        Returns:
            List of suggested patterns with metadata
        """
        patterns = self.retriever.retrieve_patterns(
            url=url,
            n_results=n_options,
            min_success_rate=0.6
        )

        return patterns

    def _get_default_pattern(
        self,
        url: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get default crawling pattern."""
        parsed = urlparse(url)

        default_pattern = {
            "type": "generic",
            "crawl_mode": "auto",
            "selectors": {
                "list_container": None,  # Auto-detect
                "item_selector": None,   # Auto-detect
                "title_selector": None,  # Auto-detect
                "url_selector": None     # Auto-detect
            }
        }

        # Adjust based on URL structure
        if ".xml" in url or "/rss" in url or "/feed" in url:
            default_pattern["type"] = "rss"
            default_pattern["crawl_mode"] = "static"

        return default_pattern

    def _is_high_quality_result(self, result: Dict[str, Any]) -> bool:
        """Check if result is high enough quality to learn from."""
        # Must be successful
        if not result.get("success", False):
            return False

        # Must have retrieved items
        items_count = result.get("items_count", 0)
        if items_count == 0:
            return False

        # Calculate quality score
        quality_score = self._calculate_quality_score(result)
        return quality_score >= self.min_quality_threshold

    def _calculate_quality_score(self, result: Dict[str, Any]) -> float:
        """Calculate quality score for a result."""
        score = 0.0

        # Item count (0-0.3)
        items_count = result.get("items_count", 0)
        score += min(items_count / 100, 1.0) * 0.3

        # Success (0-0.3)
        if result.get("success", False):
            score += 0.3

        # Low error rate (0-0.2)
        error_rate = result.get("error_rate", 0.0)
        score += (1.0 - error_rate) * 0.2

        # Content quality (0-0.2)
        if result.get("has_content", True):
            score += 0.2

        return score

    def _learn_from_result(
        self,
        url: str,
        pattern: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """Learn from a successful crawl result."""
        # Generate embedding
        embedding = self.embedding_generator.generate_url_embedding(url, pattern)

        # Prepare metadata
        metadata = {
            "url": url,
            "domain": urlparse(url).netloc,
            "success": result.get("success", False),
            "items_count": result.get("items_count", 0),
            "success_rate": self._calculate_quality_score(result),
            "timestamp": datetime.now().isoformat(),
            "pattern_type": pattern.get("type", "unknown"),
            "crawl_mode": pattern.get("crawl_mode", "auto")
        }

        # Store in knowledge base
        self.knowledge_base.store_pattern(
            url=url,
            pattern=pattern,
            embedding=embedding,
            metadata=metadata
        )

        logger.info(f"Learned from successful crawl of {url}")

    def _learn_from_failure(
        self,
        url: str,
        pattern: Dict[str, Any],
        error: Exception
    ) -> None:
        """Learn from a failed crawl attempt."""
        # Generate embedding
        embedding = self.embedding_generator.generate_url_embedding(url, pattern)

        # Prepare metadata
        metadata = {
            "url": url,
            "domain": urlparse(url).netloc,
            "success": False,
            "success_rate": 0.0,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
            "failed_pattern": pattern
        }

        # Store failure (with low success rate)
        try:
            self.knowledge_base.store_pattern(
                url=url,
                pattern=pattern,
                embedding=embedding,
                metadata=metadata
            )
        except:
            # Don't fail if we can't store the failure
            pass

    def get_statistics(self) -> Dict[str, Any]:
        """Get RAG crawler statistics."""
        stats = self.retriever.get_statistics()
        stats["auto_learn"] = self.auto_learn
        stats["min_quality_threshold"] = self.min_quality_threshold

        return stats

    def export_knowledge_base(self, filepath: str) -> None:
        """Export knowledge base to file."""
        self.knowledge_base.export(filepath)

    def import_knowledge_base(self, filepath: str) -> None:
        """Import knowledge base from file."""
        self.knowledge_base.import_kb(filepath)

    def clear_knowledge_base(self) -> None:
        """Clear all learned patterns."""
        self.vector_store.clear_collection()
        logger.warning("Knowledge base cleared")

    def __repr__(self) -> str:
        """String representation."""
        return f"RAGCrawler(patterns={self.vector_store.count_patterns()}, auto_learn={self.auto_learn})"
