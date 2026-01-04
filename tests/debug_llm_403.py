"""
调试LLM 403错误的脚本
用于诊断为什么全文提取和pattern generator会报403
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from moagent.config.settings import Config
from moagent.llm.client import get_llm_client

print("=" * 60)
print("LLM 403错误诊断")
print("=" * 60)

# 1. 检查配置
print("\n[1] 检查LLM配置")
print("-" * 60)

config = Config()
print(f"Provider: {config.llm_provider}")
print(f"Model: {config.llm_model}")
print(f"API Base URL: {config.llm_api_base_url or '(None - 使用官方端点)'}")
print(f"Has OpenAI Key: {bool(config.openai_api_key)}")
print(f"Has Anthropic Key: {bool(config.anthropic_api_key)}")

# 2. 测试基本chat调用
print("\n[2] 测试基本chat调用 (简单消息)")
print("-" * 60)

try:
    llm = get_llm_client(config)
    messages = [{"role": "user", "content": "Say 'Hello' in JSON format"}]

    print(f"调用 llm.chat()...")
    response = llm.chat_with_metadata(messages, max_tokens=50)

    print(f"✅ 成功!")
    print(f"   Provider: {response.provider}")
    print(f"   Model: {response.model}")
    print(f"   Content: {response.content[:100]}")
    print(f"   Tokens: {response.total_tokens}")

except Exception as e:
    print(f"❌ 失败: {e}")

# 3. 测试长消息调用 (模拟pattern generator)
print("\n[3] 测试长消息调用 (模拟pattern generator)")
print("-" * 60)

try:
    llm = get_llm_client(config)

    # 构造类似pattern generator的长prompt
    long_prompt = """Analyze HTML for news/article list pattern. Output JSON only.

HTML:
```html
<ul class="news-list">
  <li class="item">
    <h3><a href="/article1">Title 1</a></h3>
    <span class="date">2024-01-01</span>
  </li>
  <li class="item">
    <h3><a href="/article2">Title 2</a></h3>
    <span class="date">2024-01-02</span>
  </li>
</ul>
```

TASK: Find the article list container and item selectors.

CRITICAL RULES - FOLLOW EXACTLY:
1. EXCLUDE navigation/header/footer/sidebar links
2. EXCLUDE category/filter links and pagination
3. Focus on article links (titles with dates where possible)
4. List container must contain multiple similar items

Required JSON structure:
{
  "list_container": {"tag": "ul", "class": "news-list"},
  "item_selector": {"tag": "li", "class": "item"},
  "title_selector": {"tag": "h3", "link": true},
  "url_selector": {"type": "attr", "attr": "href"},
  "date_selector": {"tag": "span", "class": "date"},
  "confidence": 0.9,
  "reasoning": "Test explanation"
}

Return ONLY valid JSON, no markdown, no commentary.
"""

    messages = [
        {"role": "system", "content": "You are a web scraping expert. Output ONLY valid JSON describing news/article list patterns."},
        {"role": "user", "content": long_prompt}
    ]

    print(f"调用 llm.chat_with_metadata() (pattern generator模式)...")
    response = llm.chat_with_metadata(messages, temperature=0.3, max_tokens=800)

    print(f"✅ 成功!")
    print(f"   Provider: {response.provider}")
    print(f"   Model: {response.model}")
    print(f"   Content length: {len(response.content)}")
    print(f"   Tokens: {response.total_tokens}")
    print(f"   Content preview: {response.content[:200]}...")

except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    print(f"详细错误:")
    traceback.print_exc()

# 4. 测试全文提取风格的prompt
print("\n[4] 测试全文提取prompt")
print("-" * 60)

try:
    llm = get_llm_client(config)

    fulltext_prompt = """You are an expert article content extractor. Analyze the following HTML content and extract structured article information.

URL: https://example.com/article/123

HTML Content:
```html
<article>
  <h1>Test Article Title</h1>
  <p>This is a test article content with multiple paragraphs.</p>
  <p>Second paragraph here.</p>
</article>
```

Please extract the following information and return ONLY valid JSON:

{
    "title": "Main article title",
    "content": "Full article text content",
    "timestamp": "Publication date/time",
    "author": "Author name"
}

Rules:
1. Extract the MAIN article title
2. Extract FULL content
3. Return ONLY JSON, no other text

Focus on main article content.
"""

    messages = [{"role": "user", "content": fulltext_prompt}]

    print(f"调用 llm.chat() (全文提取模式)...")
    content = llm.chat(messages, temperature=0.1, max_tokens=500)

    print(f"✅ 成功!")
    print(f"   Content length: {len(content)}")
    print(f"   Content preview: {content[:200]}...")

except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 诊断结果
print("\n" + "=" * 60)
print("诊断总结")
print("=" * 60)

print("""
如果[2]成功但[3]或[4]失败，可能的原因:

1. **API代理限制**:
   - 某些代理对长prompt或高token使用有限制
   - 解决: 使用官方端点（清空API Base URL）

2. **API Key权限**:
   - API Key可能没有messages/create权限
   - 解决: 检查API Key权限设置

3. **请求格式问题**:
   - 某些代理对特定请求格式有要求
   - 解决: 检查代理文档

4. **速率限制**:
   - 短时间内请求过多导致临时限制
   - 解决: 等待几分钟后重试

5. **Model限制**:
   - 某些模型不支持高max_tokens
   - 解决: 降低max_tokens值

建议:
1. 访问 http://127.0.0.1:5000/config
2. 清空 "API Base URL" 字段
3. 保存配置
4. 重新测试
""")

print("=" * 60)
