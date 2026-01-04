"""
AgentCommunication - Agent间通信层
"""

import asyncio
import logging
from typing import Dict, Set, List, Optional, Any
from collections import defaultdict
from datetime import datetime

from .message import AgentMessage, MessageType
from .base import AgentStatus

logger = logging.getLogger(__name__)


class AgentCommunication:
    """
    Agent通信层

    提供:
    - 点对点通信 (P2P)
    - 发布订阅 (PubSub)
    - 广播 (Broadcast)
    - 协商 (Negotiation)
    """

    def __init__(self):
        """初始化通信层"""
        # Agent消息队列 (agent_id -> queue)
        self.agent_queues: Dict[str, asyncio.Queue] = {}

        # 发布订阅 (topic -> set of subscribers)
        self.pubsub_topics: Dict[str, Set[str]] = defaultdict(set)

        # 活跃Agent注册表
        self.active_agents: Dict[str, AgentStatus] = {}

        # 消息日志
        self.message_log: List[AgentMessage] = []

        # 统计
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_broadcast": 0,
            "messages_published": 0
        }

    def register_agent(self, agent_id: str):
        """
        注册Agent

        Args:
            agent_id: Agent ID
        """
        if agent_id not in self.agent_queues:
            self.agent_queues[agent_id] = asyncio.Queue()
            self.active_agents[agent_id] = AgentStatus.IDLE
            logger.info(f"Agent {agent_id} registered")

    def unregister_agent(self, agent_id: str):
        """
        注销Agent

        Args:
            agent_id: Agent ID
        """
        if agent_id in self.agent_queues:
            del self.agent_queues[agent_id]
        if agent_id in self.active_agents:
            del self.active_agents[agent_id]

        # 从所有订阅中移除
        for topic in self.pubsub_topics:
            self.pubsub_topics[topic].discard(agent_id)

        logger.info(f"Agent {agent_id} unregistered")

    async def send_message(self, message: AgentMessage) -> bool:
        """
        发送消息 (点对点)

        Args:
            message: 消息对象

        Returns:
            是否发送成功
        """
        # 检查消息是否过期
        if message.is_expired():
            logger.warning(f"Message {message.message_id} expired, discarding")
            return False

        # 验证接收者
        if message.receiver not in self.active_agents:
            logger.error(f"Receiver {message.receiver} not found")
            return False

        # 添加到接收者队列
        try:
            await self.agent_queues[message.receiver].put(message)
            self.stats["messages_sent"] += 1
            self.message_log.append(message)

            logger.debug(
                f"Message sent: {message.sender} -> {message.receiver}, "
                f"type={message.message_type.value}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def receive_message(
        self,
        agent_id: str,
        timeout: float = 1.0
    ) -> Optional[AgentMessage]:
        """
        接收消息

        Args:
            agent_id: Agent ID
            timeout: 超时时间(秒)

        Returns:
            消息对象或None
        """
        queue = self.agent_queues.get(agent_id)

        if not queue:
            logger.error(f"No queue found for agent {agent_id}")
            return None

        try:
            message = await asyncio.wait_for(queue.get(), timeout=timeout)
            self.stats["messages_received"] += 1
            return message

        except asyncio.TimeoutError:
            return None

    async def broadcast(self, message: AgentMessage):
        """
        广播消息给所有Agent

        Args:
            message: 消息对象 (receiver会被忽略)
        """
        receivers = list(self.active_agents.keys())

        # 过滤掉发送者自己
        if message.sender in receivers:
            receivers.remove(message.sender)

        # 发送给所有接收者
        for receiver_id in receivers:
            message_copy = AgentMessage(
                message_id=message.message_id,
                sender=message.sender,
                receiver=receiver_id,
                timestamp=message.timestamp,
                message_type=message.message_type,
                payload=message.payload.copy(),
                priority=message.priority,
                ttl=message.ttl
            )

            await self.send_message(message_copy)

        self.stats["messages_broadcast"] += 1
        logger.info(
            f"Broadcast from {message.sender} to {len(receivers)} agents"
        )

    async def publish(self, topic: str, message: AgentMessage):
        """
        发布消息到主题

        Args:
            topic: 主题名称
            message: 消息对象
        """
        subscribers = self.pubsub_topics.get(topic, set())

        if not subscribers:
            logger.debug(f"No subscribers for topic {topic}")
            return

        # 发送给所有订阅者
        for subscriber_id in subscribers:
            message_copy = AgentMessage(
                message_id=message.message_id,
                sender=message.sender,
                receiver=subscriber_id,
                timestamp=message.timestamp,
                message_type=message.message_type,
                payload=message.payload.copy(),
                priority=message.priority,
                ttl=message.ttl
            )

            await self.send_message(message_copy)

        self.stats["messages_published"] += 1
        logger.info(
            f"Published to topic '{topic}': {len(subscribers)} subscribers"
        )

    async def subscribe(self, agent_id: str, topic: str):
        """
        订阅主题

        Args:
            agent_id: Agent ID
            topic: 主题名称
        """
        if agent_id not in self.active_agents:
            logger.warning(f"Cannot subscribe: agent {agent_id} not registered")
            return

        self.pubsub_topics[topic].add(agent_id)
        logger.info(f"Agent {agent_id} subscribed to topic '{topic}'")

    async def unsubscribe(self, agent_id: str, topic: str):
        """
        取消订阅

        Args:
            agent_id: Agent ID
            topic: 主题名称
        """
        if topic in self.pubsub_topics:
            self.pubsub_topics[topic].discard(agent_id)
            logger.info(f"Agent {agent_id} unsubscribed from topic '{topic}'")

    def get_queue_size(self, agent_id: str) -> int:
        """
        获取Agent队列大小

        Args:
            agent_id: Agent ID

        Returns:
            队列大小
        """
        queue = self.agent_queues.get(agent_id)
        return queue.qsize() if queue else 0

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取通信统计

        Returns:
            统计信息字典
        """
        return {
            **self.stats,
            "active_agents": len(self.active_agents),
            "total_queues": len(self.agent_queues),
            "total_topics": len(self.pubsub_topics),
            "message_log_size": len(self.message_log)
        }

    async def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up communication layer")

        # 清空所有队列
        for queue in self.agent_queues.values():
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

        # 清空注册表
        self.agent_queues.clear()
        self.active_agents.clear()
        self.pubsub_topics.clear()

        logger.info("Communication layer cleaned up")
