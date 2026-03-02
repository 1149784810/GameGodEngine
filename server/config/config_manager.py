"""
配置管理器 - 从JSON文件读取配置
"""

import json
from typing import Dict, Optional
from pathlib import Path

from .agent_config import AgentConfig


class ConfigManager:
    """配置管理器 - 只从JSON文件读取"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认为项目根目录下的config/agents文件夹
        """
        if config_dir is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent
            config_dir = project_root / "config" / "agents"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self._agents_config: Dict[str, AgentConfig] = {}
        self._load_configs()
    
    def _load_configs(self):
        """从JSON文件加载所有配置"""
        if not self.config_dir.exists():
            return
        
        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                config = AgentConfig(**config_data)
                self._agents_config[config.name] = config
                
            except Exception as e:
                print(f"警告：加载配置文件 {config_file} 失败: {e}")
    
    def get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        """
        获取Agent配置
        
        Args:
            agent_name: Agent名称
            
        Returns:
            Agent配置，如果不存在返回None
        """
        return self._agents_config.get(agent_name)
    
    def list_agents(self) -> Dict[str, str]:
        """
        列出所有可用的Agent
        
        Returns:
            Agent名称到描述的映射
        """
        return {
            name: config.description 
            for name, config in self._agents_config.items()
        }
    
    def reload_configs(self):
        """重新加载所有配置"""
        self._agents_config.clear()
        self._load_configs()


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_dir: Optional[str] = None) -> ConfigManager:
    """
    获取全局配置管理器实例
    
    Args:
        config_dir: 配置文件目录
        
    Returns:
        配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
    return _config_manager
