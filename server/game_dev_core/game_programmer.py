"""
游戏程序模块 - 主程序和子程序协作

流程：
1. 主程序读取GDD，搭建基础框架（游戏循环、对象管理、UI框架、事件系统）
2. 主程序按模块分配任务，生成TODO列表
3. 子程序并行开发各自负责的模块代码
4. 主程序合并汇总代码（分析依赖、修复导入、生成结构说明）
5. 主程序审核并修复问题
6. 产出最终可运行的代码

文件映射说明：
- framework_code_map: 框架代码文件映射
- coding_tasks: 开发任务列表
- completed_tasks_map: 子程序产出的代码映射
- merge_analysis: 合并分析结果
- all_code_files_map: 所有代码文件映射
- main_entry_path: 主入口文件路径

优化：
- 移除所有长度限制，支持大文件
- 提示词从配置文件读取
- 文件内容通过read_file工具读取，不直接传入prompt
- 支持流式输出
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, TYPE_CHECKING, Callable, Optional

from agent_base import get_agent
from config.prompt_loader import format_prompt

if TYPE_CHECKING:
    from .game_dev_state import GameDevState


def _run_agent_with_stream(agent, prompt: str, agent_role: str, stream_callback: Optional[Callable[[str, str], None]] = None):
    """辅助函数：根据是否有流式回调选择run或run_stream"""
    if stream_callback:
        return agent.run_stream(prompt, callback=lambda chunk: stream_callback(chunk, agent_role))
    else:
        return agent.run(prompt)


def lead_programmer_create_framework(state: "GameDevState") -> "GameDevState":
    """
    主程序：读取GDD，搭建基础框架
    
    输入：
    - gdd_path: GDD文档路径
    - game_design_doc: GDD内容
    
    输出：
    - framework_code_map: 框架代码文件映射 {file_name -> file_path}
    - framework_files: 框架文件列表
    """
    from agent_base import OutputNormalizer
    
    agent = get_agent("programmer_agent")
    
    project_dir = state.get('project_dir', '.')
    gdd_path = state.get('gdd_path', '')
    stream_callback = state.get('stream_callback')
    
    # 设置Agent的output_normalizer当前项目
    project_name = os.path.basename(project_dir)
    agent.output_normalizer.set_current_project(
        OutputNormalizer().create_project_from_llm_response(
            project_name=project_name,
            project_type="game"
        )
    )
    

    
    # 从配置文件加载提示词
    prompt = format_prompt(
        "programmer", "lead_create_framework",
        GDD路径=gdd_path,
        框架组件=["游戏主循环", "对象管理系统", "UI框架接口", "事件系统", "配置文件"]
    )
    
    # 让Agent读取GDD并生成框架结构
    read_prompt = f"""
请先读取GDD文档：{gdd_path}
然后基于该文档，完成以下任务：

{prompt}
"""
    
    response = _run_agent_with_stream(agent, read_prompt, "主程序", stream_callback)
    
    # 解析JSON
    try:
        framework_data = json.loads(response)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            framework_data = json.loads(json_match.group())
        else:
            framework_data = {"framework_files": [], "architecture": response}
    
    # 生成框架代码
    framework_code_map = {}
    framework_files = []
    
    for file_info in framework_data.get('framework_files', []):
        file_name = file_info.get('file_name', 'unknown.py')
        description = file_info.get('description', '')
        components = file_info.get('key_components', [])
        
        # 从配置文件加载提示词
        code_prompt = format_prompt(
            "programmer", "generate_framework_code",
            文件名=file_name,
            文件描述=description,
            关键组件=components,
            GDD路径=gdd_path
        )
        
        # 让Agent读取GDD并生成代码
        read_code_prompt = f"""
请先读取GDD文档：{gdd_path}
然后基于该文档，完成以下任务：

{code_prompt}

