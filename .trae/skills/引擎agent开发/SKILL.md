---
name: "引擎agent开发"
description: "GameGodEngine项目的ReAct Agent开发技能，基于LangChain和LangGraph实现，支持规划系统、JSON配置、记忆系统、工具与Agent解耦、流式输出。Invoke when modifying agent code, adding tools, changing LLM parameters, working on game development workflow, or refactoring the ReAct Agent architecture in the GameGodEngine project."
---

# 引擎 Agent 开发技能

## 项目概述

GameGodEngine 是一个基于 **ReAct 模式** 的 AI Agent 项目，使用 **LangChain** 和 **LangGraph** 构建，支持 Moonshot API 作为底层 LLM。项目采用 **配置驱动架构** + **规划系统**，支持：

- **规划系统** - LLM生成任务规划，本地存储和校验，支持规划变更
- **JSON 配置文件** - 定义 Agent 行为和系统提示词
- **记忆系统** - 保存对话历史和规划状态
- **工具与 Agent 解耦** - 灵活组合，全局注册表
- **流式输出** - 实时显示规划、执行、观察全过程
- **游戏开发工作流** - 多角色协作

## ⚠️ 关键配置参数

模型参数在 JSON 配置文件中定义：

```json
{
  "model_settings": {
    "model": "kimi-k2.5",
    "temperature": 1.0,
    "max_tokens": 100000,
    "base_url": "https://api.moonshot.cn/v1"
  }
}
```

## 项目结构

```
GameGodEngine/
├── main.py                      # 程序入口
├── config/                      # 配置模块
│   ├── __init__.py
│   ├── agent_config.py          # 配置模型定义
│   ├── config_manager.py        # JSON 配置读取
│   └── agents/                  # JSON 配置文件
│       ├── designer_agent.json  # 游戏策划Agent
│       ├── programmer_agent.json # 程序员Agent
│       └── tester_agent.json    # 测试员Agent
├── agent_base/                  # Agent 基础模块
│   ├── __init__.py              # 导出 ReActAgent, Memory, Plan, Step
│   ├── react_agent.py           # ReAct Agent 实现（LangChain + LangGraph）
│   ├── agent_factory.py         # Agent 工厂（工具注入）
│   └── output_normalizer.py     # 输出规范器（文件路径规范化）
├── tools/                       # 工具模块
│   ├── __init__.py
│   └── file_tools.py            # 文件操作工具（@tool 装饰器）
├── game_dev_core/               # 游戏开发核心模块
│   ├── __init__.py
│   ├── game_designer.py         # 策划角色
│   ├── game_programmer.py       # 程序角色
│   ├── game_tester.py           # 测试角色
│   ├── game_fix_bugs.py         # Bug 修复模块
│   ├── game_deploy.py           # 部署模块
│   ├── game_dev_state.py        # 状态管理
│   └── game_develop_workflow.py # 开发工作流编排
├── test_react_agent.py          # 4步骤测试框架
└── .trae/skills/引擎agent开发/   # 本技能文档
```

## 核心架构

### ReAct Agent 工作流程

```
用户输入 → 规范化 → 生成规划 → 校验规划 → 单步执行 → 结果观察 → [循环] → 最终答案
```

**LangGraph 状态图：**
```
plan → validate → execute_step → observe → (继续或finalize) → finalize → END
```

### 1. 规划系统 (react_agent.py)

**核心类：**

```python
@dataclass
class Step:
    step_id: int                    # 步骤ID
    description: str                # 步骤描述
    tool_name: Optional[str]        # 工具名称
    tool_params: Dict[str, Any]     # 工具参数（content字段规划阶段留空）
    expected_result: str            # 预期结果
    status: Literal["pending", "in_progress", "completed", "failed"]
    actual_result: str              # 实际执行结果

@dataclass
class Plan:
    plan_id: str                    # 规划ID
    user_request: str               # 用户原始请求
    steps: List[Step]               # 步骤列表
    created_at: str                 # 创建时间
    updated_at: str                 # 更新时间
    is_completed: bool              # 是否完成
```

**规划生成流程：**
1. 用户输入规范化（分离用户内容 + Agent上下文）
2. LLM生成JSON格式规划
3. 本地解析并存储规划
4. 校验规划有效性（工具是否存在）

