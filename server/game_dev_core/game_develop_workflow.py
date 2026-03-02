"""
游戏开发工作流编排

完整流程：
1. 主策划生成框架规范和任务分配（按模块）
   - 输出: framework_doc_path, framework_data, design_modules
   
2. 子策划并行开发各自模块文档
   - 输入: framework_doc_path, design_modules
   - 输出: module_docs_map {module_id -> {module_name, doc_path, doc_content}}
   
3. 主策划汇总产出最终GDD
   - 输入: module_docs_map
   - 输出: gdd_path, game_design_doc
   
4. 主程序搭建基础框架
   - 输入: gdd_path
   - 输出: framework_code_map {file_name -> file_path}, framework_files
   
5. 主程序分配开发任务
   - 输入: gdd_path, framework_code_map
   - 输出: coding_tasks
   
6. 子程序并行开发各自模块代码
   - 输入: coding_tasks, gdd_path, framework_code_map
   - 输出: completed_tasks_map {task_id -> {task_name, module, file_name, file_path, code_content}}
   
7. 主程序合并汇总代码
   - 输入: completed_tasks_map, framework_code_map
   - 输出: merge_analysis, all_code_files_map, code_structure_doc
   
8. 主程序审核修复代码
   - 输入: all_code_files_map, merge_analysis
   - 输出: code_review_result, main_entry_path
   
9. 测试阶段（如实汇报）
   - 输入: all_code_files_map, main_entry_path
   - 输出: test_results, test_report_path, all_tests_passed
   
10. 如有问题，修复后重新测试
    - 输入: all_code_files_map, test_results
    - 输出: fixed_files, fix_report
    
11. 测试通过后部署
    - 输入: all_code_files_map, main_entry_path
    - 输出: build_artifact, deploy_files_map

文件映射传递链：
- 策划阶段: framework_doc_path -> module_docs_map -> gdd_path
- 程序阶段: framework_code_map -> completed_tasks_map -> all_code_files_map + main_entry_path
- 测试阶段: all_code_files_map + main_entry_path -> test_results
- 修复阶段: all_code_files_map + test_results -> fixed_files
- 部署阶段: all_code_files_map + main_entry_path -> deploy_files_map
"""

from langgraph.graph import StateGraph, END

from game_dev_core import game_designer
from game_dev_core import game_dev_state
from game_dev_core import game_programmer
from game_dev_core import game_tester
from game_dev_core import game_fix_bugs
from game_dev_core import game_deploy

# 初始化图
game_workflow_builder = StateGraph(game_dev_state.GameDevState)

# ========== 策划阶段 ==========
# 主策划生成框架
# 输入: game_idea, project_dir
# 输出: framework_doc_path, framework_data, design_modules, module_docs_map(空)
game_workflow_builder.add_node("lead_designer_framework", game_designer.lead_designer_create_framework)

# 子策划并行开发
# 输入: design_modules, framework_doc_path
# 输出: module_docs_map {module_id -> {module_name, doc_path, doc_content}}
game_workflow_builder.add_node("parallel_sub_designers", game_designer.parallel_sub_designers)

# 主策划汇总文档
# 输入: module_docs_map, framework_doc_path
# 输出: gdd_path, game_design_doc
game_workflow_builder.add_node("lead_designer_merge", game_designer.lead_designer_merge_docs)

# ========== 程序阶段 ==========
# 主程序搭建框架
# 输入: gdd_path
# 输出: framework_code_map {file_name -> file_path}, framework_files, code_framework
game_workflow_builder.add_node("lead_programmer_framework", game_programmer.lead_programmer_create_framework)

# 主程序分配任务
# 输入: gdd_path, framework_code_map
# 输出: coding_tasks, completed_tasks_map(空)
game_workflow_builder.add_node("lead_programmer_tasks", game_programmer.lead_programmer_create_tasks)

# 子程序并行开发
# 输入: coding_tasks, gdd_path, framework_code_map
# 输出: completed_tasks_map {task_id -> {task_name, module, file_name, file_path, code_content}}
game_workflow_builder.add_node("parallel_sub_programmers", game_programmer.parallel_sub_programmers)

# 主程序合并汇总代码
# 输入: completed_tasks_map, framework_code_map
# 输出: merge_analysis, all_code_files_map, code_structure_doc
game_workflow_builder.add_node("lead_programmer_merge", game_programmer.lead_programmer_merge_code)

# 主程序审核修复
# 输入: all_code_files_map, merge_analysis
# 输出: code_review_result, main_entry_path, all_code_files_map(更新)
game_workflow_builder.add_node("lead_programmer_review", game_programmer.lead_programmer_review_and_fix)

