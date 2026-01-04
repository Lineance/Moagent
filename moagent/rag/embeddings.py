"""
Embedding generation for URLs and crawling patterns.

Supports multiple embedding models:
- SentenceTransformers (local, free)
- OpenAI Embeddings API (paid, high quality)
- Cohere Embeddings API (paid, multilingual)
"""

import logging
from typing import List, Dict, Any, Optional, Union
import hashlib

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generate embeddings for URLs and crawling patterns.

    Supports multiple backend models:
    - sentence-transformers: Local, free, good quality
    - openai: Paid API, excellent quality
    - cohere: Paid API, multilingual support

    Example:
        >>> generator = EmbeddingGenerator(model_name="all-MiniLM-L6-v2")
        >>> embedding = generator.generate_embedding("https://example.com/news")
        >>> embeddings = generator.generate_embeddings([
        ...     "https://example.com/news1",
        ...     "https://example.com/news2"
        ... ])
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        model_type: str = "sentence-transformers",
        device: str = "cpu",
        api_key: Optional[str] = None
    ):
        """
        Initialize embedding generator.

        Args:
            model_name: Name of the model
            model_type: Type of model ("sentence-transformers", "openai", "cohere")
            device: Device to use ("cpu", "cuda")
            api_key: API key for paid services
        """
        self.model_name = model_name
        self.model_type = model_type
        self.device = device
        self.api_key = api_key

        # Initialize model
        self.model = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the embedding model."""
        if self.model_type == "sentence-transformers":
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ImportError(
                    "sentence-transformers is required. "
                    "Install with: pip install sentence-transformers"
                )

            logger.info(f"Loading sentence-transformers model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info("Model loaded successfully")

        elif self.model_type == "openai":
            # Lazy loading for API-based models
            logger.info("Using OpenAI embeddings API")
            self.model = "openai"

        elif self.model_type == "cohere":
            logger.info("Using Cohere embeddings API")
            self.model = "cohere"

        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

    def generate_embedding(
        self,
        text: str,
        normalize: bool = True
    ) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            normalize: Whether to normalize the embedding vector

        Returns:
            Embedding vector as list of floats

        Example:
            >>> embedding = generator.generate_embedding("https://example.com")
            >>> len(embedding)
            384
        """
        if self.model_type == "sentence-transformers":
            # Generate embedding
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=normalize
            )
            return embedding.tolist()

        elif self.model_type == "openai":
            return self._generate_openai_embedding(text, normalize)

        elif self.model_type == "cohere":
            return self._generate_cohere_embedding(text, normalize)

        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

    def generate_embeddings(
        self,
        texts: List[str],
        normalize: bool = True,
        batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing).

        Args:
            texts: List of texts to embed
            normalize: Whether to normalize embeddings
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors

        Example:
            >>> embeddings = generator.generate_embeddings([
            ...     "https://example.com/news1",
            ...     "https://example.com/news2"
            ... ])
            >>> len(embeddings)
            2
        """
        if self.model_type == "sentence-transformers":
            # Batch encoding
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=normalize,
                batch_size=batch_size,
                show_progress_bar=False
            )
            return embeddings.tolist()

        elif self.model_type in ["openai", "cohere"]:
            # Process in batches for API-based models
            embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                if self.model_type == "openai":
                    batch_embeddings = self._generate_openai_embeddings(batch, normalize)
                else:
                    batch_embeddings = self._generate_cohere_embeddings(batch, normalize)
                embeddings.extend(batch_embeddings)
            return embeddings

        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

    def generate_url_embedding(
        self,
        url: str,
        pattern: Optional[Dict[str, Any]] = None,
        normalize: bool = True
    ) -> List[float]:
        """
        Generate embedding specifically for a URL and pattern.

        Creates a rich textual representation of the URL and pattern
        before generating the embedding.

        Args:
            url: URL to embed
            pattern: Optional crawling pattern
            normalize: Whether to normalize the embedding

        Returns:
            Embedding vector

        Example:
            >>> embedding = generator.generate_url_embedding(
            ...     url="https://example.com/news",
            ...     pattern={"css": ".news-item"}
            ... )
        """
        # Create rich text representation
        text = self._url_to_text(url, pattern)
        return self.generate_embedding(text, normalize)

    def _url_to_text(
        self,
        url: str,
        pattern: Optional[Dict[str, Any]]
    ) -> str:
        """
        Convert URL and pattern to searchable text.

        Args:
            url: URL
            pattern: Crawling pattern

        Returns:
            Text representation
        """
        from urllib.parse import urlparse

        parts = []

        # URL components
        parsed = urlparse(url)
        parts.extend([
            f"URL: {url}",
            f"Domain: {parsed.netloc}",
            f"Path: {parsed.path}",
            f"Scheme: {parsed.scheme}"
        ])

        # Pattern components
        if pattern:
            if "css_selectors" in pattern:
                parts.append(f"CSS Selectors: {', '.join(pattern['css_selectors'])}")
            if "xpath" in pattern:
                parts.append(f"XPath: {pattern['xpath']}")
            if "list_container" in pattern:
                parts.append(f"List Container: {pattern['list_container']}")
            if "item_selector" in pattern:
                parts.append(f"Item Selector: {pattern['item_selector']}")
            if "crawl_mode" in pattern:
                parts.append(f"Crawl Mode: {pattern['crawl_mode']}")

        return " | ".join(parts)

    def _generate_openai_embedding(
        self,
        text: str,
        normalize: bool
    ) -> List[float]:
        """Generate embedding using OpenAI API."""
        try:
            from openai import OpenAI

            if not self.api_key:
                raise ValueError("OpenAI API key is required")

            client = OpenAI(api_key=self.api_key)

            response = client.embeddings.create(
                model="text-embedding-3-small",  # or "text-embedding-3-large"
                input=text
            )

            embedding = response.data[0].embedding

            # Normalize if requested
            if normalize:
                import numpy as np
                embedding = (np.array(embedding) / np.linalg.norm(embedding)).tolist()

            return embedding

        except ImportError:
            raise ImportError("OpenAI package is required. Install with: pip install openai")
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _generate_openai_embeddings(
        self,
        texts: List[str],
        normalize: bool
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts using OpenAI API."""
        try:
            from openai import OpenAI

            if not self.api_key:
                raise ValueError("OpenAI API key is required")

            client = OpenAI(api_key=self.api_key)

            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )

            embeddings = [item.embedding for item in response.data]

            # Normalize if requested
            if normalize:
                import numpy as np
                embeddings = [
                    (np.array(emb) / np.linalg.norm(emb)).tolist()
                    for emb in embeddings
                ]

            return embeddings

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _generate_cohere_embedding(
        self,
        text: str,
        normalize: bool
    ) -> List[float]:
        """Generate embedding using Cohere API."""
        try:
            import cohere

            if not self.api_key:
                raise ValueError("Cohere API key is required")

            client = cohere.Client(self.api_key)

            response = client.embed(
                texts=[text],
                model="embed-english-v3.0",  # or "embed-multilingual-v3.0"
                input_type="search_document"
            )

            embedding = response.embeddings[0]

            # Normalize if requested
            if normalize:
                import numpy as np
                embedding = (np.array(embedding) / np.linalg.norm(embedding)).tolist()

            return embedding

        except ImportError:
            raise ImportError("Cohere package is required. Install with: pip install cohere")
        except Exception as e:
            logger.error(f"Cohere API error: {e}")
            raise

    def _generate_cohere_embeddings(
        self,
        texts: List[str],
        normalize: bool
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts using Cohere API."""
        try:
            import cohere

            if not self.api_key:
                raise ValueError("Cohere API key is required")

            client = cohere.Client(self.api_key)

            response = client.embed(
                texts=texts,
                model="embed-english-v3.0",
                input_type="search_document"
            )

            embeddings = response.embeddings

            # Normalize if requested
            if normalize:
                import numpy as np
                embeddings = [
                    (np.array(emb) / np.linalg.norm(emb)).tolist()
                    for emb in embeddings
                ]

            return embeddings

        except Exception as e:
            logger.error(f"Cohere API error: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.

        Returns:
            Embedding dimension
        """
        if self.model_type == "sentence-transformers":
            return self.model.get_sentence_embedding_dimension()

        elif self.model_type == "openai":
            # text-embedding-3-small: 1536
            # text-embedding-3-large: 3072
            return 1536  # Default to small model

        elif self.model_type == "cohere":
            # embed-english-v3.0: 1024
            return 1024

        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

    def similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Similarity score (0-1, where 1 is identical)

        Example:
            >>> sim = generator.similarity(embedding1, embedding2)
            >>> print(f"Similarity: {sim:.2%}")
        """
        import numpy as np

        arr1 = np.array(embedding1)
        arr2 = np.array(embedding2)

        # Cosine similarity
        dot_product = np.dot(arr1, arr2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def __repr__(self) -> str:
        """String representation."""
        return f"EmbeddingGenerator(model={self.model_name}, type={self.model_type})"


class SimpleEmbeddingGenerator:
    """
    Simple hash-based embedding generator (fallback).

    Uses MD5 hash for similarity when no embedding model is available.
    Much less accurate but doesn't require external dependencies.
    """

    def generate_embedding(self, text: str) -> List[float]:
        """Generate hash-based embedding."""
        # Use MD5 hash as simple embedding
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()

        # Convert to float vector
        embedding = []
        for i in range(0, len(hash_hex), 2):
            byte_val = int(hash_hex[i:i+2], 16)
            embedding.append(byte_val / 255.0)  # Normalize to 0-1

        return embedding

    def get_embedding_dimension(self) -> int:
        """Return fixed dimension (MD5 = 16 bytes = 128 bits)."""
        return 64  # 16 bytes * 4 bits per half-byte
