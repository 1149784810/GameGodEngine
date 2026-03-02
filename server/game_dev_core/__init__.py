"""
游戏开发核心模块 - 包含所有游戏开发工作流相关的组件
"""

# 导出状态类型
from .game_dev_state import GameDevState

# 导出各个角色模块
from .game_designer import (
    lead_designer_create_framework,
    parallel_sub_designers,
    lead_designer_merge_docs,
)

from .game_programmer import (
    lead_programmer_create_framework,
    lead_programmer_create_tasks,
    parallel_sub_programmers,
    lead_programmer_merge_code,
    lead_programmer_review_and_fix,
)

from .game_tester import game_tester
from .game_fix_bugs import fix_bugs

# 导出工作流
from .game_develop_workflow import (
    game_workflow_graph,
    run_game_development,
)

__all__ = [
    # 状态
    "GameDevState",
    # 策划角色
    "lead_designer_create_framework",
    "parallel_sub_designers",
    "lead_designer_merge_docs",
    # 程序角色
    "lead_programmer_create_framework",
    "lead_programmer_create_tasks",
    "parallel_sub_programmers",
    "lead_programmer_merge_code",
    "lead_programmer_review_and_fix",
    # 测试角色
    "game_tester",
    # Bug修复
    "fix_bugs",
    # 工作流
    "game_workflow_graph",
    "run_game_development",
]