# ========== 测试阶段 ==========
# 测试员运行测试
# 输入: all_code_files_map, main_entry_path
# 输出: test_results, test_report_path, all_tests_passed
game_workflow_builder.add_node("tester", game_tester)

# Bug修复
# 输入: all_code_files_map, test_results
# 输出: fixed_files, fix_report
game_workflow_builder.add_node("fix_bugs", game_fix_bugs.fix_bugs)

# 部署
game_workflow_builder.add_node("deploy", game_deploy.deploy)

# 设置入口点
game_workflow_builder.set_entry_point("lead_designer_framework")

# ========== 添加边 ==========
# 策划阶段流程
# framework_doc_path -> module_docs_map -> gdd_path
game_workflow_builder.add_edge("lead_designer_framework", "parallel_sub_designers")
game_workflow_builder.add_edge("parallel_sub_designers", "lead_designer_merge")

# 程序阶段流程
# gdd_path -> framework_code_map -> coding_tasks -> completed_tasks_map -> all_code_files_map -> main_entry_path
game_workflow_builder.add_edge("lead_designer_merge", "lead_programmer_framework")
game_workflow_builder.add_edge("lead_programmer_framework", "lead_programmer_tasks")
game_workflow_builder.add_edge("lead_programmer_tasks", "parallel_sub_programmers")
game_workflow_builder.add_edge("parallel_sub_programmers", "lead_programmer_merge")
game_workflow_builder.add_edge("lead_programmer_merge", "lead_programmer_review")

# 测试阶段流程
# all_code_files_map + main_entry_path -> test_results
game_workflow_builder.add_edge("lead_programmer_review", "tester")

# 条件边：根据测试结果决定下一步
def after_test(state: game_dev_state.GameDevState):
    if state.get("all_tests_passed", False):
        return "deploy"
    else:
        return "fix_bugs"

game_workflow_builder.add_conditional_edges("tester", after_test)

# 修复后回到测试（保留all_code_files_map，更新test_results）
game_workflow_builder.add_edge("fix_bugs", "tester")
game_workflow_builder.add_edge("deploy", END)

# 编译图
game_workflow_graph = game_workflow_builder.compile()


# 便捷函数
def run_game_development(game_idea: str, project_name: str = None, stream_callback=None, phase_callback=None) -> dict:
    """
    运行完整的游戏开发流程
    
    Args:
        game_idea: 游戏想法描述
        project_name: 项目名称（可选，如未提供将使用默认名称）
        stream_callback: 流式输出回调函数，接收 (content, agent_role) 参数
        phase_callback: 阶段完成回调函数，接收 (phase_id, phase_name, status) 参数
    
    Returns:
        最终状态（包含所有文件映射）
    """
    import os
    from agent_base import OutputNormalizer
    
    # 创建项目目录
    normalizer = OutputNormalizer()
    
    # 项目名称必须由用户提供，如未提供则使用默认名称
    if not project_name:
        project_name = "UntitledGame"
    
    # 根据项目名称创建项目信息（默认为游戏项目类型）
    project_info = normalizer.create_project_from_llm_response(
        project_name=project_name,
        project_type="game"
    )
    
    normalizer.set_current_project(project_info)
    
    # 定义阶段列表
    phases = [
        ("design", "策划阶段"),
        ("sub_design", "子策划并行"),
        ("merge_design", "策划汇总"),
        ("framework", "程序框架"),
        ("sub_code", "子程序并行"),
        ("merge_code", "代码汇总"),
        ("review", "代码审核"),
        ("test", "测试阶段"),
        ("deploy", "部署阶段")
    ]
    
    # 初始化状态（包含所有必要的空映射）
    initial_state = game_dev_state.GameDevState(
        game_idea=game_idea,
        project_dir=project_info.base_dir,
        stream_callback=stream_callback,
        phase_callback=phase_callback,
        # 策划阶段
        framework_doc_path=None,
        framework_data=None,
        design_modules=[],
        module_docs_map={},
        gdd_path=None,
        game_design_doc=None,
        # 程序阶段
        framework_code_map={},
        framework_files=[],
        coding_tasks=[],
        completed_tasks_map={},
        merge_analysis=None,
        code_structure_doc=None,
        code_review_result=None,
        all_code_files_map={},
        main_entry_path=None,
        # 测试阶段
        test_results=None,
        test_report_path=None,
        test_report=None,
        all_tests_passed=False,
        # 部署阶段
        build_artifact=None,
        deploy_files_map={}
    )
    
    # 通知阶段开始
    if phase_callback:
        phase_callback("design", "策划阶段", "running")
    
    # 运行工作流
    final_state = game_workflow_graph.invoke(initial_state)
    
    # 通知所有阶段完成
    if phase_callback:
        for phase_id, phase_name in phases:
            phase_callback(phase_id, phase_name, "completed")
    
    return final_state
