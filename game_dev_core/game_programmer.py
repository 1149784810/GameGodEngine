from game_dev_core import game_dev_state
from agent_base.react_agent import agent_run_stream


def lead_programmer(state: game_dev_state) -> game_dev_state:
    """主程序确定技术栈和项目结构"""
    gdd = state["game_design_doc"]
    tasks = state["tasks"]
    prompt = f"""
    你是主程序。根据设计文档和任务列表，选择合适的技术栈（如Pygame、Unity、Godot等），
    并描述项目骨架结构（目录、主要文件、依赖）。请简要说明。
    设计文档：{gdd}
    任务列表：{tasks}
    """
    response = agent_run_stream(prompt)
    # 简单分割技术栈和结构（演示用）
    parts = response.split("\n\n")
    tech_stack = parts[0] if parts else ""
    structure = parts[1] if len(parts) > 1 else ""
    return {**state, "tech_stack": tech_stack, "project_structure": structure}


def sub_programmer(state: game_dev_state) -> game_dev_state:
    """子程序实现各个任务，生成代码"""
    tasks = state["tasks"]
    code_repo = state["code_repo"].copy()
    tech_stack = state["tech_stack"]

    # 找到还没有代码的任务
    for task in tasks:
        task_name = task["name"]
        if not code_repo.get(task_name):  # 未实现
            prompt = f"""
            你是负责实现任务"{task_name}"的程序员。任务描述：{task['description']}
            使用技术栈：{tech_stack}
            请编写实现该功能的代码。只输出代码，不要解释。
            """
            code = agent_run_stream(prompt)
            code_repo[task_name] = code
            # 假设一次只做一个任务，但这里全部生成
    return {**state, "code_repo": code_repo}
