---
name: "引擎agent开发"
description: "GameGodEngine项目的ReAct Agent开发技能，包含LLM配置、工具开发、流式输出和游戏开发工作流实现。Invoke when modifying agent code, adding tools, changing LLM parameters, or working on game development workflow in the GameGodEngine project."
---

# 引擎 Agent 开发技能

## 项目概述

GameGodEngine 是一个基于 ReAct 模式的 AI Agent 项目，使用 Moonshot API (kimi-k2.5) 作为底层 LLM，支持文件读写工具和流式输出。项目已扩展为完整的游戏开发引擎，包含策划、程序、测试、部署等角色工作流。

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
├── agent_base/                  # Agent 基础模块
│   ├── __init__.py
│   ├── llm_provider.py          # LLM 封装（非流式/流式）
│   └── react_agent.py           # ReAct Agent（流式输出，支持工具调用）
├── tools/                       # 工具模块
│   ├── __init__.py
│   ├── base.py                  # Tool 基类
│   └── file_tools.py            # 文件操作工具（read_file, write_file, list_files）
├── game_dev_core/               # 游戏开发核心模块
│   ├── __init__.py
│   ├── game_designer.py         # 策划角色（主策划、子策划）
│   ├── game_programmer.py       # 程序角色（主程序、子程序）
│   ├── game_tester.py           # 测试角色
│   ├── game_fix_bugs.py         # Bug修复模块
│   ├── game_deploy.py           # 部署模块
│   ├── game_dev_state.py        # 状态管理
│   └── game_develop_workflow.py # 开发工作流编排
├── test/                        # 测试模块
│   ├── __init__.py
│   └── test_game_dev.py         # 游戏开发测试
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
- `llm_stream_with_messages(messages, callback)` - 使用消息列表流式调用

**记忆管理：**
- `get_memory(session_id)` - 获取/创建记忆
- `clear_memory(session_id)` - 清除记忆
- `get_conversation_history(session_id)` - 获取对话历史
- `save_to_memory(question, answer, session_id)` - 保存对话到记忆

### 2. ReAct Agent (react_agent.py)

**核心类：** `ReActAgent`

**依赖关系：**
- 使用 `llm_provider` 提供的共享 LLM 实例
- 使用 `llm_provider` 提供的记忆管理系统
- 引用 `tools` 模块的工具类

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

### 3. 工具模块 (tools/)

**Tool 基类：**
```python
class Tool:
    def __init__(self, name: str, description: str)
    def run(self, input_str: str) -> str
```

**文件工具：**
- `ReadFileTool` - 读取文件，支持绝对/相对路径
- `WriteFileTool` - 写入文件，自动创建目录
- `ListFilesTool` - 列出目录内容

### 4. 游戏开发工作流 (game_dev_core/)

**策划模块 (game_designer.py)：**
- `lead_designer(state)` - 主策划撰写设计文档
- `sub_designer(state)` - 子策划拆解开发任务

**程序模块 (game_programmer.py)：**
- `lead_programmer(state)` - 主程序确定技术栈
- `sub_programmer(state)` - 子程序实现任务代码

**测试模块 (game_tester.py)：**
- `tester(state)` - 执行单元测试，生成测试报告

**Bug修复 (game_fix_bugs.py)：**
- `fix_bugs(state)` - 根据测试报告修复代码

**部署模块 (game_deploy.py)：**
- `deploy(state)` - 打包部署

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

1. 在 `tools/` 目录创建工具类继承 `Tool` 基类
2. 实现 `run(self, input_str)` 方法
3. 在 `tools/__init__.py` 中导出
4. 在 `ReActAgent.__init__` 中注册工具

示例：

```python
# tools/my_tool.py
from .base import Tool

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

```python
# tools/__init__.py
from .my_tool import MyTool
__all__ = [..., "MyTool"]
```

```python
# agent_base/react_agent.py
from tools import ..., MyTool

self.tools = {
    ...,
    "my_tool": MyTool(),
}
```

## 依赖包

项目使用以下核心依赖：
- `langchain_community` - 社区模型和工具
- `langchain_core` - 核心消息类型
- `langchain_classic` - 记忆管理
- `pydantic` - 数据验证

**注意：** 不使用 `langchain` 主包（避免 PyCharm 识别问题）

## 修改注意事项

1. **不要修改 LLM 参数**（model/temperature/max_tokens）
2. **保持工具类的 `run` 方法返回字符串类型**
3. **流式输出使用 `llm.stream()` 方法**
4. **记忆使用 `llm_provider` 提供的统一管理系统**
5. **工具类应单独放在 `tools/` 目录**
6. **游戏开发模块使用 `agent_run_stream` 而非 `llm_ask`**

## GitHub 仓库

- 仓库地址：https://github.com/1149784810/GameGodEngine
- 类型：私有仓库
- 已提交：agent_base, tools, game_dev_core, test 等模块