**重要原则：规划阶段不生成大段内容**
- `tool_params` 中的 `content` 字段规划阶段留空
- 实际内容在执行阶段通过 `_stream_llm_response` 流式生成
- 节省token，提高响应速度

### 2. ReActAgent 类 (react_agent.py)

**核心方法：**

```python
class ReActAgent:
    def __init__(self, config: AgentConfig, tools: List[BaseTool]):
        # 初始化LLM客户端、工具注册表、记忆系统、LangGraph工作流
        
    def _normalize_input(self, user_input: str) -> tuple[str, str]:
        """规范化用户输入：返回 (user_content, agent_context)"""
        
    def _generate_plan(self, user_input: str, agent_context: str) -> Optional[Plan]:
        """生成任务规划（规划阶段不生成具体内容）"""
        
    def _validate_plan(self, plan: Plan) -> tuple[bool, str]:
        """校验规划有效性"""
        
    def _execute_tool(self, tool_name: str, tool_params: Dict) -> str:
        """执行工具并返回结果"""
        
    def _check_plan_change(self, current_plan: Plan, llm_response: str) -> Optional[Plan]:
        """检测规划变更"""
        
    def _stream_llm_response(self, messages, callback) -> str:
        """流式调用LLM，逐字输出"""
        
    def run(self, question: str) -> str:
        """运行Agent（非流式）"""
        
    def run_stream(self, question: str, callback: Optional[Callable]) -> str:
        """流式运行Agent（实时输出）"""
```

### 3. 配置系统 (config/)

**JSON 配置文件格式：**

```json
{
  "name": "designer_agent",
  "description": "游戏策划Agent - 负责编写设计文档",
  "system_prompt": "你是游戏策划...",
  "max_iterations": 10,
  "model_settings": {
    "model": "kimi-k2.5",
    "temperature": 1.0,
    "max_tokens": 100000,
    "base_url": "https://api.moonshot.cn/v1"
  },
  "tools": ["read_file", "write_file", "list_files"],
  "memory_enabled": true,
  "memory_max_turns": 20
}
```

### 4. Agent 工厂 (agent_base/agent_factory.py)

```python
# 全局工具注册表
AgentFactory.register_tool(my_tool)   # 注册单个工具
AgentFactory.register_tools(tools)    # 批量注册工具

# 从 JSON 配置创建 Agent
agent = AgentFactory.create_agent("designer_agent")

# 便捷函数
agent = get_agent("designer_agent")
```

### 5. 工具模块 (tools/)

**使用 `@tool` 装饰器定义：**

```python
from langchain_core.tools import tool

@tool
def read_file(file_path: str) -> str:
    """读取指定文件的内容。
    
    Args:
        file_path: 文件路径
    
    Returns:
        文件内容
    """
    # 实现...
```

**内置工具：**
- `read_file` - 读取文件内容
- `write_file` - 写入文件
- `list_files` - 列出目录内容

### 6. 记忆系统 (react_agent.py)

```python
class Memory:
    def add_user_message(content)      # 添加用户消息
    def add_assistant_message(content) # 添加助手回复
    def add_tool_result(tool, result)  # 添加工具执行结果
    def add_plan(plan)                 # 添加规划
    def update_current_plan(plan)      # 更新当前规划
    def get_messages()                 # 获取历史消息
    def clear()                        # 清空记忆
```

## 输出规范器 (output_normalizer.py)

### 架构变更（重要）

**重构后的输出规范器不再使用正则表达式解析用户请求，而是将目录结构规则告知LLM，由LLM决定项目结构。**

### 职责

1. **提供工作区信息** - 向LLM提供当前工作区路径和目录结构规则
2. **创建项目目录** - 根据LLM返回的项目信息创建目录结构
3. **规范化文件路径** - 根据文件类型将文件放入正确的子目录

### 目录结构规则

```
projects/
├── {GameName}/              # 游戏项目
│   ├── docs/                # 策划文档（GDD、设计文档等）
│   ├── src/                 # 源代码
│   ├── assets/              # 资源文件
│   │   ├── sprites/         # 精灵图、图片资源
│   │   ├── audio/           # 音频资源
│   │   └── fonts/           # 字体文件
│   ├── config/              # 配置文件
│   ├── tests/               # 测试文件
│   └── build/               # 构建输出
│
├── {ProjectName}/           # 普通项目
│   ├── docs/                # 文档
│   ├── src/                 # 源代码
│   ├── config/              # 配置文件
│   └── tests/               # 测试文件
```

