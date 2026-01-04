"""
LangGraph工作流图实现

提供基于LangGraph的多Agent工作流编排。
"""

import logging
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime

from ..agents.explorer import ExplorerAgent
from ..agents.analyst import AnalystAgent
from ..agents.optimizer import OptimizerAgent
from ..agents.validator import ValidatorAgent
from ....config.settings import Config
from ....storage import get_storage

logger = logging.getLogger(__name__)

# 尝试导入LangGraph
try:
    from langgraph.graph import StateGraph, END
    from typing_extensions import TypedDict
    LANGGRAPH_AVAILABLE = True
except ImportError:
    logger.warning("LangGraph not available, using fallback implementation")
    LANGGRAPH_AVAILABLE = False
    TypedDict = dict


class MultiAgentState(TypedDict):
    """多Agent工作流状态"""
    # 任务信息
    task: Dict[str, Any]
    task_id: str
    url: str
    keywords: List[str]
    depth: int

    # 执行结果
    exploration_result: Optional[Dict[str, Any]]
    optimization_result: Optional[Dict[str, Any]]
    crawling_result: Optional[Dict[str, Any]]
    analysis_result: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]

    # 控制流
    current_phase: str
    errors: List[str]
    should_continue: bool
    should_retry: bool

    # 配置
    enable_optimization: bool
    enable_rag: bool

    # 元数据
    start_time: str
    execution_log: List[Dict[str, Any]]

    # Agent实例
    agents: Dict[str, Any]


def create_initial_state(task_params: Dict[str, Any], agents: Dict[str, Any]) -> MultiAgentState:
    """创建初始状态"""
    return {
        "task": task_params,
        "task_id": task_params.get("task_id", "default_task"),
        "url": task_params.get("url", ""),
        "keywords": task_params.get("keywords", []),
        "depth": task_params.get("depth", 2),

        "exploration_result": None,
        "optimization_result": None,
        "crawling_result": None,
        "analysis_result": None,
        "validation_result": None,

        "current_phase": "init",
        "errors": [],
        "should_continue": True,
        "should_retry": False,

        "enable_optimization": task_params.get("enable_optimization", True),
        "enable_rag": task_params.get("enable_rag", True),

        "start_time": datetime.now().isoformat(),
        "execution_log": [],

        "agents": agents
    }


def explorer_node(state: MultiAgentState) -> MultiAgentState:
    """Explorer节点"""
    logger.info("Executing Explorer Agent")

    try:
        agent = state["agents"]["explorer"]
        from ..base import Task

        task = Task(
            task_id=f"{state['task_id']}_explore",
            task_type="explore_website",
            params={
                "url": state["url"],
                "depth": state["depth"]
            }
        )

        # 异步执行 - 使用新的事件循环
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，创建任务
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(agent.receive_task(task))
                )
                result = future.result()
        except RuntimeError:
            # 没有运行的事件循环，创建新的
            result = asyncio.run(agent.receive_task(task))

        state["exploration_result"] = result.data if result.success else {}
        state["current_phase"] = "exploration"

        # 记录日志
        state["execution_log"].append({
            "phase": "exploration",
            "agent": "explorer",
            "timestamp": datetime.now().isoformat(),
            "success": result.success,
            "quality_score": result.quality_score
        })

        if not result.success:
            state["errors"].append(f"Exploration failed: {result.error}")

    except Exception as e:
        logger.error(f"Explorer node failed: {e}")
        state["errors"].append(f"Explorer error: {str(e)}")

    return state


