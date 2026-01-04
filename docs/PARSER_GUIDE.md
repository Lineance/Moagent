# MoAgent 解析器模块完整指南

## 目录

1. [解析器架构](#1-解析器架构)
2. [通用解析器](#2-通用解析器-genericparser)
3. [LLM解析器](#3-llm解析器-llmparser)
4. [混合解析器](#4-混合解析器-hybridparser)
5. [自定义解析器](#5-自定义解析器)
6. [模式系统](#6-模式系统)
7. [性能优化](#7-性能优化)

---

## 1. 解析器架构

### 1.1 设计理念

解析器的职责是从**原始HTML/文本**中提取**结构化数据**。

```
原始数据 → 解析器 → 结构化数据

HTML:
<div class="article">
  <h1>标题</h1>
  <p>内容...</p>
</div>

         ↓ 解析器

JSON:
{
  "title": "标题",
  "content": "内容..."
}
```

### 1.2 解析器层次

```
┌─────────────────────────────────────┐
│        应用层                        │
│  (使用解析器获取结构化数据)           │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│        解析器工厂                    │
│  (自动选择最佳解析器)                │
└────┬──────┬──────────┬──────────────┘
     │      │          │
     ▼      ▼          ▼
  Generic  LLM     Hybrid
     │      │          │
     └──────┴──────────┘
            │
     ┌──────▼──────┐
     │ BaseParser  │
     └─────────────┘
```

---

## 2. 通用解析器 (GenericParser)

基于规则的解析器，使用CSS选择器/XPath/正则表达式提取数据。

### 2.1 工作原理

```
输入HTML + 选择器规则
       ↓
1. 解析HTML (BeautifulSoup)
       ↓
2. 应用选择器
       ↓
3. 提取文本/属性
       ↓
4. 数据清洗
       ↓
输出结构化数据
```

### 2.2 基础使用

```python
from moagent.parsers import GenericParser
from moagent.config import Config

# 配置选择器
config = Config(
    parser_mode="generic",
    extraction_rules={
        "title": {
            "selector": "h1.title",
            "attribute": "text",  # 或 "href", "src" 等
            "required": True
        },
        "content": {
            "selector": "div.content",
            "attribute": "text",
            "clean": True  # 自动清洗HTML标签
        },
        "author": {
            "selector": "span.author",
            "attribute": "text",
            "required": False,
            "default": "未知作者"
        },
        "date": {
            "selector": "time[datetime]",
            "attribute": "datetime",
            "format": "%Y-%m-%d"  # 日期格式
        },
        "tags": {
            "selector": "div.tags a.tag",
            "attribute": "text",
            "multiple": True  # 提取多个值
        },
        "image": {
            "selector": "img.featured",
            "attribute": "src"
        }
    }
)

# 创建解析器
parser = GenericParser(config)

# 解析HTML
html = """
<div class="article">
  <h1 class="title">文章标题</h1>
  <div class="content">
    <p>这是文章内容...</p>
  </div>
  <span class="author">张三</span>
  <time datetime="2025-01-04">2025年1月4日</time>
  <div class="tags">
    <a class="tag">技术</a>
    <a class="tag">Python</a>
  </div>
  <img class="featured" src="/image.jpg">
</div>
"""

result = parser.parse(html)

print(result)
# {
#     "title": "文章标题",
#     "content": "这是文章内容...",
#     "author": "张三",
#     "date": "2025-01-04",
#     "tags": ["技术", "Python"],
#     "image": "/image.jpg"
# }
```

### 2.3 高级选择器

```python
# CSS选择器示例
rules = {
    # ID选择器
    "title1": "#article-title",

    # 类选择器
    "title2": ".title",

    # 属性选择器
    "link": "a[href^='http']",  # href以http开头
    "external": "a[target='_blank']",

    # 组合选择器
    "content": "div.article > p:first-child",

    # 伪类选择器
    "first_item": "ul.news > li:first-child",
    "last_item": "ul.news > li:last-child",
    "nth_item": "ul.news > li:nth-child(3)",

    # 复杂选择器
    "nested": "div.container div.content p.text"
}

# XPath选择器
rules = {
    "title": {
        "selector": "//h1[@class='title']/text()",
        "type": "xpath"
    },
    "all_links": {
        "selector": "//a/@href",
        "type": "xpath",
        "multiple": True
    }
}

# 正则表达式
rules = {
    "email": {
        "selector": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "type": "regex"
    },
    "phone": {
        "selector": r"\d{3}-\d{4}-\d{4}",
        "type": "regex"
    }
}
```

### 2.4 数据清洗

```python
parser = GenericParser(config)

# 启用清洗选项
parser.enable_cleaning(
    # HTML清洗
    strip_html=True,        # 移除HTML标签
    strip_scripts=True,     # 移除脚本
    strip_styles=True,      # 移除样式

    # 文本清洗
    strip_whitespace=True,  # 移除多余空白
    normalize_spaces=True,  # 标准化空格
    remove_breaks=True,     # 移除换行符

    # 内容清洗
    min_length=10,         # 最小长度
    max_length=10000,      # 最大长度
    remove_duplicates=True, # 去重

    # 自定义清洗函数
    custom_cleaners=[
        lambda text: text.replace("...", "…"),
        lambda text: text.strip("【】")
    ]
)

result = parser.parse(html)
```

### 2.5 字段验证

```python
parser = GenericParser(config)

# 添加验证规则
parser.add_validator("title", [
    lambda x: len(x) > 5,  # 标题至少5个字符
    lambda x: len(x) < 100  # 标题最多100个字符
])

parser.add_validator("email", [
    lambda x: "@" in x and "." in x
])

parser.add_validator("date", [
    lambda x: datetime.strptime(x, "%Y-%m-%d")
])

# 解析时验证
result = parser.parse(html)

if result.has_errors():
    print("验证失败:")
    for field, errors in result.errors.items():
        print(f"  {field}: {errors}")
else:
    print("验证通过")
```

---

## 3. LLM解析器 (LLMParser)

使用大语言模型理解页面语义并提取数据。

### 3.1 工作原理

```
HTML + 提取需求
       ↓
发送给LLM (带详细提示词)
       ↓
LLM分析页面结构
       ↓
LLM提取目标字段
       ↓
返回结构化JSON
```

### 3.2 基础使用

```python
from moagent.parsers import LLMParser
from moagent.config import Config

# 配置
config = Config(
    parser_mode="llm",
    llm_provider="openai",
    llm_model="gpt-4o-mini",
    llm_temperature=0.1  # 低温度以提高一致性
)

# 创建解析器
parser = LLMParser(config)

# 定义提取字段
extraction_schema = {
    "title": "文章标题",
    "content": "正文内容",
    "author": "作者姓名",
    "date": "发布日期 (YYYY-MM-DD格式)",
    "tags": "文章标签列表",
    "summary": "文章摘要 (50字以内)"
}

# 解析
result = parser.parse(
    html=html,
    schema=extraction_schema
)

print(result)
# {
#     "title": "AI技术突破",
#     "content": "完整内容...",
#     "author": "李四",
#     "date": "2025-01-04",
#     "tags": ["AI", "技术"],
#     "summary": "本文介绍了最新的AI技术进展..."
# }
```

### 3.3 自定义提示词

```python
parser = LLMParser(config)

# 设置自定义提示词
parser.set_system_prompt("""
你是一个专业的内容提取助手。你的任务是从HTML中提取结构化数据。

规则:
1. 仔细阅读整个HTML，理解页面结构
2. 区分主要内容和其他内容(广告、导航等)
3. 提取最相关、最重要的信息
4. 如果字段不存在，返回null
5. 日期统一使用YYYY-MM-DD格式
6. 保持原文的意思，不要改写

输出格式必须是JSON。
""")

parser.set_user_prompt("""
请从以下HTML中提取文章信息:

HTML:
{html}

需要提取的字段:
{schema}

返回JSON格式的结果。
""")
```

### 3.4 批量解析

```python
# 批量解析多个HTML (节省成本)
htmls = [html1, html2, html3, ...]

results = parser.parse_batch(
    htmls=htmls,
    schema=extraction_schema,
    batch_size=5  # 每批处理5个
)

# 批处理会合并请求，减少API调用次数
```

### 3.5 结果验证

```python
# 验证LLM返回的JSON
parser.set_output_validator(lambda result: {
    "is_valid": all([
        "title" in result,
        "content" in result,
        len(result.get("title", "")) > 0
    ]),
    "errors": [
        "Missing title" if "title" not in result else None,
        "Missing content" if "content" not in result else None
    ]
})

# 如果验证失败，自动重试
parser.max_validation_retries = 3
result = parser.parse(html)
```

---

## 4. 混合解析器 (HybridParser)

结合通用解析器和LLM解析器的优势。

### 4.1 工作流程

```
HTML输入
    │
    ▼
┌─────────────────┐
│ 尝试通用解析    │
│ (快速、低成本)  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
   成功      失败/低置信度
    │         │
    │         ▼
    │    ┌─────────────────┐
    │    │ LLM解析         │
    │    │ (智能、高成本)  │
    │    └────────┬────────┘
    │             │
    └──────┬──────┘
           ▼
      返回结果
```

### 4.2 基础使用

```python
from moagent.parsers import HybridParser

config = Config(
    parser_mode="hybrid",
    confidence_threshold=0.7  # 置信度阈值
)

parser = HybridParser(config)

# 设置混合策略
parser.set_strategy(
    # 第一步: 尝试通用解析
    primary_parser="generic",

    # 置信度低于阈值时使用LLM
    fallback_parser="llm",

    # 判断是否需要LLM的条件
    use_llm_if=lambda result: (
        result.confidence < 0.7 or
        result.missing_required_fields or
        len(result.content) < 100
    )
)

result = parser.parse(html)

# 查看使用的解析器
print(f"使用解析器: {result.used_parser}")
print(f"置信度: {result.confidence}")
```

### 4.3 智能降级示例

```python
parser = HybridParser(config)

# 定义降级条件
parser.add_fallback_condition(
    name="empty_fields",
    condition=lambda r: len(r.missing_fields) > 2,
    action="use_llm"
)

parser.add_fallback_condition(
    name="low_quality",
    condition=lambda r: r.quality_score < 0.5,
    action="use_llm"
)

parser.add_fallback_condition(
    name="suspicious_content",
    condition=lambda r: (
        "广告" in r.content or
        len(r.content) < 50
    ),
    action="use_llm"
)

result = parser.parse(html)
```

---

## 5. 自定义解析器

### 5.1 继承BaseParser

```python
from moagent.parsers.base import BaseParser

class CustomParser(BaseParser):
    """自定义解析器"""

    def __init__(self, config):
        super().__init__(config)
        # 初始化你的资源

    def parse(self, html: str, **kwargs) -> dict:
        """
        解析HTML

        Args:
            html: 原始HTML
            **kwargs: 额外参数

        Returns:
            解析结果字典
        """
        # 1. 预处理
        cleaned_html = self._preprocess(html)

        # 2. 提取数据
        data = self._extract(cleaned_html)

        # 3. 后处理
        result = self._postprocess(data)

        return result

    def _preprocess(self, html: str) -> str:
        """预处理"""
        # 移除注释、多余空白等
        return html.strip()

    def _extract(self, html: str) -> dict:
        """核心提取逻辑"""
        # 实现你的提取逻辑
        return {"field": "value"}

    def _postprocess(self, data: dict) -> dict:
        """后处理"""
        # 数据清洗、格式转换等
        return data

# 使用自定义解析器
parser = CustomParser(config)
result = parser.parse(html)
```

### 5.2 注册到工厂

```python
from moagent.parsers import register_parser

# 方法1: 装饰器
@register_parser("custom")
class CustomParser(BaseParser):
    pass

# 方法2: 函数注册
def custom_parser_factory(config):
    return CustomParser(config)

register_parser("custom", custom_parser_factory)

# 使用
from moagent.parsers import get_parser
parser = get_parser(mode="custom", config=config)
```

---

## 6. 模式系统

### 6.1 模式定义

```python
# 模式示例
pattern = {
    "name": "news_article",
    "description": "新闻文章提取模式",

    # 列表页模式
    "list": {
        "container": "ul.news-list",
        "item": "li.news-item",
        "fields": {
            "title": "h2.title",
            "url": "a.link@href",
            "date": "span.date"
        }
    },

    # 详情页模式
    "detail": {
        "fields": {
            "title": "h1.article-title",
            "content": "div.article-content",
            "author": "span.author",
            "date": "time@datetime"
        }
    },

    # 后处理规则
    "post_process": {
        "url": {
            "transform": "absolute_url",  # 转换为绝对URL
            "base": "https://example.com"
        },
        "date": {
            "format": "%Y-%m-%d"
        },
        "content": {
            "min_length": 50,
            "remove_html": True
        }
    },

    # 验证规则
    "validation": {
        "required_fields": ["title", "url"],
        "optional_fields": ["date", "author"]
    }
}
```

### 6.2 保存和加载模式

```python
from moagent.parsers.patterns import PatternManager

# 保存模式
manager = PatternManager()
manager.save("news_article", pattern, "patterns/news.yaml")

# 加载模式
loaded_pattern = manager.load("patterns/news.yaml")

# 使用模式
parser = GenericParser(config)
parser.set_pattern(loaded_pattern)

result = parser.parse(html)
```

### 6.3 模式生成器

```python
from moagent.agents.pattern_generator import LLMPatternGeneratorAgent

generator = LLMPatternGeneratorAgent(config)

# 从URL生成模式
pattern = generator.generate_from_url(
    url="https://news.example.com",
    page_type="list"  # 或 "detail"
)

# 查看生成的模式
print(pattern.selectors)
print(pattern.confidence)

# 保存模式
pattern.save("patterns/example_com.yaml")
```

---

## 7. 性能优化

### 7.1 并行解析

```python
from moagent.parsers import ParallelParser

# 并行解析多个HTML
parser = ParallelParser(
    parser=GenericParser(config),
    max_workers=4  # 4个工作线程
)

htmls = [html1, html2, html3, html4]
results = parser.parse_batch(htmls)
```

### 7.2 缓存解析结果

```python
from moagent.parsers import CachedParser

# 缓存解析结果
parser = CachedParser(
    parser=GenericParser(config),
    cache_size=1000,  # 缓存1000条
    ttl=3600  # 1小时过期
)

# 相同HTML会直接返回缓存结果
result1 = parser.parse(html)  # 实际解析
result2 = parser.parse(html)  # 从缓存读取
```

### 7.3 增量解析

```python
# 只解析新增内容
parser = GenericParser(config)

# 获取已处理URL的哈希
processed_hashes = storage.get_all_hashes()

for url, html in new_htmls:
    html_hash = hash(html)

    if html_hash not in processed_hashes:
        # 只解析新内容
        result = parser.parse(html)
        storage.save(result)
        processed_hashes.add(html_hash)
```

### 7.4 流式解析

```python
# 流式处理大文件
parser = GenericParser(config)

with open("large.html", "r") as f:
    for chunk in parser.parse_stream(f):
        # 逐块处理
        process(chunk)
```

---

## 8. 调试技巧

### 8.1 可视化解析过程

```python
parser = GenericParser(config)

# 启用调试模式
parser.enable_debug(
    show_html=True,        # 显示HTML
    show_selectors=True,   # 显示选择器
    show_matches=True,     # 显示匹配结果
    show_time=True         # 显示耗时
)

result = parser.parse(html)

# 输出示例:
# [DEBUG] HTML length: 15234 bytes
# [DEBUG] Selector: h1.title
# [DEBUG] Matches: 1
# [DEBUG] Extracted: "文章标题"
# [DEBUG] Time: 0.02s
```

### 8.2 测试选择器

```python
parser = GenericParser(config)

# 测试选择器是否匹配
matches = parser.test_selector(
    html=html,
    selector="h1.title"
)

print(f"找到 {len(matches)} 个匹配")
for match in matches:
    print(f"  - {match}")
```

### 8.3 错误追踪

```python
parser = GenericParser(config)

# 启用错误追踪
parser.track_errors(
    save_to_file="parser_errors.log",
    include_html=True,
    include_context=True
)

try:
    result = parser.parse(html)
except Exception as e:
    # 查看详细错误信息
    parser.show_error_context(e)
```

---

## 9. 最佳实践

### 9.1 选择合适的解析器

```
决策标准:

页面结构稳定? → GenericParser
页面结构复杂? → LLMParser
未知页面? → HybridParser

需要最高性能? → GenericParser
需要最高准确率? → LLMParser
需要平衡? → HybridParser

成本敏感? → GenericParser
质量敏感? → LLMParser
```

### 9.2 编写健壮的选择器

```python
# 好的选择器
good_selectors = {
    # 使用具体的类名
    "title": "h1.article-title",

    # 使用属性选择器
    "date": "time[datetime]",

    # 使用层级关系
    "content": "div.article-body > p"
}

# 避免的选择器
bad_selectors = {
    # 过于宽泛
    "title": "div div div h1",

    # 依赖位置
    "content": "div:nth-child(3) p:first-child",

    # 脆弱的选择器
    "link": "a[onclick*='openArticle']"
}
```

### 9.3 处理边界情况

```python
parser = GenericParser(config)

# 添加默认值
parser.set_defaults({
    "title": "无标题",
    "author": "匿名",
    "date": None
})

# 处理空值
parser.add_post_processor(lambda result: {
    k: v for k, v in result.items()
    if v not in [None, "", []]
})

# 标准化输出
parser.normalize_output(
    trim_strings=True,
    empty_values_to_none=True,
    convert_types=True
)
```

---

## 10. 实战案例

### 10.1 解析新闻网站

```python
from moagent.parsers import HybridParser

config = Config(
    parser_mode="hybrid",
    extraction_rules={
        "title": "h1.title",
        "content": "div.content",
        "category": "span.category",
        "date": "time@datetime"
    }
)

parser = HybridParser(config)

# 批量解析
from moagent.storage import get_storage
storage = get_storage("sqlite:///./data/news.db")

# 获取未解析的HTML
unparsed = storage.get_unparsed_html()

for item in unparsed:
    result = parser.parse(item['html'])

    # 保存解析结果
    storage.save_parsed({
        "url": item['url'],
        "parsed_data": result,
        "parsed_at": datetime.now()
    })
```

### 10.2 解析电商产品

```python
# 使用LLM解析复杂结构
from moagent.parsers import LLMParser

parser = LLMParser(config)

product_schema = {
    "name": "产品名称",
    "price": "价格 (数字)",
    "original_price": "原价 (数字)",
    "description": "产品描述",
    "specifications": "规格参数 (JSON格式)",
    "images": "产品图片URL列表",
    "reviews_count": "评论数",
    "rating": "评分 (0-5)"
}

result = parser.parse(
    html=product_html,
    schema=product_schema
)
```

### 10.3 解析社交媒体

```python
# 解析推文/帖子
from moagent.parsers import GenericParser

config = Config(
    extraction_rules={
        "author": "span.user-name",
        "handle": "span.user-handle",
        "content": "div.tweet-text",
        "timestamp": "time@datetime",
        "likes": "span.like-count",
        "retweets": "span.retweet-count",
        "replies": "span.reply-count",
        "attachments": "div.media img@src"
    }
)

parser = GenericParser(config)
result = parser.parse(tweet_html)
```

---

**文档版本**: v1.0
**最后更新**: 2025-01-04
**反馈**: [GitHub Issues](https://github.com/your-org/moagent/issues)
