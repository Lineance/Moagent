#!/usr/bin/env python3
"""
Installation verification script for MoAgent.

Run this script to verify that MoAgent is correctly installed
and all dependencies are available.

Usage:
    python scripts/verify_install.py
"""

import sys
import importlib
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_python_version():
    """Check Python version."""
    print("Checking Python version...")
    version = sys.version_info
    if version >= (3, 8):
        print(f"  ✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  ✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.8+)")
        return False


def check_imports():
    """Check that core dependencies can be imported."""
    print("\nChecking core dependencies...")

    dependencies = {
        "yaml": "PyYAML",
        "click": "Click",
        "bs4": "BeautifulSoup4",
        "requests": "Requests",
        "openai": "OpenAI",
        "anthropic": "Anthropic",
    }

    optional_dependencies = {
        "langgraph": "LangGraph",
        "playwright": "Playwright",
        "sentence_transformers": "Sentence Transformers",
        "chromadb": "ChromaDB",
        "pandas": "Pandas",
    }

    all_ok = True

    print("  Required dependencies:")
    for module, name in dependencies.items():
        try:
            importlib.import_module(module)
            print(f"    ✓ {name}")
        except ImportError:
            print(f"    ✗ {name} (missing)")
            all_ok = False

    print("\n  Optional dependencies:")
    for module, name in optional_dependencies.items():
        try:
            importlib.import_module(module)
            print(f"    ✓ {name}")
        except ImportError:
            print(f"    ○ {name} (not installed)")

    return all_ok


def check_moagent_imports():
    """Check that MoAgent modules can be imported."""
    print("\nChecking MoAgent modules...")

    modules = [
        "moagent",
        "moagent.config",
        "moagent.crawlers",
        "moagent.parsers",
        "moagent.llm",
        "moagent.storage",
    ]

    all_ok = True
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"  ✓ {module}")
        except ImportError as e:
            print(f"  ✗ {module}: {e}")
            all_ok = False

    return all_ok


def check_configuration():
    """Check configuration files."""
    print("\nChecking configuration...")

    config_files = [
        "configs/default.yaml",
        "configs/development.yaml",
    ]

    all_ok = True
    for config_file in config_files:
        path = project_root / config_file
        if path.exists():
            print(f"  ✓ {config_file}")
        else:
            print(f"  ○ {config_file} (not found, will use defaults)")
            all_ok = False

    # Check for .env file
    env_file = project_root / "configs" / ".env"
    if env_file.exists():
        print(f"  ✓ configs/.env (API keys configured)")
    else:
        print(f"  ○ configs/.env (not configured, see QUICKSTART.md)")

    return all_ok


def check_directories():
    """Check required directories."""
    print("\nChecking directories...")

    directories = ["data", "logs", "configs/patterns"]

    all_ok = True
    for directory in directories:
        path = project_root / directory
        if path.exists():
            print(f"  ✓ {directory}/")
        else:
            print(f"  ○ {directory}/ (will be created when needed)")

    return all_ok


def check_cli():
    """Check CLI is available."""
    print("\nChecking CLI...")

    try:
        from moagent.cli import main
        print("  ✓ CLI module available")
        return True
    except ImportError as e:
        print(f"  ✗ CLI module error: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("MoAgent Installation Verification")
    print("=" * 60)

    results = {
        "Python Version": check_python_version(),
        "Core Dependencies": check_imports(),
        "MoAgent Modules": check_moagent_imports(),
        "Configuration": check_configuration(),
        "Directories": check_directories(),
        "CLI": check_cli(),
    }

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_ok = True
    for check, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {check}")
        if not result:
            all_ok = False

    print("=" * 60)

    if all_ok:
        print("\n✓ All checks passed! MoAgent is ready to use.")
        print("\nNext steps:")
        print("  1. Configure API keys in configs/.env")
        print("  2. Run: python -m moagent --help")
        return 0
    else:
        print("\n✗ Some checks failed. Please install missing dependencies:")
        print("  pip install -e '.[all]'")
        return 1


if __name__ == "__main__":
    sys.exit(main())
