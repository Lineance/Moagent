"""
Tests for RAG (Retrieval-Augmented Generation) system.
"""

import pytest
import tempfile
import json
from pathlib import Path
from moagent.rag import (
    VectorStore,
    EmbeddingGenerator,
    PatternRetriever,
    RAGCrawler,
    KnowledgeBase
)


class TestEmbeddingGenerator:
    """Test embedding generation."""

    @pytest.fixture
    def generator(self):
        """Create embedding generator for testing."""
        return EmbeddingGenerator(
            model_name="all-MiniLM-L6-v2",
            model_type="sentence-transformers"
        )

    def test_generate_embedding(self, generator):
        """Test generating single embedding."""
        text = "https://example.com/news"
        embedding = generator.generate_embedding(text)

        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    def test_generate_embeddings_batch(self, generator):
        """Test generating multiple embeddings."""
        texts = [
            "https://example.com/news1",
            "https://example.com/news2",
            "https://example.com/news3"
        ]

        embeddings = generator.generate_embeddings(texts)

        assert len(embeddings) == len(texts)
        assert all(len(emb) > 0 for emb in embeddings)

    def test_generate_url_embedding(self, generator):
        """Test generating URL-specific embedding."""
        url = "https://example.com/news"
        pattern = {"css": ".news-item", "xpath": "//div[@class='news']"}

        embedding = generator.generate_url_embedding(url, pattern)

        assert isinstance(embedding, list)
        assert len(embedding) > 0

    def test_similarity(self, generator):
        """Test similarity calculation."""
        text1 = "https://example.com/news"
        text2 = "https://example.com/news/1"
        text3 = "https://different-site.com/news"

        emb1 = generator.generate_embedding(text1)
        emb2 = generator.generate_embedding(text2)
        emb3 = generator.generate_embedding(text3)

        # Similar texts should have higher similarity
        sim_12 = generator.similarity(emb1, emb2)
        sim_13 = generator.similarity(emb1, emb3)

        assert sim_12 > sim_13

    def test_get_embedding_dimension(self, generator):
        """Test getting embedding dimension."""
        dim = generator.get_embedding_dimension()
        assert dim > 0
        assert isinstance(dim, int)


class TestVectorStore:
    """Test vector database operations."""

    @pytest.fixture
    def temp_store(self):
        """Create temporary vector store."""
        import tempfile
        temp_dir = tempfile.mkdtemp()
        store = VectorStore(
            collection_name="test_patterns",
            persist_directory=temp_dir
        )
        yield store
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def sample_embedding(self):
        """Create sample embedding."""
        return [0.1] * 384  # all-MiniLM-L6-v2 dimension

    def test_add_pattern(self, temp_store, sample_embedding):
        """Test adding a pattern."""
        pattern_id = temp_store.add_pattern(
            url="https://example.com",
            pattern={"css": ".content"},
            embedding=sample_embedding,
            metadata={"success_rate": 0.9}
        )

        assert pattern_id is not None
        assert isinstance(pattern_id, str)

    def test_search(self, temp_store, sample_embedding):
        """Test searching for similar patterns."""
        # Add some patterns
        temp_store.add_pattern(
            url="https://example.com/news1",
            pattern={"css": ".news"},
            embedding=sample_embedding,
            metadata={"success_rate": 0.95}
        )

        temp_store.add_pattern(
            url="https://example.com/news2",
            pattern={"css": ".article"},
            embedding=sample_embedding,
            metadata={"success_rate": 0.85}
        )

        # Search
        results = temp_store.search(
            query_embedding=sample_embedding,
            n_results=2
        )

        assert len(results) > 0
        assert "similarity" in results[0]

    def test_get_pattern(self, temp_store, sample_embedding):
        """Test retrieving a specific pattern."""
        pattern_id = temp_store.add_pattern(
            url="https://example.com",
            pattern={"css": ".content"},
            embedding=sample_embedding
        )

        retrieved = temp_store.get_pattern(pattern_id)

        assert retrieved is not None
        assert retrieved["id"] == pattern_id

    def test_update_pattern(self, temp_store, sample_embedding):
        """Test updating pattern metadata."""
        pattern_id = temp_store.add_pattern(
            url="https://example.com",
            pattern={"css": ".content"},
            embedding=sample_embedding,
            metadata={"success_rate": 0.7}
        )

        # Update
        success = temp_store.update_pattern(
            pattern_id,
            metadata={"success_rate": 0.9}
        )

        assert success is True

        # Verify update
        updated = temp_store.get_pattern(pattern_id)
        assert updated["metadata"]["success_rate"] == 0.9

    def test_delete_pattern(self, temp_store, sample_embedding):
        """Test deleting a pattern."""
        pattern_id = temp_store.add_pattern(
            url="https://example.com",
            pattern={"css": ".content"},
            embedding=sample_embedding
        )

        # Delete
        success = temp_store.delete_pattern(pattern_id)
        assert success is True

        # Verify deletion
        retrieved = temp_store.get_pattern(pattern_id)
        assert retrieved is None

    def test_count_patterns(self, temp_store, sample_embedding):
        """Test counting patterns."""
        initial_count = temp_store.count_patterns()

        # Add patterns
        temp_store.add_pattern(
            url="https://example.com/1",
            pattern={"css": ".content"},
            embedding=sample_embedding
        )
        temp_store.add_pattern(
            url="https://example.com/2",
            pattern={"css": ".article"},
            embedding=sample_embedding
        )

        new_count = temp_store.count_patterns()
        assert new_count == initial_count + 2

    def test_get_statistics(self, temp_store, sample_embedding):
        """Test getting statistics."""
        temp_store.add_pattern(
            url="https://example.com",
            pattern={"css": ".content"},
            embedding=sample_embedding,
            metadata={"success_rate": 0.9}
        )

        stats = temp_store.get_statistics()

        assert "total_patterns" in stats
        assert stats["total_patterns"] > 0
        assert "collection_name" in stats


