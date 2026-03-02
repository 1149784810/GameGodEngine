"""
游戏策划模块 - 主策划和子策划协作

流程：
1. 主策划生成框架规范和任务分配（按模块分配）
2. 子策划并行开发各自负责的模块文档
3. 主策划汇总所有文档，产出最终设计文档

文件映射说明：
- framework_doc_path: 主策划框架文档路径
- module_docs_map: 子策划产出的模块文档映射
- gdd_path: 最终GDD文档路径

优化：
- 移除所有长度限制，支持大文件
- 提示词从配置文件读取
- 文件内容通过read_file工具读取，不直接传入prompt
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, TYPE_CHECKING

from agent_base import get_agent
from config.prompt_loader import format_prompt

if TYPE_CHECKING:
    from .game_dev_state import GameDevState


def lead_designer_create_framework(state: "GameDevState") -> "GameDevState":
    """
    主策划：生成框架规范和任务分配
    
    输出：
    - framework_doc_path: 框架文档路径
    - framework_data: 框架数据结构
    - design_modules: 设计模块列表（用于分配给子策划）
    """
    from agent_base import OutputNormalizer
    
    agent = get_agent("designer_agent")
    
    project_dir = state.get('project_dir', '.')
    
    # 设置Agent的output_normalizer当前项目，确保文件输出到正确位置
    project_name = os.path.basename(project_dir)
    agent.output_normalizer.set_current_project(
        OutputNormalizer().create_project_from_llm_response(
            project_name=project_name,
            project_type="game"
        )
    )
    
    # 从配置文件加载提示词，传入项目名称和路径
    project_name = os.path.basename(project_dir)
    prompt = format_prompt(
        "designer", "lead_create_framework",
        游戏想法=state['game_idea'],
        项目名称=project_name,
        项目路径=project_dir
    )
    
    # 使用流式输出
    stream_callback = state.get('stream_callback')
    if stream_callback:
        response = agent.run_stream(prompt, callback=lambda chunk: stream_callback(chunk, "主策划"))
    else:
        response = agent.run(prompt)
    
    # 解析JSON
    try:
        framework_data = json.loads(response)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            framework_data = json.loads(json_match.group())
        else:
            framework_data = {"framework": response, "modules": []}
    
    # 保存框架文档
    framework_doc = f"""# 游戏设计框架

## 游戏想法
{state['game_idea']}

## 整体框架
{framework_data.get('framework', '')}

## 模块划分
"""
    
    for i, module in enumerate(framework_data.get('modules', [])):
        framework_doc += f"""
### {i+1}. {module.get('module_name', f'模块{i+1}')}
- 模块ID: {module.get('module_id', f'module_{i:03d}')}
- 设计要点: {', '.join(module.get('design_points', []))}
- 输出要求: {module.get('output_requirements', '')}
- 设计约束: {module.get('constraints', '')}
"""
    
    # 保存框架文档到文件
    framework_path = os.path.join(project_dir, 'docs', 'framework.md')
    os.makedirs(os.path.dirname(framework_path), exist_ok=True)
    with open(framework_path, 'w', encoding='utf-8') as f:
        f.write(framework_doc)
    

    
    return {
        **state,
        "framework_doc_path": framework_path,
        "framework_data": framework_data,
        "design_modules": framework_data.get('modules', []),
        "module_docs_map": {}  # 初始化空映射，用于收集子策划文档
    }


def sub_designer_work(module_info: Dict[str, Any], game_idea: str, framework_doc_path: str, project_dir: str, stream_callback=None) -> Dict[str, Any]:
    """
    子策划：根据分配的TODO列表开发模块文档
    
    每个子策划只负责一个模块，读取自己的TODO list作为需求输入
    输出模块文档并保存到文件
    
    返回：
    - module_id: 模块ID
    - module_name: 模块名称
    - doc_path: 文档文件路径
    - doc_content: 文档内容摘要
    """
    from agent_base import OutputNormalizer
    
    agent = get_agent("designer_agent")
    
    # 设置Agent的output_normalizer当前项目
    project_name = os.path.basename(project_dir)
    agent.output_normalizer.set_current_project(
        OutputNormalizer().create_project_from_llm_response(
            project_name=project_name,
            project_type="game"
        )
    )
    
    module_name = module_info.get('module_name', '未知模块')
    module_id = module_info.get('module_id', 'unknown')
    
    # 从配置文件加载提示词
    # 注意：不直接读取文件内容传入prompt，而是让Agent使用read_file工具读取
    prompt = format_prompt(
        "designer", "sub_designer_work",
        模块名称=module_name,
        游戏想法=game_idea,
        框架文档路径=framework_doc_path,
        设计要点=module_info.get('design_points', []),
        输出要求=module_info.get('output_requirements', ''),
        设计约束=module_info.get('constraints', '')
    )
    
    # 让Agent先读取框架文档
    read_prompt = f"""
请先读取框架文档：{framework_doc_path}
然后基于该框架，完成以下任务：