### 使用方式

#### 1. 获取工作区信息（供LLM参考）

```python
from agent_base import OutputNormalizer

normalizer = OutputNormalizer()
workspace_info = normalizer.get_workspace_info()
# 返回: {
#     "current_working_directory": "F:\\GameGodEngine",
#     "projects_base_dir": "F:\\GameGodEngine\\projects",
#     "directory_structure_rules": { ... },
#     "file_type_mapping": { ... }
# }
```

#### 2. 根据LLM响应创建项目

```python
# LLM根据工作区信息和用户需求，返回项目结构
project_info = normalizer.create_project_from_llm_response(
    project_name="连连看Game",  # 由用户输入或LLM建议
    project_type="game",        # "game" 或 "project"
    directory_structure=None    # 可选的自定义目录结构
)

# 设置当前项目（自动创建目录）
normalizer.set_current_project(project_info)
```

#### 3. 规范化文件路径

```python
# 根据文件类型自动确定子目录
normalized_path = normalizer.normalize_path("design.md", file_type="doc")
# 返回: "projects/连连看Game/docs/design.md"

normalized_path = normalizer.normalize_path("player.py", file_type="code")
# 返回: "projects/连连看Game/src/player.py"
```

### 文件类型映射

| 文件扩展名 | 目标目录 |
|-----------|---------|
| .md, .txt | docs/ |
| .py, .js, .ts | src/ |
| .json, .yaml, .yml | config/ |
| .png, .jpg, .jpeg | assets/sprites/ |
| .mp3, .wav, .ogg | assets/audio/ |
| .ttf, .otf | assets/fonts/ |

### 与LLM协作示例

在Agent的提示词中，可以包含工作区信息：

```python
# 构建Agent上下文时包含工作区信息
workspace_info = normalizer.get_workspace_info()

context = f"""
【当前工作区信息】
- 工作目录: {workspace_info['current_working_directory']}
- 项目基础目录: {workspace_info['projects_base_dir']}

【目录结构规则】
游戏项目目录结构:
- projects/{{GameName}}/docs/ - 策划文档
- projects/{{GameName}}/src/ - 源代码
- projects/{{GameName}}/assets/sprites/ - 图片资源
- projects/{{GameName}}/assets/audio/ - 音频资源
- projects/{{GameName}}/config/ - 配置文件

【文件类型映射】
- .md -> docs/
- .py -> src/
- .png -> assets/sprites/
- .mp3 -> assets/audio/

请根据以上规则，将文件输出到正确的位置。
"""
```

## 测试框架 (test_react_agent.py)

### 4步骤测试（快速版）

**注意：使用简单任务进行测试，避免耗时的复杂项目**

```python
# 步骤1: 规划生成测试 - 使用简单任务
def test_step_1_plan_generation(agent):
    """测试规划生成"""
    user_input = "创建一个hello.txt文件"  # 简单任务
    
# 步骤2: 规划校验测试
def test_step_2_plan_validation(agent, plan):
    """测试规划校验"""
    
# 步骤3: 工具执行测试 - 测试所有工具
def test_step_3_tool_execution(agent):
    """测试所有工具执行"""
    
# 步骤4: 完整工作流测试 - 使用简单多步骤任务
def test_step_4_full_workflow(agent):
    """测试完整工作流"""
    # 使用 "临时测试文件" 避免创建复杂项目
```

### 自动检测新工具

```python
def auto_test_new_tools(agent):
    """自动检测并提示测试新添加的工具"""
    standard_tools = {'read_file', 'write_file', 'list_files'}
    new_tools = set(available_tools.keys()) - standard_tools
    # 提示开发者为新工具编写测试
```

### 运行测试

```bash
# 运行完整测试（快速版）
python test_react_agent.py

# 输出示例：
# ============================================================
# ReAct Agent 4步骤完整测试（快速版）
# ============================================================
# 注意：使用简单任务进行测试，避免耗时操作
# 
# [步骤1] 规划生成测试
# ✓ 规划生成成功，共 1 个步骤
# [步骤2] 规划校验测试
# ✓ 规划校验通过
# [步骤3] 工具执行测试
# ✓ write_file: 成功写入文件
# ✓ read_file: 文件内容正确
# ✓ list_files: 找到 18 项
# [步骤4] 完整工作流测试
# ✓ 文件创建: 成功
# ✓ 规划执行: 2/2 步骤完成
# ✓ 所有测试通过!
```