def optimizer_node(state: MultiAgentState) -> MultiAgentState:
    """Optimizer节点"""
    logger.info("Executing Optimizer Agent")

    # 检查是否需要优化
    if not state["enable_optimization"]:
        logger.info("Optimization disabled, skipping")
        state["optimization_result"] = {"skipped": True}
        return state

    try:
        agent = state["agents"]["optimizer"]
        from ..base import Task

        # 从探索结果获取建议模式
        suggested_pattern = state.get("exploration_result", {}).get("pattern_suggestion", {})

        task = Task(
            task_id=f"{state['task_id']}_optimize",
            task_type="optimize_pattern",
            params={
                "url": state["url"],
                "current_pattern": suggested_pattern,
                "performance_data": {"success_rate": 0.7, "avg_time": 2.0},
                "enable_ab_test": False
            }
        )

        import asyncio
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(agent.receive_task(task))
                )
                result = future.result()
        except RuntimeError:
            result = asyncio.run(agent.receive_task(task))

        state["optimization_result"] = result.data if result.success else {}
        state["current_phase"] = "optimization"

        state["execution_log"].append({
            "phase": "optimization",
            "agent": "optimizer",
            "timestamp": datetime.now().isoformat(),
            "success": result.success,
            "improvement": result.data.get("improvement", 0) if result.success else 0
        })

    except Exception as e:
        logger.error(f"Optimizer node failed: {e}")
        state["errors"].append(f"Optimizer error: {str(e)}")

    return state


