"""
AgentMessage - Agent间通信的消息格式
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import uuid


class MessageType(Enum):
    """消息类型枚举"""
    TASK = "task"  # 任务分配
    RESULT = "result"  # 结果返回
    QUERY = "query"  # 查询请求
    RESPONSE = "response"  # 查询响应
    EVENT = "event"  # 事件通知
    ERROR = "error"  # 错误报告
    STATUS = "status"  # 状态更新
    NEGOTIATE = "negotiate"  # 协商请求


@dataclass
class AgentMessage:
    """
    Agent间通信的标准消息格式

    Attributes:
        message_id: 唯一消息ID
        sender: 发送者Agent ID
        receiver: 接收者Agent ID (或"broadcast")
        timestamp: 发送时间戳
        message_type: 消息类型
        payload: 消息内容
        priority: 优先级 (1-10, 10为最高)
        ttl: 存活时间(秒)
        requires_response: 是否需要响应
        conversation_id: 对话ID (用于关联一系列消息)
        parent_message_id: 父消息ID (用于构建消息树)
        metadata: 额外元数据
    """

    message_id: str
    sender: str
    receiver: str
    timestamp: datetime
    message_type: MessageType
    payload: Dict[str, Any]
    priority: int = 5
    ttl: int = 3600
    requires_response: bool = False
    conversation_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())

    def is_expired(self) -> bool:
        """检查消息是否过期"""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > self.ttl

    def is_broadcast(self) -> bool:
        """检查是否为广播消息"""
        return self.receiver == "broadcast"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "timestamp": self.timestamp.isoformat(),
            "message_type": self.message_type.value,
            "payload": self.payload,
            "priority": self.priority,
            "ttl": self.ttl,
            "requires_response": self.requires_response,
            "conversation_id": self.conversation_id,
            "parent_message_id": self.parent_message_id,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """从字典创建"""
        return cls(
            message_id=data["message_id"],
            sender=data["sender"],
            receiver=data["receiver"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            message_type=MessageType(data["message_type"]),
            payload=data["payload"],
            priority=data.get("priority", 5),
            ttl=data.get("ttl", 3600),
            requires_response=data.get("requires_response", False),
            conversation_id=data.get("conversation_id"),
            parent_message_id=data.get("parent_message_id"),
            metadata=data.get("metadata", {})
        )


@dataclass
class TaskMessage(AgentMessage):
    """任务消息"""

    def __init__(
        self,
        sender: str,
        receiver: str,
        task_id: str,
        task_type: str,
        params: Dict[str, Any],
        **kwargs
    ):
        super().__init__(
            message_id=task_id,
            sender=sender,
            receiver=receiver,
            timestamp=datetime.now(),
            message_type=MessageType.TASK,
            payload={
                "task_type": task_type,
                "params": params
            },
            **kwargs
        )


@dataclass
class ResultMessage(AgentMessage):
    """结果消息"""

    def __init__(
        self,
        sender: str,
        receiver: str,
        original_task_id: str,
        result: Dict[str, Any],
        success: bool,
        **kwargs
    ):
        super().__init__(
            message_id=str(uuid.uuid4()),
            sender=sender,
            receiver=receiver,
            timestamp=datetime.now(),
            message_type=MessageType.RESULT,
            payload={
                "original_task_id": original_task_id,
                "result": result,
                "success": success
            },
            **kwargs
        )