只输出代码，不要其他解释。
"""
        
        code_content = _run_agent_with_stream(agent, read_code_prompt, "主程序", stream_callback)
        
        # 保存代码文件
        file_path = os.path.join(project_dir, 'src', file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code_content)
        
        framework_code_map[file_name] = file_path
        framework_files.append(file_name)
    
    return {
        **state,
        "framework_code_map": framework_code_map,
        "framework_files": framework_files,
        "code_framework": framework_data
    }


def lead_programmer_create_tasks(state: "GameDevState") -> "GameDevState":
    """
    主程序：根据GDD分配任务，生成TODO列表
    
    输入：
    - gdd_path: GDD文档路径
    - framework_code_map: 框架代码文件映射
    
    输出：
    - coding_tasks: 开发任务列表
    """
    from agent_base import OutputNormalizer
    
    agent = get_agent("programmer_agent")
    
    project_dir = state.get('project_dir', '.')
    gdd_path = state.get('gdd_path', '')
    framework_code_map = state.get('framework_code_map', {})
    stream_callback = state.get('stream_callback')
    
    # 设置Agent的output_normalizer当前项目
    project_name = os.path.basename(project_dir)
    agent.output_normalizer.set_current_project(
        OutputNormalizer().create_project_from_llm_response(
            project_name=project_name,
            project_type="game"
        )
    )
    
    # 收集框架文件路径列表
    framework_file_list = list(framework_code_map.keys())
    

    
    # 从配置文件加载提示词
    prompt = format_prompt(
        "programmer", "lead_create_tasks",
        GDD路径=gdd_path,
        框架文件列表=framework_file_list
    )
    
    # 让Agent读取GDD和框架文件，然后创建任务
    read_files_instruction = f"请按顺序读取以下文档：\n"
    read_files_instruction += f"1. GDD文档: {gdd_path}\n"
    for i, file_name in enumerate(framework_file_list[:3], 2):  # 最多读取前3个框架文件
        file_path = framework_code_map.get(file_name, '')
        if file_path:
            read_files_instruction += f"{i}. 框架文件 {file_name}: {file_path}\n"
    
    read_files_instruction += f"\n然后完成以下任务：\n\n{prompt}"
    
    response = _run_agent_with_stream(agent, read_files_instruction, "主程序", stream_callback)
    
    try:
        tasks_data = json.loads(response)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            tasks_data = json.loads(json_match.group())
        else:
            tasks_data = {"coding_tasks": []}
    
    coding_tasks = tasks_data.get('coding_tasks', [])
    
    return {
        **state,
        "coding_tasks": coding_tasks,
        "completed_tasks_map": {}
    }


def sub_programmer_work(task_info: Dict[str, Any], gdd_path: str, framework_code_map: Dict[str, str], project_dir: str, stream_callback: Optional[Callable[[str, str], None]] = None) -> Dict[str, Any]:
    """
    子程序：根据TODO列表开发模块代码
    
    输入：
    - task_info: 任务信息
    - gdd_path: GDD文档路径
    - framework_code_map: 框架代码文件映射
    
    输出：
    - task_id: 任务ID
    - task_name: 任务名称
    - module: 模块名称
    - file_name: 代码文件名
    - file_path: 代码文件路径
    - code_content: 代码内容摘要
    """
    from agent_base import OutputNormalizer
    
    agent = get_agent("programmer_agent")
    
    # 设置Agent的output_normalizer当前项目
    project_name = os.path.basename(project_dir)
    agent.output_normalizer.set_current_project(
        OutputNormalizer().create_project_from_llm_response(
            project_name=project_name,
            project_type="game"
        )
    )
    
    task_id = task_info.get('task_id', 'unknown')
    task_name = task_info.get('task_name', '未知任务')
    module = task_info.get('module', 'unknown')
    
    # 从配置文件加载提示词
    prompt = format_prompt(
        "programmer", "sub_programmer_work",
        任务ID=task_id,
        任务名称=task_name,
        负责模块=module,
        功能需求=task_info.get('requirements', []),
        输入接口=task_info.get('input_interface', ''),
        输出接口=task_info.get('output_interface', ''),
        验收标准=task_info.get('acceptance_criteria', '')
    )
    
    # 让Agent读取GDD和框架文件
    read_files_instruction = f"请按顺序读取以下文档：\n"
    read_files_instruction += f"1. GDD文档: {gdd_path}\n"
    
    # 读取框架文件（最多3个）
    framework_files = list(framework_code_map.items())[:3]
    for i, (file_name, file_path) in enumerate(framework_files, 2):
        read_files_instruction += f"{i}. 框架文件 {file_name}: {file_path}\n"
    
    read_files_instruction += f"\n然后完成以下任务：\n\n{prompt}"
    
    code_content = _run_agent_with_stream(agent, read_files_instruction, f"子程序-{task_name}", stream_callback)
    
    # 生成文件名
    file_name = f"{module.lower().replace(' ', '_').replace('系统', '_system')}.py"
    file_path = os.path.join(project_dir, 'src', file_name)
    
    return {
        "task_id": task_id,
        "task_name": task_name,
        "module": module,
        "file_name": file_name,
        "file_path": file_path,
        "code_content": code_content
    }


def parallel_sub_programmers(state: "GameDevState") -> "GameDevState":
    """
    并行启动所有子程序进行开发
    
    输入：
    - coding_tasks: 开发任务列表
    - gdd_path: GDD文档路径
    - framework_code_map: 框架代码文件映射
    
    输出：
    - completed_tasks_map: 完成的代码映射 {task_id -> {task_name, module, file_name, file_path, code_content}}
    """
    tasks = state.get('coding_tasks', [])
    gdd_path = state.get('gdd_path', '')
    framework_code_map = state.get('framework_code_map', {})
    project_dir = state.get('project_dir', '.')
    stream_callback = state.get('stream_callback')
    
    completed_tasks_map = {}
    
    with ThreadPoolExecutor(max_workers=min(len(tasks), 5)) as executor:
        future_to_task = {
            executor.submit(sub_programmer_work, task, gdd_path, framework_code_map, project_dir, stream_callback): task
            for task in tasks
        }
        
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                task_id = result['task_id']
                
                # 保存代码文件
                file_path = result['file_path']
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result['code_content'])
                
                # 存储到映射（保存摘要）
                completed_tasks_map[task_id] = {
                    "task_id": task_id,
                    "task_name": result['task_name'],
                    "module": result['module'],
                    "file_name": result['file_name'],
                    "file_path": file_path,
                    "code_content": result['code_content'][:500] + "..." if len(result['code_content']) > 500 else result['code_content']
                }
            except Exception:
                pass
    
    return {**state, "completed_tasks_map": completed_tasks_map}


def lead_programmer_merge_code(state: "GameDevState") -> "GameDevState":
    """
    主程序：合并汇总所有子程序代码
    
    输入：
    - completed_tasks_map: 完成的代码映射
    - framework_code_map: 框架代码文件映射
    
    输出：
    - merge_analysis: 合并分析结果
    - code_structure_doc: 代码结构文档路径
    """
    from agent_base import OutputNormalizer
    
    agent = get_agent("programmer_agent")
    
    project_dir = state.get('project_dir', '.')
    src_dir = os.path.join(project_dir, 'src')
    completed_tasks_map = state.get('completed_tasks_map', {})
    framework_code_map = state.get('framework_code_map', {})
    stream_callback = state.get('stream_callback')
    
    # 设置Agent的output_normalizer当前项目
    project_name = os.path.basename(project_dir)
    agent.output_normalizer.set_current_project(
        OutputNormalizer().create_project_from_llm_response(
            project_name=project_name,
            project_type="game"
        )
    )
    
    # 收集所有代码文件路径
    all_code_file_paths = []
    
    # 添加框架文件
    for file_name, file_path in framework_code_map.items():
        if os.path.exists(file_path):
            all_code_file_paths.append({"file_name": file_name, "file_path": file_path})
    
    # 添加子程序产出的文件
    for task_id, task_info in completed_tasks_map.items():
        file_path = task_info.get('file_path', '')
        file_name = task_info.get('file_name', '')
        if file_path and os.path.exists(file_path):
            all_code_file_paths.append({"file_name": file_name, "file_path": file_path})
    

    
    # 从配置文件加载提示词
    prompt = format_prompt(
        "programmer", "merge_code_analysis",
        代码文件列表=[f['file_name'] for f in all_code_file_paths]
    )
    
    # 让Agent读取所有代码文件并分析
    read_files_instruction = "请按顺序读取以下代码文件：\n"
    for i, file_info in enumerate(all_code_file_paths, 1):
        read_files_instruction += f"{i}. {file_info['file_name']}: {file_info['file_path']}\n"
    
    read_files_instruction += f"\n然后完成以下任务：\n\n{prompt}"
    
    analysis_response = _run_agent_with_stream(agent, read_files_instruction, "主程序", stream_callback)
    
    try:
        merge_analysis = json.loads(analysis_response)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{.*\}', analysis_response, re.DOTALL)
        if json_match:
            merge_analysis = json.loads(json_match.group())
        else:
            merge_analysis = {
                "dependencies": {},
                "duplicates": [],
                "import_issues": [],
                "merge_order": [f['file_name'] for f in all_code_file_paths]
            }
    
    # 构建文件路径映射
    all_code_files_map = {f['file_name']: f['file_path'] for f in all_code_file_paths}
    
    # 处理重复定义
    duplicates = merge_analysis.get('duplicates', [])
    if duplicates:
        print(f"\n[合并] 发现 {len(duplicates)} 个重复定义:")
        for dup in duplicates:
            print(f"  ⚠ {dup.get('name', '未知')} 在 {dup.get('files', [])} 中重复定义")
            print(f"    建议: {dup.get('suggestion', '需要手动处理')}")
    
    # 修复导入问题
    import_issues = merge_analysis.get('import_issues', [])
    if import_issues:
        print(f"\n[合并] 修复 {len(import_issues)} 个导入问题...")
        for issue in import_issues:
            file_name = issue.get('file', '')
            file_path = all_code_files_map.get(file_name)
            
            if file_path and os.path.exists(file_path):
                # 从配置文件加载提示词
                fix_prompt = format_prompt(
                    "programmer", "fix_import_issues",
                    文件名=file_name,
                    问题=issue.get('issue', ''),
                    修复建议=issue.get('fix', '')
                )
                
                # 让Agent读取文件并修复
                read_fix_instruction = f"请先读取文件：{file_path}\n\n然后完成以下任务：\n\n{fix_prompt}"
                
                fixed_code = _run_agent_with_stream(agent, read_fix_instruction, "主程序", stream_callback)
                
                # 保存修复后的文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_code)
                
    # 生成统一的项目结构说明
    structure_prompt = format_prompt(
        "programmer", "generate_structure_doc",
        代码文件列表=[f['file_name'] for f in all_code_file_paths],
        依赖关系=merge_analysis.get('dependencies', {})
    )
    
    # 让Agent读取关键文件并生成结构说明
    read_structure_instruction = "请读取以下关键代码文件：\n"
    for i, file_info in enumerate(all_code_file_paths[:5], 1):  # 读取前5个文件
        read_structure_instruction += f"{i}. {file_info['file_name']}: {file_info['file_path']}\n"
    
    read_structure_instruction += f"\n然后完成以下任务：\n\n{structure_prompt}"
    
    structure_doc = _run_agent_with_stream(agent, read_structure_instruction, "主程序", stream_callback)
    
    # 保存结构说明
    structure_path = os.path.join(project_dir, 'docs', 'code_structure.md')
    os.makedirs(os.path.dirname(structure_path), exist_ok=True)
    with open(structure_path, 'w', encoding='utf-8') as f:
        f.write(structure_doc)
    

    
    return {
        **state,
        "merge_analysis": merge_analysis,
        "all_code_files_map": all_code_files_map,
        "code_structure_doc": structure_path
    }


def lead_programmer_review_and_fix(state: "GameDevState") -> "GameDevState":
    """
    主程序：审核代码并修复问题
    
    输入：
    - all_code_files_map: 所有代码文件映射
    - merge_analysis: 合并分析结果
    
    输出：
    - code_review_result: 代码审核结果
    - main_entry_path: 主入口文件路径
    """
    from agent_base import OutputNormalizer
    
    agent = get_agent("programmer_agent")
    
    project_dir = state.get('project_dir', '.')
    src_dir = os.path.join(project_dir, 'src')
    all_code_files_map = state.get('all_code_files_map', {})
    stream_callback = state.get('stream_callback')
    
    # 设置Agent的output_normalizer当前项目
    project_name = os.path.basename(project_dir)
    agent.output_normalizer.set_current_project(
        OutputNormalizer().create_project_from_llm_response(
            project_name=project_name,
            project_type="game"
        )
    )
    
    # 收集所有代码文件路径
    code_file_list = []
    for file_name, file_path in all_code_files_map.items():
        if os.path.exists(file_path):
            code_file_list.append({"file_name": file_name, "file_path": file_path})
    

    
    # 从配置文件加载提示词
    prompt = format_prompt(
        "programmer", "code_review",
        代码文件列表=[f['file_name'] for f in code_file_list]
    )
    
    # 让Agent读取所有代码文件并审核
    read_files_instruction = "请按顺序读取以下代码文件：\n"
    for i, file_info in enumerate(code_file_list, 1):
        read_files_instruction += f"{i}. {file_info['file_name']}: {file_info['file_path']}\n"
    
    read_files_instruction += f"\n然后完成以下任务：\n\n{prompt}"
    
    review_response = _run_agent_with_stream(agent, read_files_instruction, "主程序", stream_callback)
    
    try:
        review_result = json.loads(review_response)
    except json.JSONDecodeError:
        review_result = {"issues": [], "overall_quality": "需要人工审核"}
    
    issues = review_result.get('issues', [])
    
    if issues:
        
        # 修复问题
        for issue in issues:
            file_name = issue.get('file', '')
            file_path = all_code_files_map.get(file_name)
            
            if file_path and os.path.exists(file_path):
                # 从配置文件加载提示词
                fix_prompt = format_prompt(
                    "programmer", "fix_code_issues",
                    文件名=file_name,
                    问题=issue.get('issue', ''),
                    修复建议=issue.get('fix_suggestion', '')
                )
                
                # 让Agent读取文件并修复
                read_fix_instruction = f"请先读取文件：{file_path}\n\n然后完成以下任务：\n\n{fix_prompt}"
                
                fixed_code = _run_agent_with_stream(agent, read_fix_instruction, "主程序", stream_callback)
                
                # 保存修复后的代码
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_code)
                

    
    # 生成整合后的主程序入口
    main_prompt = format_prompt(
        "programmer", "generate_main_entry",
        模块列表=list(all_code_files_map.keys())
    )
    
    # 让Agent读取关键模块并生成主入口
    read_main_instruction = "请读取以下关键模块文件：\n"
    for i, (file_name, file_path) in enumerate(list(all_code_files_map.items())[:5], 1):
        read_main_instruction += f"{i}. {file_name}: {file_path}\n"
    
    read_main_instruction += f"\n然后完成以下任务：\n\n{main_prompt}"
    
    main_code = _run_agent_with_stream(agent, read_main_instruction, "主程序", stream_callback)
    
    main_path = os.path.join(src_dir, 'main.py')
    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(main_code)
    
    # 更新代码文件映射
    all_code_files_map['main.py'] = main_path
    
    return {
        **state,
        "code_review_result": review_result,
        "all_code_files_map": all_code_files_map,
        "main_entry_path": main_path
    }
