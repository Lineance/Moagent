"""
Validator Agent - 数据验证Agent

负责验证数据格式、一致性、完整性和准确性。
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from ..base import BaseAgent, AgentConfig, Task, TaskResult
from ....config.settings import Config

logger = logging.getLogger(__name__)


class ValidatorAgent(BaseAgent):
    """
    Validator Agent - 验证数据质量

    职责:
    1. 验证数据格式
    2. 检查一致性
    3. 验证完整性
    4. 评估准确性
    5. 生成验证报告
    """

    def __init__(self, config: AgentConfig, system_config: Optional[Config] = None):
        """
        初始化Validator Agent

        Args:
            config: Agent配置
            system_config: 系统配置（可选）
        """
        super().__init__(config)
        self.system_config = system_config or Config()

    async def execute(self, task: Task) -> TaskResult:
        """
        执行验证任务

        Args:
            task: 任务对象
                - items: 要验证的项目列表
                - schema: 数据模式定义
                    - required: 必需字段列表
                    - types: 字段类型映射
                    - validators: 自定义验证器（可选）

        Returns:
            TaskResult: 验证结果
        """
        items = task.params.get("items", [])
        schema = task.params.get("schema", self._get_default_schema())

        logger.info(f"Validator validating {len(items)} items")

        if not items:
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.config.agent_id,
                success=True,
                data={
                    "validation_results": [],
                    "valid_items": [],
                    "invalid_items": [],
                    "issues": [],
                    "report": self._create_empty_report()
                },
                quality_score=1.0
            )

        try:
            validation_results = []
            issues = []

            for item in items:
                # 验证单个项目
                result = await self._validate_item(item, schema)
                validation_results.append(result)

                # 收集问题
                if not result["valid"]:
                    issues.extend(result["issues"])

            # 分离有效和无效项目
            valid_items = [
                r["item"] for r in validation_results if r["valid"]
            ]
            invalid_items = [
                r for r in validation_results if not r["valid"]
            ]

            # 生成报告
            report = self._generate_report(validation_results, schema)

            logger.info(
                f"Validation completed: {report['valid_count']}/{report['total_items']} valid"
            )

            return TaskResult(
                task_id=task.task_id,
                agent_id=self.config.agent_id,
                success=True,
                data={
                    "validation_results": validation_results,
                    "valid_items": valid_items,
                    "invalid_items": invalid_items,
                    "issues": issues,
                    "report": report
                },
                quality_score=report["validation_rate"]
            )

        except Exception as e:
            logger.error(f"Validation failed: {e}", exc_info=True)

            return TaskResult(
                task_id=task.task_id,
                agent_id=self.config.agent_id,
                success=False,
                data={},
                error=str(e)
            )

    async def _validate_item(
        self,
        item: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证单个项目"""

        issues = []

        # Step 1: 格式验证
        format_valid, format_score, format_errors = self._validate_format(item, schema)
        if not format_valid:
            issues.extend(format_errors)

        # Step 2: 一致性检查
        consistency_score, consistency_issues = self._check_consistency(item)
        if consistency_issues:
            issues.extend(consistency_issues)

        # Step 3: 完整性检查
        completeness_score, completeness_issues = self._check_completeness(item, schema)
        if completeness_issues:
            issues.extend(completeness_issues)

        # Step 4: 准确性验证
        accuracy_score, accuracy_issues = await self._verify_accuracy(item)
        if accuracy_issues:
            issues.extend(accuracy_issues)

        # 综合评分
        validation_score = (
            format_score * 0.2 +
            consistency_score * 0.3 +
            completeness_score * 0.3 +
            accuracy_score * 0.2
        )

        is_valid = validation_score >= 0.8

        return {
            "item": item,
            "valid": is_valid,
            "score": validation_score,
            "issues": issues if not is_valid else [],
            "breakdown": {
                "format": {"valid": format_valid, "score": format_score},
                "consistency": {"score": consistency_score, "issues": consistency_issues},
                "completeness": {"score": completeness_score, "missing": completeness_issues},
                "accuracy": {"score": accuracy_score, "issues": accuracy_issues}
            }
        }

    def _validate_format(
        self,
        item: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> tuple:
        """验证数据格式"""
        errors = []
        score = 1.0

        type_mapping = schema.get("types", {})
        required_fields = schema.get("required", [])

        # 检查必需字段
        for field in required_fields:
            if field not in item or not item[field]:
                errors.append(f"Missing required field: {field}")
                score -= 0.3

        # 检查字段类型
        for field, expected_type in type_mapping.items():
            if field in item and item[field]:
                if not self._check_type(item[field], expected_type):
                    errors.append(f"Invalid type for {field}: expected {expected_type}")
                    score -= 0.1

        return len(errors) == 0, max(score, 0.0), errors

    def _check_consistency(self, item: Dict[str, Any]) -> tuple:
        """检查一致性"""
        issues = []
        score = 1.0

        # 检查URL一致性
        if "url" in item and item["url"]:
            url = item["url"]
            if not url.startswith(("http://", "https://")):
                issues.append(f"Invalid URL format: {url}")
                score -= 0.3

        # 检查标题和内容一致性
        title = item.get("title", "")
        content = item.get("content", "")

        if title and content:
            # 如果标题太短但内容很长，可能不一致
            if len(title) < 5 and len(content) > 100:
                issues.append("Title too short compared to content")
                score -= 0.1

        return max(score, 0.0), issues

    def _check_completeness(
        self,
        item: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> tuple:
        """检查完整性"""
        missing = []
        score = 1.0

        required_fields = schema.get("required", [])

        for field in required_fields:
            if field not in item or not item[field]:
                missing.append(field)
                score -= 0.2

        # 检查推荐字段
        recommended_fields = schema.get("recommended", [])
        for field in recommended_fields:
            if field not in item or not item[field]:
                score -= 0.05  # 轻微惩罚

        return max(score, 0.0), missing

    async def _verify_accuracy(self, item: Dict[str, Any]) -> tuple:
        """验证准确性"""
        issues = []
        score = 1.0

        # 检查URL有效性
        if "url" in item:
            url = item["url"]
            if url and "example.com" in url:
                issues.append(f"URL contains placeholder: {url}")
                score -= 0.2

        # 检查标题是否为空或占位符
        if "title" in item:
            title = item["title"]
            if not title or title.lower() in ["null", "undefined", "n/a"]:
                issues.append("Title is empty or placeholder")
                score -= 0.3

        # 检查内容长度
        if "content" in item:
            content = item["content"]
            if content and len(content) < 20:
                issues.append("Content too short")
                score -= 0.1

        return max(score, 0.0), issues

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """检查类型"""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "url":
            return isinstance(value, str) and value.startswith(("http://", "https://"))
        elif expected_type == "datetime":
            # 简化检查
            return isinstance(value, (str, datetime))
        elif expected_type == "int":
            return isinstance(value, int)
        else:
            return True  # 未知类型，跳过检查

    def _generate_report(
        self,
        validation_results: List[Dict[str, Any]],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成验证报告"""
        total = len(validation_results)
        valid = sum(1 for r in validation_results if r["valid"])
        invalid = total - valid

        # 计算平均分数
        avg_score = sum(r["score"] for r in validation_results) / total if total > 0 else 0

        # 统计常见问题
        common_issues = {}
        for result in validation_results:
            for issue in result.get("issues", []):
                # 简化问题类型
                issue_type = issue.split(":")[0] if ":" in issue else issue
                common_issues[issue_type] = common_issues.get(issue_type, 0) + 1

        return {
            "total_items": total,
            "valid_count": valid,
            "invalid_count": invalid,
            "validation_rate": valid / total if total > 0 else 0,
            "avg_score": avg_score,
            "common_issues": common_issues,
            "schema_used": schema.get("name", "default")
        }

    def _create_empty_report(self) -> Dict[str, Any]:
        """创建空报告"""
        return {
            "total_items": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "validation_rate": 1.0,
            "avg_score": 1.0,
            "common_issues": {},
            "schema_used": "default"
        }

    def _get_default_schema(self) -> Dict[str, Any]:
        """获取默认模式"""
        return {
            "name": "default_news_schema",
            "required": ["title", "url"],
            "recommended": ["content", "pub_date"],
            "types": {
                "title": "string",
                "url": "url",
                "content": "string",
                "pub_date": "datetime"
            }
        }