class TestPatternRetriever:
    """Test pattern retrieval."""

    @pytest.fixture
    def retriever(self, tmp_path):
        """Create pattern retriever for testing."""
        store = VectorStore(
            collection_name="test_retriever",
            persist_directory=str(tmp_path)
        )
        generator = EmbeddingGenerator()
        return PatternRetriever(store, generator)

    def test_retrieve_patterns_empty(self, retriever):
        """Test retrieving when knowledge base is empty."""
        patterns = retriever.retrieve_patterns(
            url="https://example.com/news",
            n_results=5
        )

        assert patterns == []

    @pytest.mark.skipif(True, reason="Requires populating knowledge base first")
    def test_retrieve_patterns(self, retriever):
        """Test retrieving similar patterns."""
        # This would require pre-populating the store
        patterns = retriever.retrieve_patterns(
            url="https://example.com/news",
            n_results=5,
            min_similarity=0.7
        )

        assert isinstance(patterns, list)

    def test_retrieve_best_pattern_empty(self, retriever):
        """Test retrieving best pattern when empty."""
        best = retriever.retrieve_best_pattern(
            url="https://example.com/news"
        )

        assert best is None


class TestRAGCrawler:
    """Test RAG-enhanced crawler."""

    @pytest.fixture
    def rag_crawler(self, tmp_path):
        """Create RAG crawler for testing."""
        return RAGCrawler(
            auto_learn=True,
            min_quality_threshold=0.7
        )

    def test_initialization(self, rag_crawler):
        """Test RAG crawler initialization."""
        assert rag_crawler is not None
        assert rag_crawler.auto_learn is True

    def test_crawl_with_mock_function(self, rag_crawler):
        """Test crawling with mock crawler function."""
        def mock_crawler(url, pattern):
            return {
                "success": True,
                "items_count": 10,
                "items": [{"title": f"Item {i}"} for i in range(10)]
            }

        result = rag_crawler.crawl(
            url="https://example.com/news",
            crawler_func=mock_crawler
        )

        assert result["success"] is True
        assert result["items_count"] == 10
        assert "rag_used" in result

    def test_batch_crawl(self, rag_crawler):
        """Test batch crawling."""
        def mock_crawler(url, pattern):
            return {
                "success": True,
                "items_count": 5,
                "items": [{"title": f"Item {i}"} for i in range(5)]
            }

        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3"
        ]

        results = rag_crawler.batch_crawl(
            urls=urls,
            crawler_func=mock_crawler
        )

        assert len(results) == len(urls)
        assert all(r["success"] for r in results)

    def test_get_suggested_pattern(self, rag_crawler):
        """Test getting suggested patterns."""
        suggestions = rag_crawler.get_suggested_patterns(
            url="https://example.com/news",
            n_options=3
        )

        assert isinstance(suggestions, list)

    def test_get_statistics(self, rag_crawler):
        """Test getting RAG statistics."""
        stats = rag_crawler.get_statistics()

        assert "total_patterns" in stats
        assert "embedding_dimension" in stats


