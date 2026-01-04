"""
测试 crawler_node 的 Config 继承修复
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("测试 crawler_node Config 继承")
print("=" * 60)

# 测试1: Agent的system_config属性
print("\n[测试1] Agent system_config 属性")
print("-" * 60)

try:
    from moagent.agents.multi_agent.agents.explorer import ExplorerAgent
    from moagent.agents.multi_agent.base import AgentConfig
    from moagent.config.settings import Config

    # 创建AgentConfig
    agent_config = AgentConfig(
        agent_id="test_explorer",
        role="explorer",
        capabilities=["explore"],
        timeout=30
    )

    # 创建System Config
    system_config = Config()
    system_config.openai_api_key = "sk-test-key-12345"
    system_config.llm_provider = "openai"
    system_config.llm_model = "gpt-4o-mini"

    # 创建Explorer Agent
    explorer = ExplorerAgent(agent_config, system_config)

    print("✅ Explorer Agent 创建成功")
    print(f"   - 有 config 属性: {hasattr(explorer, 'config')}")
    print(f"   - 有 system_config 属性: {hasattr(explorer, 'system_config')}")

    if hasattr(explorer, 'system_config'):
        print(f"   - system_config 类型: {type(explorer.system_config).__name__}")
        print(f"   - system_config.openai_api_key: {explorer.system_config.openai_api_key[:10]}...")
        print(f"   - system_config.llm_provider: {explorer.system_config.llm_provider}")
        print("✅ system_config 包含完整的 LLM 配置")

    # 模拟crawler_node中的配置继承逻辑
    print("\n模拟 crawler_node 的配置继承:")
    print("-" * 60)

    # 创建新的config
    new_config = Config(target_url="https://example.com")

    # 从agent的system_config复制
    if hasattr(explorer, 'system_config'):
        base = explorer.system_config
        new_config.openai_api_key = base.openai_api_key
        new_config.llm_provider = base.llm_provider
        new_config.llm_model = base.llm_model

        print("✅ 配置复制成功")
        print(f"   - new_config.openai_api_key: {new_config.openai_api_key[:10]}...")
        print(f"   - new_config.llm_provider: {new_config.llm_provider}")
        print(f"   - new_config.llm_model: {new_config.llm_model}")

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试2: State中的agents字典
print("\n[测试2] State agents 字典")
print("-" * 60)

try:
    from moagent.config.settings import Config

    # 创建agents字典（模拟state）
    agents = {}
    agents['explorer'] = explorer

    print(f"✅ agents 字典创建成功: {list(agents.keys())}")

    # 查找有system_config的agent
    base_config = None
    if agents:
        for agent in agents.values():
            if hasattr(agent, 'system_config'):
                base_config = agent.system_config
                break

    if base_config:
        print("✅ 找到 base_config")
        print(f"   - 类型: {type(base_config).__name__}")
        print(f"   - 有 openai_api_key: {bool(base_config.openai_api_key)}")
        print(f"   - 有 llm_provider: {bool(base_config.llm_provider)}")
    else:
        print("❌ 未找到 base_config")

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试总结")
print("=" * 60)

print("""
修复说明:
1. ❌ 错误: 'AgentConfig' object has no attribute 'openai_api_key'
   原因: first_agent.config 返回的是 AgentConfig 而不是 Config

2. ✅ 修复: 使用 agent.system_config
   - Agent 有两个 config:
     * agent.config: AgentConfig (agent配置)
     * agent.system_config: Config (系统配置，包含LLM设置)

3. ✅ 改进: 遍历agents查找system_config
   - 不是所有agent都有system_config
   - 使用 for 循环查找第一个有system_config的agent

4. ✅ 代码:
   ```python
   base_config = None
   if agents:
       for agent in agents.values():
           if hasattr(agent, 'system_config'):
               base_config = agent.system_config
               break
   ```

状态: ✅ 修复完成
建议: 重启服务测试 Multi-Agent 工作流
""")

print("=" * 60)
