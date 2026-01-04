"""
Multi-Agent System for MoAgent

Provides a framework for multiple agents to collaborate on web crawling tasks.
"""

from .base import BaseAgent, AgentConfig, Task, TaskResult, AgentStatus
from .message import AgentMessage, MessageType, TaskMessage, ResultMessage
from .communication import AgentCommunication

__all__ = [
    # Base classes
    'BaseAgent',
    'AgentConfig',
    'Task',
    'TaskResult',
    'AgentStatus',

    # Message types
    'AgentMessage',
    'MessageType',
    'TaskMessage',
    'ResultMessage',

    # Communication
    'AgentCommunication',
]

__version__ = '0.1.0'