def crawler_node(state: MultiAgentState) -> MultiAgentState:
    """Crawler节点 - 支持全文提取"""
    logger.info("Executing Crawling with fulltext extraction")

    try:
        from ....crawlers import get_crawler
        from ....parsers import get_parser
        from ....crawlers.content import get_fulltext_crawler, extract_fulltext_batch

        # 使用优化后的模式或默认模式
        if state.get("optimization_result") and not state["optimization_result"].get("skipped"):
            pattern = state["optimization_result"].get("optimized_pattern", {})
        else:
            pattern = state.get("exploration_result", {}).get("pattern_suggestion", {})

        # 创建配置 - 从agents的system_config获取API密钥
        agents = state.get("agents", {})
        base_config = None

        # 尝试从任意agent的system_config获取配置
        if agents:
            for agent in agents.values():
                if hasattr(agent, 'system_config'):
                    base_config = agent.system_config
                    break

        # 创建新的config并复制LLM配置
        config = Config(target_url=state["url"])

        if base_config:
            # 复制所有LLM相关配置
            config.openai_api_key = base_config.openai_api_key
            config.anthropic_api_key = base_config.anthropic_api_key
            config.llm_provider = base_config.llm_provider
            config.llm_model = base_config.llm_model
            config.llm_api_base_url = base_config.llm_api_base_url

            # 详细日志：检查API密钥是否真的被复制了
            logger.info(f"✅ Configured LLM settings:")
            logger.info(f"   - provider: {config.llm_provider}")
            logger.info(f"   - model: {config.llm_model}")
            logger.info(f"   - has_openai_key: {bool(config.openai_api_key)}")
            logger.info(f"   - has_anthropic_key: {bool(config.anthropic_api_key)}")
            logger.info(f"   - api_base_url: {config.llm_api_base_url}")
        else:
            logger.warning("⚠️  No base_config found in agents! API keys will not be available.")
            logger.warning("⚠️  Fulltext extraction will fall back to list-only mode.")

        # 步骤1: 执行列表爬取（获取文章链接）
        logger.info("Step 1: Crawling article list")
        crawler = get_crawler(config)
        parser = get_parser(config)

        import asyncio
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_crawl = executor.submit(
                    lambda: asyncio.run(asyncio.to_thread(crawler.crawl))
                )
                crawled_items = future_crawl.result()
        except RuntimeError:
            crawled_items = asyncio.run(asyncio.to_thread(crawler.crawl))

        # 解析列表项
        parsed_items = []
        for item in crawled_items:
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future_parse = executor.submit(
                        lambda i=item: asyncio.run(asyncio.to_thread(parser.parse, i))
                    )
                    parsed = future_parse.result()
            except RuntimeError:
                parsed = asyncio.run(asyncio.to_thread(parser.parse, item))
            if parsed:
                parsed_items.append(parsed)

        logger.info(f"Parsed {len(parsed_items)} items from list")

        # 步骤2: 提取文章链接并获取全文
        article_urls = []
        for item in parsed_items:
            if isinstance(item, dict):
                url = item.get('url') or item.get('link')
            else:
                url = getattr(item, 'url', None) or getattr(item, 'link', None)

            if url:
                article_urls.append(url)

        logger.info(f"Step 2: Extracting full content for {len(article_urls)} articles")

        # 使用fulltext crawler获取完整文章内容
        if article_urls:
            # 限制提取数量（避免太慢）
            max_articles = getattr(config, 'max_articles', 10)
            urls_to_fetch = article_urls[:max_articles]

            # 检查是否有API密钥，如果没有则跳过全文提取
            has_api_key = bool(config.openai_api_key or config.anthropic_api_key)

            if not has_api_key:
                logger.warning("No API key configured, skipping fulltext extraction. Only list content will be available.")
                state["crawling_result"] = {
                    "items": parsed_items,
                    "count": len(parsed_items),
                    "pattern_used": pattern,
                    "fulltext_enabled": False,
                    "articles_with_fulltext": 0,
                    "skip_reason": "No API key configured"
                }
            else:
                try:
                    # 使用hybrid模式获取全文
                    fulltext_articles = extract_fulltext_batch(
                        urls=urls_to_fetch,
                        config=config,
                        mode='hybrid'
                    )

                    logger.info(f"Successfully extracted full content for {len(fulltext_articles)} articles")

                    # 合并列表项和全文内容
                    # 优先使用全文内容，如果提取失败则使用列表内容
                    final_items = []
                    url_to_fulltext = {article.get('url'): article for article in fulltext_articles if article}

                    for parsed_item in parsed_items[:max_articles]:
                        item_url = parsed_item.get('url') if isinstance(parsed_item, dict) else getattr(parsed_item, 'url', None)

                        if item_url and item_url in url_to_fulltext:
                            # 使用全文内容
                            fulltext_item = url_to_fulltext[item_url]
                            # 保留列表项中的额外字段（如果有的话）
                            if isinstance(parsed_item, dict):
                                for key, value in parsed_item.items():
                                    if key not in fulltext_item or not fulltext_item[key]:
                                        fulltext_item[key] = value
                            final_items.append(fulltext_item)
                        else:
                            # 全文提取失败，使用列表内容
                            logger.warning(f"Fulltext extraction failed for {item_url}, using list item")
                            final_items.append(parsed_item)

                    parsed_items = final_items

                    state["crawling_result"] = {
                        "items": parsed_items,
                        "count": len(parsed_items),
                        "pattern_used": pattern,
                        "fulltext_enabled": True,
                        "articles_with_fulltext": len([i for i in parsed_items if i.get('content') and len(i.get('content', '')) > 100])
                    }

                except Exception as e:
                    logger.error(f"Fulltext extraction failed: {e}, using list items only")
                    # 如果全文提取失败，使用列表内容
                    state["crawling_result"] = {
                        "items": parsed_items,
                        "count": len(parsed_items),
                        "pattern_used": pattern,
                        "fulltext_enabled": False,
                        "articles_with_fulltext": 0,
                        "skip_reason": f"Extraction failed: {str(e)}"
                    }
        else:
            state["crawling_result"] = {
                "items": parsed_items,
                "count": len(parsed_items),
                "pattern_used": pattern,
                "fulltext_enabled": False,
                "articles_with_fulltext": 0,
                "skip_reason": "No article URLs found"
            }

        # ✅ 自动保存到数据库
        saved_count = 0
        skipped_count = 0
        try:
            storage = get_storage(config)
            items_to_save = state["crawling_result"]["items"]

            for item in items_to_save:
                try:
                    # 确保item是字典格式
                    if not isinstance(item, dict):
                        # 如果是对象，转换为字典
                        item_dict = {
                            'title': getattr(item, 'title', ''),
                            'url': getattr(item, 'url', ''),
                            'content': getattr(item, 'content', ''),
                            'timestamp': getattr(item, 'timestamp', ''),
                            'author': getattr(item, 'author', ''),
                            'category': getattr(item, 'category', ''),
                        }
                    else:
                        item_dict = item

                    # 保存到数据库（storage会自动去重）
                    is_new = storage.save(item_dict)
                    if is_new:
                        saved_count += 1
                    else:
                        skipped_count += 1

                except Exception as item_error:
                    logger.warning(f"Failed to save item to database: {item_error}")
                    continue

            logger.info(f"✅ Database save complete: {saved_count} new items saved, {skipped_count} duplicates skipped")

            # 将保存统计添加到结果中
            state["crawling_result"]["database_save"] = {
                "success": True,
                "total_items": len(items_to_save),
                "new_items_saved": saved_count,
                "duplicates_skipped": skipped_count,
                "save_timestamp": datetime.now().isoformat()
            }

        except Exception as save_error:
            logger.error(f"Failed to save to database: {save_error}")
            state["crawling_result"]["database_save"] = {
                "success": False,
                "error": str(save_error),
                "total_items": len(state["crawling_result"]["items"]),
                "new_items_saved": 0
            }

        state["current_phase"] = "crawling"

        state["execution_log"].append({
            "phase": "crawling",
            "agent": "crawler",
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "items_count": len(parsed_items),
            "fulltext_extracted": state["crawling_result"].get("articles_with_fulltext", 0),
            "database_saved": saved_count,
            "database_skipped": skipped_count
        })

    except Exception as e:
        logger.error(f"Crawler node failed: {e}", exc_info=True)
        state["errors"].append(f"Crawler error: {str(e)}")
        state["crawling_result"] = {"items": [], "count": 0}

    return state


