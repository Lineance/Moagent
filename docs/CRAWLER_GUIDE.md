# MoAgent 爬虫模块完整使用指南

## 目录

1. [爬虫架构概述](#1-爬虫架构概述)
2. [列表爬虫详解](#2-列表爬虫详解)
3. [内容爬虫详解](#3-内容爬虫详解)
4. [爬虫工厂模式](#4-爬虫工厂模式)
5. [高级配置](#5-高级配置)
6. [性能优化](#6-性能优化)
7. [实战案例](#7-实战案例)

---

## 1. 爬虫架构概述

### 1.1 设计理念

MoAgent 爬虫系统采用**策略模式**和**工厂模式**，实现:

- ✅ **多策略支持**: 同一接口，不同实现
- ✅ **智能降级**: 自动选择最佳策略
- ✅ **易于扩展**: 添加新爬虫无需修改现有代码
- ✅ **统一配置**: 一套配置适用所有爬虫

### 1.2 架构图

```
┌─────────────────────────────────────────────────┐
│              爬虫工厂 (CrawlerFactory)           │
│  根据配置和URL特征自动选择最佳爬虫                │
└────────────┬────────────────────────────────────┘
             │
    ┌────────┼────────┬────────┬────────┐
    │        │        │        │        │
    ▼        ▼        ▼        ▼        ▼
  Static   Dynamic    RSS      LLM    Hybrid
    │        │        │        │        │
    └────────┴────────┴────────┴────────┘
                │
                ▼
        ┌───────────────┐
        │  BaseCrawler  │
        │  (统一接口)    │
        └───────────────┘
```

### 1.3 基础接口

所有爬虫继承自 `BaseCrawler`:

```python
class BaseCrawler(ABC):
    """爬虫基类"""

    @abstractmethod
    def crawl(self, url: str, **kwargs) -> List[Dict[str, Any]]:
        """
        爬取URL并返回数据

        Args:
            url: 目标URL
            **kwargs: 额外参数

        Returns:
            爬取结果列表
        """
        pass

    def fetch(self, url: str) -> str:
        """
        获取HTML内容 (带重试)

        Returns:
            HTML字符串
        """
        # 实现重试逻辑
        pass

    def handle_error(self, error: Exception) -> None:
        """
        错误处理

        Args:
            error: 捕获的异常
        """
        logger.error(f"Crawl error: {error}")
        pass
```

---

## 2. 列表爬虫详解

列表爬虫用于从**列表页面**提取多个文章/新闻的链接和摘要信息。

### 2.1 HTML列表爬虫 (HTMLListCrawler)

**适用场景**:
- ✅ 传统静态HTML网站
- ✅ 内容在HTML中直接可见
- ✅ 不需要JavaScript渲染

**技术实现**:
- 使用 `requests` 获取HTML
- 使用 `BeautifulSoup4` 解析
- 使用CSS选择器或XPath提取

#### 完整使用示例

```python
from moagent.crawlers.list import HTMLListCrawler
from moagent.config import Config
import logging

# 启用日志
logging.basicConfig(level=logging.INFO)

# 1. 基础配置
config = Config(
    target_url="https://news.example.com",
    crawl_mode="static"
)

# 2. 创建爬虫
crawler = HTMLListCrawler(config)

# 3. 基础爬取
articles = crawler.crawl()

# 4. 查看结果
for article in articles[:5]:  # 显示前5条
    print(f"标题: {article['title']}")
    print(f"链接: {article['url']}")
    print(f"日期: {article.get('date', 'N/A')}")
    print("-" * 50)
```

#### 高级配置

```python
# 使用自定义选择器
config = Config(
    target_url="https://news.example.com",
    crawler_patterns={
        # 列表容器
        "list_container": {
            "tag": "ul",
            "class": "news-list"
        },
        # 列表项
        "list_item": {
            "tag": "li"
        },
        # 字段提取
        "fields": {
            "title": {
                "selector": "h2.title",
                "extract": "text"
            },
            "url": {
                "selector": "a.link",
                "extract": "href"
            },
            "date": {
                "selector": "span.date",
                "extract": "text"
            },
            "summary": {
                "selector": "p.summary",
                "extract": "text"
            }
        }
    }
)

crawler = HTMLListCrawler(config)
articles = crawler.crawl()
```

#### 错误处理

```python
try:
    articles = crawler.crawl()
except ConnectionError as e:
    print(f"网络连接失败: {e}")
except ValueError as e:
    print(f"HTML解析失败: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

### 2.2 动态列表爬虫 (DynamicListCrawler)

**适用场景**:
- ✅ React/Vue/Angular等SPA应用
- ✅ 内容由JavaScript动态生成
- ✅ 需要等待页面加载完成

**技术实现**:
- 使用 `Playwright` 控制浏览器
- 等待页面完全加载
- 执行JavaScript获取最终HTML

#### 基础使用

```python
from moagent.crawlers.list import DynamicListCrawler

config = Config(
    target_url="https://spa.example.com/news",
    crawl_mode="dynamic"
)

crawler = DynamicListCrawler(config)

# 可选: 设置浏览器选项
crawler.set_browser_options(
    headless=True,      # 无头模式
    timeout=30000,      # 超时30秒
    wait_for_selector=".news-list"  # 等待选择器出现
)

articles = crawler.crawl()
```

#### 高级功能

```python
# 执行自定义JavaScript
crawler.add_script("""
    // 点击"加载更多"按钮
    document.querySelector('.load-more').click();
""")

# 等待特定条件
crawler.wait_for_condition(
    lambda: len(document.querySelectorAll('.news-item')) > 20
)

# 处理无限滚动
crawler.enable_infinite_scroll(
    max_scrolls=5,      # 最多滚动5次
    scroll_pause=2000   # 每次滚动暂停2秒
)

articles = crawler.crawl()
```

### 2.3 RSS列表爬虫 (RSSListCrawler)

**适用场景**:
- ✅ 网站提供RSS/Atom订阅
- ✅ 需要获取最新内容
- ✅ 对数据完整性要求高

#### 基础使用

```python
from moagent.crawlers.list import RSSListCrawler

config = Config(
    target_url="https://blog.example.com/rss.xml",
    crawl_mode="rss"
)

crawler = RSSListCrawler(config)
articles = crawler.crawl()

# RSS特殊字段
for article in articles:
    print(f"标题: {article['title']}")
    print(f"链接: {article['link']}")
    print(f"发布时间: {article['published']}")
    print(f"作者: {article.get('author', 'N/A')}")
    print(f"分类: {article.get('categories', [])}")
    print("-" * 50)
```

### 2.4 LLM列表爬虫 (LLMListCrawler)

**适用场景**:
- ✅ 页面结构极其复杂
- ✅ 传统方法无法提取
- ✅ 需要理解页面语义

#### 工作原理

```
HTML页面
    │
    ▼
发送到LLM (附带分析提示词)
    │
    ▼
LLM分析页面结构
    │
    ▼
返回提取规则和数据
    │
    ▼
结构化结果
```

#### 基础使用

```python
from moagent.crawlers.list import LLMListCrawler

config = Config(
    target_url="https://complex.example.com",
    crawl_mode="llm",
    llm_provider="openai",
    llm_model="gpt-4o-mini"
)

crawler = LLMListCrawler(config)
articles = crawler.crawl()

# LLM还返回分析过程
print(crawler.last_analysis.reasoning)
print(crawler.last_analysis.confidence)
```

#### 自定义提示词

```python
crawler.set_prompt("""
分析以下HTML页面，提取新闻列表信息。

要求:
1. 找到列表容器
2. 提取每条新闻的: 标题、链接、发布时间、摘要
3. 忽略广告和无关内容
4. 返回JSON格式

页面HTML:
{html}
""")
```

### 2.5 混合列表爬虫 (HybridListCrawler)

**智能降级策略**:

```
1. 尝试规则爬取 (最快)
    │
    ├─ 成功 → 返回结果
    │
    └─ 失败
        │
        ▼
2. 尝试动态爬取
    │
    ├─ 成功 → 返回结果
    │
    └─ 失败
        │
        ▼
3. 尝试LLM爬取 (最慢但最智能)
    │
    └─ 返回结果
```

#### 基础使用

```python
from moagent.crawlers.list import HybridListCrawler

config = Config(
    target_url="https://unknown.example.com",
    crawl_mode="auto"  # 自动选择
)

crawler = HybridListCrawler(config)

# 设置策略
crawler.set_fallback_strategy([
    "static",   # 先尝试静态
    "dynamic",  # 再尝试动态
    "llm"       # 最后使用LLM
])

articles = crawler.crawl()

# 查看实际使用的策略
print(f"使用策略: {crawler.used_strategy}")
print(f"成功提取: {len(articles)}条")
```

---

## 3. 内容爬虫详解

内容爬虫用于从**详情页面**提取完整的文章内容。

### 3.1 模式内容爬虫 (PatternFullTextCrawler)

基于预定义模式提取内容。

#### 基础使用

```python
from moagent.crawlers.content import PatternFullTextCrawler

config = Config(
    content_selectors={
        "title": "h1.article-title",
        "content": "div.article-content",
        "author": "span.author-name",
        "date": "time.publish-date",
        "tags": "div.tags a.tag"
    }
)

crawler = PatternFullTextCrawler(config)
article = crawler.crawl("https://example.com/article/123")

# 结果示例:
# {
#     "title": "文章标题",
#     "content": "完整文章内容...",
#     "author": "作者名",
#     "date": "2025-01-04",
#     "tags": ["技术", "Python"],
#     "images": ["url1", "url2"],
#     "word_count": 1500
# }
```

#### 清洗选项

```python
crawler.enable_cleaning(
    remove_ads=True,           # 移除广告
    remove_scripts=True,       # 移除脚本
    remove_styles=True,        # 移除样式
    min_paragraph_length=50,   # 最小段落长度
    preserve_formatting=True   # 保留格式
)
```

### 3.2 LLM内容爬虫 (LLMFullTextCrawler)

使用LLM理解页面语义并提取内容。

#### 基础使用

```python
from moagent.crawlers.content import LLMFullTextCrawler

config = Config(
    llm_provider="openai",
    llm_model="gpt-4o"
)

crawler = LLMFullTextCrawler(config)
article = crawler.crawl("https://example.com/article/123")

# LLM可以智能识别:
# - 正文 vs 广告 vs 评论
# - 主要内容 vs 侧边栏
# - 文章结构 (标题、段落、列表)
```

### 3.3 混合内容爬虫 (HybridFullTextCrawler)

结合规则和LLM的优势。

```python
from moagent.crawlers.content import HybridFullTextCrawler

crawler = HybridFullTextCrawler(config)

# 设置置信度阈值
crawler.set_confidence_threshold(0.8)

article = crawler.crawl("https://example.com/article/123")

# 如果规则提取置信度 < 0.8，自动使用LLM验证
```

---

## 4. 爬虫工厂模式

工厂自动选择最合适的爬虫。

### 4.1 自动选择

```python
from moagent.crawlers import get_crawler

# 工厂会根据:
# 1. 配置的crawl_mode
# 2. URL特征
# 3. 历史数据
# 自动选择最佳爬虫

crawler = get_crawler(
    url="https://example.com/news",
    config=config
)

# 查看选择的爬虫类型
print(f"爬虫类型: {type(crawler).__name__}")
```

### 4.2 手动指定

```python
# 强制使用特定爬虫
crawler = get_crawler(
    url="https://example.com/news",
    config=config,
    crawler_type="dynamic"  # 强制使用动态爬虫
)
```

---

## 5. 高级配置

### 5.1 请求配置

```python
config = Config(
    # 超时设置
    timeout=30,

    # 重试设置
    max_retries=3,
    retry_delay=1,

    # 请求头
    headers={
        "User-Agent": "Mozilla/5.0...",
        "Accept": "text/html",
        "Accept-Language": "en-US"
    },

    # 代理
    proxy="http://proxy.example.com:8080",

    # 速率限制
    rate_limit={
        "requests_per_second": 2,
        "burst_size": 5
    }
)
```

### 5.2 认证配置

```python
# Basic Auth
config = Config(
    auth={
        "type": "basic",
        "username": "user",
        "password": "pass"
    }
)

# API Key
config = Config(
    auth={
        "type": "api_key",
        "key": "your-api-key",
        "header": "X-API-Key"
    }
)

# OAuth2
config = Config(
    auth={
        "type": "oauth2",
        "access_token": "your-token"
    }
)
```

### 5.3 Cookie处理

```python
# 方法1: 从浏览器导入
crawler.load_cookies_from_browser("chrome")

# 方法2: 手动设置
crawler.set_cookies([
    {"name": "session", "value": "abc123"},
    {"name": "auth", "value": "token123"}
])

# 方法3: 从文件加载
crawler.load_cookies("cookies.json")
```

---

## 6. 性能优化

### 6.1 并发爬取

```python
from moagent.async_processor import AsyncProcessor

async def crawl_multiple_urls():
    processor = AsyncProcessor(max_concurrent=10)

    urls = [
        "https://example.com/page/1",
        "https://example.com/page/2",
        "https://example.com/page/3",
        # ... 更多URL
    ]

    results = await processor.process(
        urls,
        crawler=crawler
    )

    return results
```

### 6.2 批量处理

```python
from moagent.crawlers import BatchCrawler

batch_crawler = BatchCrawler(
    crawler=crawler,
    batch_size=20,       # 每批20个
    delay_between_batches=5  # 批次间延迟5秒
)

results = batch_crawler.crawl_batch(url_list)
```

### 6.3 缓存策略

```python
from moagent.cache import CacheManager

cache = CacheManager(
    backend="redis",  # 或 "memory"
    ttl=3600,         # 缓存1小时
    max_size=10000    # 最多缓存1万条
)

crawler.enable_cache(cache)

# 再次爬取相同URL会直接从缓存读取
articles1 = crawler.crawl(url)  # 实际爬取
articles2 = crawler.crawl(url)  # 从缓存读取
```

---

## 7. 实战案例

### 7.1 案例1: 新闻网站爬取

```python
from moagent import Config, run_agent
from moagent.crawlers import get_crawler

# 目标: 爬取新闻网站的所有文章

# 1. 配置
config = Config(
    target_url="https://news.example.com",
    crawl_mode="auto",
    parser_mode="hybrid",
    max_concurrent=5,
    follow_links=True,      # 跟踪链接
    max_depth=2            # 最多深入2层
)

# 2. 获取爬虫
crawler = get_crawler(
    url="https://news.example.com",
    config=config
)

# 3. 爬取列表页
list_articles = crawler.crawl()

# 4. 爬取详情页
from moagent.crawlers.content import HybridFullTextCrawler
content_crawler = HybridFullTextCrawler(config)

for article in list_articles:
    detail = content_crawler.crawl(article['url'])
    article['content'] = detail['content']
    article['author'] = detail['author']

# 5. 保存
from moagent.storage import get_storage
storage = get_storage("sqlite:///./data/news.db")
storage.store(list_articles)

print(f"成功爬取 {len(list_articles)} 篇文章")
```

### 7.2 案例2: 博客RSS订阅

```python
import feedparser
from moagent.crawlers.content import PatternFullTextCrawler

# 1. 解析RSS
feed = feedparser.parse("https://blog.example.com/rss.xml")

# 2. 配置内容爬虫
config = Config(
    content_selectors={
        "title": "h1.post-title",
        "content": "div.post-content",
        "author": "span.author",
        "date": "time.published"
    }
)

crawler = PatternFullTextCrawler(config)

# 3. 爬取每篇文章
articles = []
for entry in feed.entries:
    detail = crawler.crawl(entry.link)

    articles.append({
        "title": entry.title,
        "url": entry.link,
        "published": entry.published,
        "content": detail['content'],
        "author": detail['author']
    })

# 4. 存储
storage.store(articles)
```

### 7.3 案例3: 电商产品信息

```python
from moagent.crawlers.list import DynamicListCrawler
from moagent.crawlers.content import LLMFullTextCrawler

# 1. 爬取产品列表
list_crawler = DynamicListCrawler(
    config=Config(
        target_url="https://shop.example.com/products",
        crawler_patterns={
            "list_item": "div.product-card",
            "fields": {
                "title": "h3.product-title",
                "price": "span.price",
                "url": "a.product-link"
            }
        }
    )
)

products = list_crawler.crawl()

# 2. 爬取产品详情
content_crawler = LLMFullTextCrawler(
    config=Config(
        llm_model="gpt-4o",
        extraction_fields=[
            "title", "price", "description",
            "images", "specifications", "reviews"
        ]
    )
)

for product in products:
    detail = content_crawler.crawl(product['url'])
    product.update(detail)

# 3. 保存到数据库
storage.store(products)
```

---

## 8. 调试与监控

### 8.1 日志配置

```python
import logging

# 详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log'),
        logging.StreamHandler()
    ]
)

# 爬虫会输出详细日志:
# - 请求URL
# - 响应状态
# - 提取的数据
# - 错误信息
```

### 8.2 性能监控

```python
from moagent.monitor import CrawlerMonitor

monitor = CrawlerMonitor()

crawler.enable_monitoring(monitor)

# 爬取后查看统计
stats = monitor.get_stats()

print(f"总请求数: {stats['total_requests']}")
print(f"成功率: {stats['success_rate']:.2%}")
print(f"平均响应时间: {stats['avg_response_time']:.2f}s")
print(f"总数据量: {stats['total_data_mb']:.2f}MB")
```

### 8.3 错误处理

```python
from moagent.crawlers import RetryStrategy

# 自定义重试策略
retry_strategy = RetryStrategy(
    max_retries=3,
    backoff_factor=2,  # 指数退避
    retry_on=[
        ConnectionError,
        TimeoutError,
        HTTPError  # 特定状态码
    ]
)

crawler.set_retry_strategy(retry_strategy)
```

---

## 9. 最佳实践

### 9.1 选择合适的爬虫

```
决策树:

页面是否需要JavaScript?
├─ 否 → HTMLListCrawler
└─ 是 →
    ├─ 有RSS? → RSSListCrawler
    └─ 无 → DynamicListCrawler

页面结构是否复杂?
├─ 简单 → PatternFullTextCrawler
└─ 复杂 → LLMFullTextCrawler

是否需要平衡性能和准确性?
└─ 是 → HybridCrawler
```

### 9.2 遵守robots.txt

```python
from moagent.robots import RobotsTxtChecker

robots = RobotsTxtChecker("https://example.com")

if robots.allowed("/news"):
    crawler.crawl("https://example.com/news")
else:
    print("被robots.txt禁止")
```

### 9.3 设置合理的延迟

```python
# 避免对服务器造成压力
config = Config(
    min_delay=1,        # 每次请求最少延迟1秒
    random_delay=2,     # 随机延迟0-2秒
    respect_retry_after=True  # 遵守Retry-After头
)
```

### 9.4 监控资源使用

```python
import psutil

def check_resources():
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent

    if cpu > 90:
        print("CPU使用率过高，降低并发")
        config.max_concurrent = 2

    if memory > 90:
        print("内存不足，减少缓存")
        cache.clear()

# 定期检查
crawler.add_callback(check_resources, interval=60)
```

---

## 10. 故障排查

### 10.1 常见问题

**问题1: 爬取不到数据**
```python
# 检查1: 查看实际HTML
html = crawler.fetch(url)
print(html)  # 检查是否包含目标数据

# 检查2: 选择器是否正确
soup = BeautifulSoup(html, 'html.parser')
elements = soup.select('your-selector')
print(f"找到 {len(elements)} 个元素")

# 检查3: 尝试其他爬虫
crawler = DynamicListCrawler(config)  # 或 LLMListCrawler
```

**问题2: 爬虫速度慢**
```python
# 解决1: 启用并发
config.max_concurrent = 10

# 解决2: 启用缓存
crawler.enable_cache()

# 解决3: 减少LLM调用
config.parser_mode = "generic"  # 而非 "llm"
```

**问题3: 被反爬虫拦截**
```python
# 解决1: 设置请求头
config.headers = {
    "User-Agent": "真实浏览器UA",
    "Referer": "网站首页"
}

# 解决2: 使用代理
config.proxy = "http://proxy.example.com:8080"

# 解决3: 降低频率
config.min_delay = 3
```

---

**文档版本**: v1.0
**最后更新**: 2025-01-04
**反馈**: [GitHub Issues](https://github.com/your-org/moagent/issues)
