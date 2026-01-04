"""
Simple RAG functionality test
"""

import sys
sys.path.insert(0, '/mnt/d/Code/MoAgent')

from moagent.rag.embeddings import SimpleEmbeddingGenerator
from moagent.rag.vector_store import SimpleVectorStore
from moagent.rag.retriever import PatternRetriever
from moagent.rag.knowledge_base import KnowledgeBase

def test_embedding_generator():
    """Test 1: Embedding Generator"""
    print("\n" + "="*60)
    print("Test 1: Embedding Generator")
    print("="*60)

    gen = SimpleEmbeddingGenerator()

    # Generate embeddings
    emb1 = gen.generate_embedding("test text for example.com")
    emb2 = gen.generate_embedding("another test text")

    print(f"✓ Generated embedding 1: length={len(emb1)}")
    print(f"✓ Generated embedding 2: length={len(emb2)}")
    print(f"✓ Different texts produce different embeddings: {emb1 != emb2}")
    print(f"✓ Embedding dimension: {gen.get_embedding_dimension()}")

    return True


def test_vector_store():
    """Test 2: Vector Store"""
    print("\n" + "="*60)
    print("Test 2: Vector Store")
    print("="*60)

    store = SimpleVectorStore()

    # Test adding patterns
    pattern1 = {
        "url": "https://example.com",
        "list_container": "div.article-list",
        "item_selector": "div.item",
        "success_rate": 0.9
    }

    pattern2 = {
        "url": "https://test.com",
        "list_container": "ul.posts",
        "item_selector": "li.post",
        "success_rate": 0.85
    }

    store.add_pattern("https://example.com", pattern1, embedding=[0.1, 0.2, 0.3])
    store.add_pattern("https://test.com", pattern2, embedding=[0.4, 0.5, 0.6])

    print(f"✓ Added 2 patterns to store")
    print(f"✓ Total patterns: {store.get_pattern_count()}")

    # Test retrieval
    results = store.search_similar([0.1, 0.2, 0.3], top_k=2)
    print(f"✓ Found {len(results)} similar patterns")

    return True


def test_pattern_retriever():
    """Test 3: Pattern Retriever"""
    print("\n" + "="*60)
    print("Test 3: Pattern Retriever")
    print("="*60)

    from moagent.rag.embeddings import SimpleEmbeddingGenerator
    gen = SimpleEmbeddingGenerator()
    store = SimpleVectorStore()

    # Add some patterns
    pattern1 = {
        "list_container": "div.news-list",
        "item_selector": "div.news-item",
        "title": "h2.title",
        "link": "a.link"
    }

    store.add_pattern(
        "https://news.example.com",
        pattern1,
        embedding=gen.generate_embedding("https://news.example.com")
    )

    # Create retriever
    retriever = PatternRetriever(store, gen)

    # Test retrieval
    results = retriever.retrieve_similar_patterns("https://similar-news.com", top_k=1)

    print(f"✓ Retrieved {len(results)} similar patterns")
    if results:
        print(f"✓ Top match confidence: {results[0].get('confidence', 'N/A')}")

    return True


def test_knowledge_base():
    """Test 4: Knowledge Base"""
    print("\n" + "="*60)
    print("Test 4: Knowledge Base")
    print("="*60)

    kb = KnowledgeBase()

    # Add successful pattern
    pattern = {
        "list_container": "div.articles",
        "item_selector": "article",
        "title": "h2",
        "success_rate": 0.95
    }

    kb.add_successful_pattern("https://blog.example.com", pattern)

    # Get stats
    stats = kb.get_statistics()
    print(f"✓ Total patterns in KB: {stats['total_patterns']}")
    print(f"✓ Average success rate: {stats['average_success_rate']:.2%}")

    # Test retrieval
    similar = kb.find_similar_patterns("https://another-blog.com", top_k=1)
    print(f"✓ Found {len(similar)} similar patterns")

    return True


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("RAG System Simple Test Suite")
    print("="*60)

    tests = [
        ("Embedding Generator", test_embedding_generator),
        ("Vector Store", test_vector_store),
        ("Pattern Retriever", test_pattern_retriever),
        ("Knowledge Base", test_knowledge_base),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                print(f"\n✅ {name}: PASSED")
                passed += 1
            else:
                print(f"\n❌ {name}: FAILED")
                failed += 1
        except Exception as e:
            print(f"\n❌ {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    print(f"📊 Success Rate: {passed/len(tests)*100:.1f}%")

    if passed == len(tests):
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} test(s) failed")

    return passed == len(tests)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