{prompt}
"""
    
    # 使用流式输出
    if stream_callback:
        doc_content = agent.run_stream(read_prompt, callback=lambda chunk: stream_callback(chunk, f"子策划-{module_name}"))
    else:
        doc_content = agent.run(read_prompt)
    
    # 保存模块文档到文件
    doc_filename = f"{module_name.replace(' ', '_').replace('系统', '_system')}_design.md"
    doc_path = os.path.join(project_dir, 'docs', 'modules', doc_filename)
    os.makedirs(os.path.dirname(doc_path), exist_ok=True)
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(doc_content)
    
    return {
        "module_id": module_id,
        "module_name": module_name,
        "doc_path": doc_path,
        "doc_content": doc_content[:500] + "..." if len(doc_content) > 500 else doc_content  # 存储摘要
    }


def parallel_sub_designers(state: "GameDevState") -> "GameDevState":
    """
    并行启动所有子策划进行开发
    
    输入：
    - design_modules: 设计模块列表
    - framework_doc_path: 框架文档路径
    - project_dir: 项目目录
    
    输出：
    - module_docs_map: 模块文档映射
    """
    modules = state.get('design_modules', [])
    game_idea = state['game_idea']
    framework_doc_path = state.get('framework_doc_path', '')
    project_dir = state.get('project_dir', '.')
    
    module_docs_map = {}
    
    # 如果没有模块，直接返回空结果
    if not modules:
        return {
            **state,
            'module_docs_map': module_docs_map,
            'design_status': 'completed'
        }
    
    # 获取流式回调
    stream_callback = state.get('stream_callback')
    
    # 使用线程池并行执行子策划任务
    with ThreadPoolExecutor(max_workers=min(len(modules), 5)) as executor:
        # 提交所有任务
        future_to_module = {
            executor.submit(sub_designer_work, module, game_idea, framework_doc_path, project_dir, stream_callback): module
            for module in modules
        }
        
        # 收集结果
        for future in as_completed(future_to_module):
            module = future_to_module[future]
            try:
                result = future.result()
                module_id = result['module_id']
                module_docs_map[module_id] = result
            except Exception:
                pass
    
    return {**state, "module_docs_map": module_docs_map}


def lead_designer_merge_docs(state: "GameDevState") -> "GameDevState":
    """
    主策划：汇总所有子策划的文档，产出最终设计文档
    
    输入：
    - module_docs_map: 模块文档映射
    - framework_doc_path: 框架文档路径
    
    输出：
    - gdd_path: 最终GDD文档路径
    - game_design_doc: GDD内容
    
    优化：不直接读取所有文档内容传入prompt，而是让Agent使用工具读取
    """
    from agent_base import OutputNormalizer
    
    agent = get_agent("designer_agent")
    
    module_docs_map = state.get('module_docs_map', {})
    framework_doc_path = state.get('framework_doc_path', '')
    game_idea = state['game_idea']
    project_dir = state.get('project_dir', '.')
    
    # 设置Agent的output_normalizer当前项目
    project_name = os.path.basename(project_dir)
    agent.output_normalizer.set_current_project(
        OutputNormalizer().create_project_from_llm_response(
            project_name=project_name,
            project_type="game"
        )
    )
    
    # 收集所有模块文档路径
    module_doc_paths = []
    for module_id, doc_info in module_docs_map.items():
        doc_path = doc_info.get('doc_path', '')
        if os.path.exists(doc_path):
            module_doc_paths.append({
                "module_name": doc_info.get('module_name', '未知模块'),
                "doc_path": doc_path
            })
    
    # 从配置文件加载提示词
    prompt = format_prompt(
        "designer", "lead_merge_docs",
        游戏想法=game_idea,
        框架文档路径=framework_doc_path,
        模块文档列表=module_doc_paths
    )
    
    # 让Agent读取所有文档并生成GDD
    # 构建读取所有文档的指令
    read_docs_instruction = "请按顺序读取以下文档：\n"
    read_docs_instruction += f"1. 框架文档: {framework_doc_path}\n"
    for i, doc_info in enumerate(module_doc_paths, 2):
        read_docs_instruction += f"{i}. {doc_info['module_name']}: {doc_info['doc_path']}\n"
    
    read_docs_instruction += f"\n然后完成以下任务：\n\n{prompt}"
    
    # 使用流式输出
    stream_callback = state.get('stream_callback')
    if stream_callback:
        final_gdd = agent.run_stream(read_docs_instruction, callback=lambda chunk: stream_callback(chunk, "主策划"))
    else:
        final_gdd = agent.run(read_docs_instruction)
    
    # 保存最终文档
    gdd_path = os.path.join(project_dir, 'docs', 'GDD.md')
    with open(gdd_path, 'w', encoding='utf-8') as f:
        f.write(final_gdd)
    

    
    return {
        **state,
        "gdd_path": gdd_path,
        "game_design_doc": final_gdd
    }
