"""
BaseAgent - 所有Agent的抽象基类

定义了Agent的核心接口和通用功能。
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent状态枚举"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class AgentConfig:
    """Agent配置"""
    agent_id: str
    role: str
    capabilities: List[str]
    timeout: int = 30
    max_retries: int = 3
    enable_logging: bool = True


@dataclass
class Task:
    """任务定义"""
    task_id: str
    task_type: str
    params: Dict[str, Any]
    priority: int = 5
    timeout: Optional[int] = None
    depends_on: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    agent_id: str
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    execution_time: float = 0.0
    quality_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    所有Agent的抽象基类

    提供通用功能:
    - 任务接收和执行
    - 消息通信
    - 状态管理
    - 日志记录
    - 错误处理
    """

    def __init__(self, config: AgentConfig):
        """
        初始化Agent

        Args:
            config: Agent配置
        """
        self.config = config
        self.status = AgentStatus.IDLE
        self.message_queue = asyncio.Queue()
        self.execution_history: List[TaskResult] = []

        # 性能指标
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_execution_time": 0.0,
            "success_rate": 1.0
        }

        logger.info(f"Agent {config.agent_id} initialized as {config.role}")

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """
        执行任务 (抽象方法，子类必须实现)

        Args:
            task: 任务对象

        Returns:
            TaskResult: 执行结果
        """
        pass

    async def receive_task(self, task: Task) -> TaskResult:
        """
        接收并执行任务

        Args:
            task: 任务对象

        Returns:
            TaskResult: 执行结果
        """
        if self.status == AgentStatus.BUSY:
            logger.warning(f"Agent {self.config.agent_id} is busy, queuing task")

        self.status = AgentStatus.BUSY
        start_time = datetime.now()

        try:
            logger.info(
                f"Agent {self.config.agent_id} executing task {task.task_id}"
            )

            # 执行任务
            result = await self.execute(task)

            # 更新指标
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            result.agent_id = self.config.agent_id

            self._update_metrics(result)
            self.execution_history.append(result)

            logger.info(
                f"Agent {self.config.agent_id} completed task {task.task_id} "
                f"in {execution_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(
                f"Agent {self.config.agent_id} failed task {task.task_id}: {e}"
            )

            result = TaskResult(
                task_id=task.task_id,
                agent_id=self.config.agent_id,
                success=False,
                data={},
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            )

            self._update_metrics(result)
            self.execution_history.append(result)
            return result

        finally:
            self.status = AgentStatus.IDLE

    async def send_message(self, message: 'AgentMessage'):
        """
        发送消息给其他Agent

        Args:
            message: 消息对象
        """
        # 这个方法将在通信层实现
        pass

    async def receive_message(self, message: 'AgentMessage'):
        """
        接收来自其他Agent的消息

        Args:
            message: 消息对象
        """
        await self.message_queue.put(message)

        # 处理消息
        await self._handle_message(message)

    async def _handle_message(self, message: 'AgentMessage'):
        """
        处理接收到的消息

        Args:
            message: 消息对象
        """
        from .message import MessageType, TaskMessage

        if message.message_type == MessageType.TASK:
            # 转换为Task并执行
            task = Task(
                task_id=message.message_id,
                task_type=message.payload.get("task_type", "unknown"),
                params=message.payload.get("params", {})
            )
            result = await self.receive_task(task)

            # 如果需要回复
            if message.requires_response:
                from .message import ResultMessage
                response = ResultMessage(
                    sender=self.config.agent_id,
                    receiver=message.sender,
                    original_task_id=message.message_id,
                    result=result.to_dict() if hasattr(result, 'to_dict') else {"success": result.success},
                    success=result.success
                )
                await self.send_message(response)

    def _update_metrics(self, result: TaskResult):
        """
        更新性能指标

        Args:
            result: 任务结果
        """
        if result.success:
            self.metrics["tasks_completed"] += 1
        else:
            self.metrics["tasks_failed"] += 1

        total = self.metrics["tasks_completed"] + self.metrics["tasks_failed"]
        self.metrics["success_rate"] = self.metrics["tasks_completed"] / total if total > 0 else 0

        # 更新平均执行时间
        if self.metrics["tasks_completed"] > 0:
            current_avg = self.metrics["avg_execution_time"]
            n = self.metrics["tasks_completed"]
            self.metrics["avg_execution_time"] = (
                (current_avg * (n - 1) + result.execution_time) / n
            )

    def get_status(self) -> Dict[str, Any]:
        """
        获取Agent状态

        Returns:
            状态字典
        """
        return {
            "agent_id": self.config.agent_id,
            "role": self.config.role,
            "status": self.status.value,
            "capabilities": self.config.capabilities,
            "metrics": self.metrics,
            "queue_size": self.message_queue.qsize()
        }

    def get_execution_history(self, limit: int = 10) -> List[TaskResult]:
        """
        获取执行历史

        Args:
            limit: 返回数量限制

        Returns:
            执行历史列表
        """
        return self.execution_history[-limit:]

    async def shutdown(self):
        """关闭Agent"""
        logger.info(f"Agent {self.config.agent_id} shutting down")
        self.status = AgentStatus.OFFLINE


# 为TaskResult添加to_dict方法
def _task_result_to_dict(self) -> Dict[str, Any]:
    """转换为字典"""
    return {
        "task_id": self.task_id,
        "agent_id": self.agent_id,
        "success": self.success,
        "data": self.data,
        "error": self.error,
        "execution_time": self.execution_time,
        "quality_score": self.quality_score,
        "metadata": self.metadata
    }


TaskResult.to_dict = _task_result_to_dict
