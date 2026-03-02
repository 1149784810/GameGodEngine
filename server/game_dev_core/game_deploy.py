from game_dev_core import GameDevState
from agent_base import get_agent


def deploy(state: GameDevState) -> GameDevState:
    """所有测试通过后，打包部署"""
    code_repo = state["code_repo"]
    # 模拟打包
    build = f"Build created at {__import__('datetime').datetime.now()}\n包含模块：{list(code_repo.keys())}"
    return {**state, "build_artifact": build}
