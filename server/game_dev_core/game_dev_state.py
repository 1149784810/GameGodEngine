from typing import TypedDict, List, Dict, Any, Optional, Callable

class GameDevState(TypedDict):
    # ==================== 基础信息 ====================
    # 输入需求
    game_idea: str
    # 项目目录
    project_dir: str
    # 流式输出回调函数
    stream_callback: Optional[Callable[[str, str], None]]
    # 阶段完成回调函数
    phase_callback: Optional[Callable[[str, str, str], None]]
    
    # ==================== 策划阶段产出 ====================
    # 主策划框架文档路径
    framework_doc_path: Optional[str]
    # 框架数据结构
    framework_data: Optional[Dict[str, Any]]
    # 设计模块列表
    design_modules: List[Dict[str, Any]]
    
    # 子策划产出的模块文档映射: module_id -> {module_name, doc_path, doc_content}
    module_docs_map: Dict[str, Dict[str, Any]]
    
    # 最终GDD文档路径
    gdd_path: Optional[str]
    # GDD内容
    game_design_doc: Optional[str]
    
    # ==================== 程序阶段产出 ====================
    # 框架代码文件映射: file_name -> file_path
    framework_code_map: Dict[str, str]
    # 框架文件列表（用于传递给子程序）
    framework_files: List[str]
    
    # 开发任务列表
    coding_tasks: List[Dict[str, Any]]
    
    # 子程序产出的代码映射: task_id -> {task_name, module, file_name, file_path, code_content}
    completed_tasks_map: Dict[str, Dict[str, Any]]
    
    # 合并分析结果
    merge_analysis: Optional[Dict[str, Any]]
    # 代码结构文档路径
    code_structure_doc: Optional[str]
    
    # 审核结果
    code_review_result: Optional[Dict[str, Any]]
    # 所有代码文件映射: file_name -> file_path
    all_code_files_map: Dict[str, str]
    # 主入口文件路径
    main_entry_path: Optional[str]
    
    # ==================== 测试阶段产出 ====================
    # 测试结果
    test_results: Optional[Dict[str, Any]]
    # 测试报告路径
    test_report_path: Optional[str]
    # 测试报告内容
    test_report: Optional[str]
    # 是否通过测试
    all_tests_passed: bool
    
    # ==================== 部署阶段产出 ====================
    # 部署产物路径
    build_artifact: Optional[str]
    # 部署产物文件映射
    deploy_files_map: Dict[str, str]
