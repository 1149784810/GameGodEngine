"""
Agent工厂 - 从JSON配置创建Agent并注入工具
"""

from typing import List, Optional, Dict
from langchain_core.tools import BaseTool

from config import AgentConfig, get_config_manager, ModelSettings
from tools import file_tools, shell_tools
from .react_agent import ReActAgent


class AgentFactory:
    """Agent工厂类 - 工具与Agent解耦"""
    
    # 全局工具注册表
    _tools_registry: Dict[str, BaseTool] = {}
    
    @classmethod
    def register_tool(cls, tool: BaseTool):
        """注册工具到全局注册表"""
        cls._tools_registry[tool.name] = tool
    
    @classmethod
    def register_tools(cls, tools: List[BaseTool]):
        """批量注册工具"""
        for tool in tools:
            cls._tools_registry[tool.name] = tool
    
    @classmethod
    def get_tool(cls, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return cls._tools_registry.get(name)
    
    @classmethod
    def list_tools(cls) -> Dict[str, str]:
        """列出所有可用工具"""
        return {
            name: tool.description 
            for name, tool in cls._tools_registry.items()
        }
    
    @classmethod
    def create_agent(cls, agent_name: str) -> ReActAgent:
        """
        从JSON配置创建Agent实例
        
        Args:
            agent_name: Agent名称（对应config/agents/目录下的JSON文件名）
            
        Returns:
            ReActAgent实例
            
        Raises:
            ValueError: 如果配置不存在或工具未找到
        """
        # 从配置管理器获取配置（从JSON文件读取）
        config_manager = get_config_manager()
        config = config_manager.get_agent_config(agent_name)
        
        if config is None:
            raise ValueError(f"未找到Agent配置: {agent_name}，请检查 config/agents/{agent_name}.json 是否存在")
        
        # 根据配置加载工具
        tools = cls._load_tools_from_config(config)
        
        # 创建Agent（注入工具）
        return ReActAgent(config, tools)
    
    @classmethod
    def _load_tools_from_config(cls, config: AgentConfig) -> List[BaseTool]:
        """
        根据配置加载工具列表
        
        Args:
            config: Agent配置
            
        Returns:
            工具列表
        """
        tools = []
        for tool_name in config.tools:
            tool = cls.get_tool(tool_name)
            if tool:
                tools.append(tool)
            else:
                print(f"警告：未找到工具 '{tool_name}'，请确保已注册")
        return tools


# 初始化：注册默认工具
AgentFactory.register_tools(file_tools)
AgentFactory.register_tools(shell_tools)


# 便捷函数
def get_agent(agent_name: str) -> ReActAgent:
    """
    获取Agent实例
    
    Args:
        agent_name: Agent名称（对应JSON配置文件名）
        
    Returns:
        ReActAgent实例
    """
    return AgentFactory.create_agent(agent_name)


def list_available_agents() -> Dict[str, str]:
    """
    列出所有可用的Agent
    
    Returns:
        Agent名称到描述的映射
    """
    config_manager = get_config_manager()
    return config_manager.list_agents()


def list_available_tools() -> Dict[str, str]:
    """
    列出所有可用的工具
    
    Returns:
        工具名称到描述的映射
    """
    return AgentFactory.list_tools()


def register_tool(tool: BaseTool):
    """
    注册工具到全局注册表
    
    Args:
        tool: 工具实例
    """
    AgentFactory.register_tool(tool)


def register_tools(tools: List[BaseTool]):
    """
    批量注册工具
    
    Args:
        tools: 工具列表
    """
    AgentFactory.register_tools(tools)
