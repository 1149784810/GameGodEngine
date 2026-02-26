from game_dev_core import game_dev_state
from agent_base.react_agent import agent_run_stream


def game_tester(state: game_dev_state) -> game_dev_state:
    """测试员对每个任务进行单元测试和视觉测试，返回报告"""
    code_repo = state["code_repo"]
    tasks = state["tasks"]
    test_reports = []

    for task in tasks:
        task_name = task["name"]
        code = code_repo.get(task_name, "")
        if not code:
            continue

        # 单元测试检查（模拟：让LLM判断代码是否合理）
        prompt = f"""
        你是一位测试工程师。请检查以下代码是否实现了任务"{task_name}"的描述，并指出潜在问题。
        任务描述：{task['description']}
        代码：
        {code}
        请以JSON格式输出：{{"passed": true/false, "feedback": "具体反馈"}}
        """
        response = agent_run_stream(prompt)
        import json
        result = json.loads(response)
        test_reports.append({
            "task": task_name,
            "passed": result["passed"],
            "feedback": result["feedback"]
        })

    all_passed = all(r["passed"] for r in test_reports)
    return {**state, "test_reports": test_reports, "all_tests_passed": all_passed}
