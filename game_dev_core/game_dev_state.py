from typing import TypedDict, List, Dict, Any, Optional

class GameDevState(TypedDict):
    # 输入需求
    game_idea: str
    
    # 主策划产出
    game_design_doc: Optional[str]  # 设计文档
    
    # 子策划产出：任务列表，每个任务包含任务名、负责人、状态等
    tasks: List[Dict[str, Any]]  # [{"name": "角色移动", "assignee": "程序A", "code": "", "test_result": None}, ...]
    
    # 主程序产出：技术栈和项目结构描述
    tech_stack: Optional[str]
    project_structure: Optional[str]
    
    # 代码仓库：每个任务的代码
    code_repo: Dict[str, str]  # 任务名 -> 代码存放地址
    
    # 测试结果
    test_reports: List[Dict[str, Any]]  # [{"task": "角色移动", "passed": False, "feedback": "缺少边界检测"}, ...]
    
    # 部署产物
    build_artifact: Optional[str]
    
    # 循环控制标志
    all_tests_passed: bool