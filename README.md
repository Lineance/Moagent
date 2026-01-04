# MoAgent

<div align="center">

**LangGraph-based Intelligent News Crawler System**

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A modular, extensible intelligent web content extraction system combining traditional crawling techniques with modern LLM capabilities.

</div>

⚠️ WARNING: This project is in active development and is not suitable for production use. Bugs and breaking changes should be expected.

## Features

- **Intelligent Crawling**: Combines rule-based and LLM-powered extraction strategies
- **Multi-Modal Support**: Static HTML, dynamic JavaScript-rendered pages, and RSS feeds
- **Flexible Architecture**: Plugin-based crawler and parser system
- **Multiple agent**: Base multi-agents framework for collaborative work
- **LangGraph Integration**: Workflow orchestration with state management
- **Multiple LLM Providers**: Support for OpenAI, Anthropic, and custom endpoints
- **RAG-Powered**: Pattern learning and retrieval for enhanced extraction accuracy
- **Async Processing**: High-throughput concurrent operations with backpressure control

## Architecture

MoAgent follows a modular, layered architecture:

```
moagent/
├── agents/                  # Agent-based orchestration
│   ├── coordinator.py      # LangGraph workflow coordinator
│   ├── multi_agent/        # Multi-agent collaboration system
│   └── pattern_generator/ # Automatic pattern generation
├── crawlers/               # Web crawling engine
│   ├── base/              # Base crawler interfaces
│   ├── content/           # Content extraction (HTML, LLM, Hybrid)
│   └── list/              # List page crawlers (HTML, RSS, Dynamic, LLM)
├── llm/                   # LLM client integration
├── parsers/               # Content parsing (Generic, LLM, Hybrid)
├── storage/               # Data persistence (SQLite, PostgreSQL)
├── rag/                   # RAG system for pattern learning
├── config/                # Configuration management
└── utils/                 # Utility functions
```

### Core Components

#### 1. Agent System

**Coordinator Agent** (`agents/coordinator.py`)

- LangGraph-based workflow orchestration
- State management with TypedDict
- Conditional routing and error recovery
- Multi-agent coordination

**Multi-Agent System** (`agents/multi_agent/`)

- Base agent framework for collaborative work
- Specialized agents: Analyst, Explorer, Optimizer, Validator, Supervisor
- Message passing and task distribution

**Pattern Generator** (`agents/pattern_generator/`)

- Rule-based pattern generation from HTML structure
- LLM-powered semantic pattern understanding
- Pattern comparison and refinement
- Confidence scoring and validation

#### 2. Crawler Architecture

**List Crawlers** (`crawlers/list/`)

- `HTMLListCrawler`: Static HTML list page extraction
- `RSSListCrawler`: RSS/Atom feed processing
- `DynamicListCrawler`: JavaScript-rendered pages (Playwright)
- `LLMListCrawler`: LLM-powered intelligent list extraction
- `HybridListCrawler`: Combined approach with intelligent fallback

**Content Crawlers** (`crawlers/content/`)

- `PatternFullTextCrawler`: CSS/XPath/regex-based extraction
- `LLMFullTextCrawler`: LLM-powered content extraction
- `HybridFullTextCrawler`: Pattern + LLM with fallback

**Base Layer** (`crawlers/base/`)

- `BaseCrawler`: Core HTTP fetching with retry logic
- `BaseExtractor`: Content extraction interface
- Factory pattern for crawler selection

#### 3. Parser System

Three parsing strategies:

1. **Generic Parser**: Rule-based extraction using XPath/CSS selectors
2. **LLM Parser**: Pure LLM-powered content extraction
3. **Hybrid Parser**: Generic first, LLM fallback for complex cases

Factory function `get_parser()` selects parser based on configuration.

#### 4. LLM Integration

**Unified Client** (`llm/client.py`)

- Provider-agnostic interface (OpenAI, Anthropic, custom)
- Automatic API key detection
- Custom base URL support
- Response metadata tracking
- Error handling and fallbacks

#### 5. Storage System

- **SQLite**: Default lightweight storage
- **PostgreSQL**: Enterprise-grade storage available
- Batch operations optimization
- Factory pattern for backend selection

#### 6. RAG System

- Vector store (ChromaDB) for pattern storage
- Embedding generation for URLs and patterns
- Semantic similarity search
- Continuous learning from crawling results

#### 7. Async Processing

- **AsyncProcessor**: Concurrent operations with semaphore control
- **AsyncBatchProcessor**: Batch processing with backpressure
- Configurable timeouts and error aggregation

## Installation

### Requirements

- Python 3.8+
- pip or poetry

### Setup

```bash
# Clone the repository
git clone https://github.com/Lineance/Moagent.git
cd moagent

# Install dependencies
pip install -r requirements.txt

# Install web app dependencies (optional)
pip install -r web_app/requirements.txt
```

### Configuration

1. Copy the default configuration:

```bash
cp configs/default.yaml configs/user_config.yaml
```

1. Edit `configs/user_config.yaml` or use environment variables:

```bash
# Set LLM API keys
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Or create configs/.env file
echo "OPENAI_API_KEY=your-key" > configs/.env
```

1. Configure your target and crawling mode in `configs/user_config.yaml`:

```yaml
target_url: "https://example.com/news"
crawl_mode: "auto"  # static, dynamic, auto
parser_mode: "hybrid"  # generic, llm, hybrid
llm_provider: "openai"
llm_model: "gpt-4o-mini"
database_url: "sqlite:///./data/moagent.db"
```

