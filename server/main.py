"""
GameGodEngine - 多Agent架构入口
支持记忆系统和JSON配置
使用LangChain和LangGraph实现的ReAct Agent
"""

import json
from agent_base import get_agent, list_available_agents, list_available_tools


def print_help():
    """打印帮助信息"""
    print("=" * 60)
    print("GameGodEngine - 一款自然语言游戏引擎")
    print("=" * 60)
    print("\n可用命令：")
    print("  help              - 显示帮助")
    print("  agents            - 列出所有可用的Agent")
    print("  tools             - 列出所有可用的工具")
    print("  use <name>        - 切换Agent")
    print("  clear             - 清除当前Agent的记忆")
    print("  history           - 查看当前Agent的记忆历史")
    print("  plan              - 查看当前规划")
    print("  engine_test       - 测试不同工具")
    print("  exit              - 退出程序")
    print("=" * 60)


def print_agents():
    """打印可用Agent列表"""
    agents = list_available_agents()
    print("\n" + "=" * 60)
    print("可用的Agent（从config/agents/*.json加载）：")
    print("=" * 60)
    for name, desc in agents.items():
        print(f"  {name:20s} - {desc}")
    print("=" * 60)


def print_tools():
    """打印可用工具列表"""
    tools = list_available_tools()
    print("\n" + "=" * 60)
    print("可用的工具：")
    print("=" * 60)
    for name, desc in tools.items():
        print(f"  {name:20s} - {desc[:50]}...")
    print("=" * 60)


def print_memory_history(agent):
    """打印记忆历史"""
    history = agent.get_memory_history()
    if not history:
        print("\n当前Agent没有记忆历史")
        return
    
    print("\n" + "=" * 60)
    print("记忆历史：")
    print("=" * 60)
    for msg in history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        
        if role == "tool":
            tool_name = msg.get("tool_name", "unknown")
            print(f"\n[{timestamp}] 工具({tool_name}):")
            print(f"  {content[:200]}..." if len(content) > 200 else f"  {content}")
        else:
            print(f"\n[{timestamp}] {role}:")
            print(f"  {content[:200]}..." if len(content) > 200 else f"  {content}")
    print("=" * 60)


def print_current_plan(agent):
    """打印当前规划"""
    plan = agent.get_current_plan()
    if not plan:
        print("\n当前没有活动的规划")
        return
    
    print("\n" + "=" * 60)
    print("当前规划：")
    print("=" * 60)
    print(f"规划ID: {plan.get('plan_id', 'N/A')}")
    print(f"用户请求: {plan.get('user_request', 'N/A')}")
    print(f"创建时间: {plan.get('created_at', 'N/A')}")
    print(f"更新时间: {plan.get('updated_at', 'N/A')}")
    print(f"完成状态: {'已完成' if plan.get('is_completed') else '进行中'}")
    print("\n步骤列表：")
    
    for step in plan.get('steps', []):
        status = step.get('status', 'unknown')
        status_icon = {
            'completed': '✓',
            'failed': '✗',
            'in_progress': '→',
            'pending': '○'
        }.get(status, '?')
        
        print(f"\n  {status_icon} 步骤 {step.get('step_id', '?')}: {step.get('description', 'N/A')}")
        if step.get('tool_name'):
            print(f"     工具: {step['tool_name']}")
        print(f"     预期: {step.get('expected_result', 'N/A')}")
        if step.get('actual_result'):
            result = step['actual_result'][:100] + "..." if len(step['actual_result']) > 100 else step['actual_result']
            print(f"     实际: {result}")
    
    print("=" * 60)


def test_tools_menu(agent):
    """测试不同工具的菜单"""
    print("\n" + "=" * 60)
    print("工具测试菜单")
    print("=" * 60)
    print("\n可用工具：")
    print("  1. write_file  - 测试写入文件")
    print("  2. read_file   - 测试读取文件")
    print("  3. list_files  - 测试列出文件")
    print("  4. all         - 测试所有工具")
    print("  0. back        - 返回主菜单")
    print("=" * 60)
    
    while True:
        choice = input("\n请选择要测试的工具 (0-4): ").strip()
        
        if choice == "0" or choice.lower() == "back":
            print("返回主菜单")
            break
        
        elif choice == "1":
            print("\n--- 测试 write_file ---")
            result = agent.run_stream('创建一个测试文件 test_write.txt，内容为 "Hello from write_file tool!"')
            print(f"\n结果: {result}")
        
        elif choice == "2":
            print("\n--- 测试 read_file ---")
            # 先确保文件存在
            agent.run('创建一个测试文件 test_read.txt，内容为 "Hello from read_file tool!"')
            result = agent.run_stream('读取 test_read.txt 文件的内容')
            print(f"\n结果: {result}")
        
        elif choice == "3":
            print("\n--- 测试 list_files ---")
            result = agent.run_stream('列出当前目录的文件')
            print(f"\n结果: {result}")
        
        elif choice == "4":
            print("\n--- 测试所有工具 ---")
            print("\n[1/3] 测试 write_file...")
            agent.run_stream('创建一个测试文件 test_all.txt，内容为 "Testing all tools!"')
            
            print("\n[2/3] 测试 read_file...")
            agent.run_stream('读取 test_all.txt 文件的内容')
            
            print("\n[3/3] 测试 list_files...")
            agent.run_stream('列出当前目录中 test_ 开头的文件')
            
            print("\n所有工具测试完成！")
        
        else:
            print("无效选择，请重新输入")





def main():
    """主函数"""
    print_help()
    
    # 默认使用designer_agent
    current_agent_name = "designer_agent"
    try:
        current_agent = get_agent(current_agent_name)
        print(f"\n当前Agent: {current_agent_name}")
        print(f"记忆系统: {'启用' if current_agent.memory else '禁用'}")
        print(f"Agent类型: ReActAgent (LangChain + LangGraph)")
        print()
    except ValueError as e:
        print(f"\n错误: {e}")
        print(f"请确保 {current_agent_name} 存在")
        return
    
    while True:
        try:
            user_input = input("> ").strip()
            
            if not user_input:
                continue
            
            # 处理命令
            if user_input.lower() == 'exit':
                print("再见!")
                break
            
            if user_input.lower() == 'help':
                print_help()
                continue
            
            if user_input.lower() == 'agents':
                print_agents()
                continue
            
            if user_input.lower() == 'tools':
                print_tools()
                continue
            
            if user_input.lower().startswith('use '):
                agent_name = user_input[4:].strip()
                try:
                    current_agent = get_agent(agent_name)
                    current_agent_name = agent_name
                    print(f"已切换到Agent: {agent_name}")
                    print(f"记忆系统: {'启用' if current_agent.memory else '禁用'}")
                except ValueError as e:
                    print(f"错误: {e}")
                continue
            
            if user_input.lower() == 'clear':
                current_agent.clear_memory()
                print("记忆已清除")
                continue
            
            if user_input.lower() == 'history':
                print_memory_history(current_agent)
                continue
            
            if user_input.lower() == 'plan':
                print_current_plan(current_agent)
                continue
            
            if user_input.lower() == 'engine_test':
                test_tools_menu(current_agent)
                continue
            
            # 运行Agent
            print("\n" + "-" * 60)
            final_answer = current_agent.run_stream(user_input)
            print("-" * 60)
            print(f"\n[最终答案]\n{final_answer}\n")
            
        except KeyboardInterrupt:
            print("\n再见!")
            break
        except Exception as e:
            print(f"\n错误: {e}")
            import traceback
            traceback.print_exc()
            continue


if __name__ == "__main__":
    main()
