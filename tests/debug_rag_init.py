#!/usr/bin/env python
"""调试RAG初始化"""

import sys
sys.path.insert(0, '/mnt/d/Code/MoAgent')

import time

print("开始RAG初始化调试...")

# 测试1: 导入chromadb
print("\n1. 导入chromadb...")
start = time.time()
import chromadb
elapsed = time.time() - start
print(f"   完成! 耗时: {elapsed:.2f}秒")

# 测试2: 创建ChromaDB客户端
print("\n2. 创建ChromaDB客户端...")
start = time.time()
from chromadb.config import Settings
client = chromadb.PersistentClient(
    path="/mnt/d/Code/MoAgent/data/vector_db",
    settings=Settings(anonymized_telemetry=False, allow_reset=True)
)
elapsed = time.time() - start
print(f"   完成! 耗时: {elapsed:.2f}秒")

# 测试3: 获取或创建collection
print("\n3. 获取或创建collection...")
start = time.time()
try:
    collection = client.get_collection(name="test_collection")
    print(f"   找到已存在的collection")
except:
    collection = client.create_collection(
        name="test_collection",
        metadata={"hnsw:space": "cosine"}
    )
    print(f"   创建新collection")
elapsed = time.time() - start
print(f"   完成! 耗时: {elapsed:.2f}秒")

# 测试4: 导入VectorStore类
print("\n4. 导入VectorStore类...")
start = time.time()
from moagent.rag.vector_store import VectorStore
elapsed = time.time() - start
print(f"   完成! 耗时: {elapsed:.2f}秒")

# 测试5: 创建VectorStore实例
print("\n5. 创建VectorStore实例...")
start = time.time()
store = VectorStore(collection_name="test_collection2")
elapsed = time.time() - start
print(f"   完成! 耗时: {elapsed:.2f}秒")
print(f"   当前collection: {store.collection_name}")

print("\n✅ 所有步骤完成!")
