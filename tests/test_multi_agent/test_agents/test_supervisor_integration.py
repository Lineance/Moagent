"""
测试核心Agent的集成
"""

import pytest
import asyncio

from moagent.agents.multi_agent.base import AgentConfig, Task
from moagent.agents.multi_agent.agents.explorer import ExplorerAgent
from moagent.agents.multi_agent.agents.analyst import AnalystAgent
from moagent.agents.multi_agent.agents.optimizer import OptimizerAgent
from moagent.agents.multi_agent.agents.validator import ValidatorAgent
from moagent.agents.multi_agent.agents.supervisor import SupervisorAgent


@pytest.mark.asyncio
async def test_explorer_agent():
    """测试Explorer Agent"""
    config = AgentConfig(
        agent_id="explorer_test",
        role="explorer",
        capabilities=["explore"]
    )

    agent = ExplorerAgent(config)

    task = Task(
        task_id="explore_test",
        task_type="explore_website",
        params={
            "url": "https://example.com",
            "depth": 1
        }
    )

    result = await agent.receive_task(task)

    assert result.success
    assert "structure" in result.data
    assert "pattern_suggestion" in result.data


@pytest.mark.asyncio
async def test_analyst_agent():
    """测试Analyst Agent"""
    config = AgentConfig(
        agent_id="analyst_test",
        role="analyst",
        capabilities=["analyze"]
    )

    agent = AnalystAgent(config)

    # 创建测试数据
    test_items = [
        {
            "title": "AI Breakthrough in 2024",
            "url": "https://example.com/ai-news",
            "content": "This is an article about AI developments."
        },
        {
            "title": "Technology Trends",
            "url": "https://example.com/tech",
            "content": "Latest in technology."
        }
    ]

    task = Task(
        task_id="analyze_test",
        task_type="analyze_content",
        params={
            "items": test_items,
            "keywords": ["AI", "technology"],
            "min_quality": 0.7
        }
    )

    result = await agent.receive_task(task)

    assert result.success
    assert "analyzed_items" in result.data
    assert "summary" in result.data
    assert len(result.data["analyzed_items"]) == 2


@pytest.mark.asyncio
async def test_validator_agent():
    """测试Validator Agent"""
    config = AgentConfig(
        agent_id="validator_test",
        role="validator",
        capabilities=["validate"]
    )

    agent = ValidatorAgent(config)

    # 创建测试数据
    test_items = [
        {
            "title": "Valid Article",
            "url": "https://example.com/article1",
            "content": "This is valid content with enough length."
        },
        {
            "title": "",  # 无效：缺少标题
            "url": "https://example.com/article2",
            "content": "Content"
        }
    ]

    task = Task(
        task_id="validate_test",
        task_type="validate_data",
        params={
            "items": test_items,
            "schema": agent._get_default_schema()
        }
    )

    result = await agent.receive_task(task)

    assert result.success
    assert "valid_items" in result.data
    assert "invalid_items" in result.data
    assert "report" in result.data


@pytest.mark.asyncio
async def test_supervisor_agent_basic():
    """测试Supervisor Agent（基础测试）"""
    config = AgentConfig(
        agent_id="supervisor_test",
        role="supervisor",
        capabilities=["coordinate"],
        timeout=300  # 5分钟超时
    )

    supervisor = SupervisorAgent(config, enable_rag=False)

    task = Task(
        task_id="supervisor_test",
        task_type="coordinate_workflow",
        params={
            "url": "https://example.com",
            "keywords": ["test"],
            "depth": 1,
            "enable_optimization": False  # 禁用优化以加快测试
        }
    )

    result = await supervisor.receive_task(task)

    assert result.success
    assert "final_result" in result.data
    assert "workflow_results" in result.data
    assert "agent_performance" in result.data

    # 验证工作流包含所有阶段
    workflow = result.data["workflow_results"]
    assert "exploration" in workflow
    assert "crawling" in workflow
    assert "analysis" in workflow
    assert "validation" in workflow

    # 清理
    await supervisor.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
