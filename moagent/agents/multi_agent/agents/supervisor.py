"""
Supervisor Agent - 多Agent协调Agent

负责任务分解、Agent调度、执行监控和结果整合。
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base import BaseAgent, AgentConfig, Task, TaskResult
from ..communication import AgentCommunication
from .explorer import ExplorerAgent
from .analyst import AnalystAgent
from .optimizer import OptimizerAgent
from .validator import ValidatorAgent
from ....config.settings import Config

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent - 协调多Agent工作流

    职责:
    1. 任务分解
    2. Agent分配
    3. 执行监控
    4. 异常处理
    5. 结果整合
    """

    def __init__(
        self,
        config: AgentConfig,
        system_config: Optional[Config] = None,
        enable_rag: bool = True
    ):
        """
        初始化Supervisor Agent

        Args:
            config: Agent配置
            system_config: 系统配置（可选）
            enable_rag: 是否启用RAG（默认True）
        """
        super().__init__(config)
        self.system_config = system_config or Config()
        self.enable_rag = enable_rag

        # 初始化通信层
        self.communication = AgentCommunication()

        # 初始化子Agent
        self.agents: Dict[str, BaseAgent] = {}
        self._init_agents()

        # 注册到通信层
        self.communication.register_agent(self.config.agent_id)
        for agent_id in self.agents.keys():
            self.communication.register_agent(agent_id)

    def _init_agents(self):
        """初始化子Agent"""
        # Explorer Agent
        self.agents["explorer"] = ExplorerAgent(
            AgentConfig(
                agent_id="explorer",
                role="explorer",
                capabilities=["explore", "analyze_structure"],
                timeout=30
            ),
            self.system_config
        )

        # Analyst Agent
        self.agents["analyst"] = AnalystAgent(
            AgentConfig(
                agent_id="analyst",
                role="analyst",
                capabilities=["analyze", "assess_quality"],
                timeout=60
            ),
            self.system_config
        )

        # Optimizer Agent
        self.agents["optimizer"] = OptimizerAgent(
            AgentConfig(
                agent_id="optimizer",
                role="optimizer",
                capabilities=["optimize", "tune_parameters"],
                timeout=45
            ),
            self.system_config,
            use_rag=self.enable_rag
        )

        # Validator Agent
        self.agents["validator"] = ValidatorAgent(
            AgentConfig(
                agent_id="validator",
                role="validator",
                capabilities=["validate", "check_quality"],
                timeout=30
            ),
            self.system_config
        )

        logger.info(f"Initialized {len(self.agents)} sub-agents")

    async def execute(self, task: Task) -> TaskResult:
        """
        执行监督任务

        Args:
            task: 任务对象
                - url: 目标URL
                - keywords: 关键词列表
                - depth: 探索深度（默认2）
                - enable_optimization: 是否启用优化（默认True）

        Returns:
            TaskResult: 最终结果
        """
        url = task.params.get("url")
        keywords = task.params.get("keywords", [])
        depth = task.params.get("depth", 2)
        enable_optimization = task.params.get("enable_optimization", True)

        logger.info(f"Supervisor coordinating workflow for {url}")

        start_time = datetime.now()

        try:
            # Step 1: 任务分解
            sub_tasks = self._decompose_task(task)
            logger.info(f"Decomposed into {len(sub_tasks)} sub-tasks")

            # Step 2: 执行工作流
            workflow_results = await self._execute_workflow(
                url,
                keywords,
                depth,
                enable_optimization
            )

            # Step 3: 整合结果
            final_result = self._integrate_results(workflow_results)

            execution_time = (datetime.now() - start_time).total_seconds()

            # 收集Agent性能
            agent_performance = self._collect_agent_performance()

            logger.info(
                f"Supervisor completed workflow in {execution_time:.2f}s: "
                f"{final_result.get('total_items', 0)} items processed"
            )

            return TaskResult(
                task_id=task.task_id,
                agent_id=self.config.agent_id,
                success=True,
                data={
                    "final_result": final_result,
                    "workflow_results": workflow_results,
                    "agent_performance": agent_performance,
                    "execution_time": execution_time
                },
                quality_score=0.9,
                metadata={
                    "workflow": "supervisor_coordinated",
                    "agents_used": len(self.agents)
                }
            )

        except Exception as e:
            logger.error(f"Supervisor workflow failed: {e}", exc_info=True)

            return TaskResult(
                task_id=task.task_id,
                agent_id=self.config.agent_id,
                success=False,
                data={},
                error=str(e)
            )

    def _decompose_task(self, task: Task) -> List[Task]:
        """将高层任务分解为子任务"""
        sub_tasks = []

        # 任务1: 探索网站
        sub_tasks.append(Task(
            task_id=f"{task.task_id}_explore",
            task_type="explore_website",
            params={
                "url": task.params.get("url"),
                "depth": task.params.get("depth", 2)
            },
            priority=10  # 最高优先级
        ))

        # 后续任务会在执行中动态创建
        return sub_tasks

    async def _execute_workflow(
        self,
        url: str,
        keywords: List[str],
        depth: int,
        enable_optimization: bool
    ) -> Dict[str, Any]:
        """执行工作流"""

        results = {}

        # Phase 1: 探索
        logger.info("Phase 1: Exploration")
        explorer_task = Task(
            task_id="explore_1",
            task_type="explore_website",
            params={"url": url, "depth": depth}
        )

        explorer_result = await self.agents["explorer"].receive_task(explorer_task)
        results["exploration"] = explorer_result.data if explorer_result.success else {}

        if not explorer_result.success:
            logger.error("Exploration failed, aborting workflow")
            return results

        # Phase 2: 优化（可选）
        if enable_optimization:
            logger.info("Phase 2: Optimization")

            # 获取建议的模式
            suggested_pattern = results["exploration"].get("pattern_suggestion", {})

            optimizer_task = Task(
                task_id="optimize_1",
                task_type="optimize_pattern",
                params={
                    "url": url,
                    "current_pattern": suggested_pattern,
                    "performance_data": {"success_rate": 0.7, "avg_time": 2.0},
                    "enable_ab_test": False  # 暂时禁用A/B测试以加快速度
                }
            )

            optimizer_result = await self.agents["optimizer"].receive_task(optimizer_task)
            results["optimization"] = optimizer_result.data if optimizer_result.success else {}

        # Phase 3: 爬取（使用现有Coordinator）
        logger.info("Phase 3: Crawling")

        # 使用现有的crawler和parser
        from ....crawlers import get_crawler
        from ....parsers import get_parser

        temp_config = Config(target_url=url)
        crawler = get_crawler(temp_config)
        parser = get_parser(temp_config)

        # 执行爬取
        loop = asyncio.get_event_loop()
        crawled_items = await loop.run_in_executor(None, crawler.crawl)

        # 解析
        parsed_items = []
        for item in crawled_items:
            parsed = await loop.run_in_executor(None, parser.parse, item)
            if parsed:
                parsed_items.append(parsed)

        results["crawling"] = {
            "items": parsed_items,
            "count": len(parsed_items)
        }

        # Phase 4: 分析
        logger.info("Phase 4: Analysis")

        if parsed_items:
            analyst_task = Task(
                task_id="analyze_1",
                task_type="analyze_content",
                params={
                    "items": parsed_items,
                    "keywords": keywords,
                    "min_quality": 0.7
                }
            )

            analyst_result = await self.agents["analyst"].receive_task(analyst_task)
            results["analysis"] = analyst_result.data if analyst_result.success else {}
        else:
            results["analysis"] = {"analyzed_items": [], "summary": {}}

        # Phase 5: 验证
        logger.info("Phase 5: Validation")

        analyzed_items = results["analysis"].get("analyzed_items", [])
        kept_items = [item["item"] for item in analyzed_items if item.get("should_keep", False)]

        if kept_items:
            validator_task = Task(
                task_id="validate_1",
                task_type="validate_data",
                params={
                    "items": kept_items,
                    "schema": self.agents["validator"]._get_default_schema()
                }
            )

            validator_result = await self.agents["validator"].receive_task(validator_task)
            results["validation"] = validator_result.data if validator_result.success else {}
        else:
            results["validation"] = {"valid_items": [], "report": {}}

        return results

    def _integrate_results(self, workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """整合所有结果"""

        # 从验证结果获取有效项目
        validation = workflow_results.get("validation", {})
        valid_items = validation.get("valid_items", [])

        # 从分析结果获取统计
        analysis = workflow_results.get("analysis", {})
        summary = analysis.get("summary", {})

        # 从探索结果获取模式
        exploration = workflow_results.get("exploration", {})
        pattern = exploration.get("pattern_suggestion", {})

        return {
            "items": valid_items,
            "total_items": len(valid_items),
            "new_items": summary.get("kept_items", len(valid_items)),
            "pattern_used": pattern,
            "statistics": summary,
            "quality_score": summary.get("avg_quality", 0.8)
        }

    def _collect_agent_performance(self) -> Dict[str, Dict[str, Any]]:
        """收集所有Agent的性能"""
        performance = {}

        for agent_id, agent in self.agents.items():
            status = agent.get_status()
            performance[agent_id] = {
                "success_rate": status["metrics"]["success_rate"],
                "avg_time": status["metrics"]["avg_execution_time"],
                "tasks_completed": status["metrics"]["tasks_completed"],
                "tasks_failed": status["metrics"]["tasks_failed"],
                "status": status["status"]
            }

        return performance

    async def shutdown(self):
        """关闭Supervisor和所有子Agent"""
        logger.info("Shutting down Supervisor and all sub-agents")

        # 关闭所有子Agent
        for agent_id, agent in self.agents.items():
            await agent.shutdown()

        # 清理通信层
        await self.communication.cleanup()

        # 关闭自己
        await super().shutdown()
