#!/usr/bin/env python
"""测试导入"""
import sys
import os

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from agent_base import get_agent, list_available_agents, list_available_tools
    print("✓ agent_base 导入成功")
    
    from game_dev_core import run_game_development
    print("✓ game_dev_core 导入成功")
    
    from config import get_config_manager
    print("✓ config 导入成功")
    
    from tools import file_tools
    print("✓ tools 导入成功")
    
    print("\n所有模块导入成功！")
    
except Exception as e:
    print(f"✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()