## Usage

### Command Line Interface

```bash
# Run with default configuration
python -m moagent

# Run with custom config
python -m moagent --config configs/user_config.yaml

# Run in specific mode
python -m moagent --mode dynamic --url "https://example.com"

# Enable verbose logging
python -m moagent --verbose

# Show help
python -m moagent --help
```

### Python API

```python
from moagent import Config, run_agent

# Create configuration
config = Config.from_file("configs/user_config.yaml")

# Or create programmatically
config = Config(
    target_url="https://example.com/news",
    crawl_mode="auto",
    llm_provider="openai",
    llm_model="gpt-4o-mini",
    database_url="sqlite:///./data/moagent.db"
)

# Run the agent
result = run_agent(config)
```

### Using Specific Crawlers

```python
from moagent.crawlers import get_crawler
from moagent.parsers import get_parser
from moagent.storage import get_storage

# Get crawler based on configuration
crawler = get_crawler(
    url="https://example.com/news",
    mode="dynamic"
)

# Get parser
parser = get_parser(mode="hybrid")

# Get storage
storage = get_storage("sqlite:///./data/moagent.db")

# Crawl and parse
articles = crawler.crawl()
for article in articles:
    parsed = parser.parse(article)
    storage.store(parsed)
```

### Web Application

```bash
# Start the web server
cd web_app
python app.py

# Access at http://localhost:5000
```

## Configuration

### Crawl Modes

- **`static`**: For static HTML pages (fastest)
- **`dynamic`**: For JavaScript-rendered pages (uses Playwright)
- **`auto`**: Automatically detects page type
- **`rss`**: For RSS/Atom feeds
- **`llm`**: Pure LLM-based extraction

### Parser Modes

- **`generic`**: Rule-based extraction using patterns
- **`llm`**: Pure LLM-powered extraction
- **`hybrid`**: Generic first, falls back to LLM if needed

### Pattern Configuration

Define custom extraction patterns in configuration:

```yaml
crawler_patterns:
  list_container:
    tag: "ul"
    class: "news-list"
  list_item:
    tag: "li"
  title:
    selector: "h2.title"
  link:
    selector: "a.link"
    attribute: "href"
```

Or use predefined patterns:

```yaml
crawler_patterns:
  pattern_name: "seu_news"
```

### LLM Settings

```yaml
llm_provider: "openai"  # openai, anthropic
llm_model: "gpt-4o-mini"
llm_temperature: 0.3
llm_max_tokens: 800
llm_api_base_url: ""  # Custom endpoint
```

### Performance Tuning

```yaml
max_concurrent: 5      # Max concurrent requests
batch_size: 10         # Batch processing size
timeout: 30            # Request timeout (seconds)
max_retries: 3         # Retry attempts
check_interval: 3600   # Update check interval (seconds)
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=moagent --cov-report=html

# Run specific test file
pytest tests/test_crawler.py
```

### Project Structure

```
moagent/
├── agents/          # Agent orchestration and coordination
├── crawlers/        # Web crawling implementations
├── llm/            # LLM integration layer
├── parsers/        # Content parsing logic
├── storage/        # Data persistence layer
├── rag/            # RAG system for pattern learning
├── config/         # Configuration management
└── utils/          # Helper functions
```

### Adding Custom Crawlers

1. Inherit from `BaseCrawler`:

```python
from moagent.crawlers.base import BaseCrawler

class MyCustomCrawler(BaseCrawler):
    def crawl(self):
        # Implement crawling logic
        pass
```

1. Register in factory:

```python
# In moagent/crawlers/__init__.py
def get_crawler(mode: str):
    if mode == "custom":
        return MyCustomCrawler(config)
    # ...
```

### Adding Custom Parsers

1. Inherit from `BaseParser`:

```python
from moagent.parsers.base import BaseParser

class MyCustomParser(BaseParser):
    def parse(self, content):
        # Implement parsing logic
        pass
```

1. Register in factory:

```python
# In moagent/parsers/__init__.py
def get_parser(mode: str):
    if mode == "custom":
        return MyCustomParser(config)
    # ...
```

## Design Patterns

MoAgent employs several design patterns:

- **Factory Pattern**: Object creation for crawlers, parsers, storage
- **Strategy Pattern**: Pluggable crawling and parsing strategies
- **Repository Pattern**: Data access abstraction
- **Template Method**: Base classes define algorithm skeleton
- **Observer Pattern**: Progress tracking and error notification
- **Circuit Breaker**: Fault tolerance and retry logic

## Technologies

- **Python 3.8+**: Core language
- **LangGraph**: Workflow orchestration
- **OpenAI/Anthropic**: LLM providers
- **Playwright**: Dynamic page rendering
- **BeautifulSoup4**: HTML parsing
- **ChromaDB**: Vector store for RAG
- **SQLite/PostgreSQL**: Data persistence
- **Flask**: Web application framework

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- LangGraph team for the excellent workflow orchestration framework
- OpenAI and Anthropic for powerful LLM APIs
- The open-source community for invaluable tools and libraries

## Roadmap

- [ ] Enhanced multi-agent collaboration patterns
- [ ] Support for more content types (videos, podcasts)
- [ ] Distributed crawling with Redis queues
- [ ] Real-time web interface for monitoring
- [ ] Advanced pattern learning with ML
- [ ] Plugin marketplace for community patterns

---
