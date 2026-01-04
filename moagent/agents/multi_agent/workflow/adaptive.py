"""
自适应工作流实现

根据执行结果动态调整工作流。
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .graph import MultiAgentGraph, MultiAgentState, create_initial_state, create_multi_agent_graph

logger = logging.getLogger(__name__)


class AdaptiveWorkflow:
    """
    自适应工作流

    根据中间结果动态调整下一个执行的Agent或策略。
    """

    def __init__(self, enable_rag: bool = True):
        """
        初始化自适应工作流

        Args:
            enable_rag: 是否启用RAG
        """
        self.enable_rag = enable_rag
        self.graph = create_multi_agent_graph(enable_rag=enable_rag)

    async def execute(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行自适应工作流

        Args:
            task_params: 任务参数

        Returns:
            执行结果
        """
        logger.info("Executing adaptive workflow")

        # 第一轮：标准执行
        result = await self._execute_with_adaptation(task_params, max_iterations=3)

        return result

    async def _execute_with_adaptation(
        self,
        task_params: Dict[str, Any],
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """带自适应的执行"""
        iteration = 0
        current_params = task_params.copy()
        execution_history = []

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Adaptive workflow iteration {iteration}/{max_iterations}")

            # 执行工作流
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.graph.execute,
                current_params
            )

            execution_history.append(result)

            # 检查是否成功
            if result["success"]:
                final_result = result["final_result"]

                # 检查质量是否满足要求
                if final_result.get("quality_score", 0) >= 0.8:
                    logger.info(f"Workflow succeeded with quality {final_result['quality_score']:.2%}")
                    break
                else:
                    logger.warning(
                        f"Quality score {final_result['quality_score']:.2%} below threshold, adapting..."
                    )

                    # 自适应调整
                    current_params = await self._adapt_parameters(
                        result,
                        current_params
                    )
            else:
                logger.error(f"Workflow failed: {result.get('error')}")
                break

        # 返回最终结果
        return {
            "success": result["success"],
            "final_result": result.get("final_result", {}),
            "iterations": iteration,
            "execution_history": execution_history,
            "adaptations_made": iteration > 1
        }

    async def _adapt_parameters(
        self,
        previous_result: Dict[str, Any],
        current_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        根据前一次结果自适应调整参数

        Args:
            previous_result: 前一次执行结果
            current_params: 当前参数

        Returns:
            调整后的参数
        """
        logger.info("Adapting workflow parameters")

        adapted_params = current_params.copy()

        # 检查工作流日志
        workflow_state = previous_result.get("workflow_state", {})
        execution_log = workflow_state.get("execution_log", [])

        # 分析哪个阶段出了问题
        quality_issues = []

        for log_entry in execution_log:
            phase = log_entry.get("phase")
            quality_score = log_entry.get("quality_score", 1.0)

            if quality_score < 0.7:
                quality_issues.append(phase)

        logger.info(f"Quality issues in phases: {quality_issues}")

        # 根据问题阶段调整参数
        if "exploration" in quality_issues:
            # 探索质量低，增加深度
            adapted_params["depth"] = adapted_params.get("depth", 2) + 1
            logger.info(f"Increased depth to {adapted_params['depth']}")

        if "analysis" in quality_issues:
            # 分析质量低，降低质量阈值
            adapted_params["min_quality"] = adapted_params.get("min_quality", 0.7) - 0.1
            logger.info(f"Decreased min_quality to {adapted_params['min_quality']}")

        if "validation" in quality_issues:
            # 验证失败率高，可能模式有问题
            adapted_params["enable_optimization"] = True
            logger.info("Enabled optimization for next iteration")

        # 如果整体质量不高，启用RAG
        if previous_result.get("final_result", {}).get("quality_score", 0) < 0.7:
            adapted_params["enable_rag"] = True
            logger.info("Enabled RAG for next iteration")

        return adapted_params


class SmartWorkflow:
    """
    智能工作流

    提供更高级的自适应能力，包括:
    - 动态Agent选择
    - 并行执行
    - 结果缓存
    """

    def __init__(self, enable_rag: bool = True):
        """
        初始化智能工作流

        Args:
            enable_rag: 是否启用RAG
        """
        self.enable_rag = enable_rag
        self.adaptive_workflow = AdaptiveWorkflow(enable_rag=enable_rag)
        self.execution_cache = {}  # 简单的执行缓存

    async def execute(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行智能工作流

        Args:
            task_params: 任务参数

        Returns:
            执行结果
        """
        url = task_params.get("url")

        # 检查缓存
        if url and url in self.execution_cache:
            logger.info(f"Using cached result for {url}")
            cached = self.execution_cache[url]
            cached["from_cache"] = True
            return cached

        # 执行自适应工作流
        result = await self.adaptive_workflow.execute(task_params)

        # 如果成功，缓存结果
        if result["success"] and url:
            self.execution_cache[url] = {
                **result,
                "cached_at": datetime.now().isoformat()
            }
            logger.info(f"Cached result for {url}")

        return result

    def clear_cache(self):
        """清空缓存"""
        self.execution_cache.clear()
        logger.info("Execution cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "cache_size": len(self.execution_cache),
            "cached_urls": list(self.execution_cache.keys())
        }
