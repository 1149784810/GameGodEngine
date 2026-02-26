import game_dev_core.game_dev_state
from game_dev_core import game_dev_state
from game_dev_core.game_develop_workflow import game_workflow_graph

def run_game_dev(in_game_idea: str):
    initial_state = game_dev_state.GameDevState(game_idea=in_game_idea)

    # 执行图
    final_state = game_workflow_graph.invoke(initial_state)
    # 输出最终结果
    print("游戏设计文档：", final_state["game_design_doc"])
    print("\n任务列表：", final_state["tasks"])
    print("\n技术栈：", final_state["tech_stack"])
    print("\n代码仓库：", final_state["code_repo"].keys())
    print("\n测试报告：", final_state["test_reports"])
    print("\n构建产物：", final_state["build_artifact"])