def analyst_node(state: MultiAgentState) -> MultiAgentState:
    """Analyst节点"""
    logger.info("Executing Analyst Agent")

    try:
        agent = state["agents"]["analyst"]
        from ..base import Task

        # 获取爬取的项目
        items = state.get("crawling_result", {}).get("items", [])

        task = Task(
            task_id=f"{state['task_id']}_analyze",
            task_type="analyze_content",
            params={
                "items": items,
                "keywords": state["keywords"],
                "min_quality": 0.7
            }
        )

        import asyncio
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(agent.receive_task(task))
                )
                result = future.result()
        except RuntimeError:
            result = asyncio.run(agent.receive_task(task))

        state["analysis_result"] = result.data if result.success else {}
        state["current_phase"] = "analysis"

        state["execution_log"].append({
            "phase": "analysis",
            "agent": "analyst",
            "timestamp": datetime.now().isoformat(),
            "success": result.success
        })

    except Exception as e:
        logger.error(f"Analyst node failed: {e}")
        state["errors"].append(f"Analyst error: {str(e)}")

    return state


def validator_node(state: MultiAgentState) -> MultiAgentState:
    """Validator节点"""
    logger.info("Executing Validator Agent")

    try:
        agent = state["agents"]["validator"]
        from ..base import Task

        # 从分析结果获取高质量项目
        analyzed_items = state.get("analysis_result", {}).get("analyzed_items", [])
        kept_items = [item["item"] for item in analyzed_items if item.get("should_keep", False)]

        task = Task(
            task_id=f"{state['task_id']}_validate",
            task_type="validate_data",
            params={
                "items": kept_items,
                "schema": agent._get_default_schema()
            }
        )

        import asyncio
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(agent.receive_task(task))
                )
                result = future.result()
        except RuntimeError:
            result = asyncio.run(agent.receive_task(task))

        state["validation_result"] = result.data if result.success else {}
        state["current_phase"] = "validation"

        state["execution_log"].append({
            "phase": "validation",
            "agent": "validator",
            "timestamp": datetime.now().isoformat(),
            "success": result.success,
            "valid_count": len(result.data.get("valid_items", [])) if result.success else 0
        })

    except Exception as e:
        logger.error(f"Validator node failed: {e}")
        state["errors"].append(f"Validator error: {str(e)}")

    return state


