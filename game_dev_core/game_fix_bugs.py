from game_dev_core import game_dev_state
from agent_base.react_agent import agent_run_stream


def fix_bugs(state: game_dev_state) -> game_dev_state:
    """根据测试报告，让对应程序员修复问题"""
    reports = state["test_reports"]
    code_repo = state["code_repo"].copy()

    for report in reports:
        if not report["passed"]:
            task_name = report["task"]
            old_code = code_repo[task_name]
            feedback = report["feedback"]
            prompt = f"""
            你是负责任务"{task_name}"的程序员。之前的代码存在以下问题：
            {feedback}
            请根据反馈修复代码。只输出修复后的完整代码。
            原代码：
            {old_code}
            """
            new_code = agent_run_stream(prompt)
            code_repo[task_name] = new_code

    # 修复后清除旧测试报告，等待重新测试
    return {**state, "code_repo": code_repo, "test_reports": []}
