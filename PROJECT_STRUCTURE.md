# MoAgent Project Structure

This document describes the complete file and directory structure of the MoAgent project.

## Root Level Files

```
Moagent/
├── README.md                  # Main project documentation
├── QUICKSTART.md              # Quick start guide
├── CHANGELOG.md               # Version changelog
├── CONTRIBUTING.md            # Contribution guidelines
├── LICENSE                    # MIT License
├── PROJECT_STRUCTURE.md       # This file
├── .gitignore                 # Git ignore patterns
├── .pre-commit-config.yaml    # Pre-commit hooks configuration
├── MANIFEST.in                # Package manifest
├── Makefile                   # Build automation commands
├── pyproject.toml             # Modern Python project configuration
├── setup.py                   # Legacy setup.py (for compatibility)
├── requirements.txt           # Core dependencies
├── requirements-dev.txt       # Development dependencies
├── requirements-test.txt      # Testing dependencies
├── requirements-web.txt       # Web application dependencies
├── requirements-all.txt       # All dependencies combined
└── tox.ini                    # Tox configuration for testing
```

## Source Code Structure

```
moagent/                      # Main package
├── __init__.py               # Package initialization
├── main.py                   # Main entry point
├── cli.py                    # Command-line interface
├── async_processor.py        # Async processing framework
└── rate_limiter.py           # Rate limiting utilities

moagent/agents/               # Agent system
├── __init__.py
├── coordinator.py           # LangGraph workflow coordinator
├── rag_coordinator.py       # RAG-enabled coordinator
├── multi_agent/             # Multi-agent collaboration
│   ├── __init__.py
│   ├── base.py             # Base agent class
│   ├── communication.py    # Agent communication
│   ├── message.py          # Message types
│   └── workflow/           # Workflow definitions
│       ├── __init__.py
│       ├── graph.py        # LangGraph workflow graph
│       └── adaptive.py     # Adaptive workflow
└── pattern_generator/       # Pattern generation
    ├── __init__.py
    ├── basic_list_pattern_generator.py
    ├── html_downloader.py
    ├── llm_pattern_comparator.py
    ├── llm_pattern_generator.py
    └── llm_pattern_refiner.py

moagent/crawlers/            # Web crawling system
├── __init__.py
├── base/                   # Base crawler classes
│   ├── __init__.py
│   ├── crawler.py         # Base crawler
│   └── extractor.py       # Base extractor
├── list/                   # List page crawlers
│   ├── __init__.py
│   ├── base.py           # Base list crawler
│   ├── html.py           # HTML list crawler
│   ├── rss.py            # RSS/Atom crawler
│   ├── dynamic.py        # Dynamic JS crawler
│   └── llm.py            # LLM-based crawler
└── content/                # Content extractors
    ├── __init__.py
    ├── base.py           # Base content crawler
    ├── html.py           # HTML content extractor
    ├── dynamic.py        # Dynamic content extractor
    ├── llm.py            # LLM content extractor
    ├── patterns.py       # Pattern-based extractor
    └── generic.py        # Generic content extractor

moagent/llm/                # LLM integration
├── __init__.py
├── client.py              # Unified LLM client
├── ops_parsing.py         # LLM output parsing
├── ops_pattern.py         # LLM pattern operations
└── templating.py          # Prompt templates

moagent/parsers/            # Content parsing
├── __init__.py
├── base.py               # Base parser
├── schema.py             # Data schemas
├── rules.py              # Rule-based parser
├── generic.py            # Generic parser
├── llm.py                # LLM parser
└── config_loader.py      # Parser config loading

moagent/storage/            # Data persistence
├── __init__.py
├── base.py               # Base storage interface
└── sqlite.py             # SQLite implementation

moagent/rag/                # RAG system
├── __init__.py
├── embeddings.py          # Embedding generation
├── retriever.py           # Pattern retrieval
├── vector_store.py        # Vector database
└── knowledge_base.py      # Knowledge base management

moagent/config/             # Configuration
├── __init__.py
├── settings.py            # Configuration class
└── constants.py           # Constants

moagent/cache/              # Caching layer
└── __init__.py

moagent/utils/              # Utility functions
└── __init__.py
```

## Configuration Files

```
configs/                     # Configuration directory
├── README.md               # Configuration guide
├── default.yaml            # Default configuration
├── development.yaml        # Development configuration
├── production.yaml         # Production configuration (optional)
├── .env                    # Environment variables (not in git)
├── .env.example            # Environment variables template
└── patterns/               # Crawler patterns
    ├── seu_news.yaml       # Example pattern for SEU news
    ├── example_pattern.yaml
    └── README.md           # Pattern documentation
```

## Data Directory

```
data/                        # Data storage (not in git)
├── .gitkeep                # Keep directory in git
├── moagent.db              # SQLite database (created at runtime)
└── cache/                  # Cached data
    └── .gitkeep
```

## Web Application

