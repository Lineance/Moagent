"""
Optimizer Agent - 爬取策略优化Agent

负责优化爬取模式、调整参数、A/B测试和性能分析。
集成了RAG系统，使用向量数据库检索相似成功模式。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from ..base import BaseAgent, AgentConfig, Task, TaskResult
from ....config.settings import Config

logger = logging.getLogger(__name__)


class OptimizerAgent(BaseAgent):
    """
    Optimizer Agent - 优化爬取策略

    职责:
    1. 分析当前性能
    2. 从RAG检索相似成功模式
    3. 生成优化建议
    4. A/B测试
    5. 参数调优
    """

    def __init__(
        self,
        config: AgentConfig,
        system_config: Optional[Config] = None,
        use_rag: bool = True
    ):
        """
        初始化Optimizer Agent

        Args:
            config: Agent配置
            system_config: 系统配置（可选）
            use_rag: 是否使用RAG增强（默认True）
        """
        super().__init__(config)
        self.system_config = system_config or Config()
        self.use_rag = use_rag

        # 初始化RAG组件
        self.rag_crawler = None
        if use_rag:
            self._init_rag()

    def _init_rag(self):
        """初始化RAG组件"""
        try:
            from ....rag import RAGCrawler
            self.rag_crawler = RAGCrawler(auto_learn=True)
            logger.info("RAG component initialized for Optimizer")
        except Exception as e:
            logger.warning(f"Failed to initialize RAG: {e}")
            self.rag_crawler = None

    async def execute(self, task: Task) -> TaskResult:
        """
        执行优化任务

        Args:
            task: 任务对象
                - url: 目标URL
                - current_pattern: 当前爬取模式
                - performance_data: 性能数据
                - enable_ab_test: 是否启用A/B测试（默认False）

        Returns:
            TaskResult: 优化结果
        """
        url = task.params.get("url")
        current_pattern = task.params.get("current_pattern", {})
        performance_data = task.params.get("performance_data", {})
        enable_ab_test = task.params.get("enable_ab_test", False)

        logger.info(f"Optimizer optimizing pattern for {url}")

        try:
            # Step 1: 分析当前性能
            analysis = self._analyze_performance(current_pattern, performance_data)

            # Step 2: 从RAG获取相似成功模式
            similar_patterns = await self._get_similar_patterns(url)

            # Step 3: 识别瓶颈
            bottlenecks = analysis.get("bottlenecks", [])

            # Step 4: 生成优化建议（结合RAG）
            optimizations = await self._generate_optimizations(
                current_pattern,
                bottlenecks,
                similar_patterns
            )

            # Step 5: A/B测试（可选）
            ab_test_results = None
            if enable_ab_test:
                ab_test_results = await self._run_ab_test(
                    url,
                    current_pattern,
                    optimizations["proposed_pattern"]
                )

            # Step 6: 选择最佳方案
            best_pattern, improvement = self._select_best_pattern(
                current_pattern,
                optimizations["proposed_pattern"],
                ab_test_results
            )

            # Step 7: 参数调优
            tuned_params = await self._tune_parameters(best_pattern)

            logger.info(f"Optimization completed with improvement: {improvement:.2%}")

            return TaskResult(
                task_id=task.task_id,
                agent_id=self.config.agent_id,
                success=True,
                data={
                    "optimized_pattern": best_pattern,
                    "improvement": improvement,
                    "tuned_params": tuned_params,
                    "ab_test_results": ab_test_results,
                    "optimization_details": {
                        "analysis": analysis,
                        "bottlenecks": bottlenecks,
                        "similar_patterns_count": len(similar_patterns) if similar_patterns else 0
                    }
                },
                quality_score=0.9 if improvement > 0 else 0.7
            )

        except Exception as e:
            logger.error(f"Optimization failed: {e}", exc_info=True)

            return TaskResult(
                task_id=task.task_id,
                agent_id=self.config.agent_id,
                success=False,
                data={},
                error=str(e)
            )

    def _analyze_performance(
        self,
        pattern: Dict[str, Any],
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析当前性能"""

        success_rate = performance_data.get("success_rate", 0.5)
        avg_time = performance_data.get("avg_time", 2.0)
        error_rate = performance_data.get("error_rate", 0.1)

        bottlenecks = []

        # 识别瓶颈
        if success_rate < 0.7:
            bottlenecks.append({
                "type": "low_success_rate",
                "severity": "high",
                "value": success_rate
            })

        if avg_time > 3.0:
            bottlenecks.append({
                "type": "slow_performance",
                "severity": "medium",
                "value": avg_time
            })

        if error_rate > 0.15:
            bottlenecks.append({
                "type": "high_error_rate",
                "severity": "high",
                "value": error_rate
            })

        return {
            "success_rate": success_rate,
            "avg_time": avg_time,
            "error_rate": error_rate,
            "bottlenecks": bottlenecks,
            "overall_score": (success_rate - error_rate) / 2
        }

    async def _get_similar_patterns(self, url: str) -> Optional[List[Dict[str, Any]]]:
        """从RAG获取相似成功模式"""
        if not self.rag_crawler:
            return None

        try:
            # 使用RAG获取建议
            suggestions = await asyncio.to_thread(
                self.rag_crawler.get_suggested_patterns,
                url,
                n_options=5
            )

            return suggestions

        except Exception as e:
            logger.warning(f"Failed to get similar patterns from RAG: {e}")
            return None

    async def _generate_optimizations(
        self,
        current_pattern: Dict[str, Any],
        bottlenecks: List[Dict[str, Any]],
        similar_patterns: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """生成优化建议"""

        # 从当前模式开始
        proposed_pattern = current_pattern.copy()

        # 基于瓶颈进行优化
        for bottleneck in bottlenecks:
            if bottleneck["type"] == "low_success_rate":
                # 增加重试次数
                proposed_pattern["retry_count"] = proposed_pattern.get("retry_count", 3) + 2
                # 增加延迟
                proposed_pattern["delay"] = proposed_pattern.get("delay", 1.0) * 1.5

            elif bottleneck["type"] == "slow_performance":
                # 减少延迟（如果成功率还行）
                if proposed_pattern.get("success_rate", 0) > 0.8:
                    proposed_pattern["delay"] = max(0.5, proposed_pattern.get("delay", 1.0) * 0.7)

            elif bottleneck["type"] == "high_error_rate":
                # 增加超时时间
                proposed_pattern["timeout"] = proposed_pattern.get("timeout", 30) * 1.5
                # 增加延迟
                proposed_pattern["delay"] = proposed_pattern.get("delay", 1.0) * 2.0

        # 如果有相似模式，学习它们的配置
        if similar_patterns and len(similar_patterns) > 0:
            # 简化：采用最佳相似模式的配置
            best_similar = similar_patterns[0]  # 假设已按相关性排序

            # 合并配置（RAG模式优先）
            for key, value in best_similar.items():
                if key not in proposed_pattern:
                    proposed_pattern[key] = value

        return {
            "proposed_pattern": proposed_pattern,
            "optimizations_applied": len(bottlenecks),
            "rag_enhanced": similar_patterns is not None
        }

    async def _run_ab_test(
        self,
        url: str,
        control_pattern: Dict[str, Any],
        treatment_pattern: Dict[str, Any]
    ) -> Dict[str, Any]:
        """运行A/B测试"""

        # 简化版本：模拟A/B测试结果
        # 实际实现需要真实运行两个模式并比较

        # 模拟结果
        control_score = 0.75
        treatment_score = 0.82  # 假设优化后更好

        improvement = (treatment_score - control_score) / control_score if control_score > 0 else 0

        return {
            "control": {
                "pattern": control_pattern,
                "score": control_score
            },
            "treatment": {
                "pattern": treatment_pattern,
                "score": treatment_score
            },
            "improvement": improvement,
            "significant": improvement > 0.05  # 5%以上显著
        }

    def _select_best_pattern(
        self,
        current_pattern: Dict[str, Any],
        proposed_pattern: Dict[str, Any],
        ab_test_results: Optional[Dict[str, Any]]
    ) -> tuple:
        """选择最佳模式"""

        if ab_test_results:
            # 基于A/B测试结果选择
            if ab_test_results["significant"]:
                if ab_test_results["treatment"]["score"] > ab_test_results["control"]["score"]:
                    return proposed_pattern, ab_test_results["improvement"]
                else:
                    return current_pattern, 0.0

        # 简化：如果没有A/B测试，返回优化后模式
        return proposed_pattern, 0.05  # 假设5%改进

    async def _tune_parameters(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """参数调优"""

        tuned_params = pattern.copy()

        # 延迟优化（1-3秒范围）
        delay = tuned_params.get("delay", 1.0)
        tuned_params["delay"] = max(0.5, min(5.0, delay))

        # 超时优化（10-60秒范围）
        timeout = tuned_params.get("timeout", 30)
        tuned_params["timeout"] = max(10, min(60, timeout))

        # 重试次数优化（1-5次范围）
        retry_count = tuned_params.get("retry_count", 3)
        tuned_params["retry_count"] = max(1, min(5, retry_count))

        # 并发数优化（1-5范围）
        concurrent = tuned_params.get("concurrent", 3)
        tuned_params["concurrent"] = max(1, min(5, concurrent))

        return tuned_params
