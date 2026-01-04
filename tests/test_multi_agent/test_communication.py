"""
测试AgentCommunication通信层
"""

import pytest
import asyncio
from datetime import datetime

from moagent.agents.multi_agent.communication import AgentCommunication
from moagent.agents.multi_agent.message import (
    AgentMessage, MessageType, TaskMessage, ResultMessage
)
from moagent.agents.multi_agent.base import AgentStatus


@pytest.mark.asyncio
async def test_communication_initialization():
    """测试通信层初始化"""

    comm = AgentCommunication()

    assert len(comm.active_agents) == 0
    assert len(comm.agent_queues) == 0
    assert comm.stats["messages_sent"] == 0


@pytest.mark.asyncio
async def test_agent_registration():
    """测试Agent注册"""

    comm = AgentCommunication()

    # 注册Agent
    comm.register_agent("agent_1")
    comm.register_agent("agent_2")

    assert "agent_1" in comm.active_agents
    assert "agent_2" in comm.active_agents
    assert comm.active_agents["agent_1"] == AgentStatus.IDLE

    # 检查队列
    assert "agent_1" in comm.agent_queues
    assert "agent_2" in comm.agent_queues


@pytest.mark.asyncio
async def test_agent_unregister():
    """测试Agent注销"""

    comm = AgentCommunication()

    # 注册并订阅
    comm.register_agent("agent_1")
    await comm.subscribe("agent_1", "test_topic")

    # 注销
    comm.unregister_agent("agent_1")

    assert "agent_1" not in comm.active_agents
    assert "agent_1" not in comm.agent_queues
    # 订阅也应该被移除
    assert "agent_1" not in comm.pubsub_topics.get("test_topic", set())


@pytest.mark.asyncio
async def test_send_message():
    """测试点对点消息发送"""

    comm = AgentCommunication()

    # 注册Agent
    comm.register_agent("sender")
    comm.register_agent("receiver")

    # 创建消息
    message = AgentMessage(
        message_id="msg_1",
        sender="sender",
        receiver="receiver",
        timestamp=datetime.now(),
        message_type=MessageType.TASK,
        payload={"test": "data"}
    )

    # 发送
    success = await comm.send_message(message)

    assert success is True
    assert comm.stats["messages_sent"] == 1

    # 接收
    received = await comm.receive_message("receiver")

    assert received is not None
    assert received.message_id == "msg_1"
    assert received.sender == "sender"
    assert received.receiver == "receiver"


@pytest.mark.asyncio
async def test_send_to_unknown_agent():
    """测试发送给不存在的Agent"""

    comm = AgentCommunication()

    comm.register_agent("sender")

    message = AgentMessage(
        message_id="msg_fail",
        sender="sender",
        receiver="unknown",
        timestamp=datetime.now(),
        message_type=MessageType.TASK,
        payload={}
    )

    success = await comm.send_message(message)

    assert success is False


@pytest.mark.asyncio
async def test_broadcast_message():
    """测试广播消息"""

    comm = AgentCommunication()

    # 注册多个Agent
    comm.register_agent("broadcaster")
    comm.register_agent("listener_1")
    comm.register_agent("listener_2")
    comm.register_agent("listener_3")

    # 广播消息
    message = AgentMessage(
        message_id="broadcast_1",
        sender="broadcaster",
        receiver="broadcast",
        timestamp=datetime.now(),
        message_type=MessageType.EVENT,
        payload={"event": "test"}
    )

    await comm.broadcast(message)

    # 统计
    assert comm.stats["messages_broadcast"] == 1
    assert comm.stats["messages_sent"] == 3  # 3个listener

    # 每个listener都应该收到
    msg1 = await comm.receive_message("listener_1")
    msg2 = await comm.receive_message("listener_2")
    msg3 = await comm.receive_message("listener_3")

    assert msg1 is not None
    assert msg2 is not None
    assert msg3 is not None

    assert msg1.message_id == "broadcast_1"
    assert msg2.message_id == "broadcast_1"
    assert msg3.message_id == "broadcast_1"


