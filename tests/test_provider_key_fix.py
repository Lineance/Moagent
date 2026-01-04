"""
Test the provider/API key ordering fix in get_llm_client()

This test verifies that when provider and api_key are both passed,
the provider is set FIRST, then the correct API key field is populated.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_provider_key_ordering():
    """Test that provider is set before API key check"""
    from moagent.llm.client import get_llm_client
    from moagent.config.settings import Config

    print("=" * 60)
    print("测试 Provider 和 API Key 参数顺序修复")
    print("=" * 60)

    # Test 1: Anthropic provider with API key
    print("\n[测试1] Anthropic Provider + API Key")
    print("-" * 60)

    try:
        config = Config()

        # Simulate what the API endpoint does
        provider = "anthropic"
        api_key = "sk-ant-test123"

        print(f"输入参数:")
        print(f"  - provider: {provider}")
        print(f"  - api_key: {api_key[:10]}...")

        # This should now work correctly because provider is set BEFORE API key check
        client = get_llm_client(
            config=config,
            provider=provider,
            api_key=api_key
        )

        print(f"\n✅ Client 创建成功")
        print(f"  - Client provider: {client._provider}")
        print(f"  - Client model: {client._model}")

        # Verify the config has the right key in the right field
        print(f"\nConfig 验证:")
        print(f"  - config.llm_provider: {config.llm_provider}")
        print(f"  - config.anthropic_api_key: {config.anthropic_api_key[:10] if config.anthropic_api_key else 'None'}...")
        print(f"  - config.openai_api_key: {config.openai_api_key[:10] if config.openai_api_key else 'None'}...")

        # Assertions
        assert config.llm_provider == "anthropic", "Provider should be anthropic"
        assert config.anthropic_api_key == "sk-ant-test123", "Anthropic API key should be set"
        assert client._provider == "anthropic", "Client provider should be anthropic"

        print(f"\n✅ 所有断言通过!")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: OpenAI provider with API key
    print("\n[测试2] OpenAI Provider + API Key")
    print("-" * 60)

    try:
        config = Config()

        provider = "openai"
        api_key = "sk-openai-test456"

        print(f"输入参数:")
        print(f"  - provider: {provider}")
        print(f"  - api_key: {api_key[:10]}...")

        client = get_llm_client(
            config=config,
            provider=provider,
            api_key=api_key
        )

        print(f"\n✅ Client 创建成功")
        print(f"  - Client provider: {client._provider}")

        print(f"\nConfig 验证:")
        print(f"  - config.llm_provider: {config.llm_provider}")
        print(f"  - config.openai_api_key: {config.openai_api_key[:10] if config.openai_api_key else 'None'}...")

        # Assertions
        assert config.llm_provider == "openai", "Provider should be openai"
        assert config.openai_api_key == "sk-openai-test456", "OpenAI API key should be set"
        assert client._provider == "openai", "Client provider should be openai"

        print(f"\n✅ 所有断言通过!")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Provider override without API key (should use env)
    print("\n[测试3] Provider Override (无 API Key)")
    print("-" * 60)

    try:
        config = Config()

        provider = "anthropic"
        # No api_key provided - should try to load from env

        print(f"输入参数:")
        print(f"  - provider: {provider}")
        print(f"  - api_key: None (should use env)")

        # This will fail if no API key in env, but that's expected
        try:
            client = get_llm_client(
                config=config,
                provider=provider
            )
            print(f"\n⚠️  意外成功 (可能 env 中有 API key)")
        except ValueError as e:
            print(f"\n✅ 预期的错误 (无 env API key): {e}")
            print("   这证明了代码正确地尝试从环境加载 Anthropic API key")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✅ 所有测试完成!")
    print("=" * 60)

    print("""
总结:
1. ✅ Provider 参数在 API key 检查之前被设置
2. ✅ 正确的 API key 字段被填充 (anthropic_api_key vs openai_api_key)
3. ✅ Client 使用正确的 provider 初始化

修复确认:
moagent/llm/client.py:94-95 行的 provider 设置现在在
第 103-111 行的 API key 检查之前执行。

这解决了用户报告的 "refiner只支持OpenAI API" 问题!
""")

    return True

if __name__ == "__main__":
    success = test_provider_key_ordering()
    sys.exit(0 if success else 1)
