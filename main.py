from agent_base.react_agent import agent_run_stream, agent_clear_memory, agent_get_memory
from test.test_game_dev import run_game_dev

if __name__ == "__main__":
    print("=" * 60)
    print("ReAct Agent 游戏开发助手已启动（流式输出模式）")
    print("=" * 60)
    print("可用命令：")
    print("  exit    - 退出程序")
    print("  clear   - 清除对话记忆")
    print("  history - 查看对话历史")
    print("=" * 60)
    print("示例问题：")
    print('  - 请读取 main.py 并解释它的功能')
    print('  - 创建一个 hello.txt 文件，内容为 Hello World')
    print("=" * 60)
    print()

    while True:
        try:
            question = input("> 请输入问题：").strip()

            if not question:
                continue

            if question.lower() == 'exit':
                print("再见!")
                break

            if question.lower() == 'clear':
                agent_clear_memory()
                print("记忆已清除\n")
                continue

            if question.lower() == 'history':
                history = agent_get_memory()
                if history:
                    print("\n=== 对话历史 ===")
                    for item in history:
                        print(item)
                    print("================\n")
                else:
                    print("暂无对话历史\n")
                continue

            if question.lower() == 'run dev':
                run_game_dev("开发一款极简连连看，不要过于复杂")
                continue

            # 流式运行Agent
            print("\n" + "-" * 40)
            final_answer = agent_run_stream(question)
            print("-" * 40)
            print(f"\n[最终答案]\n{final_answer}\n")

        except KeyboardInterrupt:
            print("\n再见!")
            break
        except Exception as e:
            print(f"\n错误: {e}\n")
            continue