## 使用指南

### 基本使用

```python
from agent_base import get_agent

# 获取 Agent - 游戏策划Agent
agent = get_agent("designer_agent")

# 运行
result = agent.run("创建一个游戏设计文档")

# 流式运行
result = agent.run_stream("列出文件")

# 查看当前规划
plan = agent.get_current_plan()

# 清除记忆
agent.clear_memory()
```

## 添加新工具

### 1. 定义工具

```python
# tools/my_tool.py
from langchain_core.tools import tool

@tool
def my_tool(param: str) -> str:
    """工具描述。"""
    return f"结果: {param}"
```

### 2. 注册工具

```python
# tools/__init__.py
from .my_tool import my_tool
all_tools = [my_tool] + file_tools
```

### 3. 添加到配置

```json
{
  "tools": ["read_file", "write_file", "my_tool"]
}
```

### 4. 更新测试框架

在 `test_react_agent.py` 的 `test_step_3_tool_execution` 中添加新工具的测试用例。

## 游戏开发工作流 (game_dev_core/)

### 完整开发流程

```
1. 主策划生成框架规范和任务分配（按模块：数值系统、战斗系统、UI系统等）
   ↓
2. 子策划并行开发各自模块文档（读取自己的TODO list）
   ↓
3. 主策划汇总所有文档，产出最终GDD
   ↓
4. 主程序搭建基础框架（游戏循环、对象管理、UI框架、事件系统）
   ↓
5. 主程序分配开发任务，生成TODO list
   ↓
6. 子程序并行开发各自模块代码（读取自己的TODO list）
   ↓
7. 主程序汇总代码，审核并修复问题
   ↓
8. 测试阶段（如实汇报，不隐瞒问题）
   ↓
9. 如有问题 → 修复 → 重新测试
   ↓
10. 测试通过 → 部署
```

### 角色职责

**主策划 (lead_designer)**
- 生成游戏整体框架
- 按模块分配任务（数值、战斗、UI等）
- 汇总子策划文档，产出最终GDD
- 只写文档，不写代码

**子策划 (sub_designer)**
- 读取分配的TODO list
- 并行开发各自模块的设计文档
- 只写文档，不写代码

**主程序 (lead_programmer)**
- 搭建基础框架（游戏循环、对象管理等）
- 分配编码任务
- 汇总、审核、修复子程序代码
- 产出最终可运行的代码

**子程序 (sub_programmer)**
- 读取分配的TODO list
- 并行开发各自模块的代码
- 实现具体功能

**测试 (tester)**
- 实际运行测试，不能出现幻觉
- 如实汇报所有问题
- 不隐瞒、不漏测
- 生成详细测试报告

### 使用工作流

```python
from game_dev_core import run_game_development

# 运行完整的游戏开发流程
final_state = run_game_development(
    game_idea="创建一个连连看游戏",
    project_name="连连看Game"  # 项目名称由用户输入
)

# 检查结果
print(f"测试通过: {final_state['all_tests_passed']}")
print(f"项目位置: {final_state['project_dir']}")
```

## 修改注意事项

### ⚠️ 配置优先原则（重要）

**新增功能或修改行为时，优先通过 config/ 目录下的 JSON 配置文件实现，而不是修改已写好的 Python 代码。**

✅ **正确做法：**
- 新增角色：创建新的 JSON 配置文件（如 `config/agents/new_role_agent.json`）
- 修改提示词：编辑对应的 JSON 文件中的 `system_prompt` 字段
- 新增工具：在 `tools/` 定义工具，然后在 JSON 配置的 `tools` 列表中添加
- 调整模型参数：修改 JSON 中的 `model_settings`

❌ **错误做法：**
- 不要修改 `react_agent.py` 中的核心逻辑
- 不要修改 `agent_factory.py` 中的工厂代码
- 不要修改已稳定的角色实现代码

### 项目名称来源

**项目名称必须由用户输入提供，而不是通过输出规范器解析用户请求获得。**

✅ **正确做法：**
```python
# 用户明确提供项目名称
final_state = run_game_development(
    game_idea="创建一个连连看游戏",
    project_name="连连看Game"  # 用户输入的项目名称
)
```

❌ **错误做法：**
```python
# 不要从用户请求中解析项目名称
project_info = normalizer.analyze_request(game_idea)  # 解析出的名称可能不符合用户期望
project_name = project_info.project_name  # 不要这样做
```

