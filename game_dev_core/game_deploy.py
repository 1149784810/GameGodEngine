from game_dev_core import game_dev_state
from agent_base.react_agent import agent_run_stream


def deploy(state: game_dev_state) -> game_dev_state:
    """所有测试通过后，打包部署"""
    code_repo = state["code_repo"]
    # 模拟打包
    build = f"Build created at {__import__('datetime').datetime.now()}\n包含模块：{list(code_repo.keys())}"
    return {**state, "build_artifact": build}