@pytest.mark.asyncio
async def test_pubsub():
    """测试发布订阅"""

    comm = AgentCommunication()

    # 注册Agent
    comm.register_agent("publisher")
    comm.register_agent("sub1")
    comm.register_agent("sub2")
    comm.register_agent("non_sub")

    # 订阅主题
    await comm.subscribe("sub1", "news")
    await comm.subscribe("sub2", "news")

    # 发布消息
    message = AgentMessage(
        message_id="pub_1",
        sender="publisher",
        receiver="",
        timestamp=datetime.now(),
        message_type=MessageType.EVENT,
        payload={"title": "Test"}
    )

    await comm.publish("news", message)

    # 订阅者应该收到
    msg1 = await comm.receive_message("sub1")
    msg2 = await comm.receive_message("sub2")

    assert msg1 is not None
    assert msg2 is not None
    assert msg1.message_id == "pub_1"
    assert msg2.message_id == "pub_1"

    # 非订阅者不应该收到
    msg_none = await comm.receive_message("non_sub", timeout=0.1)
    assert msg_none is None


@pytest.mark.asyncio
async def test_unsubscribe():
    """测试取消订阅"""

    comm = AgentCommunication()

    comm.register_agent("agent1")

    # 订阅
    await comm.subscribe("agent1", "topic1")
    assert "agent1" in comm.pubsub_topics["topic1"]

    # 取消订阅
    await comm.unsubscribe("agent1", "topic1")
    assert "agent1" not in comm.pubsub_topics["topic1"]


@pytest.mark.asyncio
async def test_message_expiry():
    """测试消息过期"""

    from datetime import timedelta

    comm = AgentCommunication()

    comm.register_agent("sender")
    comm.register_agent("receiver")

    # 创建一个已过期的消息
    expired_message = AgentMessage(
        message_id="expired",
        sender="sender",
        receiver="receiver",
        timestamp=datetime.now() - timedelta(seconds=3700),  # 超过TTL
        message_type=MessageType.TASK,
        payload={},
        ttl=3600  # 1小时
    )

    # 发送应该失败
    success = await comm.send_message(expired_message)

    assert success is False
    assert expired_message.is_expired() is True


@pytest.mark.asyncio
async def test_communication_statistics():
    """测试通信统计"""

    comm = AgentCommunication()

    # 注册Agent
    comm.register_agent("a1")
    comm.register_agent("a2")

    # 发送一些消息
    for i in range(5):
        message = AgentMessage(
            message_id=f"msg_{i}",
            sender="a1",
            receiver="a2",
            timestamp=datetime.now(),
            message_type=MessageType.TASK,
            payload={}
        )
        await comm.send_message(message)

    # 广播
    await comm.broadcast(AgentMessage(
        message_id="bc",
        sender="a1",
        receiver="broadcast",
        timestamp=datetime.now(),
        message_type=MessageType.EVENT,
        payload={}
    ))

    # 统计
    stats = comm.get_statistics()

    assert stats["messages_sent"] == 6  # 5点对点 + 1广播
    assert stats["messages_broadcast"] == 1
    assert stats["active_agents"] == 2


@pytest.mark.asyncio
async def test_queue_size():
    """测试队列大小"""

    comm = AgentCommunication()

    comm.register_agent("sender")
    comm.register_agent("receiver")

    # 发送多条消息
    for i in range(5):
        message = AgentMessage(
            message_id=f"msg_{i}",
            sender="sender",
            receiver="receiver",
            timestamp=datetime.now(),
            message_type=MessageType.TASK,
            payload={}
        )
        await comm.send_message(message)

    # 检查队列大小
    queue_size = comm.get_queue_size("receiver")
    assert queue_size == 5

    # 接收一条后
    await comm.receive_message("receiver")
    queue_size = comm.get_queue_size("receiver")
    assert queue_size == 4


@pytest.mark.asyncio
async def test_cleanup():
    """测试资源清理"""

    comm = AgentCommunication()

    # 注册Agent并发送消息
    comm.register_agent("a1")
    comm.register_agent("a2")

    message = AgentMessage(
        message_id="cleanup_test",
        sender="a1",
        receiver="a2",
        timestamp=datetime.now(),
        message_type=MessageType.TASK,
        payload={}
    )
    await comm.send_message(message)

    # 清理
    await comm.cleanup()

    # 检查
    assert len(comm.agent_queues) == 0
    assert len(comm.active_agents) == 0
    assert len(comm.pubsub_topics) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
