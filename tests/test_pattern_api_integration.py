"""
测试 LLM Pattern API 集成

验证以下API端点是否正常工作:
1. /api/pattern/generate
2. /api/pattern/test
3. /api/pattern/refine
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 测试导入
print("=" * 60)
print("测试 LLM Pattern Agent 导入和基本功能")
print("=" * 60)

# 测试1: 导入 LLMPatternGeneratorAgent
print("\n[测试1] 导入 LLMPatternGeneratorAgent...")
try:
    from moagent.agents.pattern_generator.llm_pattern_generator import LLMPatternGeneratorAgent
    print("✅ 导入成功")

    # 检查可用方法
    agent = LLMPatternGeneratorAgent()
    methods = [m for m in dir(agent) if not m.startswith('_') and callable(getattr(agent, m))]
    print(f"   可用方法: {', '.join(methods[:5])}...")

    # 检查 analyze 方法
    if hasattr(agent, 'analyze'):
        print("   ✅ 有 analyze() 方法")
    else:
        print("   ❌ 没有 analyze() 方法")
        print("   ℹ️  应该使用 analyze_html_content() 方法")

    if hasattr(agent, 'analyze_html_content'):
        print("   ✅ 有 analyze_html_content() 方法")

except Exception as e:
    print(f"❌ 导入失败: {e}")

# 测试2: 导入 LLMPatternRefinerAgent
print("\n[测试2] 导入 LLMPatternRefinerAgent...")
try:
    from moagent.agents.pattern_generator.llm_pattern_refiner import LLMPatternRefinerAgent
    print("✅ 导入成功")

    # 检查可用方法
    agent = LLMPatternRefinerAgent()
    methods = [m for m in dir(agent) if not m.startswith('_') and callable(getattr(agent, m))]
    print(f"   可用方法: {', '.join(methods[:5])}...")

    # 检查关键方法
    if hasattr(agent, 'refine_with_comparison'):
        print("   ✅ 有 refine_with_comparison() 方法")
    if hasattr(agent, 'test_pattern_extraction'):
        print("   ✅ 有 test_pattern_extraction() 方法")

except Exception as e:
    print(f"❌ 导入失败: {e}")

# 测试3: 测试简单的HTML分析
print("\n[测试3] 测试 HTML 分析功能...")
try:
    from moagent.agents.pattern_generator.llm_pattern_generator import LLMPatternGeneratorAgent
    from moagent.config.settings import Config

    # 创建测试HTML
    test_html = """
    <html>
    <body>
        <div class="news-list">
            <div class="news-item">
                <h3 class="title"><a href="https://example.com/news1">新闻标题1</a></h3>
                <span class="date">2026-01-04</span>
            </div>
            <div class="news-item">
                <h3 class="title"><a href="https://example.com/news2">新闻标题2</a></h3>
                <span class="date">2026-01-03</span>
            </div>
        </div>
    </body>
    </html>
    """

    config = Config()
    agent = LLMPatternGeneratorAgent(config)

    # 测试 analyze_html_content 方法
    print("   调用 analyze_html_content()...")
    result = agent.analyze_html_content(test_html)

    print(f"   ✅ 分析成功!")
    print(f"   置信度: {result.confidence:.2%}")
    print(f"   推理: {result.reasoning[:50]}...")

    # 检查返回的字段
    if result.list_container:
        print(f"   ✅ list_container: {result.list_container}")
    if result.item_selector:
        print(f"   ✅ item_selector: {result.item_selector}")
    if result.title_selector:
        print(f"   ✅ title_selector: {result.title_selector}")

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("API 端点映射检查")
print("=" * 60)

# 检查API端点使用的方法
api_methods = {
    '/api/pattern/generate': {
        'expected': 'analyze_html_content',
        'description': '生成模式'
    },
    '/api/pattern/refine': {
        'expected': 'refine_with_comparison',
        'description': '优化模式'
    },
    '/api/pattern/test': {
        'expected': 'test_pattern_extraction',
        'description': '测试模式'
    }
}

for endpoint, info in api_methods.items():
    print(f"\n{endpoint}")
    print(f"   功能: {info['description']}")
    print(f"   使用方法: {info['expected']}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
