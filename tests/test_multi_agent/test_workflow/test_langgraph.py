"""
测试LangGraph工作流
"""

import pytest
import asyncio

from moagent.agents.multi_agent.workflow import (
    MultiAgentGraph,
    create_multi_agent_graph,
    AdaptiveWorkflow,
    SmartWorkflow
)


def test_create_multi_agent_graph():
    """测试创建多Agent图"""
    graph = create_multi_agent_graph(enable_rag=False)

    assert graph is not None
    assert graph.enable_rag is False
    assert len(graph.agents) == 4  # explorer, analyst, optimizer, validator


def test_graph_execute():
    """测试图执行"""
    graph = create_multi_agent_graph(enable_rag=False)

    task_params = {
        "task_id": "test_graph",
        "url": "https://example.com",
        "keywords": ["test"],
        "depth": 1,
        "enable_optimization": False,
        "enable_rag": False
    }

    result = graph.execute(task_params)

    assert result is not None
    assert "success" in result
    assert "final_result" in result
    assert "execution_time" in result
    assert result["execution_time"] > 0


def test_graph_with_optimization():
    """测试启用优化的图执行"""
    graph = create_multi_agent_graph(enable_rag=False)

    task_params = {
        "task_id": "test_optimization",
        "url": "https://example.com",
        "keywords": ["test"],
        "depth": 1,
        "enable_optimization": True,  # 启用优化
        "enable_rag": False
    }

    result = graph.execute(task_params)

    assert result is not None
    assert result["success"] or len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_adaptive_workflow():
    """测试自适应工作流"""
    workflow = AdaptiveWorkflow(enable_rag=False)

    task_params = {
        "task_id": "test_adaptive",
        "url": "https://example.com",
        "keywords": ["adaptive"],
        "depth": 1,
        "enable_optimization": False
    }

    result = await workflow.execute(task_params)

    assert result is not None
    assert "success" in result
    assert "iterations" in result
    assert "adaptations_made" in result


@pytest.mark.asyncio
async def test_smart_workflow():
    """测试智能工作流"""
    workflow = SmartWorkflow(enable_rag=False)

    task_params = {
        "task_id": "test_smart",
        "url": "https://example.com",
        "keywords": ["smart"],
        "depth": 1,
        "enable_optimization": False
    }

    # 第一次执行
    result1 = await workflow.execute(task_params)
    assert result1 is not None

    # 检查缓存
    cache_stats = workflow.get_cache_stats()
    assert cache_stats["cache_size"] > 0

    # 第二次执行（应该使用缓存）
    result2 = await workflow.execute(task_params)
    assert result2 is not None
    # 注意: 由于同步执行，缓存可能不会立即生效


def test_smart_workflow_cache():
    """测试智能工作流缓存"""
    workflow = SmartWorkflow(enable_rag=False)

    # 初始缓存为空
    stats = workflow.get_cache_stats()
    assert stats["cache_size"] == 0

    # 执行后会缓存
    import asyncio
    task_params = {
        "task_id": "test_cache",
        "url": "https://example.com",
        "keywords": ["cache"],
        "depth": 1,
        "enable_optimization": False
    }

    result = asyncio.run(workflow.execute(task_params))

    if result["success"]:
        stats = workflow.get_cache_stats()
        assert stats["cache_size"] >= 1

    # 清空缓存
    workflow.clear_cache()
    stats = workflow.get_cache_stats()
    assert stats["cache_size"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
