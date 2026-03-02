"""
游戏测试模块 - 确保如实汇报测试结果

测试原则：
1. 必须实际运行测试，不能出现幻觉
2. 每个测试用例都要有明确的通过/失败标记
3. 发现问题必须详细记录，不能遗漏
4. 测试报告必须真实反映测试情况

文件映射说明：
- all_code_files_map: 从state读取的代码文件映射
- main_entry_path: 主入口文件路径
- test_results: 测试结果
- test_report_path: 测试报告路径

优化：
- 移除所有长度限制，支持大文件
- 提示词从配置文件读取
- 支持流式输出
"""

import json
import os
import subprocess
import sys
from typing import List, Dict, Any, Tuple, Callable, Optional

from agent_base import get_agent
from game_dev_core.game_dev_state import GameDevState
from config.prompt_loader import format_prompt


def _run_agent_with_stream(agent, prompt: str, agent_role: str, stream_callback: Optional[Callable[[str, str], None]] = None):
    """辅助函数：根据是否有流式回调选择run或run_stream"""
    if stream_callback:
        return agent.run_stream(prompt, callback=lambda chunk: stream_callback(chunk, agent_role))
    else:
        return agent.run(prompt)


def game_tester(state: GameDevState) -> GameDevState:
    """
    游戏测试员：运行测试并如实汇报结果
    
    输入（从state读取）：
    - all_code_files_map: 代码文件映射 {file_name -> file_path}
    - main_entry_path: 主入口文件路径
    - project_dir: 项目目录
    
    输出（写入state）：
    - test_results: 测试结果
    - test_report_path: 测试报告路径
    - test_report: 测试报告内容
    - all_tests_passed: 是否通过测试
    
    测试流程：
    1. 检查代码文件（从all_code_files_map读取）
    2. 检查代码语法是否正确
    3. 尝试运行主程序（从main_entry_path读取）
    4. 记录所有测试结果
    5. 如实汇报，不隐瞒问题
    """
    from agent_base import OutputNormalizer
    
    agent = get_agent("tester_agent")
    
    project_dir = state.get('project_dir', '.')
    src_dir = os.path.join(project_dir, 'src')
    stream_callback = state.get('stream_callback')
    
    # 设置Agent的output_normalizer当前项目
    project_name = os.path.basename(project_dir)
    agent.output_normalizer.set_current_project(
        OutputNormalizer().create_project_from_llm_response(
            project_name=project_name,
            project_type="game"
        )
    )
    
    # 从state读取代码文件映射
    all_code_files_map = state.get('all_code_files_map', {})
    main_entry_path = state.get('main_entry_path', '')
    

    
    test_results = {
        "file_check": {},
        "syntax_check": {},
        "run_test": {},
        "issues": [],
        "passed": False
    }
    
    # 1. 检查代码文件（优先使用state中的映射，如果不存在则扫描目录）
    code_files_to_check = {}
    
    if all_code_files_map:
        # 使用state中的文件映射
        for file_name, file_path in all_code_files_map.items():
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                code_files_to_check[file_name] = file_path
                test_results["file_check"][file_name] = {"exists": True, "size": size, "path": file_path}
            else:
                test_results["file_check"][file_name] = {"exists": False, "path": file_path}
                test_results["issues"].append({
                    "type": "严重",
                    "description": f"代码文件不存在: {file_name}",
                    "file": file_path
                })
    elif os.path.exists(src_dir):
        # 回退到扫描目录
        code_files = [f for f in os.listdir(src_dir) if f.endswith('.py')]
        for f in code_files:
            file_path = os.path.join(src_dir, f)
            size = os.path.getsize(file_path)
            code_files_to_check[f] = file_path
            test_results["file_check"][f] = {"exists": True, "size": size, "path": file_path}
    else:
        test_results["issues"].append({
            "type": "严重",
            "description": "源代码目录不存在",
            "file": src_dir
        })
    
    # 2. 语法检查
    syntax_errors = []
    
    for file_name, file_path in code_files_to_check.items():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 尝试编译检查语法
            compile(code, file_path, 'exec')
            test_results["syntax_check"][file_name] = {"valid": True, "path": file_path}
        except SyntaxError as e:
            test_results["syntax_check"][file_name] = {"valid": False, "error": str(e), "path": file_path}
            syntax_errors.append({
                "file": file_name,
                "error": str(e),
                "line": e.lineno
            })
        except Exception as e:
            test_results["syntax_check"][file_name] = {"valid": False, "error": str(e), "path": file_path}
            syntax_errors.append({
                "file": file_name,
                "error": str(e)
            })
    
    if syntax_errors:
        test_results["issues"].extend([
            {
                "type": "严重",
                "description": f"语法错误: {err['file']} - {err['error']}",
                "file": err['file']
            }
            for err in syntax_errors
        ])
    
    # 3. 尝试运行主程序（优先使用state中的main_entry_path）
    main_file_to_run = main_entry_path if main_entry_path and os.path.exists(main_entry_path) else os.path.join(src_dir, 'main.py')
    main_file_name = os.path.basename(main_file_to_run)
    
    if os.path.exists(main_file_to_run):
        try:
            # 使用subprocess运行，设置超时
            result = subprocess.run(
                [sys.executable, main_file_to_run],
                capture_output=True,
                text=True,
                timeout=10,  # 10秒超时
                cwd=project_dir
            )
            
            if result.returncode == 0:
                test_results["run_test"][main_file_name] = {
                    "success": True,
                    "output": result.stdout[:500],  # 限制输出长度
                    "path": main_file_to_run
                }
            else:
                test_results["run_test"][main_file_name] = {
                    "success": False,
                    "error": result.stderr[:500],
                    "path": main_file_to_run
                }
                test_results["issues"].append({
                    "type": "严重",
                    "description": f"运行失败: {result.stderr[:200]}",
                    "file": main_file_name
                })
        
        except subprocess.TimeoutExpired:
            test_results["run_test"][main_file_name] = {
                "success": False,
                "error": "运行超时（超过10秒）",
                "path": main_file_to_run
            }
            test_results["issues"].append({
                "type": "警告",
                "description": "程序运行超时，可能存在死循环",
                "file": main_file_name
            })
            print(f"    ⚠ {main_file_name} - 运行超时")
        
        except Exception as e:
            test_results["run_test"][main_file_name] = {
                "success": False,
                "error": str(e),
                "path": main_file_to_run
            }
            test_results["issues"].append({
                "type": "严重",
                "description": f"运行异常: {str(e)}",
                "file": main_file_name
            })
            print(f"    ✗ {main_file_name} - 运行异常: {e}")
    else:
        test_results["issues"].append({
            "type": "严重",
            "description": f"主程序不存在: {main_file_name}",
            "file": main_file_to_run
        })
    
    # 4. 生成测试报告
    
    # 统计结果
    total_files = len(test_results["file_check"])
    syntax_valid = sum(1 for v in test_results["syntax_check"].values() if v.get("valid"))
    run_success = sum(1 for v in test_results["run_test"].values() if v.get("success"))
    total_issues = len(test_results["issues"])
    critical_issues = sum(1 for i in test_results["issues"] if i.get("type") == "严重")
    
    # 判断是否通过测试
    all_tests_passed = (
        total_files > 0 and
        syntax_valid == total_files and
        run_success > 0 and
        critical_issues == 0
    )
    
    test_results["passed"] = all_tests_passed
    test_results["summary"] = {
        "total_files": total_files,
        "syntax_valid": syntax_valid,
        "run_success": run_success,
        "total_issues": total_issues,
        "critical_issues": critical_issues
    }
    
    # 从配置文件加载提示词
    prompt = format_prompt(
        "tester", "test_report",
        代码文件数=total_files,
        语法正确=f"{syntax_valid}/{total_files}",
        运行成功=run_success,
        问题总数=total_issues,
        严重问题=critical_issues,
        详细结果=json.dumps(test_results, ensure_ascii=False, indent=2)
    )
    
    test_report = _run_agent_with_stream(agent, prompt, "测试员", stream_callback)
    
    # 保存测试报告
    report_path = os.path.join(project_dir, 'tests', 'test_report.md')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(test_report)
    

    
    return {
        **state,
        "test_results": test_results,
        "test_report_path": report_path,
        "test_report": test_report,
        "all_tests_passed": all_tests_passed
    }
