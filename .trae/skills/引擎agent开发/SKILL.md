---
name: "引擎agent开发"
description: "GameGodEngine项目的ReAct Agent开发技能，包含LLM配置、工具开发和流式输出实现。Invoke when modifying agent code, adding tools, or changing LLM parameters in the GameGodEngine project."
---

# 引擎 Agent 开发技能

## 项目概述

GameGodEngine 是一个基于 ReAct 模式的 AI Agent 项目，使用 Moonshot API (kimi-k2.5) 作为底层 LLM，支持文件读写工具和流式输出。

## ⚠️ 关键配置参数（禁止修改）

在修改代码时，**严禁修改**以下 LLM 参数：

```python
model="kimi-k2.5"
temperature=1
max_tokens=100000
```

这些参数在以下文件中使用：
- `agent_base/llm_provider.py` - LLM 提供者
- `agent_base/react_agent.py` - ReAct Agent 实现

## 项目结构

```
GameGodEngine/
├── main.py                      # 程序入口
├── agent_base/
│   ├── llm_provider.py          # LLM 封装（非流式/流式）
│   └── react_agent.py           # ReAct Agent（流式输出）
└── .trae/skills/引擎agent开发/   # 本技能文档
```

## 核心功能

### 1. LLM 提供者 (llm_provider.py)

**非流式函数：**
- `llm_ask(question)` - 基础问答
- `llm_set_and_ask(system, user)` - 带系统提示
- `llm_ask_with_memory(question, session_id)` - 带记忆

**流式函数：**
- `llm_ask_stream(question)` - 流式输出
- `llm_set_and_ask_stream(system, user)` - 带系统提示流式
- `llm_ask_with_memory_stream(question, session_id)` - 带记忆流式

**记忆管理：**
- `get_memory(session_id)` - 获取/创建记忆
- `clear_memory(session_id)` - 清除记忆
- `get_conversation_history(session_id)` - 获取对话历史

### 2. ReAct Agent (react_agent.py)

**核心类：** `ReActAgent`

**内置工具：**
- `read_file` - 读取文件内容
- `write_file` - 写入文件（格式：路径|内容）
- `list_files` - 列出目录文件

**主要方法：**
- `run_stream(question, callback, max_iterations)` - 流式运行
- `clear_memory()` - 清除记忆
- `get_memory()` - 获取记忆

**便捷函数：**
- `agent_run_stream(question, callback)` - 流式运行 Agent
- `agent_clear_memory()` - 清除 Agent 记忆
- `agent_get_memory()` - 获取 Agent 记忆

## ReAct 格式

Agent 使用以下格式进行推理：

```
问题：[用户的问题]
思考：我需要如何解决这个问题
行动：[工具名称]，参数：[工具参数]
观察：[工具执行结果]
...（重复思考/行动/观察）...
思考：我现在知道最终答案
最终答案：[给用户的最终回答]
```

## 添加新工具

要添加新工具，需要：

1. 创建工具类继承 `Tool` 基类
2. 实现 `run(self, input_str)` 方法
3. 在 `ReActAgent.__init__` 中注册工具

示例：

```python
class MyTool(Tool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="工具描述"
        )
    
    def run(self, input_str: str) -> str:
        # 实现工具逻辑
        return result
```

## 依赖包

项目使用以下核心依赖：
- `langchain_community` - 社区模型和工具
- `langchain_core` - 核心消息类型
- `pydantic` - 数据验证

**注意：** 不使用 `langchain` 主包（避免 PyCharm 识别问题）

## 修改注意事项

1. **不要修改 LLM 参数**（model/temperature/max_tokens）
2. 保持工具类的 `run` 方法返回字符串类型
3. 流式输出使用 `llm.stream()` 方法
4. 记忆使用 `ConversationBufferMemory` 或自定义列表实现
