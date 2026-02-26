from langgraph.graph import StateGraph, END

from game_dev_core import game_designer
from game_dev_core import game_dev_state
from game_dev_core import game_programmer
from game_dev_core import game_tester
from game_dev_core import game_fix_bugs
from game_dev_core import game_deploy

# 初始化图
game_workflow_builder = StateGraph(game_dev_state.GameDevState)

# 添加节点
game_workflow_builder.add_node("lead_designer", game_designer.lead_designer)
game_workflow_builder.add_node("sub_designer", game_designer.sub_designer)
game_workflow_builder.add_node("lead_programmer", game_programmer.lead_programmer)
game_workflow_builder.add_node("sub_programmer", game_programmer.sub_programmer)
game_workflow_builder.add_node("tester", game_tester.game_tester)
game_workflow_builder.add_node("fix_bugs", game_fix_bugs.fix_bugs)
game_workflow_builder.add_node("deploy", game_deploy.deploy)

# 设置入口点
game_workflow_builder.set_entry_point("lead_designer")

# 添加边
game_workflow_builder.add_edge("lead_designer", "sub_designer")
game_workflow_builder.add_edge("sub_designer", "lead_programmer")
game_workflow_builder.add_edge("lead_programmer", "sub_programmer")
game_workflow_builder.add_edge("sub_programmer", "tester")

# 条件边：根据测试结果决定下一步
def after_test(state: game_dev_state.GameDevState):
    if state["all_tests_passed"]:
        return "deploy"
    else:
        return "fix_bugs"

game_workflow_builder.add_conditional_edges("tester", after_test)

# 修复后回到测试
game_workflow_builder.add_edge("fix_bugs", "tester")
game_workflow_builder.add_edge("deploy", END)

# 编译图
game_workflow_graph = game_workflow_builder.compile()