"""
MoAgent Web Application
Flask web interface for the MoAgent intelligent crawling system
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS

# Load environment variables from configs/.env
env_path = Path(__file__).parent.parent / 'configs' / '.env'
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        logger = logging.getLogger(__name__)
        logger.info(f"Loaded environment variables from {env_path}")
    except ImportError:
        # python-dotenv not available, use simple env loading
        logger = logging.getLogger(__name__)
        logger.warning("python-dotenv not installed, trying manual env loading")
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            logger.info(f"Loaded environment variables from {env_path}")
        except Exception as e:
            logger.warning(f"Failed to load {env_path}: {e}")
else:
    logger = logging.getLogger(__name__)
    logger.warning(f"Environment file not found: {env_path}")
    logger.warning("Please create configs/.env with your API keys")

# MoAgent imports
from moagent.config.settings import Config
from moagent.crawlers import get_crawler
from moagent.parsers import get_parser
from moagent.storage import get_storage
from moagent.notify import get_notifier

# Multi-agent imports
from moagent.agents.multi_agent.workflow import create_multi_agent_graph
from moagent.agents.multi_agent.base import AgentConfig, Task

# RAG imports (lazy loading - disabled by default)
# from moagent.rag import RAGCrawler, KnowledgeBase, VectorStore
# from moagent.rag.embeddings import SimpleEmbeddingGenerator

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'moagent-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# RAG configuration
RAG_ENABLED = os.environ.get('RAG_ENABLED', 'false').lower() == 'true'

# Global instances
storage = None
rag_crawler = None
knowledge_base = None


def init_storage():
    """Initialize storage backend"""
    global storage
    if storage is None:
        config = Config()
        storage = get_storage(config)
    return storage


def init_rag():
    """Initialize RAG components (only if RAG_ENABLED is true)"""
    global rag_crawler, knowledge_base

    if not RAG_ENABLED:
        print("RAG system disabled by default (set RAG_ENABLED=true to enable)")
        return False

    try:
        # Lazy import RAG modules
        from moagent.rag import RAGCrawler, KnowledgeBase

        print("Initializing RAG system (this may take 30-60 seconds)...")
        rag_crawler = RAGCrawler(auto_learn=True)
        knowledge_base = KnowledgeBase()
        print("✓ RAG system initialized successfully")
        return True
    except Exception as e:
        print(f"RAG initialization failed: {e}")
        print("Continuing without RAG support...")
        return False


# =============================================================================
# Routes
# =============================================================================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/crawl')
def crawl_page():
    """Crawling interface"""
    return render_template('crawl.html')


@app.route('/rag')
def rag_page():
    """RAG system interface"""
    return render_template('rag.html')


@app.route('/multi-agent')
def multi_agent_page():
    """Multi-agent workflow interface"""
    return render_template('multi_agent.html')


@app.route('/dashboard')
def dashboard():
    """Dashboard and monitoring"""
    return render_template('dashboard.html')


@app.route('/config')
def config_page():
    """Configuration page"""
    return render_template('config.html')


@app.route('/storage')
def storage_page():
    """Storage viewer page"""
    return render_template('storage.html')


# =============================================================================
# API Routes
# =============================================================================

@app.route('/api/crawl', methods=['POST'])
def api_crawl():
    """
    Execute crawling task

    Request JSON:
    {
        "url": "https://example.com",
        "mode": "auto",
        "depth": 1,
        "use_rag": false,
        "pattern": {...}  // Optional: LLM-generated pattern
    }
    """
    try:
        data = request.get_json()
        url = data.get('url')
        mode = data.get('mode', 'auto')
        depth = data.get('depth', 1)
        use_rag = data.get('use_rag', False)
        pattern = data.get('pattern')  # LLM-generated pattern (optional)

        if not url:
            return jsonify({'error': 'URL is required'}), 400

        # Create config
        config = Config(target_url=url, crawl_mode=mode)

        # If pattern is provided, use it for crawler configuration
        if pattern:
            # Convert LLM pattern to crawler pattern format
            crawler_pattern = {
                'list_container': pattern.get('list_container', {}),
                'item_selector': pattern.get('item_selector', {}),
                'title_selector': pattern.get('title_selector', {}),
                'url_selector': pattern.get('url_selector', {}),
                'date_selector': pattern.get('date_selector', {}),
                'content_selector': pattern.get('content_selector', {}),
                'post_process': pattern.get('post_process', {})
            }

            # Set crawler_patterns in config
            config.crawler_patterns = [crawler_pattern]

            logger.info(f"Using LLM-generated pattern for crawling: {url}")
            logger.info(f"Pattern confidence: {pattern.get('confidence', 0):.2%}")

        # Initialize components
        crawler = get_crawler(config)
        parser = get_parser(config)
        storage = get_storage(config)

        # Execute crawling
        results = crawler.crawl()

        # Parse results
        parsed_items = []
        for item in results:
            parsed = parser.parse(item)
            if parsed:
                parsed_items.append(parsed)

        # Store results
        stored_count = 0
        for item in parsed_items:
            if storage.store(item):
                stored_count += 1

        # Get statistics
        stats = {
            'total_items': len(storage.get_all()),
            'recent_items': storage.get_recent(limit=10)
        }

        response_data = {
            'success': True,
            'url': url,
            'mode': mode,
            'crawled_count': len(results),
            'parsed_count': len(parsed_items),
            'stored_count': stored_count,
            'items': parsed_items[:10],  # Return first 10 items
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }

        # Add pattern info if used
        if pattern:
            response_data['pattern_used'] = True
            response_data['pattern_confidence'] = pattern.get('confidence', 0)

        return jsonify(response_data)

    except Exception as e:
        import traceback
        logger.error(f"Crawling error: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/storage/stats', methods=['GET'])
def api_storage_stats():
    """Get storage statistics"""
    try:
        storage = init_storage()
        all_items = storage.get_all()

        # Calculate statistics
        total_items = len(all_items)

        # Count items by source if available
        sources = {}
        for item in all_items:
            source = item.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1

        # Get recent items
        recent_items = storage.get_recent(limit=10)

        stats = {
            'total_items': total_items,
            'sources': sources,
            'recent_count': len(recent_items),
            'last_updated': recent_items[0].get('timestamp') if recent_items else None
        }

        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/storage/items', methods=['GET'])
def api_storage_items():
    """Get stored items"""
    try:
        storage = init_storage()
        limit = request.args.get('limit', 50, type=int)

        # Use get_recent() instead of get_items()
        items = storage.get_recent(limit=limit)

        return jsonify({
            'success': True,
            'items': items,
            'count': len(items)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/rag/stats', methods=['GET'])
def api_rag_stats():
    """Get RAG system statistics"""
    try:
        global knowledge_base

        if knowledge_base is None:
            init_rag()

        if knowledge_base is None:
            return jsonify({
                'success': False,
                'error': 'RAG system not initialized'
            }), 503

        stats = knowledge_base.get_statistics()

        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/rag/patterns', methods=['GET'])
def api_rag_patterns():
    """Get RAG patterns"""
    try:
        global knowledge_base

        if knowledge_base is None:
            return jsonify({
                'success': False,
                'error': 'RAG system not initialized'
            }), 503

        limit = request.args.get('limit', 20, type=int)
        patterns = knowledge_base.get_best_patterns(limit=limit)

        return jsonify({
            'success': True,
            'patterns': patterns,
            'count': len(patterns)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/rag/similar', methods=['POST'])
def api_rag_similar():
    """Find similar patterns"""
    try:
        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({'error': 'URL is required'}), 400

        global knowledge_base
        if knowledge_base is None:
            return jsonify({
                'success': False,
                'error': 'RAG system not initialized'
            }), 503

        limit = data.get('limit', 5)
        patterns = knowledge_base.find_similar_patterns(url, top_k=limit)

        return jsonify({
            'success': True,
            'url': url,
            'similar_patterns': patterns,
            'count': len(patterns)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/multi-agent/execute', methods=['POST'])
def api_multi_agent_execute():
    """
    Execute multi-agent workflow

    Request JSON:
    {
        "url": "https://example.com",
        "keywords": ["AI", "tech"],
        "depth": 2,
        "enable_optimization": true,
        "enable_rag": false,
        "llm_config": {
            "api_key": "sk-xxx",
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini",
            "api_base_url": ""
        }
    }
    """
    try:
        data = request.get_json()
        url = data.get('url')
        keywords = data.get('keywords', [])
        depth = data.get('depth', 1)
        enable_optimization = data.get('enable_optimization', True)
        enable_rag = data.get('enable_rag', False)

        # LLM配置从前端传入
        llm_config = data.get('llm_config', {})

        if not url:
            return jsonify({'error': 'URL is required'}), 400

        # Create workflow with LLM config
        graph = create_multi_agent_graph(enable_rag=enable_rag, llm_config=llm_config)

        # Execute workflow
        result = graph.execute({
            'url': url,
            'keywords': keywords,
            'depth': depth,
            'enable_optimization': enable_optimization
        })

        # Clean result to make JSON serializable
        cleaned_result = clean_for_json(result)

        return jsonify({
            'success': cleaned_result.get('success', False),
            'url': url,
            'result': cleaned_result,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


def clean_for_json(obj):
    """Clean objects for JSON serialization by removing non-serializable items"""
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()
                if not k.startswith('_') and not callable(v)}
    elif isinstance(obj, list):
        return [clean_for_json(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        # Convert object to dict, excluding private attributes and methods
        return clean_for_json({k: v for k, v in obj.__dict__.items()
                              if not k.startswith('_') and not callable(v)})
    else:
        # Return basic types as-is, convert others to string
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        return str(obj)


@app.route('/api/system/info', methods=['GET'])
def api_system_info():
    """Get system information"""
    try:
        from moagent import __version__

        info = {
            'version': __version__,
            'features': {
                'crawling': True,
                'parsing': True,
                'storage': True,
                'rag': knowledge_base is not None,
                'multi_agent': True
            },
            'timestamp': datetime.now().isoformat()
        }

        return jsonify({
            'success': True,
            'info': info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/config/test', methods=['POST'])
def api_test_llm_config():
    """Test LLM configuration"""
    try:
        data = request.get_json()
        provider = data.get('llm_provider', 'openai')
        model = data.get('llm_model', 'gpt-4o-mini')
        api_key = data.get('api_key')
        api_base = data.get('api_base_url')

        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API密钥不能为空'
            }), 400

        # Create test config
        from moagent.llm.client import get_llm_client

        test_config = Config()
        test_config.llm_provider = provider
        test_config.llm_model = model
        test_config.openai_api_key = api_key if provider == 'openai' else None
        test_config.anthropic_api_key = api_key if provider == 'anthropic' else None
        if api_base:
            test_config.llm_api_base_url = api_base

        # Test the connection
        import time
        start_time = time.time()

        client = get_llm_client(config=test_config)

        # Use chat() method instead of generate()
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Please respond with 'OK' if you receive this message."}
        ]

        response = client.chat(messages)

        latency = time.time() - start_time

        return jsonify({
            'success': True,
            'model': model,
            'response': response[:100] if response else 'OK',
            'latency': f'{latency:.2f}s'
        })

    except Exception as e:
        import traceback
        error_msg = str(e)

        # Provide more helpful error messages
        if "API key" in error_msg:
            error_msg = "API密钥无效或未设置"
        elif "connection" in error_msg.lower():
            error_msg = "无法连接到API服务器，请检查网络和API地址"
        elif "rate limit" in error_msg.lower():
            error_msg = "API请求频率超限，请稍后再试"

        return jsonify({
            'success': False,
            'error': error_msg,
            'traceback': traceback.format_exc() if os.environ.get('DEBUG') else ''
        }), 500


@app.route('/api/pattern/generate', methods=['POST'])
def api_generate_pattern():
    """
    Generate crawling pattern using LLM

    Request JSON:
    {
        "html": "<html>...</html>",
        "url": "https://example.com",
        "api_key": "sk-...",  // Optional: override API key
        "llm_provider": "openai",  // Optional: override provider
        "llm_model": "gpt-4o-mini"  // Optional: override model
    }
    """
    try:
        data = request.get_json()
        html_content = data.get('html', '')
        url = data.get('url', '')
        api_key = data.get('api_key')  # Optional API key from request
        llm_provider = data.get('llm_provider')  # Optional provider override
        llm_model = data.get('llm_model')  # Optional model override

        if not html_content:
            return jsonify({'error': 'HTML content is required'}), 400

        # Import pattern generator
        from moagent.agents.pattern_generator.llm_pattern_generator import LLMPatternGeneratorAgent

        # Create agent with optional overrides
        config = Config()

        # Apply overrides if provided
        if llm_provider:
            config.llm_provider = llm_provider
        if llm_model:
            config.llm_model = llm_model

        # Create agent with API key if provided
        agent = LLMPatternGeneratorAgent(
            config=config,
            api_key=api_key if api_key else None
        )

        # Generate pattern - use analyze_html_content method
        analysis = agent.analyze_html_content(html_content)

        # Convert to dict for JSON response
        result = {
            'success': True,
            'pattern': {
                'list_container': analysis.list_container,
                'item_selector': analysis.item_selector,
                'title_selector': analysis.title_selector,
                'url_selector': analysis.url_selector,
                'date_selector': analysis.date_selector,
                'content_selector': analysis.content_selector,
                'post_process': analysis.post_process,
                'confidence': analysis.confidence,
                'reasoning': analysis.reasoning
            },
            'raw_response': analysis.llm_response,
            'metadata': analysis.llm_metadata
        }

        logger.info(f"Pattern generated for URL: {url} (confidence: {analysis.confidence:.2%})")

        return jsonify(result)

    except Exception as e:
        import traceback
        logger.error(f"Pattern generation error: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc() if os.environ.get('DEBUG') else ''
        }), 500


@app.route('/api/pattern/refine', methods=['POST'])
def api_refine_pattern():
    """
    Refine crawling pattern using LLM with feedback

    Request JSON:
    {
        "current_pattern": {...},
        "feedback": "用户反馈",
        "html": "<html>...</html>",
        "api_key": "sk-...",  // Optional: override API key
        "llm_provider": "openai",  // Optional: override provider
        "llm_model": "gpt-4o-mini"  // Optional: override model
    }
    """
    try:
        data = request.get_json()
        current_pattern_dict = data.get('current_pattern', {})
        feedback = data.get('feedback', '')
        html_content = data.get('html', '')
        api_key = data.get('api_key')  # Optional API key from request
        llm_provider = data.get('llm_provider')  # Optional provider override
        llm_model = data.get('llm_model')  # Optional model override

        if not feedback:
            return jsonify({'error': 'Feedback is required'}), 400
        if not html_content:
            return jsonify({'error': 'HTML content is required'}), 400

        # Import pattern refiner
        from moagent.agents.pattern_generator.llm_pattern_refiner import LLMPatternRefinerAgent
        from moagent.agents.pattern_generator.llm_pattern_generator import LLMPatternAnalysis

        # Create agent with optional overrides
        config = Config()

        # Apply overrides if provided
        if llm_provider:
            config.llm_provider = llm_provider
        if llm_model:
            config.llm_model = llm_model

        # Create agent with API key if provided
        agent = LLMPatternRefinerAgent(
            config=config,
            api_key=api_key if api_key else None
        )

        # Convert dict back to LLMPatternAnalysis
        current_analysis = LLMPatternAnalysis(
            list_container=current_pattern_dict.get('list_container', {}),
            item_selector=current_pattern_dict.get('item_selector', {}),
            title_selector=current_pattern_dict.get('title_selector', {}),
            url_selector=current_pattern_dict.get('url_selector', {}),
            date_selector=current_pattern_dict.get('date_selector', {}),
            content_selector=current_pattern_dict.get('content_selector', {}),
            post_process=current_pattern_dict.get('post_process', {}),
            confidence=current_pattern_dict.get('confidence', 0.0),
            reasoning=current_pattern_dict.get('reasoning', ''),
            sample_html=html_content,
            llm_response=current_pattern_dict,
            llm_metadata=current_pattern_dict.get('metadata', {})
        )

        # Refine pattern
        result = agent.refine_with_comparison(current_analysis, feedback, html_content)

        # Convert to dict for JSON response
        refined_pattern = {
            'list_container': result.refined.list_container,
            'item_selector': result.refined.item_selector,
            'title_selector': result.refined.title_selector,
            'url_selector': result.refined.url_selector,
            'date_selector': result.refined.date_selector,
            'content_selector': result.refined.content_selector,
            'post_process': result.refined.post_process,
            'confidence': result.refined.confidence,
            'reasoning': result.refined.reasoning
        }

        return jsonify({
            'success': True,
            'original_pattern': current_pattern_dict,
            'refined_pattern': refined_pattern,
            'changes': result.changes,
            'improvement_score': result.improvement_score,
            'validation_passed': result.validation_passed,
            'validation_errors': result.validation_errors,
            'report': agent.generate_refinement_report(result)
        })

    except Exception as e:
        import traceback
        logger.error(f"Pattern refinement error: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc() if os.environ.get('DEBUG') else ''
        }), 500


@app.route('/api/pattern/test', methods=['POST'])
def api_test_pattern():
    """
    Test pattern extraction on HTML content

    Request JSON:
    {
        "pattern": {...},
        "html": "<html>...</html>",
        "base_url": "https://example.com"
    }
    """
    try:
        data = request.get_json()
        pattern_dict = data.get('pattern', {})
        html_content = data.get('html', '')
        base_url = data.get('base_url', '')

        if not html_content:
            return jsonify({'error': 'HTML content is required'}), 400

        # Import pattern refiner (has test method)
        from moagent.agents.pattern_generator.llm_pattern_refiner import LLMPatternRefinerAgent
        from moagent.agents.pattern_generator.llm_pattern_generator import LLMPatternAnalysis

        # Create agent
        config = Config()
        agent = LLMPatternRefinerAgent(config)

        # Convert dict to LLMPatternAnalysis
        analysis = LLMPatternAnalysis(
            list_container=pattern_dict.get('list_container', {}),
            item_selector=pattern_dict.get('item_selector', {}),
            title_selector=pattern_dict.get('title_selector', {}),
            url_selector=pattern_dict.get('url_selector', {}),
            date_selector=pattern_dict.get('date_selector', {}),
            content_selector=pattern_dict.get('content_selector', {}),
            post_process=pattern_dict.get('post_process', {}),
            confidence=pattern_dict.get('confidence', 0.0),
            reasoning=pattern_dict.get('reasoning', ''),
            sample_html=html_content,
            llm_response=pattern_dict,
            llm_metadata=pattern_dict.get('metadata', {})
        )

        # Test extraction
        items, stats = agent.test_pattern_extraction(analysis, html_content, base_url)

        return jsonify({
            'success': True,
            'items': items[:20],  # Return first 20 items
            'total_extracted': len(items),
            'stats': stats
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/fetch-html', methods=['GET'])
def api_fetch_html():
    """
    Fetch HTML content from URL using HTMLDownloader

    Query params:
        url: URL to fetch
        use_js: Use JavaScript rendering (optional, default=False)

    Returns:
        JSON with html content or error message
    """
    try:
        url = request.args.get('url')
        use_js = request.args.get('use_js', 'false').lower() == 'true'

        if not url:
            return jsonify({'error': 'URL is required'}), 400

        # Import HTMLDownloader
        from moagent.agents.pattern_generator.html_downloader import HTMLDownloader

        # Create downloader instance with longer timeout
        downloader = HTMLDownloader()
        downloader.timeout = 60  # Increase timeout to 60 seconds

        # Validate URL
        if not downloader.validate_url(url):
            return jsonify({
                'success': False,
                'error': 'Invalid URL format'
            }), 400

        # Download HTML content (without saving to file)
        try:
            if use_js:
                html_content = downloader._download_with_js(url, wait_time=5)
                method = 'JavaScript rendering'
            else:
                html_content = downloader._download_simple(url)
                method = 'HTTP requests'

            logger.info(f"Successfully fetched HTML from {url} using {method}, size: {len(html_content)} bytes")

        except Exception as download_error:
            logger.warning(f"Simple download failed for {url}: {download_error}, trying with JavaScript...")

            # Fallback to JavaScript rendering
            try:
                html_content = downloader._download_with_js(url, wait_time=5)
                method = 'JavaScript rendering (fallback)'
                logger.info(f"Fallback successful: fetched HTML using {method}, size: {len(html_content)} bytes")
            except Exception as js_error:
                logger.error(f"Both simple and JS download failed for {url}")
                raise Exception(f"Failed to download HTML: {download_error}. JavaScript fallback also failed: {js_error}")

        # Limit HTML size to prevent memory issues (max 10MB)
        max_size = 10 * 1024 * 1024
        original_size = len(html_content)

        if len(html_content) > max_size:
            html_content = html_content[:max_size]
            return jsonify({
                'success': True,
                'html': html_content,
                'size': len(html_content),
                'original_size': original_size,
                'truncated': True,
                'warning': f'HTML truncated from {original_size} to {max_size} bytes',
                'method': method
            })

        return jsonify({
            'success': True,
            'html': html_content,
            'size': len(html_content),
            'method': method
        })

    except Exception as e:
        import traceback
        error_msg = str(e)

        # Provide user-friendly error messages
        if "SSL" in error_msg or "certificate" in error_msg.lower():
            error_msg = "SSL证书验证失败，请检查URL是否使用HTTPS"
        elif "timeout" in error_msg.lower():
            error_msg = "请求超时，请检查网络连接或稍后重试"
        elif "connection" in error_msg.lower():
            error_msg = "无法连接到服务器，请检查URL是否正确"
        elif "404" in error_msg or "Not Found" in error_msg:
            error_msg = "页面不存在(404)，请检查URL"
        elif "403" in error_msg or "Forbidden" in error_msg:
            error_msg = "访问被拒绝(403)，该网站可能禁止爬虫访问"

        return jsonify({
            'success': False,
            'error': error_msg,
            'traceback': traceback.format_exc() if os.environ.get('DEBUG') else ''
        }), 500


# =============================================================================
# Error Handlers
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# Main
# =============================================================================

def main():
    """Run the Flask application"""
    print("="*60)
    print("MoAgent Web Application")
    print("="*60)
    print("\nInitializing components...")

    # Initialize storage
    print("✓ Storage backend")
    init_storage()

    # Try to initialize RAG (optional, disabled by default)
    print("\nRAG System: ", end="")
    rag_enabled = os.environ.get('RAG_ENABLED', 'false').lower() == 'true'

    if rag_enabled:
        print("Enabled")
        print("  Initializing RAG system (this may take 30-60 seconds)...")
        rag_ready = init_rag()
        if rag_ready:
            print("  ✓ RAG ready")
        else:
            print("  ⚠ RAG initialization failed, continuing without RAG")
    else:
        print("Disabled (set RAG_ENABLED=true to enable)")
        print("  Tip: RAG system requires ChromaDB and may take 30-60s to initialize")

    print("\n" + "="*60)
    print("Server starting on http://127.0.0.1:5000")
    print("="*60)
    print("\nAvailable pages:")
    print("  - http://127.0.0.1:5000/          : Home")
    print("  - http://127.0.0.1:5000/crawl     : Crawling")
    print("  - http://127.0.0.1:5000/rag       : RAG System")
    print("  - http://127.0.0.1:5000/multi-agent: Multi-Agent")
    print("  - http://127.0.0.1:5000/dashboard : Dashboard")
    print("  - http://127.0.0.1:5000/config    : Configuration")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")

    # Run Flask app
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True
    )


if __name__ == '__main__':
    main()