⚠️ **注意：输出规范器架构变更**

**重构后的输出规范器不再使用正则表达式解析用户请求。**

**新的工作流程：**
1. 调用 `get_workspace_info()` 获取工作区信息和目录结构规则
2. 将这些信息包含在Agent的提示词中
3. 由LLM根据规则决定文件输出位置
4. 调用 `create_project_from_llm_response()` 创建项目目录

**示例：**
```python
from agent_base import OutputNormalizer

normalizer = OutputNormalizer()

# 获取工作区信息（供LLM参考）
workspace_info = normalizer.get_workspace_info()

# 在Agent提示词中包含工作区信息
system_prompt = f"""
你是游戏开发助手。

【工作区信息】
当前工作目录: {workspace_info['current_working_directory']}
项目基础目录: {workspace_info['projects_base_dir']}

【目录结构规则】
{workspace_info['directory_structure_rules']}

【文件类型映射】
{workspace_info['file_type_mapping']}

请根据以上规则，将文件输出到正确的位置。
"""

# LLM决定项目结构和文件位置后，创建项目
project_info = normalizer.create_project_from_llm_response(
    project_name="连连看Game",  # 由用户输入
    project_type="game"
)
normalizer.set_current_project(project_info)
```

### 其他注意事项

1. **规划阶段不生成大段内容** - `content` 字段留空，执行阶段再生成
2. **流式输出** - 使用 `_stream_llm_response` 实现真正的逐字输出
3. **工具调用不重复打印内容** - write_file 只显示文件路径和长度
4. **规划可变更** - 执行过程中LLM可以建议调整规划
5. **LangGraph 状态管理** - 所有状态通过 AgentState 传递
6. **新工具自动检测** - 测试框架会自动发现未测试的新工具
7. **输出规范器** - 用于规范化文件路径，但不用于解析项目名称
8. **测试使用简单任务** - 避免"开发游戏"等耗时请求，使用"创建文件"等简单任务

## 测试与服务器管理

### 前端自动化测试

使用 Playwright 进行前端测试：

```bash
# 运行基础功能测试
python test_frontend.py

# 运行高级功能测试
python test_comprehensive.py
```

**测试完成后必须关闭服务器：**

```bash
# 查找并关闭 uvicorn 进程
Get-Process | Where-Object {$_.ProcessName -like "*uvicorn*"} | Stop-Process

# 或在运行测试的 Python 脚本中添加关闭逻辑
import subprocess
subprocess.run(["powershell", "-Command", "Get-Process uvicorn | Stop-Process -Force"])
```

### 测试脚本最佳实践

1. **启动服务器前检查** - 确保端口未被占用
2. **测试完成后清理** - 必须关闭服务器进程
3. **使用 headless 模式** - Playwright 使用 `headless=True` 静默运行
4. **处理对话框** - 重置按钮的 confirm 对话框需要特殊处理

```python
# 处理 confirm 对话框
page.on("dialog", lambda dialog: dialog.accept())

# 确保流式面板关闭后再点击其他元素
def ensure_stream_panel_closed(page):
    close_btn = page.query_selector(".btn-close")
    if close_btn and page.is_visible("#streamPanel"):
        close_btn.click()
        time.sleep(0.5)
```

### 服务器启动与关闭完整流程

```python
import subprocess
import time

# 1. 启动服务器
server_process = subprocess.Popen(
    ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"],
    cwd="server"
)
time.sleep(3)  # 等待服务器启动

# 2. 运行测试
try:
    run_tests()
finally:
    # 3. 必须关闭服务器
    server_process.terminate()
    server_process.wait(timeout=5)
    # 如果进程仍在运行，强制结束
    if server_process.poll() is None:
        server_process.kill()
```

## 调试技巧

### 查看完整执行流程

```
[阶段1: 生成规划]
[阶段2: 校验规划]
[阶段3: 执行步骤 X]
[阶段4: 结果观察与规划校验]
[阶段5: 生成最终答案]
```

### 检查规划状态

```python
plan = agent.get_current_plan()
if plan:
    for step in plan['steps']:
        print(f"步骤 {step['step_id']}: {step['status']}")
```

## GitHub 仓库

- 仓库地址：https://github.com/1149784810/GameGodEngine
- 类型：私有仓库
