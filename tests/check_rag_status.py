"""
快速检查RAG依赖和初始化时间
"""

import sys
import time
sys.path.insert(0, '/mnt/d/Code/MoAgent')

print("="*60)
print("RAG依赖检查")
print("="*60)

# 检查1: ChromaDB
print("\n1. 检查ChromaDB...")
try:
    import chromadb
    print("   ✓ ChromaDB已安装")
    print(f"   版本: {chromadb.__version__}")
except ImportError as e:
    print(f"   ✗ ChromaDB未安装: {e}")

# 检查2: sentence-transformers
print("\n2. 检查sentence-transformers...")
try:
    import sentence_transformers
    print("   ✓ sentence-transformers已安装")
    print(f"   版本: {sentence_transformers.__version__}")
except ImportError as e:
    print(f"   ✗ sentence-transformers未安装: {e}")

# 检查3: 测试SimpleEmbeddingGenerator
print("\n3. 测试SimpleEmbeddingGenerator (无依赖)...")
try:
    from moagent.rag.embeddings import SimpleEmbeddingGenerator

    start = time.time()
    gen = SimpleEmbeddingGenerator()
    emb = gen.generate_embedding("test text")
    elapsed = time.time() - start

    print(f"   ✓ SimpleEmbeddingGenerator工作正常")
    print(f"   生成时间: {elapsed:.4f}秒")
    print(f"   嵌入维度: {len(emb)}")
except Exception as e:
    print(f"   ✗ 错误: {e}")

# 检查4: 测试完整的EmbeddingGenerator (可能很慢)
print("\n4. 测试完整EmbeddingGenerator (需要加载模型)...")
print("   ⚠️ 这可能需要10-30秒...")

try:
    from moagent.rag.embeddings import EmbeddingGenerator

    start = time.time()
    gen = EmbeddingGenerator(model_name="all-MiniLM-L6-v2")
    init_time = time.time() - start

    print(f"   ✓ 模型初始化完成 (耗时: {init_time:.2f}秒)")

    start = time.time()
    emb = gen.generate_embedding("test text for example.com")
    gen_time = time.time() - start

    print(f"   ✓ 嵌入生成完成 (耗时: {gen_time:.4f}秒)")
    print(f"   嵌入维度: {len(emb)}")
    print(f"   模型维度: {gen.get_embedding_dimension()}")

except Exception as e:
    print(f"   ✗ 错误: {e}")
    import traceback
    traceback.print_exc()

# 检查5: 测试VectorStore初始化
print("\n5. 测试VectorStore初始化...")
try:
    from moagent.rag.vector_store import VectorStore

    start = time.time()
    store = VectorStore(collection_name="test_collection")
    init_time = time.time() - start

    print(f"   ✓ VectorStore初始化完成 (耗时: {init_time:.2f}秒)")
    print(f"   当前模式数: {store.count_patterns()}")

except Exception as e:
    print(f"   ✗ 错误: {e}")
    import traceback
    traceback.print_exc()

# 检查6: 测试PatternRetriever
print("\n6. 测试PatternRetriever初始化...")
try:
    from moagent.rag.retriever import PatternRetriever
    from moagent.rag.embeddings import SimpleEmbeddingGenerator

    # 使用Simple版本避免加载模型
    from moagent.rag.vector_store import VectorStore
    store = VectorStore(collection_name="test_collection")

    class SimpleGenWrapper:
        def __init__(self):
            self.gen = SimpleEmbeddingGenerator()
            self.model_name = "simple"
        def generate_url_embedding(self, url, pattern=None):
            return self.gen.generate_embedding(url)
        def generate_embedding(self, text):
            return self.gen.generate_embedding(text)
        def get_embedding_dimension(self):
            return self.gen.get_embedding_dimension()

    wrapper = SimpleGenWrapper()

    start = time.time()
    retriever = PatternRetriever(store, wrapper)
    init_time = time.time() - start

    print(f"   ✓ PatternRetriever初始化完成 (耗时: {init_time:.4f}秒)")

except Exception as e:
    print(f"   ✗ 错误: {e}")
    import traceback
    traceback.print_exc()

# 检查7: 测试KnowledgeBase
print("\n7. 测试KnowledgeBase初始化...")
try:
    from moagent.rag.knowledge_base import KnowledgeBase

    start = time.time()
    kb = KnowledgeBase()
    init_time = time.time() - start

    print(f"   ✓ KnowledgeBase初始化完成 (耗时: {init_time:.4f}秒)")

    stats = kb.get_statistics()
    print(f"   模式数: {stats['total_patterns']}")

except Exception as e:
    print(f"   ✗ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("RAG组件检查完成")
print("="*60)
print("\n💡 建议:")
print("- 如果EmbeddingGenerator初始化很慢(>10秒)，建议使用SimpleEmbeddingGenerator")
print("- VectorStore首次创建需要初始化ChromaDB，后续会快很多")
print("- 所有组件都支持fallback模式，无需依赖sentence-transformers")