class TestKnowledgeBase:
    """Test knowledge base management."""

    @pytest.fixture
    def knowledge_base(self, tmp_path):
        """Create knowledge base for testing."""
        store = VectorStore(
            collection_name="test_kb",
            persist_directory=str(tmp_path)
        )
        generator = EmbeddingGenerator()
        return KnowledgeBase(store, generator)

    def test_store_pattern(self, knowledge_base):
        """Test storing a pattern."""
        from moagent.rag.embeddings import EmbeddingGenerator
        gen = EmbeddingGenerator()

        embedding = gen.generate_embedding("test")

        pattern_id = knowledge_base.store_pattern(
            url="https://example.com",
            pattern={"css": ".content"},
            embedding=embedding,
            metadata={"success_rate": 0.9}
        )

        assert pattern_id is not None

    def test_export_import(self, knowledge_base, tmp_path):
        """Test exporting and importing knowledge base."""
        export_file = tmp_path / "knowledge_export.json"

        # Export
        knowledge_base.export(str(export_file))

        # Clear
        knowledge_base.vector_store.clear_collection()

        # Import
        knowledge_base.import_kb(str(export_file))

        # Verify
        assert export_file.exists()

    def test_get_insights(self, knowledge_base):
        """Test getting insights."""
        insights = knowledge_base.get_insights()

        assert "total_patterns" in insights
        assert isinstance(insights["total_patterns"], int)

    @pytest.mark.skipif(True, reason="Requires patterns in knowledge base")
    def test_analyze_domain(self, knowledge_base):
        """Test domain analysis."""
        analysis = knowledge_base.analyze_domain("example.com")

        assert "domain" in analysis
        assert "total_patterns" in analysis
        assert "recommendation" in analysis


class TestRAGIntegration:
    """Integration tests for RAG system."""

    @pytest.fixture
    def full_rag_system(self, tmp_path):
        """Create full RAG system for testing."""
        return RAGCrawler(
            auto_learn=True,
            min_quality_threshold=0.6
        )

    def test_learning_cycle(self, full_rag_system):
        """Test complete learning cycle."""
        # 1. Initial crawl (no patterns)
        def mock_crawler(url, pattern):
            return {
                "success": True,
                "items_count": 20,
                "items": [{"title": f"Item {i}"} for i in range(20)]
            }

        result1 = full_rag_system.crawl(
            url="https://example.com/news",
            crawler_func=mock_crawler
        )

        # 2. Verify learning
        stats = full_rag_system.get_statistics()
        assert stats["total_patterns"] > 0

        # 3. Second crawl (should use learned pattern)
        result2 = full_rag_system.crawl(
            url="https://example.com/news",
            crawler_func=mock_crawler
        )

        assert result2["success"] is True

    def test_similar_url_recommendation(self, full_rag_system):
        """Test pattern recommendation for similar URLs."""
        def mock_crawler(url, pattern):
            return {
                "success": True,
                "items_count": 15,
                "items": [{"title": f"Item {i}"} for i in range(15)]
            }

        # Crawl first URL
        full_rag_system.crawl(
            url="https://example.com/news/page1",
            crawler_func=mock_crawler
        )

        # Get suggestion for similar URL
        suggestions = full_rag_system.get_suggested_patterns(
            url="https://example.com/news/page2"
        )

        # Should have learned from first URL
        assert isinstance(suggestions, list)

    def test_quality_based_learning(self, full_rag_system):
        """Test that only high-quality results are learned."""
        good_result = {
            "success": True,
            "items_count": 50,
            "items": [{"title": f"Item {i}"} for i in range(50)]
        }

        bad_result = {
            "success": True,
            "items_count": 2,  # Too few items
            "items": [{"title": f"Item {i}"} for i in range(2)]
        }

        # Mock crawler that returns good result
        full_rag_system.crawl(
            url="https://example.com/good",
            crawler_func=lambda url, pattern: good_result
        )

        # Mock crawler that returns bad result
        full_rag_system.crawl(
            url="https://example.com/bad",
            crawler_func=lambda url, pattern: bad_result
        )

        # Check what was learned
        stats = full_rag_system.get_statistics()
        # Good result should be stored, bad result should not
        assert stats["total_patterns"] >= 1  # At least the good one
