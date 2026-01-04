#!/usr/bin/env python3
"""
MoAgent Web应用测试脚本
验证所有页面和API接口是否正常工作
"""

import sys
import time
import requests
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:5000"

def test_page(page_url, page_name):
    """测试页面是否可访问"""
    try:
        response = requests.get(f"{BASE_URL}{page_url}", timeout=5)
        if response.status_code == 200:
            print(f"✓ {page_name}: OK (状态码 {response.status_code})")
            return True
        else:
            print(f"✗ {page_name}: 失败 (状态码 {response.status_code})")
            return False
    except Exception as e:
        print(f"✗ {page_name}: 错误 - {e}")
        return False

def test_api(api_url, api_name, method="GET", data=None):
    """测试API接口"""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{api_url}", timeout=10)
        else:
            response = requests.post(f"{BASE_URL}{api_url}", json=data, timeout=30)

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✓ {api_name}: OK")
                return True
            else:
                print(f"✗ {api_name}: API返回失败 - {result.get('error', 'Unknown')}")
                return False
        else:
            print(f"✗ {api_name}: HTTP错误 (状态码 {response.status_code})")
            return False
    except Exception as e:
        print(f"✗ {api_name}: 错误 - {e}")
        return False

def main():
    print("="*60)
    print("MoAgent Web应用测试")
    print("="*60)
    print()

    # 检查服务器是否运行
    print("1. 检查服务器连接...")
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"✓ 服务器运行中 (状态码 {response.status_code})")
    except Exception as e:
        print(f"✗ 无法连接到服务器: {e}")
        print("\n请确保服务器正在运行:")
        print("  cd web_app && python app.py")
        sys.exit(1)

    print()

    # 测试页面
    print("2. 测试页面...")
    pages = [
        ("/", "首页"),
        ("/crawl", "爬虫页面"),
        ("/rag", "RAG系统"),
        ("/multi-agent", "多Agent"),
        ("/dashboard", "监控面板"),
    ]

    page_results = []
    for url, name in pages:
        page_results.append(test_page(url, name))
        time.sleep(0.5)  # 避免请求过快

    print()

    # 测试API
    print("3. 测试API接口...")
    api_tests = [
        ("/api/system/info", "系统信息API", "GET"),
        ("/api/storage/stats", "存储统计API", "GET"),
        ("/api/rag/stats", "RAG统计API", "GET"),
    ]

    api_results = []
    for url, name, method in api_tests:
        api_results.append(test_api(url, name, method))
        time.sleep(0.5)

    print()

    # 测试爬虫API（可选，需要API密钥）
    print("4. 测试爬虫API（可选）...")
    print("  跳过实际爬取测试（需要API密钥和目标URL）")
    print("  提示: 可以通过Web界面手动测试爬虫功能")

    print()
    print("="*60)
    print("测试结果汇总")
    print("="*60)

    page_success = sum(page_results)
    page_total = len(page_results)
    api_success = sum(api_results)
    api_total = len(api_results)

    print(f"页面测试: {page_success}/{page_total} 通过")
    print(f"API测试: {api_success}/{api_total} 通过")

    if page_success == page_total and api_success == api_total:
        print()
        print("🎉 所有测试通过！")
        return 0
    else:
        print()
        print("⚠️ 部分测试失败，请检查服务器配置")
        return 1

if __name__ == "__main__":
    sys.exit(main())
