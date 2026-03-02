"""
配置模块 - 从JSON文件读取Agent配置
只支持ReAct模式
"""

from .agent_config import AgentConfig, ModelSettings
from .config_manager import ConfigManager, get_config_manager

__all__ = [
    "AgentConfig",
    "ModelSettings",
    "ConfigManager",
    "get_config_manager",
]