def should_optimize(state: MultiAgentState) -> str:
    """决定是否需要优化"""
    if not state["enable_optimization"]:
        return "skip"

    # 检查探索结果
    exploration = state.get("exploration_result", {})
    confidence = exploration.get("confidence", 0.0)

    # 如果置信度低，需要优化
    if confidence < 0.8:
        return "optimize"

    return "skip"


def should_validate(state: MultiAgentState) -> str:
    """决定是否需要验证"""
    # 检查是否有项目需要验证
    analysis = state.get("analysis_result") or {}
    summary = analysis.get("summary") or {}
    kept_items = summary.get("kept_items", 0)

    if kept_items > 0:
        return "validate"

    return "skip"


def should_retry_workflow(state: MultiAgentState) -> str:
    """决定是否需要重试工作流"""
    # 检查错误数量
    if len(state["errors"]) > 3:
        logger.warning("Too many errors, not retrying")
        return "end"

    # 检查是否有探索结果
    if not state.get("exploration_result"):
        logger.warning("No exploration result, retrying")
        return "retry"

    return "end"


class MultiAgentGraph:
    """多Agent工作流图"""

    def __init__(self, enable_rag: bool = True, llm_config: dict = None):
        """
        初始化工作流图

        Args:
            enable_rag: 是否启用RAG
            llm_config: LLM配置字典 (api_key, llm_provider, llm_model, api_base_url)
        """
        self.enable_rag = enable_rag
        self.llm_config = llm_config or {}
        self.graph = None
        self.agents = {}

        # 初始化Agents (传入LLM配置)
        self._init_agents()

        # 构建图
        if LANGGRAPH_AVAILABLE:
            self.graph = self._build_langgraph()
            logger.info("MultiAgentGraph initialized with LangGraph")
        else:
            logger.warning("LangGraph not available, using fallback")

    def _init_agents(self):
        """初始化所有Agent"""
        from ..base import AgentConfig
        config = Config()

        # 应用传入的LLM配置
        if self.llm_config:
            if self.llm_config.get('api_key'):
                provider = self.llm_config.get('llm_provider', 'openai')
                if provider == 'openai':
                    config.openai_api_key = self.llm_config['api_key']
                elif provider == 'anthropic':
                    config.anthropic_api_key = self.llm_config['api_key']

            if self.llm_config.get('llm_provider'):
                config.llm_provider = self.llm_config['llm_provider']
            if self.llm_config.get('llm_model'):
                config.llm_model = self.llm_config['llm_model']
            if self.llm_config.get('api_base_url'):
                config.llm_api_base_url = self.llm_config['api_base_url']

            logger.info(f"✅ Applied LLM config from request: provider={config.llm_provider}, has_key={bool(config.openai_api_key or config.anthropic_api_key)}")
        else:
            logger.info("Using LLM config from environment variables")

        self.agents["explorer"] = ExplorerAgent(
            AgentConfig(
                agent_id="explorer",
                role="explorer",
                capabilities=["explore"],
                timeout=30
            ),
            config
        )

        self.agents["analyst"] = AnalystAgent(
            AgentConfig(
                agent_id="analyst",
                role="analyst",
                capabilities=["analyze"],
                timeout=60
            ),
            config
        )

        self.agents["optimizer"] = OptimizerAgent(
            AgentConfig(
                agent_id="optimizer",
                role="optimizer",
                capabilities=["optimize"],
                timeout=45
            ),
            config,
            use_rag=self.enable_rag
        )

        self.agents["validator"] = ValidatorAgent(
            AgentConfig(
                agent_id="validator",
                role="validator",
                capabilities=["validate"],
                timeout=30
            ),
            config
        )

        logger.info(f"Initialized {len(self.agents)} agents")

    def _build_langgraph(self) -> Optional['StateGraph']:
        """构建LangGraph工作流图"""
        if not LANGGRAPH_AVAILABLE:
            return None

        # 创建状态图
        graph = StateGraph(MultiAgentState)

        # 添加节点
        graph.add_node("explorer", explorer_node)
        graph.add_node("optimizer", optimizer_node)
        graph.add_node("crawler", crawler_node)
        graph.add_node("analyst", analyst_node)
        graph.add_node("validator", validator_node)

        # 设置入口点
        graph.set_entry_point("explorer")

        # 添加边
        # Explorer -> (是否优化?) -> Optimizer or Crawler
        graph.add_conditional_edges(
            "explorer",
            should_optimize,
            {
                "optimize": "optimizer",
                "skip": "crawler"
            }
        )

        # Optimizer -> Crawler
        graph.add_edge("optimizer", "crawler")

        # Crawler -> Analyst
        graph.add_edge("crawler", "analyst")

        # Analyst -> (是否验证?) -> Validator or END
        graph.add_conditional_edges(
            "analyst",
            should_validate,
            {
                "validate": "validator",
                "skip": END
            }
        )

        # Validator -> END
        graph.add_edge("validator", END)

        # 编译图
        return graph.compile()

    def execute(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工作流

        Args:
            task_params: 任务参数
                - url: 目标URL
                - keywords: 关键词列表
                - depth: 探索深度
                - enable_optimization: 是否启用优化
                - enable_rag: 是否启用RAG

        Returns:
            执行结果
        """
        logger.info(f"Executing multi-agent workflow for {task_params.get('url')}")

        start_time = datetime.now()

        try:
            # 创建初始状态
            initial_state = create_initial_state(task_params, self.agents)

            # 执行图
            if self.graph:
                # 使用LangGraph
                final_state = self.graph.invoke(initial_state)
            else:
                # 降级到顺序执行
                final_state = self._execute_fallback(initial_state)

            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()

            # 整合结果
            final_result = self._integrate_results(final_state)

            return {
                "success": len(final_state["errors"]) == 0,
                "final_result": final_result,
                "workflow_state": final_state,
                "execution_time": execution_time,
                "agents_used": list(self.agents.keys()),
                "phases_executed": len(final_state["execution_log"]),
                "errors": final_state["errors"]
            }

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "execution_time": (datetime.now() - start_time).total_seconds()
            }

    def _execute_fallback(self, state: MultiAgentState) -> MultiAgentState:
        """降级执行（顺序执行）"""
        logger.info("Using fallback execution")

        # 顺序执行节点
        state = explorer_node(state)

        if state["enable_optimization"]:
            state = optimizer_node(state)

        state = crawler_node(state)
        state = analyst_node(state)

        # 验证是可选的
        if state.get("analysis_result"):
            analyzed_items = state["analysis_result"].get("analyzed_items", [])
            if analyzed_items:
                state = validator_node(state)

        return state

    def _integrate_results(self, state: MultiAgentState) -> Dict[str, Any]:
        """整合所有阶段的结果"""
        validation = state.get("validation_result") or {}
        analysis = state.get("analysis_result") or {}
        crawling = state.get("crawling_result") or {}
        exploration = state.get("exploration_result") or {}

        valid_items = validation.get("valid_items", []) if validation else []

        # 如果没有验证结果，使用爬取结果
        if not valid_items and crawling:
            valid_items = crawling.get("items", [])

        summary = analysis.get("summary", {}) if analysis else {}

        return {
            "items": valid_items,
            "total_items": len(valid_items),
            "new_items": summary.get("kept_items", len(valid_items)) if summary else len(valid_items),
            "pattern_used": exploration.get("pattern_suggestion", {}) if exploration else {},
            "statistics": summary,
            "quality_score": summary.get("avg_quality", 0.8) if summary else 0.8,
            "workflow_log": state.get("execution_log", [])
        }


def create_multi_agent_graph(enable_rag: bool = True, llm_config: dict = None) -> MultiAgentGraph:
    """
    创建多Agent工作流图

    Args:
        enable_rag: 是否启用RAG
        llm_config: LLM配置字典 (api_key, llm_provider, llm_model, api_base_url)

    Returns:
        MultiAgentGraph实例
    """
    return MultiAgentGraph(enable_rag=enable_rag, llm_config=llm_config)
