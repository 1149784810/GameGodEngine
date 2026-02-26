import re
from typing import List, Dict, Any, Optional, Callable
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

from tools import ReadFileTool, WriteFileTool, ListFilesTool
from agent_base.llm_provider import (
    llm,
    get_memory,
    clear_memory,
    get_conversation_history,
    llm_stream_with_messages,
    save_to_memory
)


class ReActAgent:
    """
    ReAct Agent：通过推理-行动循环解决问题，支持流式输出
    使用 llm_provider 提供的 LLM 和记忆管理功能
    """

    def __init__(self, session_id: str = "react_agent_default"):
        self.session_id = session_id
        self.tools: Dict[str, Any] = {
            "read_file": ReadFileTool(),
            "write_file": WriteFileTool(),
            "list_files": ListFilesTool(),
        }

        self.tools_description = self._build_tools_description()

        self.system_prompt = f"""你是一个AI助手，可以使用以下工具帮助用户：

{self.tools_description}

请使用以下ReAct格式回答问题：

问题：[用户的问题]
思考：我需要如何解决这个问题
行动：[工具名称]，参数：[工具参数]
观察：[工具执行结果]
...（这个思考/行动/观察可以重复多次）...
思考：我现在知道最终答案
最终答案：[给用户的最终回答]

重要提示：
1. 每次只能使用一个工具
2. 必须等待观察结果后才能继续
3. 如果不需要工具，直接给出最终答案
4. 文件路径请使用绝对路径或相对于工作目录的路径
5. 工具名称必须是以下之一：read_file, write_file, list_files
6. 行动格式必须严格为：行动：[工具名称]，参数：[工具参数]

示例1 - 读取文件：
思考：用户想知道文件内容，我需要读取文件
行动：read_file，参数：test.txt
观察：文件内容：```...```
思考：我现在知道最终答案
最终答案：文件内容是...

示例2 - 列出目录：
思考：用户想查看目录内容
行动：list_files，参数：.
观察：目录 E:\... 的内容：📁 ...
思考：我现在知道最终答案
最终答案：目录包含以下文件...

示例3 - 写入文件：
思考：用户想创建一个新文件
行动：write_file，参数：new.txt|文件内容
观察：成功写入文件：...
思考：我现在知道最终答案
最终答案：文件已成功创建
"""

    def _build_tools_description(self) -> str:
        descriptions = []
        for name, tool in self.tools.items():
            descriptions.append(f"- {name}: {tool.description}")
        return "\n".join(descriptions)

    def _parse_action(self, text: str) -> Optional[tuple]:
        action_match = re.search(r'行动[：:]\s*(\w+)\s*[,，]\s*参数[：:]\s*(.+)', text)
        if action_match:
            return (action_match.group(1).strip(), action_match.group(2).strip())
        return None

    def _has_final_answer(self, text: str) -> bool:
        return "\n最终答案" in text

    def _extract_final_answer(self, text: str) -> str:
        match = re.search(r'最终答案[：:]\s*(.+)', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

    def _get_memory_messages(self) -> List[BaseMessage]:
        """获取当前会话的记忆消息"""
        return get_conversation_history(self.session_id)

    def _save_to_memory(self, question: str, answer: str):
        """保存对话到记忆"""
        save_to_memory(question, answer, self.session_id)

    def run_stream(self, question: str, callback: Optional[Callable[[str], None]] = None, max_iterations: int = 10) -> str:
        """
        流式运行ReAct Agent

        Args:
            question: 用户问题
            callback: 流式输出回调函数，接收每个chunk
            max_iterations: 最大迭代次数

        Returns:
            最终答案
        """
        if callback is None:
            callback = lambda x: print(x, end="", flush=True)

        # 构建消息列表
        messages = [SystemMessage(content=self.system_prompt)]
        messages.extend(self._get_memory_messages())
        messages.append(HumanMessage(content=f"问题：{question}\n思考："))

        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # 流式调用LLM - 输出思考过程
            callback(f"\n[思考 {iteration}] ")
            response_text = llm_stream_with_messages(messages, callback)

            # 检查是否有最终答案
            if self._has_final_answer(response_text):
                final_answer = self._extract_final_answer(response_text)
                callback(f"\n[完成]\n")

                # 保存到记忆
                self._save_to_memory(question, final_answer)

                return final_answer

            # 解析行动
            action = self._parse_action(response_text)
            if action:
                tool_name, tool_input = action
                callback(f"\n[行动] 使用工具: {tool_name}, 参数: {tool_input}\n")

                # 执行工具
                if tool_name in self.tools:
                    observation = self.tools[tool_name].run(tool_input)
                else:
                    observation = f"错误：未知工具 '{tool_name}'"

                callback(f"[观察] {observation[:200]}...\n" if len(observation) > 200 else f"[观察] {observation}\n")

                # 添加观察结果到对话
                messages.append(AIMessage(content=response_text))
                messages.append(HumanMessage(content=f"观察：{observation}"))
            else:
                callback("\n[提示] 请继续思考或使用工具\n")
                messages.append(AIMessage(content=response_text))
                messages.append(HumanMessage(content="请继续思考，如果需要使用工具请按格式输出，否则给出最终答案。"))

        return "达到最大迭代次数，未能完成回答。"

    def clear_memory(self):
        """清除当前会话的记忆"""
        clear_memory(self.session_id)

    def get_memory(self) -> List[str]:
        """获取当前会话的记忆内容"""
        history = get_conversation_history(self.session_id)
        result = []
        for msg in history:
            role = "用户" if isinstance(msg, HumanMessage) else "AI"
            result.append(f"{role}: {msg.content}")
        return result


# 全局Agent实例
_agent = None


def get_agent() -> ReActAgent:
    global _agent
    if _agent is None:
        _agent = ReActAgent()
    return _agent


def agent_run_stream(question: str, callback: Optional[Callable[[str], None]] = None) -> str:
    """流式运行Agent"""
    agent = get_agent()
    return agent.run_stream(question, callback)


def agent_clear_memory():
    """清除Agent记忆"""
    agent = get_agent()
    agent.clear_memory()


def agent_get_memory() -> List[str]:
    """获取Agent记忆"""
    agent = get_agent()
    return agent.get_memory()
