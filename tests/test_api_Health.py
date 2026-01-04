#!/usr/bin/env python
"""
MoAgent API Health Check Script
Quick test all Flask API endpoints
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:5000"


def print_section(title: str):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)


def print_result(name: str, success: bool, message: str = "", data: Any = None):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\n{status} | {name}")
    if message:
        print(f"      {message}")
    if data and not success:
        print(f"      错误详情: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}")


def test_api_get(name: str, endpoint: str, expected_status: int = 200) -> bool:
    """Test GET endpoint"""
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
        success = response.status_code == expected_status

        if success:
            try:
                data = response.json()
                print_result(name, True, f"状态码: {response.status_code}")
                return True
            except:
                print_result(name, True, f"状态码: {response.status_code} (非JSON响应)")
                return True
        else:
            try:
                data = response.json()
                print_result(name, False, f"状态码: {response.status_code} (期望: {expected_status})", data)
                return False
            except:
                print_result(name, False, f"状态码: {response.status_code} (期望: {expected_status})")
                return False
    except Exception as e:
        print_result(name, False, f"连接错误: {str(e)}")
        return False


def test_api_post(name: str, endpoint: str, data: Dict[str, Any], expected_status: int = 200) -> bool:
    """Test POST endpoint"""
    try:
        response = requests.post(
            f"{BASE_URL}{endpoint}",
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        success = response.status_code == expected_status

        if success:
            try:
                result = response.json()
                print_result(name, True, f"状态码: {response.status_code}")
                return True
            except:
                print_result(name, True, f"状态码: {response.status_code} (非JSON响应)")
                return True
        else:
            try:
                result = response.json()
                print_result(name, False, f"状态码: {response.status_code} (期望: {expected_status})", result)
                return False
            except:
                print_result(name, False, f"状态码: {response.status_code} (期望: {expected_status})")
                return False
    except Exception as e:
        print_result(name, False, f"连接错误: {str(e)}")
        return False


def main():
    """Run all API tests"""
    print_section("MoAgent API 健康检查")
    print(f"测试服务器: {BASE_URL}")
    print(f"开始时间: {requests.get(f'{BASE_URL}/api/system/info').json().get('info', {}).get('timestamp', 'Unknown')}")

    results = []

    # Test 1: System Info
    print_section("1. 系统信息 API")
    results.append(test_api_get("系统信息", "/api/system/info"))

    # Test 2: Storage Stats
    print_section("2. 存储统计 API")
    results.append(test_api_get("存储统计", "/api/storage/stats"))

    # Test 3: Storage Items
    print_section("3. 存储项目 API")
    results.append(test_api_get("存储项目 (limit=10)", "/api/storage/items?limit=10"))

    # Test 4: Crawl API
    print_section("4. 爬取 API")
    results.append(test_api_post(
        "执行爬取",
        "/api/crawl",
        {
            "url": "https://wjx.seu.edu.cn/zhxw/list.htm",
            "mode": "auto",
            "depth": 1
        }
    ))

    # Test 5: Config Test API (will fail without real API key)
    print_section("5. 配置测试 API (预期失败)")
    results.append(test_api_post(
        "LLM配置测试",
        "/api/config/test",
        {
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini",
            "api_key": "test-invalid-key"
        },
        expected_status=400  # Expected to fail
    ))

    # Test 6: Multi-Agent Execute
    print_section("6. 多Agent工作流 API")
    results.append(test_api_post(
        "多Agent执行",
        "/api/multi-agent/execute",
        {
            "url": "https://wjx.seu.edu.cn/zhxw/list.htm",
            "keywords": ["新闻"],
            "depth": 1,
            "enable_optimization": False,
            "enable_rag": False
        }
    ))

    # Test 7: RAG APIs (expected to fail if RAG not enabled)
    print_section("7. RAG API (预期失败，RAG未启用)")
    results.append(test_api_get("RAG统计", "/api/rag/stats", expected_status=503))
    results.append(test_api_get("RAG模式", "/api/rag/patterns?limit=10", expected_status=503))

    # Summary
    print_section("测试总结")
    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"\n总计: {total} 个测试")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"通过率: {(passed/total*100):.1f}%")

    if passed == total:
        print("\n🎉 所有API测试通过！")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")

    print(f"\n测试完成时间: {requests.get(f'{BASE_URL}/api/system/info').json().get('info', {}).get('timestamp', 'Unknown')}")
    print('='*60 + '\n')


if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到服务器")
        print(f"请确保Flask应用正在运行: {BASE_URL}")
        print("启动命令: cd web_app && python app.py")
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试脚本错误: {str(e)}")
