#!/usr/bin/env python
"""
快速RAG检查 - 分步骤测试
"""

import sys
import os

# 确保路径正确
sys.path.insert(0, '/mnt/d/Code/MoAgent')
os.chdir('/mnt/d/Code/MoAgent')

print("RAG系统快速检查\n")

# 步骤1: 检查依赖
print("步骤1: 检查依赖...")
try:
    import chromadb
    print("  ✓ ChromaDB")
except ImportError:
    print("  ✗ ChromaDB 未安装")
    sys.exit(1)

try:
    import sentence_transformers
    print("  ✓ sentence-transformers")
except ImportError:
    print("  ✗ sentence-transformers 未安装")

# 步骤2: 测试SimpleEmbeddingGenerator (快速)
print("\n步骤2: 测试SimpleEmbeddingGenerator...")
from moagent.rag.embeddings import SimpleEmbeddingGenerator

gen = SimpleEmbeddingGenerator()
emb = gen.generate_embedding("test")
print(f"  ✓ 生成嵌入: 维度={len(emb)}")

# 步骤3: 测试完整导入 (不初始化)
print("\n步骤3: 测试RAG模块导入...")
from moagent.rag import VectorStore, EmbeddingGenerator, PatternRetriever, RAGCrawler, KnowledgeBase
print("  ✓ 所有RAG模块导入成功")

# 步骤4: 创建简单的VectorStore
print("\n步骤4: 测试VectorStore...")
store = VectorStore(collection_name="quick_test")
print(f"  ✓ VectorStore创建成功, 模式数={store.count_patterns()}")

# 步骤5: 测试添加模式
print("\n步骤5: 测试添加模式...")
pattern = {
    "list_container": "div.test",
    "item_selector": "div.item"
}

gen = SimpleEmbeddingGenerator()
emb = gen.generate_embedding("https://example.com")

store.add_pattern(
    url="https://example.com",
    pattern=pattern,
    embedding=emb,
    metadata={"success_rate": 0.9}
)
print(f"  ✓ 模式添加成功, 总模式数={store.count_patterns()}")

# 步骤6: 测试检索
print("\n步骤6: 测试模式检索...")
results = store.search(query_embedding=emb, n_results=1)
print(f"  ✓ 检索成功, 找到{len(results)}个结果")

# 步骤7: 测试KnowledgeBase
print("\n步骤7: 测试KnowledgeBase...")
kb = KnowledgeBase()
kb.add_successful_pattern("https://test.com", {"selector": ".test"})
stats = kb.get_statistics()
print(f"  ✓ KnowledgeBase工作正常, 模式数={stats['total_patterns']}")

print("\n" + "="*50)
print("✅ RAG系统基础功能正常!")
print("="*50)
print("\n注意: 完整的sentence-transformers模型加载需要较长时间")
print("当前使用的是SimpleEmbeddingGenerator (基于hash)")
