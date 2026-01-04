"""
Command-line interface for MoAgent.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import click
import yaml

from .agents.pattern_generator.basic_list_pattern_generator import PatternGeneratorAgent
from .agents.pattern_generator.llm_pattern_comparator import LLMPatternComparatorAgent
from .agents.pattern_generator.llm_pattern_generator import (
    LLMPatternAnalysis,
    LLMPatternGeneratorAgent,
)
from .agents.pattern_generator.llm_pattern_refiner import (
    LLMPatternRefinerAgent,
    RefinementResult,
)
from .config.settings import Config
from .llm.client import get_llm_client
from .main import run_agent

logger = logging.getLogger(__name__)


def _setup_logging(config: Optional[Config] = None, verbose: bool = False) -> None:
    """
    Setup logging configuration based on config or CLI options.

    Args:
        config: Optional Config object with log_level setting
        verbose: If True, override log level to DEBUG
    """
    # Determine log level
    if verbose:
        log_level = logging.DEBUG
    elif config and config.log_level:
        log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    else:
        log_level = logging.INFO

    # Determine log file
    log_file = "logs/moagent.log"
    if config and config.log_file:
        log_file = config.log_file

    # Ensure log directory exists
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file),
        ],
    )


def _create_llm_pattern_generator(
    config: Optional[Config] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLMPatternGeneratorAgent:
    """
    Create LLM pattern generator with unified client configuration.

    This function provides a single point for creating LLM pattern generators
    with automatic API key detection and configuration merging.
    """
    return LLMPatternGeneratorAgent(
        config=config,
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
    )


@click.group()
@click.version_option(version="0.1.0", prog_name="moagent")
def main():
    """MoAgent - LangGraph-based intelligent news crawler.

    Crawl Modes:
      list       Fast link extraction only (best for queue building)
      dynamic    JavaScript support for dynamic list pages
      auto       Smart fallback (list → dynamic)
      article    Full article content extraction
      full       Complete pipeline: list crawling + article fetching (testing)

    Commands:
      crawl              Crawl news from target URL
      init               Initialize configuration and directories
      info               Display current configuration

    HTML Downloading (for pattern analysis):
      download           Download single HTML file
      download-batch     Download multiple HTML files
      preview            Preview HTML without downloading

    Pattern Generation:
      generate-pattern   Auto-generate pattern from HTML (rule-based)
      llm-generate       LLM-powered pattern generation from HTML
      llm-refine         Refine pattern using LLM with feedback
      llm-compare        Compare two HTML files with LLM

    Validation:
      validate-pattern   Validate pattern against HTML content
      compare-html       Compare two HTML files (rule-based)
    """
    pass


@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
)
@click.option(
    "--target",
    "-t",
    type=str,
    help="Target URL to crawl",
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["list", "static", "dynamic", "auto", "article", "full"]),
    default="auto",
    help="Crawling mode (full = list + article for testing)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def crawl(config: Optional[str], target: Optional[str], mode: str, verbose: bool):
    """Crawl news from target URL."""
    # Load configuration
    cfg = Config.from_file(config) if config else Config()

    # Setup logging before any other operations
    _setup_logging(cfg, verbose)

    # Override with CLI options
    if target:
        cfg.target_url = target
    cfg.crawl_mode = mode

    logger.info(f"Starting crawl in {mode} mode")
    if cfg.target_url:
        logger.info(f"Target: {cfg.target_url}")

    try:
        run_agent(cfg)
        logger.info("Crawl completed successfully")
    except Exception as e:
        logger.error(f"Crawl failed: {e}")
        raise click.ClickException(str(e))


@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
)
def init(config: Optional[str]):
    """Initialize MoAgent configuration and directories."""
    cfg = Config()

    # Create directories
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    Path("configs").mkdir(exist_ok=True)

    # Save default config
    config_path = Path(config) if config else Path("configs/default.yaml")
    cfg.save_to_file(config_path)

    click.echo(f"Configuration initialized at: {config_path}")
    click.echo("Directories created: data/, logs/, configs/")


@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
)
def info(config: Optional[str]):
    """Display current configuration."""
    cfg = Config.from_file(config) if config else Config()

    click.echo("MoAgent Configuration:")
    click.echo(f"  Target URL: {cfg.target_url}")
    click.echo(f"  Crawl Mode: {cfg.crawl_mode}")
    click.echo(f"  LLM Provider: {cfg.llm_provider}")
    click.echo(f"  Database: {cfg.database_url}")
    click.echo(f"  Check Interval: {cfg.check_interval}s")


@main.command()
@click.option(
    "--html",
    "-h",
    required=True,
    type=click.Path(exists=True),
    help="Path to HTML file to analyze",
)
@click.option(
    "--name",
    "-n",
    required=True,
    type=str,
    help="Name for the generated pattern",
)
@click.option(
    "--description",
    "-d",
    type=str,
    help="Description for the pattern",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file for generated config (default: configs/patterns/{name}.yaml)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed analysis results",
)
def generate_pattern(html: str, name: str, description: Optional[str], output: Optional[str], verbose: bool):
    """Generate a crawler pattern from an HTML file."""
    click.echo(f"🔍 Analyzing HTML file: {html}")
    click.echo(f"📝 Pattern name: {name}")

    try:
        # Initialize pattern generator
        generator = PatternGeneratorAgent()

        # Analyze HTML
        analysis = generator.analyze_html_file(html)

        # Show verbose results
        if verbose:
            click.echo("\n📊 Analysis Results:")
            click.echo(f"  Confidence: {analysis.confidence:.2f}")
            click.echo(f"  List Container: {analysis.list_container}")
            click.echo(f"  Item Selector: {analysis.item_selector}")
            click.echo(f"  Title Selector: {analysis.title_selector}")
            click.echo(f"  URL Selector: {analysis.url_selector}")
            if analysis.date_selector:
                click.echo(f"  Date Selector: {analysis.date_selector}")
            if analysis.content_selector:
                click.echo(f"  Content Selector: {analysis.content_selector}")
            if analysis.post_process:
                click.echo(f"  Post Process: {analysis.post_process}")

            click.echo(f"\n📋 Sample Items ({len(analysis.sample_items)}):")
            for i, item in enumerate(analysis.sample_items[:3], 1):
                click.echo(f"  {i}. {item.get_text(strip=True)[:80]}...")

            if analysis.issues:
                click.echo(f"\n⚠️  Issues:")
                for issue in analysis.issues:
                    click.echo(f"  - {issue}")

        # Generate config
        config = generator.generate_config_yaml(analysis, name, description)

        # Determine output path
        if not output:
            output_dir = Path("configs/patterns")
            output_dir.mkdir(exist_ok=True)
            output = output_dir / f"{name}.yaml"

        # Save config
        with open(output, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        click.echo(f"\n✅ Pattern generated successfully!")
        click.echo(f"📁 Config saved to: {output}")

        if analysis.confidence >= 0.7:
            click.echo("🎯 High confidence pattern - ready to use!")
        elif analysis.confidence >= 0.5:
            click.echo("⚠️  Medium confidence - review and adjust if needed")
        else:
            click.echo("❌ Low confidence - manual editing required")

        # Show usage instructions
        click.echo(f"\n🚀 Usage:")
        click.echo(f"   python -m moagent crawl --config {output}")

        # Also show Python code option
        if verbose:
            click.echo(f"\n🐍 Python Code:")
            code = generator.generate_pattern_code(analysis, name, description)
            click.echo(code)

    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.ClickException(str(e))


@main.command()
@click.option(
    "--html",
    "-h",
    required=True,
    type=click.Path(exists=True),
    help="Path to HTML file to analyze",
)
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Path to existing config to test",
)
def validate_pattern(html: str, config: str):
    """Validate a pattern against HTML content."""
    click.echo(f"🔍 Validating pattern from: {config}")
    click.echo(f"📄 Against HTML: {html}")

    try:
        # Load config
        with open(config, 'r') as f:
            config_data = yaml.safe_load(f)

        # Load HTML
        with open(html, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()

        # Initialize generator
        generator = PatternGeneratorAgent()

        # Validate
        pattern = config_data.get("crawler_patterns", {})
        if "pattern_name" in pattern:
            from .crawlers.list.patterns import get_pattern, pattern_to_config
            pattern_obj = get_pattern(pattern["pattern_name"])
            pattern = pattern_to_config(pattern_obj)

        result = generator.validate_pattern(pattern, html_content)

        if result["success"]:
            click.echo(f"✅ Pattern valid! Found {result['items_found']} items")
            if result["sample_items"]:
                click.echo("\nSample items:")
                for i, item in enumerate(result["sample_items"], 1):
                    click.echo(f"  {i}. {item['title']}")
                    click.echo(f"     URL: {item['url']}")
        else:
            click.echo(f"❌ Pattern validation failed:")
            for issue in result["issues"]:
                click.echo(f"  - {issue}")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.ClickException(str(e))


@main.command()
@click.option(
    "--html",
    "-h",
    required=True,
    type=click.Path(exists=True),
    help="Path to HTML file to analyze",
)
@click.option(
    "--compare",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Path to second HTML file to compare",
)
def compare_html(html: str, compare: str):
    """Compare two HTML files to find common patterns."""
    click.echo(f"🔍 Comparing HTML files:")
    click.echo(f"  File 1: {html}")
    click.echo(f"  File 2: {compare}")

    try:
        generator = PatternGeneratorAgent()

        # Analyze both files
        analysis1 = generator.analyze_html_file(html)
        analysis2 = generator.analyze_html_file(compare)

        # Convert to config format for comparison
        config1 = generator.generate_config_yaml(analysis1, "file1")
        config2 = generator.generate_config_yaml(analysis2, "file2")

        # Compare patterns
        pattern1 = config1["crawler_patterns"]
        pattern2 = config2["crawler_patterns"]

        differences = generator.compare_patterns(pattern1, pattern2)

        click.echo(f"\n📊 Comparison Results:")
        click.echo(f"  File 1 confidence: {analysis1.confidence:.2f}")
        click.echo(f"  File 2 confidence: {analysis2.confidence:.2f}")

        if not differences:
            click.echo("✅ Patterns are identical!")
        else:
            click.echo("⚠️  Found differences:")
            for key, diff in differences.items():
                click.echo(f"  {key}:")
                click.echo(f"    File 1: {diff['pattern1']}")
                click.echo(f"    File 2: {diff['pattern2']}")

        # Suggest unified pattern
        if analysis1.confidence > analysis2.confidence:
            best = analysis1
            source = html
        else:
            best = analysis2
            source = compare

        click.echo(f"\n💡 Recommendation:")
        click.echo(f"  Use pattern from: {source}")
        click.echo(f"  Confidence: {best.confidence:.2f}")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.ClickException(str(e))


@main.command()
@click.option(
    "--html",
    "-h",
    required=True,
    type=click.Path(exists=True),
    help="Path to HTML file to analyze",
)
@click.option(
    "--name",
    "-n",
    required=True,
    type=str,
    help="Name for the generated pattern",
)
@click.option(
    "--description",
    "-d",
    type=str,
    help="Description for the pattern",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file for generated config (default: configs/patterns/{name}.yaml)",
)
@click.option(
    "--main-config",
    type=click.Path(exists=True),
    help="Path to main config file (for auto-detecting provider/model/API keys)",
)
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["openai", "anthropic"]),
    default=None,
    help="LLM provider to use (auto-detected from config if not specified)",
)
@click.option(
    "--model",
    "-m",
    type=str,
    default=None,
    help="LLM model name (auto-detected from config if not specified)",
)
@click.option(
    "--api-base-url",
    type=str,
    help="Custom base URL for API (e.g., https://api.xiaomimimo.com/v1)",
)
@click.option(
    "--api-key",
    type=str,
    help="API key (auto-detected from config or env vars if not specified)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed analysis and reasoning",
)
def llm_generate(html: str, name: str, description: Optional[str], output: Optional[str],
                 main_config: Optional[str], provider: Optional[str], model: Optional[str],
                 api_base_url: Optional[str], api_key: Optional[str], verbose: bool):
    """LLM-powered pattern generation from HTML file.

    API Key Detection Priority:
    1. --api-key CLI option
    2. Config file (openai_api_key or anthropic_api_key)
    3. Environment variables (OPENAI_API_KEY or ANTHROPIC_API_KEY)
    """
    # Load main config file if provided
    cfg = None
    if main_config:
        cfg = Config.from_file(main_config)
        click.echo(f"📄 Loaded main config from: {main_config}")

    try:
        # Create LLM pattern generator with unified client
        generator = _create_llm_pattern_generator(
            config=cfg,
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=api_base_url,
        )

        # Show configuration info
        click.echo(f"🤖 LLM Pattern Generation")
        click.echo(f"📄 HTML file: {html}")
        click.echo(f"📝 Pattern name: {name}")
        click.echo(f"🔧 Provider: {generator.llm._provider} (Model: {generator.llm._model or 'default'})")
        
        # Show API configuration (from CLI or config file)
        effective_base_url = api_base_url or (cfg.llm_api_base_url if cfg else None)
        if effective_base_url:
            click.echo(f"🔧 Using custom API: {effective_base_url}")
        
        if cfg and verbose:
            click.echo(f"🔧 LLM Temperature: {cfg.llm_temperature}")
            click.echo(f"🔧 LLM Max Tokens: {cfg.llm_max_tokens}")

        # Analyze HTML with LLM
        click.echo(f"\n🔍 Analyzing with {generator.llm._provider}...")
        analysis = generator.analyze_html_file(html)

        # Show results
        click.echo(f"\n✅ Analysis complete!")
        click.echo(f"🎯 Confidence: {analysis.confidence:.2f}")

        if verbose:
            click.echo(f"\n📊 Generated Pattern:")
            click.echo(f"   List Container: {analysis.list_container}")
            click.echo(f"   Item Selector: {analysis.item_selector}")
            click.echo(f"   Title Selector: {analysis.title_selector}")
            click.echo(f"   URL Selector: {analysis.url_selector}")
            if analysis.date_selector:
                click.echo(f"   Date Selector: {analysis.date_selector}")
            if analysis.content_selector:
                click.echo(f"   Content Selector: {analysis.content_selector}")
            if analysis.post_process:
                click.echo(f"   Post Process: {analysis.post_process}")

            click.echo(f"\n💡 LLM Reasoning:")
            click.echo(f"   {analysis.reasoning}")

        # Generate config
        config = generator.generate_config_yaml(analysis, name, "" , description)

        # Determine output path
        if not output:
            output_dir = Path("configs/patterns")
            output_dir.mkdir(exist_ok=True)
            output = output_dir / f"{name}_llm.yaml"

        # Save config
        with open(output, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        click.echo(f"\n📁 Config saved to: {output}")

        if analysis.confidence >= 0.8:
            click.echo("🎯 High confidence - ready to use!")
        elif analysis.confidence >= 0.6:
            click.echo("⚠️  Medium confidence - review recommended")
        else:
            click.echo("❌ Low confidence - manual editing needed")

        click.echo(f"\n🚀 Usage:")
        click.echo(f"   python -m moagent crawl --config {output}")
        click.echo(f"   python -m moagent validate-pattern --html {html} --config {output}")

        # Show Python code
        if verbose:
            click.echo(f"\n🐍 Python Code:")
            code = generator.generate_pattern_code(analysis, name, description)
            click.echo(code)

        # Show explanation
        if verbose:
            click.echo(f"\n📝 Full Analysis:")
            click.echo(generator.explain_analysis(analysis))

    except Exception as e:
        click.echo(f"❌ Error: {e}")
        if "No module named" in str(e):
            click.echo("💡 Install required packages:")
            if provider == "openai":
                click.echo("   pip install openai")
            else:
                click.echo("   pip install anthropic")
        raise click.ClickException(str(e))


@main.command()
@click.option(
    "--html",
    "-h",
    required=True,
    type=click.Path(exists=True),
    help="Path to HTML file to analyze",
)
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Path to existing LLM-generated config",
)
@click.option(
    "--feedback",
    "-f",
    required=True,
    type=str,
    help="Feedback on what needs to be fixed",
)
@click.option(
    "--main-config",
    type=click.Path(exists=True),
    help="Path to main config file (for auto-detecting provider/model/API keys)",
)
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["openai", "anthropic"]),
    default=None,
    help="LLM provider to use (auto-detected from config if not specified)",
)
@click.option(
    "--model",
    "-m",
    type=str,
    default=None,
    help="LLM model name (auto-detected from config if not specified)",
)
@click.option(
    "--api-base-url",
    type=str,
    help="Custom base URL for API (e.g., https://api.xiaomimimo.com/v1)",
)
@click.option(
    "--api-key",
    type=str,
    help="API key (auto-detected from config or env vars if not specified)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file for refined config",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed refinement reasoning and changes",
)
@click.option(
    "--test",
    "-t",
    is_flag=True,
    help="Test pattern extraction after refinement",
)
@click.option(
    "--iterations",
    "-i",
    type=int,
    default=1,
    help="Number of refinement iterations (for iterative refinement)",
)
@click.option(
    "--test-base-url",
    type=str,
    default="",
    help="Base URL for testing pattern extraction (defaults to target_url from config)",
)
def llm_refine(html: str, config: str, feedback: str, main_config: Optional[str],
               provider: Optional[str], model: Optional[str], api_base_url: Optional[str],
               api_key: Optional[str], output: Optional[str], verbose: bool,
               test: bool, iterations: int, test_base_url: str):
    """Refine a pattern using LLM with user feedback.

    API Key Detection Priority:
    1. --api-key CLI option
    2. Main config file (openai_api_key or anthropic_api_key)
    3. Environment variables (OPENAI_API_KEY or ANTHROPIC_API_KEY)
    """
    # Load main config file if provided
    cfg = None
    if main_config:
        cfg = Config.from_file(main_config)
        click.echo(f"📄 Loaded main config from: {main_config}")

    try:
        # Create LLM refinement agent with unified client
        refinement_agent = LLMPatternRefinerAgent(
            config=cfg,
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=api_base_url,
        )

        click.echo(f"🔄 LLM Pattern Refinement")
        click.echo(f"📄 HTML file: {html}")
        click.echo(f"🔧 Current config: {config}")
        click.echo(f"💬 Feedback: {feedback}")
        click.echo(f"🔧 Provider: {refinement_agent.llm._provider} (Model: {refinement_agent.llm._model or 'default'})")
        
        # Show API configuration
        effective_base_url = api_base_url or (cfg.llm_api_base_url if cfg else None)
        if effective_base_url:
            click.echo(f"🔧 Using custom API: {effective_base_url}")
        
        if cfg and verbose:
            click.echo(f"🔧 LLM Temperature: {cfg.llm_temperature}")
            click.echo(f"🔧 LLM Max Tokens: {cfg.llm_max_tokens}")

        # Load current config
        with open(config, 'r') as f:
            config_data = yaml.safe_load(f)

        # Load HTML
        with open(html, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()

        # Create current analysis from config
        current_analysis = LLMPatternAnalysis(
            list_container=config_data.get("crawler_patterns", {}).get("list_container", {}),
            item_selector=config_data.get("crawler_patterns", {}).get("item_selector", {}),
            title_selector=config_data.get("crawler_patterns", {}).get("title_selector", {}),
            url_selector=config_data.get("crawler_patterns", {}).get("url_selector", {}),
            date_selector=config_data.get("crawler_patterns", {}).get("date_selector"),
            content_selector=config_data.get("crawler_patterns", {}).get("content_selector"),
            post_process=config_data.get("crawler_patterns", {}).get("post_process", {}),
            confidence=config_data.get("crawler_patterns", {}).get("_llm_metadata", {}).get("confidence", 0.5),
            reasoning=config_data.get("crawler_patterns", {}).get("_llm_metadata", {}).get("reasoning", ""),
            sample_html="",
            llm_response=config_data.get("crawler_patterns", {}),
        )

        # Get base URL from config if not provided
        if not test_base_url:
            test_base_url = config_data.get("target_url", "")

        # Refine with LLM
        click.echo(f"\n🔄 Refining with {provider}...")
        
        if iterations > 1:
            # Iterative refinement
            click.echo(f"📊 Using iterative refinement ({iterations} iterations)")
            feedback_list = [feedback] * iterations
            refined_analysis = refinement_agent.refine_iterative(
                current_analysis,
                feedback_list,
                html_content,
                max_iterations=iterations,
            )
        else:
            # Single refinement with comparison
            refinement_result = refinement_agent.refine_with_comparison(
                current_analysis, feedback, html_content
            )
            refined_analysis = refinement_result.refined

            # Display refinement report
            click.echo("\n" + "=" * 60)
            click.echo("Refinement Report")
            click.echo("=" * 60)
            click.echo(f"Confidence: {refinement_result.original.confidence:.2f} → {refinement_result.refined.confidence:.2f}")
            click.echo(f"Improvement Score: {refinement_result.improvement_score:.2f}")
            
            if refinement_result.validation_passed:
                click.echo("✅ Validation: PASSED")
            else:
                click.echo("❌ Validation: FAILED")
                if refinement_result.validation_errors:
                    for error in refinement_result.validation_errors:
                        click.echo(f"   - {error}")
            
            if refinement_result.changes:
                click.echo("\nChanges Made:")
                for field, change_data in refinement_result.changes.items():
                    if field != "confidence":
                        click.echo(f"  • {field}: Updated")
                        if verbose:
                            click.echo(f"    Original: {change_data.get('original')}")
                            click.echo(f"    Refined:  {change_data.get('refined')}")

        # Test extraction if requested
        if test:
            click.echo("\n🧪 Testing pattern extraction...")
            items, stats = refinement_agent.test_pattern_extraction(
                refined_analysis, html_content, test_base_url
            )
            click.echo(f"  Items found: {stats.get('items_found', 0)}")
            click.echo(f"  Items with title: {stats.get('items_with_title', 0)}")
            click.echo(f"  Items with URL: {stats.get('items_with_url', 0)}")
            click.echo(f"  Items filtered: {stats.get('items_filtered', 0)}")
            if items:
                click.echo(f"\n  Sample items:")
                for i, item in enumerate(items[:3], 1):
                    click.echo(f"    {i}. {item.get('title', 'No title')[:50]}")
                    click.echo(f"       {item.get('url', 'No URL')[:80]}")

        # Generate refined config
        metadata = config_data.get("crawler_patterns", {}).get("_llm_metadata", {})
        name = metadata.get("name", "refined")
        description = metadata.get("description", "")
        refined_desc = f"{description} (Refined)" if description else "Refined pattern"

        generator = LLMPatternGeneratorAgent(
            config=cfg,
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )
        refined_config = generator.generate_config_yaml(
            refined_analysis,
            name,
            refined_desc
        )

        # Save
        if not output:
            output = config.replace(".yaml", "_refined.yaml")

        with open(output, 'w', encoding='utf-8') as f:
            yaml.dump(refined_config, f, default_flow_style=False, sort_keys=False)

        click.echo(f"\n✅ Refined pattern saved to: {output}")
        click.echo(f"🎯 Confidence: {refined_analysis.confidence:.2f} (was {current_analysis.confidence:.2f})")

        if verbose:
            click.echo(f"\n📝 Refinement Reasoning:")
            click.echo(f"   {refined_analysis.reasoning}")
            
            # Show LLM metadata if available
            if refined_analysis.llm_metadata:
                meta = refined_analysis.llm_metadata
                click.echo(f"\n📊 LLM Metadata:")
                click.echo(f"   Response time: {meta.get('response_time', 0):.2f}s")
                click.echo(f"   Tokens: {meta.get('total_tokens', 0)} (prompt: {meta.get('prompt_tokens', 0)}, completion: {meta.get('completion_tokens', 0)})")
                click.echo(f"   Model: {meta.get('model', 'unknown')}")
                click.echo(f"   Provider: {meta.get('provider', 'unknown')}")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.ClickException(str(e))


@main.command()
@click.option(
    "--html",
    "-h",
    required=True,
    type=click.Path(exists=True),
    help="Path to first HTML file",
)
@click.option(
    "--compare",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Path to second HTML file",
)
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["openai", "anthropic"]),
    default="openai",
    help="LLM provider to use",
)
@click.option(
    "--model",
    "-m",
    type=str,
    default="gpt-4o-mini",
    help="LLM model name",
)
@click.option(
    "--base-url",
    type=str,
    help="Custom base URL for API (e.g., https://api.xiaomimimo.com/v1)",
)
@click.option(
    "--api-key",
    type=str,
    envvar="OPENAI_API_KEY",
    help="API key",
)
@click.option(
    "--main-config",
    type=click.Path(exists=True),
    help="Path to main config file (for auto-detecting provider/model/API keys)",
)
def llm_compare(html: str, compare: str, provider: str, model: str, base_url: Optional[str],
                api_key: Optional[str], main_config: Optional[str]):
    """Compare two HTML files using LLM to find common patterns.

    API Key Detection Priority:
    1. --api-key CLI option
    2. Main config file (openai_api_key or anthropic_api_key)
    3. Environment variables (OPENAI_API_KEY or ANTHROPIC_API_KEY)
    """
    # Load main config file if provided
    cfg = None
    if main_config:
        cfg = Config.from_file(main_config)
        click.echo(f"📄 Loaded main config from: {main_config}")

    try:
        # Create LLM pattern generator with unified client
        generator = _create_llm_pattern_generator(
            config=cfg,
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )

        click.echo(f"🔍 LLM Pattern Comparison")
        click.echo(f"📄 File 1: {html}")
        click.echo(f"📄 File 2: {compare}")
        click.echo(f"🔧 Provider: {generator.llm._provider} (Model: {generator.llm._model or 'default'})")
        if base_url:
            click.echo(f"🔧 Using custom API: {base_url}")

        comparator = LLMPatternComparatorAgent()

        # Analyze both files
        click.echo(f"\n🔍 Analyzing file 1 with {generator.llm._provider}...")
        analysis1 = generator.analyze_html_file(html)

        click.echo(f"🔍 Analyzing file 2 with {generator.llm._provider}...")
        analysis2 = generator.analyze_html_file(compare)

        # Compare
        comparison = comparator.compare_llm_analyses(analysis1, analysis2)

        click.echo(f"\n📊 Comparison Results:")
        click.echo(f"  File 1 confidence: {analysis1.confidence:.2f}")
        click.echo(f"  File 2 confidence: {analysis2.confidence:.2f}")
        click.echo(f"  Confidence difference: {comparison['confidence_diff']:.2f}")

        if comparison["patterns_match"]:
            click.echo("✅ Patterns match! Can use same configuration.")
        else:
            click.echo("⚠️  Patterns differ. Analysis:")
            click.echo(f"  File 1 pattern: {analysis1.list_container} / {analysis1.item_selector}")
            click.echo(f"  File 2 pattern: {analysis2.list_container} / {analysis2.item_selector}")

        # Recommendation
        if analysis1.confidence > analysis2.confidence:
            best = analysis1
            source = html
        else:
            best = analysis2
            source = compare

        click.echo(f"\n💡 Recommendation:")
        click.echo(f"  Use pattern from: {source}")
        click.echo(f"  Confidence: {best.confidence:.2f}")
        click.echo(f"  Reasoning: {best.reasoning}")

        # Generate unified config if patterns match
        if comparison["patterns_match"]:
            config = generator.generate_config_yaml(best, "unified_pattern", "Unified pattern from both files")
            output_path = Path("configs/patterns/unified_llm.yaml")
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            click.echo(f"\n📁 Unified config saved to: {output_path}")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.ClickException(str(e))


@main.command()
@click.option(
    "--url",
    "-u",
    required=True,
    type=str,
    help="URL to download HTML from",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="data/samples",
    help="Output directory for downloaded files",
)
@click.option(
    "--js",
    "-j",
    is_flag=True,
    help="Use Playwright for JavaScript rendering",
)
@click.option(
    "--preview",
    "-p",
    is_flag=True,
    help="Show preview of downloaded content",
)
def download(url: str, output: str, js: bool, preview: bool):
    """Download HTML file for pattern analysis.

    This command fetches HTML content from a URL and saves it locally
    for use with pattern generation commands.
    """
    from .agents.pattern_generator.html_downloader import (
        DownloaderFactory,
        HTMLDownloader,
    )

    click.echo(f"📥 Downloading HTML from: {url}")
    if js:
        click.echo("   Using JavaScript rendering...")

    try:
        downloader = DownloaderFactory.create_user_agent()
        file_path = downloader.download(url, output, use_js=js)

        click.echo(f"✅ Saved to: {file_path}")

        if preview:
            click.echo("\n📄 Preview:")
            preview_content = downloader.preview(url, use_js=js, max_chars=500)
            click.echo(preview_content)

        click.echo(f"\n💡 Next steps:")
        click.echo(f"   Generate pattern: python -m moagent generate-pattern --html {file_path}")
        click.echo(f"   LLM analysis:     python -m moagent llm-generate --html {file_path}")

    except Exception as e:
        click.echo(f"❌ Download failed: {e}")
        raise click.ClickException(str(e))


@main.command()
@click.option(
    "--urls",
    "-u",
    required=True,
    multiple=True,
    type=str,
    help="URLs to download (can specify multiple)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="data/samples",
    help="Output directory",
)
@click.option(
    "--js",
    "-j",
    is_flag=True,
    help="Use JavaScript rendering",
)
@click.option(
    "--skip-existing",
    "-s",
    is_flag=True,
    help="Skip files that already exist",
)
def download_batch(urls: tuple, output: str, js: bool, skip_existing: bool):
    """Download multiple HTML files for pattern analysis.

    Useful for collecting samples from multiple pages to analyze patterns.
    """
    from .agents.pattern_generator.html_downloader import DownloaderFactory

    click.echo(f"📥 Downloading {len(urls)} files...")
    if js:
        click.echo("   Using JavaScript rendering...")
    if skip_existing:
        click.echo("   Skipping existing files...")

    try:
        downloader = DownloaderFactory.create_user_agent()
        results = downloader.download_batch(list(urls), output, use_js=js, skip_existing=skip_existing)

        success = sum(1 for v in results.values() if v is not None)
        click.echo(f"\n✅ Success: {success}/{len(urls)}")

        if success > 0:
            click.echo("\n💡 Next steps:")
            click.echo("   Batch analyze: python -m moagent batch-generate --html data/samples/")
            click.echo("   Or use individual files with generate-pattern/llm-generate")

    except Exception as e:
        click.echo(f"❌ Batch download failed: {e}")
        raise click.ClickException(str(e))


@main.command()
@click.option(
    "--url",
    "-u",
    required=True,
    type=str,
    help="URL to preview",
)
@click.option(
    "--js",
    "-j",
    is_flag=True,
    help="Use JavaScript rendering",
)
@click.option(
    "--chars",
    "-c",
    type=int,
    default=1000,
    help="Number of characters to preview",
)
def preview(url: str, js: bool, chars: int):
    """Preview HTML content without downloading.

    Useful for checking if a page has the expected structure
    before downloading for pattern analysis.
    """
    from .agents.pattern_generator.html_downloader import DownloaderFactory

    click.echo(f"🔍 Previewing: {url}")
    if js:
        click.echo("   Using JavaScript rendering...")

    try:
        downloader = DownloaderFactory.create_user_agent()
        preview_content = downloader.preview(url, use_js=js, max_chars=chars)

        click.echo("\n" + "="*60)
        click.echo(preview_content)
        click.echo("="*60)

    except Exception as e:
        click.echo(f"❌ Preview failed: {e}")
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()