```
web_app/                    # Web interface
├── README.md               # Web app documentation
├── app.py                  # Flask application
├── run.sh                  # Startup script
├── requirements.txt        # Web app dependencies
├── test_web_app.py         # Web app tests
├── static/                 # Static files
│   ├── css/               # Stylesheets
│   ├── js/                # JavaScript
│   └── images/            # Images
└── templates/              # HTML templates
    ├── index.html         # Main page
    ├── dashboard.html     # Dashboard
    └── config.html        # Configuration page
```

## Tests

```
tests/                      # Test suite
├── __init__.py
├── conftest.py            # Pytest configuration
├── test_crawler.py        # Crawler tests
├── test_parser.py         # Parser tests
├── test_storage.py        # Storage tests
├── test_llm.py            # LLM client tests
├── test_config.py         # Configuration tests
├── test_rag.py            # RAG system tests
├── check_rag_status.py    # RAG status checker
├── debug_llm_403.py       # LLM debugging
├── debug_rag_init.py      # RAG initialization debug
└── test_yaml_save.py      # YAML saving test
```

## Scripts

```
scripts/                    # Utility scripts
├── verify_install.py      # Installation verification
├── init_db.py             # Database initialization
├── migrate.py             # Data migration
└── benchmark.py           # Performance benchmarking
```

## Documentation (if docs/ exists)

```
docs/                       # Documentation source
├── conf.py                 # Sphinx configuration
├── index.md                # Documentation index
├── installation.md         # Installation guide
├── configuration.md        # Configuration guide
├── api/                    # API documentation
│   ├── crawler.md
│   ├── parser.md
│   └── storage.md
├── guides/                 # User guides
│   ├── getting_started.md
│   ├── advanced_usage.md
│   └── custom_crawlers.md
└── _build/                 # Built documentation (not in git)
    └── html/
```

## Logs Directory

```
logs/                       # Log files (not in git)
├── .gitkeep                # Keep directory in git
├── moagent.log             # Main application log
└── moagent.error.log       # Error log
```

## Build Artifacts (not in git)

```
dist/                       # Distribution packages
build/                      # Build artifacts
*.egg-info/                 # Package metadata
__pycache__/                # Python cache
.pytest_cache/              # Pytest cache
.ruff_cache/                # Ruff cache
.mypy_cache/                # MyPy cache
htmlcov/                    # Coverage reports
.coverage                   # Coverage data
```

## Virtual Environment (not in git)

```
venv/                       # Virtual environment
.env                        # Environment variables
.venv/                      # Alternative virtual environment
```

## Key Files Description

### Configuration Files

- **pyproject.toml**: Modern Python project configuration with build settings, dependencies, and tool configurations (Black, Ruff, MyPy, Pytest)
- **setup.py**: Backward-compatible setup script
- **requirements*.txt**: Pip-style dependency files for different use cases
- **tox.ini**: Multi-environment testing configuration
- **.pre-commit-config.yaml**: Git hooks for code quality

### Documentation Files

- **README.md**: Main project documentation with features, installation, and usage
- **QUICKSTART.md**: Getting started guide for new users
- **CONTRIBUTING.md**: Guidelines for contributors
- **CHANGELOG.md**: Version history and changes
- **PROJECT_STRUCTURE.md**: This file

### Build Files

- **Makefile**: Common development tasks (install, test, lint, format, etc.)
- **MANIFEST.in**: Files to include in distribution packages

### Source Code Organization

The source code follows a clear separation of concerns:

1. **agents/**: Workflow orchestration and multi-agent coordination
2. **crawlers/**: Web crawling implementations (list and content)
3. **llm/**: LLM integration layer
4. **parsers/**: Content parsing logic
5. **storage/**: Data persistence layer
6. **rag/**: Retrieval Augmented Generation system
7. **config/**: Configuration management
8. **utils/**: Shared utility functions

## Adding New Components

When adding new components to MoAgent:

1. **New Crawler**: Add to `moagent/crawlers/list/` or `moagent/crawlers/content/`
2. **New Parser**: Add to `moagent/parsers/`
3. **New Storage Backend**: Add to `moagent/storage/`
4. **New Agent**: Add to `moagent/agents/`
5. **New Utility**: Add to `moagent/utils/`

Each component should have:
- `__init__.py` with exports
- Clear separation of concerns
- Unit tests in `tests/`
- Documentation in docstrings

## Development Workflow

Typical development workflow:

```bash
# Install development dependencies
make dev

# Make changes
vim moagent/crawlers/my_crawler.py

# Format and lint
make format
make lint

# Run tests
make test

# Run with coverage
make test-cov

# Type check
make type-check

# Verify installation
python scripts/verify_install.py
```

## File Naming Conventions

- Python modules: `snake_case.py`
- Test files: `test_*.py` or `*_test.py`
- Configuration: `*.yaml` (not `*.yml`)
- Documentation: `*.md`
- Classes: `PascalCase`
- Functions/Variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
