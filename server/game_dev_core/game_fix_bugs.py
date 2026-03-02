"""
Bug修复模块 - 根据测试报告修复代码问题

文件映射说明：
- all_code_files_map: 代码文件映射（从state读取）
- test_results: 测试结果（从state读取）

优化：
- 移除所有长度限制，支持大文件
- 提示词从配置文件读取
- 文件内容通过read_file工具读取，不直接传入prompt
- 支持流式输出
"""

import os
from typing import Callable, Optional

from agent_base import get_agent
from game_dev_core import GameDevState
from config.prompt_loader import format_prompt


def _run_agent_with_stream(agent, prompt: str, agent_role: str, stream_callback: Optional[Callable[[str, str], None]] = None):
    """辅助函数：根据是否有流式回调选择run或run_stream"""
    if stream_callback:
        return agent.run_stream(prompt, callback=lambda chunk: stream_callback(chunk, agent_role))
    else:
        return agent.run(prompt)


def fix_bugs(state: GameDevState) -> GameDevState:
    """
    根据测试报告，让程序员修复问题
    
    输入（从state读取）：
    - all_code_files_map: 代码文件映射 {file_name -> file_path}
    - test_results: 测试结果（包含issues）
    
    输出（写入state）：
    - fixed_files: 修复的文件列表
    - fix_report: 修复报告
    """
    agent = get_agent("programmer_agent")
    
    # 从state读取信息
    all_code_files_map = state.get("all_code_files_map", {})
    test_results = state.get("test_results", {})
    project_dir = state.get("project_dir", ".")
    stream_callback = state.get("stream_callback")
    
    # 从test_results中提取问题
    issues = test_results.get("issues", [])
    
    if not issues:
        return {
            **state,
            "fixed_files": [],
            "fix_report": "没有需要修复的问题"
        }
    
    fixed_files = []
    fix_details = []
    
    # 按文件分组问题
    issues_by_file = {}
    for issue in issues:
        file_name = issue.get("file", "")
        if file_name:
            if file_name not in issues_by_file:
                issues_by_file[file_name] = []
            issues_by_file[file_name].append(issue)
    
    # 逐个文件修复
    for file_name, file_issues in issues_by_file.items():
        # 获取文件路径
        file_path = all_code_files_map.get(file_name)
        if not file_path or not os.path.exists(file_path):
            continue
        
        # 构建问题描述
        issues_description = "\n".join([
            f"- [{issue.get('type', '未知')}] {issue.get('description', '')}"
            for issue in file_issues
        ])
        

        
        # 从配置文件加载提示词
        prompt = format_prompt(
            "fix_bugs", "fix_code",
            文件名=file_name,
            问题列表=issues_description
        )
        
        # 让Agent读取文件并修复
        read_fix_instruction = f"请先读取文件：{file_path}\n\n然后完成以下任务：\n\n{prompt}"
        
        # 调用Agent修复代码（使用流式输出）
        fixed_code = _run_agent_with_stream(agent, read_fix_instruction, "修复程序", stream_callback)
        
        # 保存修复后的代码
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_code)
        
        fixed_files.append(file_name)
        fix_details.append({
            "file": file_name,
            "issues_fixed": len(file_issues)
        })
    
    # 生成修复报告
    fix_report = f"""# Bug修复报告

## 修复概况
- 修复文件数: {len(fixed_files)}
- 修复问题数: {len(issues)}

## 修复详情
"""
    for detail in fix_details:
        fix_report += f"""
### {detail['file']}
- 修复问题数: {detail['issues_fixed']}
"""
    
    # 保存修复报告
    report_path = os.path.join(project_dir, 'tests', 'fix_report.md')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(fix_report)
    

    
    # 修复后清除旧的测试结果，等待重新测试
    return {
        **state,
        "fixed_files": fixed_files,
        "fix_report": fix_report,
        "test_results": {},  # 清除旧的测试结果
        "all_tests_passed": False  # 重置测试状态
    }
