"""
Explorer Agent - 网站结构探索Agent

负责探索网站结构、识别内容类型、发现分页机制、检测反爬虫措施。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..base import BaseAgent, AgentConfig, Task, TaskResult
from ....config.settings import Config
from ....crawlers import get_crawler
from ....parsers import get_parser

logger = logging.getLogger(__name__)


class ExplorerAgent(BaseAgent):
    """
    Explorer Agent - 探索网站结构

    职责:
    1. 访问目标URL
    2. 分析HTML结构
    3. 检测JavaScript渲染
    4. 提取链接和发现分页
    5. 检测反爬虫措施
    6. 生成初始爬取模式建议
    """

    def __init__(self, config: AgentConfig, system_config: Optional[Config] = None):
        """
        初始化Explorer Agent

        Args:
            config: Agent配置
            system_config: 系统配置（可选）
        """
        super().__init__(config)
        self.system_config = system_config or Config()

    async def execute(self, task: Task) -> TaskResult:
        """
        执行探索任务

        Args:
            task: 任务对象
                - url: 目标URL
                - depth: 探索深度（默认1）
                - timeout: 超时时间（默认30秒）

        Returns:
            TaskResult: 探索结果
        """
        url = task.params.get("url")
        depth = task.params.get("depth", 1)
        timeout = task.params.get("timeout", 30)

        logger.info(f"Explorer exploring URL: {url}, depth: {depth}")

        start_time = datetime.now()

        try:
            # Step 1: 使用现有crawler获取内容
            exploration_data = await self._fetch_url(url, timeout)

            # Step 2: 分析HTML结构
            structure = await self._analyze_structure(exploration_data)

            # Step 3: 检测JavaScript渲染
            js_analysis = await self._analyze_javascript(exploration_data)

            # Step 4: 提取链接
            links = await self._extract_links(exploration_data)

            # Step 5: 发现分页
            pagination = await self._discover_pagination(exploration_data, links)

            # Step 6: 检测反爬虫
            anti_scraping = await self._detect_anti_scraping(exploration_data)

            # Step 7: 生成模式建议
            pattern_suggestion = await self._generate_pattern(
                structure, pagination, js_analysis, url
            )

            # Step 8: 计算置信度
            confidence = self._calculate_confidence(
                structure, pagination, anti_scraping
            )

            result_data = {
                "url": url,
                "structure": structure,
                "javascript_analysis": js_analysis,
                "links_sample": links[:20] if links else [],  # 只保留前20个
                "pagination": pagination,
                "anti_scraping": anti_scraping,
                "pattern_suggestion": pattern_suggestion,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat(),
                "exploration_time": (datetime.now() - start_time).total_seconds()
            }

            logger.info(f"Exploration completed for {url} with confidence {confidence:.2%}")

            return TaskResult(
                task_id=task.task_id,
                agent_id=self.config.agent_id,
                success=True,
                data=result_data,
                quality_score=confidence
            )

        except Exception as e:
            logger.error(f"Exploration failed for {url}: {e}", exc_info=True)

            return TaskResult(
                task_id=task.task_id,
                agent_id=self.config.agent_id,
                success=False,
                data={},
                error=str(e)
            )

    async def _fetch_url(self, url: str, timeout: int) -> Dict[str, Any]:
        """使用现有crawler获取URL内容"""
        try:
            # 创建临时配置
            temp_config = Config(target_url=url, crawl_mode="auto")

            # 获取crawler
            crawler = get_crawler(temp_config)

            # 执行爬取（在异步上下文中运行同步代码）
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                crawler.crawl
            )

            # 返回探索数据
            return {
                "url": url,
                "results": results,
                "success": True,
                "item_count": len(results) if results else 0
            }

        except Exception as e:
            logger.error(f"Failed to fetch URL {url}: {e}")
            return {
                "url": url,
                "results": [],
                "success": False,
                "error": str(e),
                "item_count": 0
            }

    async def _analyze_structure(self, exploration_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析HTML结构"""
        results = exploration_data.get("results", [])

        if not results:
            return {
                "main_container": "unknown",
                "item_selector": "unknown",
                "title_selector": "unknown",
                "clarity_score": 0.0,
                "has_content": False
            }

        # 基于爬取结果分析结构
        # 这里简化处理，实际可以使用更复杂的HTML分析
        has_titles = any("title" in item and item["title"] for item in results)
        has_urls = any("url" in item and item["url"] for item in results)

        clarity_score = 0.5
        if has_titles:
            clarity_score += 0.3
        if has_urls:
            clarity_score += 0.2

        return {
            "main_container": "detected_by_crawler",
            "item_selector": "article",
            "title_selector": "h1, h2, h3",
            "clarity_score": min(clarity_score, 1.0),
            "has_content": len(results) > 0,
            "item_count": len(results)
        }

    async def _analyze_javascript(self, exploration_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析JavaScript使用情况"""
        # 简化版本：基于爬取结果推断
        success = exploration_data.get("success", False)
        item_count = exploration_data.get("item_count", 0)

        # 如果爬取成功且有内容，可能不需要JS渲染
        requires_js = not (success and item_count > 0)

        return {
            "requires_js": requires_js,
            "script_count": 0,  # 需要更详细的HTML分析
            "frameworks_detected": [],
            "suggested_crawler": "dynamic" if requires_js else "static"
        }

    async def _extract_links(self, exploration_data: Dict[str, Any]) -> list:
        """提取链接"""
        results = exploration_data.get("results", [])

        # 提取所有URL
        links = []
        for item in results:
            if "url" in item and item["url"]:
                links.append(item["url"])

        return links

    async def _discover_pagination(
        self,
        exploration_data: Dict[str, Any],
        links: list
    ) -> Dict[str, Any]:
        """发现分页机制"""
        results = exploration_data.get("results", [])

        # 简化版本：基于结果数量推断
        has_many_items = len(results) > 10
        has_next_links = any("next" in str(link).lower() for link in links)

        return {
            "has_pagination": has_many_items or has_next_links,
            "type": "detected_automatically",
            "selector": "auto",
            "max_pages": 10 if has_many_items else 1,
            "item_count": len(results)
        }

    async def _detect_anti_scraping(self, exploration_data: Dict[str, Any]) -> Dict[str, Any]:
        """检测反爬虫措施"""
        success = exploration_data.get("success", False)
        error = exploration_data.get("error", "")

        detected = []
        suggested_delay = 1.0

        # 基于错误信息检测
        if not success:
            if "403" in error or "forbidden" in error.lower():
                detected.append("user_agent_check")
                suggested_delay = 2.0
            elif "timeout" in error.lower() or "timed out" in error.lower():
                detected.append("rate_limiting")
                suggested_delay = 3.0

        return {
            "detected": len(detected) > 0,
            "measures": detected,
            "suggested_delay": suggested_delay
        }

    async def _generate_pattern(
        self,
        structure: Dict[str, Any],
        pagination: Dict[str, Any],
        js_analysis: Dict[str, Any],
        url: str
    ) -> Dict[str, Any]:
        """生成初始爬取模式建议"""
        crawler_type = js_analysis.get("suggested_crawler", "static")

        pattern = {
            "crawler": crawler_type,
            "target_url": url,
            "list_container": structure.get("main_container", "div.content"),
            "item_selector": structure.get("item_selector", "article"),
            "title": structure.get("title_selector", "h1, h2, h3"),
            "link": "a[href]",
            "delay": 1.5,
            "retry_count": 3,
            "max_pages": pagination.get("max_pages", 10)
        }

        return pattern

    def _calculate_confidence(
        self,
        structure: Dict[str, Any],
        pagination: Dict[str, Any],
        anti_scraping: Dict[str, Any]
    ) -> float:
        """计算探索结果置信度"""
        confidence = 0.5  # 基础置信度

        # 结构清晰度
        if structure.get("clarity_score", 0) > 0.8:
            confidence += 0.2

        # 内容存在
        if structure.get("has_content", False):
            confidence += 0.1

        # 分页检测
        if pagination.get("has_pagination"):
            confidence += 0.1

        # 反爬虫检测
        if not anti_scraping.get("detected"):
            confidence += 0.1

        return min(confidence, 1.0)
