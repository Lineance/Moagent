"""
测试BaseAgent基础功能
"""

import pytest
import asyncio
from moagent.agents.multi_agent.base import (
    BaseAgent, AgentConfig, Task, TaskResult, AgentStatus
)


class DummyAgent(BaseAgent):
    """测试用Agent"""

    async def execute(self, task: Task) -> TaskResult:
        """简单执行"""
        await asyncio.sleep(0.1)  # 模拟工作

        return TaskResult(
            task_id=task.task_id,
            agent_id=self.config.agent_id,
            success=True,
            data={"message": "success"},
            quality_score=0.95
        )


class FailingAgent(BaseAgent):
    """总是失败的Agent"""

    async def execute(self, task: Task) -> TaskResult:
        """总是抛出异常"""
        raise ValueError("Test error")


@pytest.mark.asyncio
async def test_agent_initialization():
    """测试Agent初始化"""

    config = AgentConfig(
        agent_id="test_agent",
        role="tester",
        capabilities=["test"]
    )

    agent = DummyAgent(config)

    assert agent.config.agent_id == "test_agent"
    assert agent.status == AgentStatus.IDLE
    assert agent.metrics["tasks_completed"] == 0


@pytest.mark.asyncio
async def test_agent_task_execution():
    """测试任务执行"""

    agent = DummyAgent(AgentConfig(
        agent_id="worker",
        role="worker",
        capabilities=["work"]
    ))

    task = Task(
        task_id="task_1",
        task_type="test",
        params={"data": "test"}
    )

    result = await agent.receive_task(task)

    assert result.success is True
    assert result.task_id == "task_1"
    assert result.agent_id == "worker"
    assert result.execution_time > 0
    assert result.quality_score == 0.95


@pytest.mark.asyncio
async def test_agent_metrics():
    """测试性能指标"""

    agent = DummyAgent(AgentConfig(
        agent_id="metrics_test",
        role="tester",
        capabilities=["test"]
    ))

    # 执行3个任务
    for i in range(3):
        task = Task(
            task_id=f"task_{i}",
            task_type="test",
            params={}
        )
        await agent.receive_task(task)

    # 检查指标
    assert agent.metrics["tasks_completed"] == 3
    assert agent.metrics["tasks_failed"] == 0
    assert agent.metrics["success_rate"] == 1.0
    assert agent.metrics["avg_execution_time"] > 0


@pytest.mark.asyncio
async def test_agent_error_handling():
    """测试错误处理"""

    agent = FailingAgent(AgentConfig(
        agent_id="failing_agent",
        role="tester",
        capabilities=["test"]
    ))

    task = Task(
        task_id="fail_task",
        task_type="test",
        params={}
    )

    result = await agent.receive_task(task)

    assert result.success is False
    assert result.error is not None
    assert "Test error" in result.error

    # 检查失败指标
    assert agent.metrics["tasks_failed"] == 1


@pytest.mark.asyncio
async def test_agent_status():
    """测试Agent状态"""

    agent = DummyAgent(AgentConfig(
        agent_id="status_test",
        role="tester",
        capabilities=["test"]
    ))

    # 初始状态
    assert agent.status == AgentStatus.IDLE

    # 执行任务时应该是BUSY
    task = Task(
        task_id="status_task",
        task_type="test",
        params={}
    )

    # 由于执行很快，状态变化可能看不出来
    # 但至少可以检查状态查询功能
    status = agent.get_status()
    assert status["agent_id"] == "status_test"
    assert status["role"] == "tester"
    assert "capabilities" in status
    assert "metrics" in status


@pytest.mark.asyncio
async def test_agent_execution_history():
    """测试执行历史"""

    agent = DummyAgent(AgentConfig(
        agent_id="history_test",
        role="tester",
        capabilities=["test"]
    ))

    # 执行几个任务
    for i in range(5):
        task = Task(
            task_id=f"history_{i}",
            task_type="test",
            params={}
        )
        await agent.receive_task(task)

    # 获取历史
    history = agent.get_execution_history(limit=3)

    assert len(history) == 3
    assert history[0].task_id == "history_2"
    assert history[1].task_id == "history_3"
    assert history[2].task_id == "history_4"


@pytest.mark.asyncio
async def test_agent_shutdown():
    """测试Agent关闭"""

    agent = DummyAgent(AgentConfig(
        agent_id="shutdown_test",
        role="tester",
        capabilities=["test"]
    ))

    await agent.shutdown()

    assert agent.status == AgentStatus.OFFLINE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
