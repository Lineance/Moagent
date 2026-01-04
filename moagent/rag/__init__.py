"""
RAG-Enhanced Crawling System for MoAgent.

This module implements Retrieval-Augmented Generation for intelligent web crawling:
- Vector database storage of successful crawling patterns
- Semantic similarity search for pattern retrieval
- LLM-assisted pattern adaptation
- Continuous learning from crawling results

Key Components:
- VectorStore: ChromaDB wrapper for pattern storage
- EmbeddingGenerator: Generate embeddings for URLs and patterns
- PatternRetriever: Retrieve similar patterns from knowledge base
- RAGCrawler: Main RAG-enhanced crawling coordinator
"""

from .vector_store import VectorStore
from .embeddings import EmbeddingGenerator
from .retriever import PatternRetriever
from .rag_crawler import RAGCrawler
from .knowledge_base import KnowledgeBase

__all__ = [
    "VectorStore",
    "EmbeddingGenerator",
    "PatternRetriever",
    "RAGCrawler",
    "KnowledgeBase",
]

__version__ = "1.0.0"
