"""
Analyst Agent - 内容分析Agent

负责分析内容质量、相关性、去重和分类。
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base import BaseAgent, AgentConfig, Task, TaskResult
from ....storage import get_storage
from ....config.settings import Config

logger = logging.getLogger(__name__)


class AnalystAgent(BaseAgent):
    """
    Analyst Agent - 分析内容质量

    职责:
    1. 关键词相关性分析
    2. 内容质量评分
    3. 去重检测
    4. 垃圾内容过滤
    5. 内容分类
    """

    def __init__(self, config: AgentConfig, system_config: Optional[Config] = None):
        """
        初始化Analyst Agent

        Args:
            config: Agent配置
            system_config: 系统配置（可选）
        """
        super().__init__(config)
        self.system_config = system_config or Config()

        # 初始化storage用于去重检测
        try:
            self.storage = get_storage(self.system_config)
        except Exception as e:
            logger.warning(f"Failed to initialize storage: {e}")
            self.storage = None

    async def execute(self, task: Task) -> TaskResult:
        """
        执行分析任务

        Args:
            task: 任务对象
                - items: 要分析的项目列表
                - keywords: 目标关键词列表
                - min_quality: 最低质量阈值（默认0.7）

        Returns:
            TaskResult: 分析结果
        """
        items = task.params.get("items", [])
        keywords = task.params.get("keywords", [])
        min_quality = task.params.get("min_quality", 0.7)

        logger.info(f"Analyst analyzing {len(items)} items with keywords: {keywords}")

        if not items:
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.config.agent_id,
                success=True,
                data={
                    "analyzed_items": [],
                    "summary": {
                        "total_items": 0,
                        "kept_items": 0,
                        "filtered_items": 0,
                        "avg_quality": 0.0,
                        "categories": {}
                    }
                },
                quality_score=1.0
            )

        try:
            analyzed_items = []

            for item in items:
                # 分析单个项目
                analysis = await self._analyze_item(item, keywords, min_quality)
                analyzed_items.append(analysis)

            # 生成总结
            summary = self._generate_summary(analyzed_items)

            logger.info(
                f"Analysis completed: {summary['kept_items']}/{summary['total_items']} items kept"
            )

            return TaskResult(
                task_id=task.task_id,
                agent_id=self.config.agent_id,
                success=True,
                data={
                    "analyzed_items": analyzed_items,
                    "summary": summary
                },
                quality_score=summary["avg_quality"]
            )

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)

            return TaskResult(
                task_id=task.task_id,
                agent_id=self.config.agent_id,
                success=False,
                data={},
                error=str(e)
            )

    async def _analyze_item(
        self,
        item: Dict[str, Any],
        keywords: List[str],
        min_quality: float
    ) -> Dict[str, Any]:
        """分析单个项目"""

        # Step 1: 关键词相关性
        keyword_score = self._calculate_keyword_relevance(item, keywords)

        # Step 2: 质量评分
        quality_score = self._assess_quality(item)

        # Step 3: 去重检查
        is_duplicate = await self._check_duplicate(item)

        # Step 4: 垃圾检测
        is_spam = self._check_spam(item)

        # Step 5: 内容分类
        category = self._classify_content(item)

        # 综合评分
        overall_score = (
            keyword_score * 0.3 +
            quality_score * 0.4 +
            (0.0 if is_duplicate else 0.2) +
            (0.0 if is_spam else 0.1)
        )

        # 判断是否保留
        should_keep = (
            overall_score >= min_quality and
            not is_duplicate and
            not is_spam
        )

        return {
            "item": item,
            "keyword_score": keyword_score,
            "quality_score": quality_score,
            "is_duplicate": is_duplicate,
            "is_spam": is_spam,
            "category": category,
            "overall_score": overall_score,
            "should_keep": should_keep
        }

    def _calculate_keyword_relevance(self, item: Dict[str, Any], keywords: List[str]) -> float:
        """计算关键词相关性"""
        if not keywords:
            return 0.5

        # 获取文本内容
        text = self._extract_text(item)
        text_lower = text.lower()

        # 计算匹配分数
        matches = 0
        for keyword in keywords:
            if keyword.lower() in text_lower:
                matches += 1

        return matches / len(keywords) if keywords else 0.5

    def _assess_quality(self, item: Dict[str, Any]) -> float:
        """评估内容质量"""
        score = 0.5  # 基础分数

        # 检查标题
        title = item.get("title", "")
        if title and len(title) > 10:
            score += 0.2

        # 检查URL
        url = item.get("url", "")
        if url and url.startswith("http"):
            score += 0.1

        # 检查内容
        content = item.get("content", "")
        if content and len(content) > 50:
            score += 0.2

        return min(score, 1.0)

    async def _check_duplicate(self, item: Dict[str, Any]) -> bool:
        """检查重复"""
        if not self.storage:
            return False

        try:
            # 生成项目的哈希
            url = item.get("url", "")
            title = item.get("title", "")

            if not url or not title:
                return False

            # 使用storage的hash生成方法
            hash_str = self.storage._generate_item_hash({"url": url, "title": title})

            # 这里简化处理，实际应该查询数据库
            # 由于这是异步操作，我们在实际使用时需要实现
            return False

        except Exception as e:
            logger.warning(f"Duplicate check failed: {e}")
            return False

    def _check_spam(self, item: Dict[str, Any]) -> bool:
        """检测垃圾内容"""
        # 简化版本的垃圾检测

        # 检查标题
        title = item.get("title", "")

        # 常见垃圾关键词
        spam_keywords = [
            "advertisement", "click here", "buy now",
            "免费", "点击", "广告"
        ]

        title_lower = title.lower() if title else ""

        for keyword in spam_keywords:
            if keyword in title_lower:
                return True

        return False

    def _classify_content(self, item: Dict[str, Any]) -> str:
        """分类内容"""
        title = item.get("title", "")
        content = item.get("content", "")
        text = f"{title} {content}".lower()

        # 简单的关键词分类
        categories = {
            "technology": ["ai", "tech", "软件", "技术"],
            "business": ["business", "经济", "财经"],
            "science": ["science", "科学", "研究"],
            "general": []
        }

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text:
                    return category

        return "general"

    def _extract_text(self, item: Dict[str, Any]) -> str:
        """提取文本内容"""
        parts = []

        if "title" in item:
            parts.append(str(item["title"]))

        if "content" in item:
            parts.append(str(item["content"]))

        return " ".join(parts)

    def _generate_summary(self, analyzed_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成分析总结"""
        total = len(analyzed_items)
        kept = sum(1 for item in analyzed_items if item["should_keep"])
        filtered = total - kept

        # 计算平均质量
        avg_quality = sum(item["overall_score"] for item in analyzed_items) / total if total > 0 else 0

        # 统计分类
        categories = {}
        for item in analyzed_items:
            category = item["category"]
            categories[category] = categories.get(category, 0) + 1

        return {
            "total_items": total,
            "kept_items": kept,
            "filtered_items": filtered,
            "avg_quality": avg_quality,
            "categories": categories
        }
