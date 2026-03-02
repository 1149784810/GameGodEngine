"""
提示词加载器 - 从多个JSON配置文件加载工作流提示词

配置文件目录: config/prompts/
- designer_prompts.json    - 策划角色提示词
- programmer_prompts.json  - 程序角色提示词
- tester_prompts.json      - 测试角色提示词
- fix_bugs_prompts.json    - Bug修复角色提示词
"""

import json
import os
from typing import Dict, Any, Optional

# 配置文件目录
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'prompts')

# 缓存
_prompts_cache: Optional[Dict[str, Any]] = None


def _get_prompt_file_path(role: str) -> str:
    """获取角色对应的提示词文件路径"""
    file_name = f"{role}_prompts.json"
    return os.path.join(PROMPTS_DIR, file_name)


def load_prompts() -> Dict[str, Any]:
    """加载所有提示词配置"""
    global _prompts_cache
    
    if _prompts_cache is not None:
        return _prompts_cache
    
    _prompts_cache = {}
    
    # 定义所有角色
    roles = ['designer', 'programmer', 'tester', 'fix_bugs']
    
    for role in roles:
        file_path = _get_prompt_file_path(role)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    role_prompts = json.load(f)
                    # 移除version、role、description等元数据，只保留提示词
                    prompts = {k: v for k, v in role_prompts.items() 
                              if k not in ['version', 'role', 'description']}
                    _prompts_cache[role] = prompts
            except Exception as e:
                print(f"警告：加载角色 '{role}' 的提示词配置失败: {e}")
        else:
            print(f"警告：未找到角色 '{role}' 的提示词配置文件: {file_path}")
    
    return _prompts_cache


def get_prompt(role: str, prompt_key: str) -> Dict[str, Any]:
    """
    获取指定角色的提示词配置
    
    Args:
        role: 角色名称 (designer, programmer, tester, fix_bugs)
        prompt_key: 提示词键名
    
    Returns:
        提示词配置字典
    """
    prompts = load_prompts()
    
    if role not in prompts:
        # 尝试重新加载该角色的配置文件
        file_path = _get_prompt_file_path(role)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    role_prompts = json.load(f)
                    prompts[role] = {k: v for k, v in role_prompts.items() 
                                    if k not in ['version', 'role', 'description']}
            except Exception as e:
                raise KeyError(f"加载角色 '{role}' 的提示词配置失败: {e}")
        else:
            raise KeyError(f"未找到角色 '{role}' 的提示词配置文件")
    
    if prompt_key not in prompts[role]:
        raise KeyError(f"未找到提示词 '{role}.{prompt_key}'")
    
    return prompts[role][prompt_key]


def format_prompt(role: str, prompt_key: str, **kwargs) -> str:
    """
    格式化提示词，支持变量替换
    
    Args:
        role: 角色名称
        prompt_key: 提示词键名
        **kwargs: 要替换的变量
    
    Returns:
        格式化后的提示词字符串
    """
    prompt_config = get_prompt(role, prompt_key)
    
    # 构建提示词
    parts = []
    
    # 系统角色
    if 'system' in prompt_config:
        parts.append(f"【角色】{prompt_config['system']}")
    
    # 任务
    if 'task' in prompt_config:
        parts.append(f"\n【任务】{prompt_config['task']}")
    
    # 动态内容（从kwargs传入）
    for key, value in kwargs.items():
        if value:
            if isinstance(value, list):
                parts.append(f"\n【{key}】")
                for item in value:
                    parts.append(f"  - {item}")
            elif isinstance(value, dict):
                parts.append(f"\n【{key}】")
                for k, v in value.items():
                    parts.append(f"  - {k}: {v}")
            else:
                parts.append(f"\n【{key}】\n{value}")
    
    # 输出格式
    if 'output_format' in prompt_config:
        parts.append(f"\n【输出格式】{prompt_config['output_format']}")
    
    # 约束条件
    if 'constraints' in prompt_config:
        parts.append("\n【约束条件】")
        for constraint in prompt_config['constraints']:
            parts.append(f"  - {constraint}")
    
    # 检查点
    if 'check_points' in prompt_config:
        parts.append("\n【检查点】")
        for point in prompt_config['check_points']:
            parts.append(f"  - {point}")
    
    # 要求
    if 'requirements' in prompt_config:
        parts.append("\n【要求】")
        for req in prompt_config['requirements']:
            parts.append(f"  - {req}")
    
    # 文档要求
    if 'document_requirements' in prompt_config:
        parts.append("\n【文档要求】")
        for req in prompt_config['document_requirements']:
            parts.append(f"  - {req}")
    
    # 报告章节
    if 'report_sections' in prompt_config:
        parts.append("\n【报告章节】")
        for section in prompt_config['report_sections']:
            parts.append(f"  - {section}")
    
    # 原则
    if 'principles' in prompt_config:
        parts.append("\n【原则】")
        for principle in prompt_config['principles']:
            parts.append(f"  - {principle}")
    
    return "\n".join(parts)


def reload_prompts():
    """重新加载提示词配置（用于热更新）"""
    global _prompts_cache
    _prompts_cache = None
    return load_prompts()


def list_available_prompts() -> Dict[str, list]:
    """
    列出所有可用的提示词
    
    Returns:
        字典，键为角色名，值为该角色可用的提示词键名列表
    """
    prompts = load_prompts()
    return {role: list(prompts[role].keys()) for role in prompts}
