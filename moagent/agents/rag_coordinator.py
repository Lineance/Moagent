"""
RAG-enhanced coordinator for intelligent crawling.

Integrates RAG capabilities into the existing coordinator workflow.
"""

import logging
from typing import Dict, Any, Optional

from ..config.settings import Config
from ..rag import RAGCrawler, VectorStore, EmbeddingGenerator

logger = logging.getLogger(__name__)


class RAGEnhancedCoordinator:
    """
    RAG-enhanced coordinator that uses learned patterns.

    Wraps the existing coordinator but adds RAG capabilities
    for intelligent pattern selection and continuous learning.

    Example:
        >>> from moagent.agents import RAGEnhancedCoordinator
        >>>
        >>> # Initialize with config
        >>> coordinator = RAGEnhancedCoordinator(config)
        >>>
        >>> # Run with RAG enhancement
        >>> result = coordinator.run(target_url="https://example.com")
        >>>
        >>> # Check if RAG pattern was used
        >>> if result["used_rag_pattern"]:
        ...     print(f"RAG similarity: {result['rag_similarity']:.2f}")
    """

    def __init__(
        self,
        config: Config,
        enable_rag: bool = True,
        auto_learn: bool = True
    ):
        """
        Initialize RAG-enhanced coordinator.

        Args:
            config: Configuration object
            enable_rag: Whether to enable RAG features
            auto_learn: Whether to automatically learn from results
        """
        self.config = config
        self.enable_rag = enable_rag
        self.auto_learn = auto_learn

        # Initialize RAG components
        if self.enable_rag:
            try:
                self.rag_crawler = RAGCrawler(
                    auto_learn=auto_learn,
                    min_quality_threshold=0.7
                )
                logger.info("RAG features enabled")
            except Exception as e:
                logger.warning(f"Could not initialize RAG: {e}. Falling back to standard mode.")
                self.enable_rag = False
                self.rag_crawler = None
        else:
            self.rag_crawler = None

    def run(
        self,
        target_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run crawling with RAG enhancement.

        Args:
            target_url: URL to crawl
            **kwargs: Additional arguments

        Returns:
            Crawl result with RAG metadata
        """
        from .coordinator import CoordinatorAgent

        # Use config target if not specified
        if not target_url:
            target_url = self.config.target_url

        result = {
            "url": target_url,
            "used_rag_pattern": False,
            "rag_similarity": None,
            "rag_success_rate": None
        }

        # Check for RAG-recommended pattern
        if self.enable_rag and self.rag_crawler:
            suggested_patterns = self.rag_crawler.get_suggested_pattern(
                url=target_url,
                n_options=1
            )

            if suggested_patterns:
                best_pattern = suggested_patterns[0]
                result["used_rag_pattern"] = True
                result["rag_similarity"] = best_pattern["similarity"]
                result["rag_success_rate"] = best_pattern["success_rate"]

                logger.info(
                    f"Using RAG pattern (similarity: {best_pattern['similarity']:.2f}, "
                    f"success rate: {best_pattern['success_rate']:.2f})"
                )

        # Run standard coordinator
        try:
            # Import here to avoid circular dependency
            coordinator = CoordinatorAgent(self.config)
            coordinator_result = coordinator.run()

            # Merge results
            result.update(coordinator_result)

            # Learn from result
            if self.auto_learn and self.rag_crawler:
                self._learn_from_run(target_url, result)

        except Exception as e:
            logger.error(f"Coordinator run failed: {e}")
            result["error"] = str(e)
            result["success"] = False

        return result

    def _learn_from_run(self, url: str, result: Dict[str, Any]) -> None:
        """Learn from crawl result."""
        if not self.rag_crawler:
            return

        # Prepare pattern
        pattern = {
            "type": "coordinator",
            "crawl_mode": self.config.crawl_mode,
            "parser_mode": self.config.parser_mode
        }

        # Add crawler pattern if available
        if "crawler_pattern" in result:
            pattern["crawler_pattern"] = result["crawler_pattern"]

        # Calculate success metrics
        success = result.get("success", not result.get("errors"))
        items_count = result.get("new_count", result.get("processed_count", 0))

        # Prepare metadata
        crawl_result = {
            "success": success,
            "items_count": items_count,
            "error_count": len(result.get("errors", [])),
            "timestamp": result.get("timestamp")
        }

        # Only learn if we got good results
        if success and items_count > 0:
            try:
                # Create embedding
                from ..rag.embeddings import EmbeddingGenerator
                gen = EmbeddingGenerator()
                embedding = gen.generate_url_embedding(url, pattern)

                # Store in knowledge base
                self.rag_crawler.knowledge_base.store_pattern(
                    url=url,
                    pattern=pattern,
                    embedding=embedding,
                    metadata={
                        **crawl_result,
                        "success_rate": min(items_count / 100, 1.0)  # Normalized
                    }
                )

                logger.info(f"Learned from crawl of {url} ({items_count} items)")

            except Exception as e:
                logger.warning(f"Could not learn from result: {e}")

    def get_rag_statistics(self) -> Optional[Dict[str, Any]]:
        """Get RAG system statistics."""
        if not self.enable_rag or not self.rag_crawler:
            return None

        return self.rag_crawler.get_statistics()

    def get_suggested_patterns(self, url: str, n_options: int = 3) -> list:
        """Get RAG-suggested patterns for a URL."""
        if not self.enable_rag or not self.rag_crawler:
            return []

        return self.rag_crawler.get_suggested_pattern(url, n_options=n_options)

    def export_knowledge(self, filepath: str) -> None:
        """Export RAG knowledge base."""
        if self.rag_crawler:
            self.rag_crawler.export_knowledge_base(filepath)

    def import_knowledge(self, filepath: str) -> None:
        """Import RAG knowledge base."""
        if self.rag_crawler:
            self.rag_crawler.import_knowledge_base(filepath)

    def clear_knowledge(self) -> None:
        """Clear all learned patterns."""
        if self.rag_crawler:
            self.rag_crawler.clear_knowledge_base()

    def __repr__(self) -> str:
        """String representation."""
        return f"RAGEnhancedCoordinator(rag_enabled={self.enable_rag}, auto_learn={self.auto_learn})"
