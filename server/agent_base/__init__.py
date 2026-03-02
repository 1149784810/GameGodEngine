"""
Agent基础模块 - 提供多Agent架构实现
使用LangChain和LangGraph实现的ReAct Agent
"""

# ReAct Agent实现（使用LangChain和LangGraph）
from .react_agent import ReActAgent, Memory, Plan, Step

# Agent工厂和工具注册
from .agent_factory import (
    AgentFactory,
    get_agent,
    list_available_agents,
    list_available_tools,
    register_tool,
    register_tools,
)

# 输出规范器
from .output_normalizer import (
    OutputNormalizer,
    ProjectInfo,
    ProjectType,
    normalize_output_path,
)

__all__ = [
    # ReAct Agent实现
    "ReActAgent",
    "Memory",
    "Plan",
    "Step",
    # Agent工厂和工具注册
    "AgentFactory",
    "get_agent",
    "list_available_agents",
    "list_available_tools",
    "register_tool",
    "register_tools",
    # 输出规范器
    "OutputNormalizer",
    "ProjectInfo",
    "ProjectType",
    "normalize_output_path",
]
