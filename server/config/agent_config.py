"""
Agent配置定义 - 从JSON文件读取
只支持ReAct模式
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class ModelSettings(BaseModel):
    """模型配置"""
    model_config = ConfigDict(extra="allow")
    
    model: str = Field(default=None)
    temperature: float = Field(default=1.0)
    max_tokens: int = Field(default=100000)
    base_url: str = Field(default=None)
    api_key: Optional[str] = Field(default=None)


class AgentConfig(BaseModel):
    """Agent配置 - 从JSON文件加载，只支持ReAct模式"""
    model_config = ConfigDict(extra="allow")
    
    name: str
    description: str = Field(default="")
    system_prompt: str = Field(default="")
    max_iterations: int = Field(default=10)
    model_settings: ModelSettings = Field(default_factory=ModelSettings)
    tools: List[str] = Field(default_factory=list)
    memory_enabled: bool = Field(default=True)
    memory_max_turns: int = Field(default=20)
