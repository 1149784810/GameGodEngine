import os
from typing import Iterator, List, Optional, Callable
from langchain_community.chat_models.moonshot import MoonshotChat
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage
from langchain_classic.memory import ConversationBufferMemory

# set your API key once
os.environ.setdefault("MOONSHOT_API_KEY", "sk-ye0y8CRoH6TitnQwyau6psMD0eYOpyBegIebe7FoulcezZvL")

# create a shared llm instance using MoonshotChat (supports streaming)
llm = MoonshotChat(
    model="kimi-k2.5",
    temperature=1,
    max_tokens=100000,
)

# 全局记忆存储（支持多会话）
memories = {}


def get_memory(session_id: str = "default") -> ConversationBufferMemory:
    """获取或创建指定会话的记忆"""
    if session_id not in memories:
        memories[session_id] = ConversationBufferMemory(
            return_messages=True,
            human_prefix="用户",
            ai_prefix="AI"
        )
    return memories[session_id]


def clear_memory(session_id: str = "default"):
    """清除指定会话的记忆"""
    if session_id in memories:
        del memories[session_id]


def get_conversation_history(session_id: str = "default") -> List[BaseMessage]:
    """获取指定会话的对话历史"""
    memory = get_memory(session_id)
    history = memory.load_memory_variables({})
    return history.get("history", [])


def llm_ask(question: str) -> AIMessage:
    """Convenience wrapper that sends a human message and returns the answer."""
    return llm.invoke([HumanMessage(content=question)])


def llm_ask_stream(question: str) -> Iterator[str]:
    """Stream the answer from the LLM, yielding content chunks one by one."""
    for chunk in llm.stream([HumanMessage(content=question)]):
        yield chunk.content


def llm_set_and_ask(system_message: str, user_question: str) -> AIMessage:
    """Convenience wrapper that sends a system message and a human message and returns the answer."""
    return llm.invoke([
        SystemMessage(content=system_message),
        HumanMessage(content=user_question)
    ])


def llm_set_and_ask_stream(system_message: str, user_question: str) -> Iterator[str]:
    """Stream the answer with system prompt, yielding content chunks one by one."""
    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=user_question)
    ]
    for chunk in llm.stream(messages):
        yield chunk.content


def llm_ask_with_memory(question: str, session_id: str = "default") -> str:
    """
    带记忆的对话，AI会记住之前的对话内容
    
    Args:
        question: 用户问题
        session_id: 会话ID，用于区分不同对话
    """
    memory = get_memory(session_id)
    
    # 获取历史对话
    history = memory.load_memory_variables({})
    
    # 添加系统提示
    messages = [SystemMessage(content="你是一名游戏开发工程师，请记住之前的对话内容。")]

    # 添加历史消息
    if "history" in history:
        messages.extend(history["history"])
    
    # 添加当前问题
    messages.append(HumanMessage(content=question))
    
    # 调用LLM
    response = llm.invoke(messages)
    
    # 保存到记忆
    memory.save_context(
        {"input": question},
        {"output": response.content}
    )
    
    return response.content


def llm_ask_with_memory_stream(question: str, session_id: str = "default") -> Iterator[str]:
    """
    带记忆的流式对话
    
    Args:
        question: 用户问题
        session_id: 会话ID，用于区分不同对话
    """
    memory = get_memory(session_id)
    
    # 获取历史对话
    history = memory.load_memory_variables({})
    
    # 添加系统提示
    messages = [SystemMessage(content="你是一名游戏开发工程师，请记住之前的对话内容。")]

    # 添加历史消息
    if "history" in history:
        messages.extend(history["history"])
    
    # 添加当前问题
    messages.append(HumanMessage(content=question))
    
    # 流式调用LLM
    full_response = []
    for chunk in llm.stream(messages):
        content = chunk.content
        full_response.append(content)
        yield content
    
    # 保存到记忆
    memory.save_context(
        {"input": question},
        {"output": "".join(full_response)}
    )


def llm_set_and_ask_with_memory_stream(system: str, question: str, session_id: str = "default") -> Iterator[str]:
    """
    带记忆的流式对话，使用自定义系统提示
    
    Args:
        system: 系统提示
        question: 用户问题
        session_id: 会话ID，用于区分不同对话
    """
    memory = get_memory(session_id)
    
    # 获取历史对话
    history = memory.load_memory_variables({})
    
    # 添加系统提示
    messages = [SystemMessage(content=system)]

    # 添加历史消息
    if "history" in history:
        messages.extend(history["history"])
    
    # 添加当前问题
    messages.append(HumanMessage(content=question))
    
    # 流式调用LLM
    full_response = []
    for chunk in llm.stream(messages):
        content = chunk.content
        full_response.append(content)
        yield content
    
    # 保存到记忆
    memory.save_context(
        {"input": question},
        {"output": "".join(full_response)}
    )


def llm_stream_with_messages(messages: List[BaseMessage], callback: Optional[Callable[[str], None]] = None) -> str:
    """
    使用消息列表进行流式调用
    
    Args:
        messages: 消息列表
        callback: 流式输出回调函数
        
    Returns:
        完整的响应文本
    """
    if callback is None:
        callback = lambda x: print(x, end="", flush=True)
    
    response_text = ""
    for chunk in llm.stream(messages):
        content = chunk.content
        response_text += content
        callback(content)
    
    return response_text


def save_to_memory(question: str, answer: str, session_id: str = "default"):
    """
    保存对话到记忆
    
    Args:
        question: 用户问题
        answer: AI回答
        session_id: 会话ID
    """
    memory = get_memory(session_id)
    memory.save_context(
        {"input": question},
        {"output": answer}
    )
