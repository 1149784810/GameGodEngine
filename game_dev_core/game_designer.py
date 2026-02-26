from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from game_dev_core import game_dev_state
from agent_base.react_agent import *


def lead_designer(state: game_dev_state) -> game_dev_state:
    """主策划根据游戏想法撰写设计文档"""
    prompt = f"""
    你是一位经验丰富的游戏主策划。请根据以下游戏想法，撰写一份详细的游戏设计文档（GDD），
    包含游戏类型、核心玩法、角色设定、关卡设计、美术风格、技术需求等。
    想法：{state['game_idea']}
    请用清晰的章节结构输出。
    """
    response = agent_run_stream(prompt)
    return {**state, "game_design_doc": response}


def sub_designer(state: game_dev_state) -> game_dev_state:
    """子策划将设计文档拆解为具体开发任务"""
    gdd = state["game_design_doc"]
    prompt = f"""
    你是游戏子策划。根据以下设计文档，将开发工作拆解为5-8个具体任务，每个任务应包含：
    - 任务名称（如"玩家移动控制"）
    - 任务描述
    - 预计负责人角色（如"程序A"、"程序B"、"美术"）
    请在回答中只输出JSON数组格式的数据，不要附加其他任何非json的内容，每个元素包含name, description, assignee字段。
    设计文档：{gdd}
    """
    response = agent_run_stream(prompt)
    # 这里简化解析，假设LLM返回可解析的JSON
    import json
    tasks = json.loads(response)  # 实际可能需要更健壮的解析
    # 初始化code_repo占位
    code_repo = {task["name"]: "" for task in tasks}
    return {**state, "tasks": tasks, "code_repo": code_repo}
