"""
使用LangChain和LangGraph实现的ReAct Agent - 支持真正的流式输出
核心特性：
1. 用户输入规范化（分离用户内容和agent内容）
2. 规划存储和本地校验
3. 单步执行循环
4. 结果检测和规划变更检测
5. 真正的流式输出（逐字输出）
"""

import os
import json
import re
import sys
from typing import List, Optional, Callable, Dict, Any, TypedDict, Annotated, Literal
from datetime import datetime
from dataclasses import dataclass, field
from openai import OpenAI
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, END
from langgraph.types import Command

from config import AgentConfig
from .output_normalizer import OutputNormalizer, ProjectInfo


@dataclass
class Step:
    """规划中的单个步骤"""
    step_id: int
    description: str
    tool_name: Optional[str] = None
    tool_params: Dict[str, Any] = field(default_factory=dict)
    expected_result: str = ""
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    actual_result: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "tool_name": self.tool_name,
            "tool_params": self.tool_params,
            "expected_result": self.expected_result,
            "status": self.status,
            "actual_result": self.actual_result
        }


@dataclass
class Plan:
    """任务规划"""
    plan_id: str
    user_request: str
    steps: List[Step] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_completed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "user_request": self.user_request,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_completed": self.is_completed
        }
    
    def get_current_step(self) -> Optional[Step]:
        """获取当前待执行的步骤"""
        for step in self.steps:
            if step.status == "pending":
                return step
        return None
    
    def get_next_step(self) -> Optional[Step]:
        """获取下一个待执行的步骤"""
        found_current = False
        for step in self.steps:
            if found_current and step.status == "pending":
                return step
            if step.status == "pending":
                found_current = True
        return None
    
    def update_step_status(self, step_id: int, status: str, result: str = ""):
        """更新步骤状态"""
        for step in self.steps:
            if step.step_id == step_id:
                step.status = status
                step.actual_result = result
                self.updated_at = datetime.now().isoformat()
                break
    
    def check_all_completed(self) -> bool:
        """检查是否所有步骤都已完成"""
        return all(step.status in ["completed", "failed"] for step in self.steps)


class Memory:
    """增强的记忆系统 - 支持规划和执行历史"""
    
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.messages: List[Dict[str, Any]] = []
        self.plans: List[Plan] = []
        self.current_plan: Optional[Plan] = None
    
    def add_user_message(self, content: str):
        self.messages.append({
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self._trim_memory()
    
    def add_assistant_message(self, content: str):
        self.messages.append({
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self._trim_memory()
    
    def add_tool_result(self, tool_name: str, result: str):
        self.messages.append({
            "role": "tool",
            "tool_name": tool_name,
            "content": result,
            "timestamp": datetime.now().isoformat()
        })
        self._trim_memory()
    
    def add_plan(self, plan: Plan):
        """添加新的规划"""
        self.plans.append(plan)
        self.current_plan = plan
    
    def update_current_plan(self, plan: Plan):
        """更新当前规划"""
        self.current_plan = plan
        for i, p in enumerate(self.plans):
            if p.plan_id == plan.plan_id:
                self.plans[i] = plan
                break
    
    def get_messages(self) -> List[Dict[str, str]]:
        result = []
        for msg in self.messages:
            if msg["role"] == "tool":
                result.append({
                    "role": "user",
                    "content": f"[工具{msg['tool_name']}执行结果] {msg['content']}"
                })
            else:
                result.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        return result
    
    def clear(self):
        self.messages.clear()
        self.plans.clear()
        self.current_plan = None
    
    def _trim_memory(self):
        while len(self.messages) > self.max_turns * 2:
            self.messages.pop(0)


class AgentState(TypedDict):
    """LangGraph状态定义"""
    messages: List[Dict[str, str]]
    user_input: str
    agent_context: str
    iteration_count: int
    final_answer: Optional[str]
    current_plan: Optional[Plan]
    current_step: Optional[Step]
    last_observation: str
    plan_validated: bool
    stream_callback: Optional[Callable[[str], None]]


class ReActAgent:
    """
    使用LangChain和LangGraph实现的ReAct Agent - 支持真正的流式输出
    
    核心流程：
    1. 用户输入规范化 -> 生成规划
    2. 规划存储和校验
    3. 单步执行循环（思考-行动-观察）
    4. 结果检测和规划变更
    5. 真正的流式输出（逐字输出）
    """
    
    def __init__(self, config: AgentConfig, tools: List[BaseTool]):
        self.config = config
        self.tools = tools
        self.tools_by_name = {tool.name: tool for tool in tools}
        
        # 创建OpenAI客户端
        model_settings = config.model_settings
        api_key = model_settings.api_key
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=model_settings.base_url
        )
        
        self.model_settings = model_settings
        
        # 初始化记忆系统
        if config.memory_enabled:
            self.memory = Memory(max_turns=config.memory_max_turns)
        else:
            self.memory = None
        
        # 初始化输出规范器
        self.output_normalizer = OutputNormalizer()
        self.current_project: Optional[ProjectInfo] = None
        
        # 构建LangGraph工作流
        self.workflow = self._build_workflow()
    
    def _normalize_input(self, user_input: str) -> tuple[str, str]:
        """规范化用户输入"""
        user_content = user_input
        agent_context = self._build_agent_context()
        return user_content, agent_context
    
    def _build_agent_context(self) -> str:
        """构建agent附加内容"""
        cwd = os.getcwd()
        tools_info = []
        for name, tool in self.tools_by_name.items():
            tools_info.append(f"- {name}: {tool.description}")
        
        # 获取工作区信息
        workspace_info = self.output_normalizer.get_workspace_info()
        workspace_info_str = f"""
【工作区信息】
- 当前工作目录: {workspace_info['current_working_directory']}
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
"""
        
        context = f"""我当前的工作目录为：{cwd}
我现在能用的工具有：
{chr(10).join(tools_info)}
{workspace_info_str}

请你将我如何完成用户的需求拆分成流程规划，并告诉我应该采用什么行为。
每一步都由以下要素构成：
1. 步骤描述：这一步要做什么（简要描述，不要生成具体内容）
2. 工具调用：使用什么工具（如果有）
3. 工具参数：工具需要的参数（仅包含file_path等元数据，不包含content）
4. 预期结果：这一步应该返回什么结果

【重要规则 - 严格遵守】
- 规划阶段只生成步骤框架，不生成实际文档内容或代码
- 如果需要写入文件，在tool_params中**只指定file_path，不要包含content字段**
- 实际的内容生成（如文档正文、代码实现）在**执行阶段**由LLM动态生成
- 规划中严禁包含：游戏设计文档全文、代码实现、配置文件内容等大段文本
- 规划中的tool_params应该只包含元数据（如file_path），不包含实际内容

【文件输出规范 - 严格遵守】
- 所有文件必须放在 projects/{{GameName}}/ 目录结构下
- 策划文档 -> projects/{{GameName}}/docs/ 目录
- 源代码 -> projects/{{GameName}}/src/ 目录
- 配置文件 -> projects/{{GameName}}/config/ 目录
- 游戏资源 -> projects/{{GameName}}/assets/ 下的相应子目录
  - 图片资源 -> assets/sprites/
  - 音频资源 -> assets/audio/
  - 字体文件 -> assets/fonts/
- 测试文件 -> projects/{{GameName}}/tests/ 目录
- 在tool_params中**只需要指定文件名**（如 "game_design.md"），系统会自动处理完整路径
- 如果不确定当前目录结构，**必须先使用 list_files 工具查看**
- 严禁将文件输出到 projects/{{GameName}}/ 之外的目录

请以JSON格式返回规划，格式如下：
{{
    "steps": [
        {{
            "step_id": 1,
            "description": "步骤描述（简要）",
            "tool_name": "工具名称（可选）",
            "tool_params": {{"file_path": "文件名（不含路径）"}},
            "expected_result": "预期结果描述"
        }}
    ]
}}

【示例】
{{
    "steps": [
        {{
            "step_id": 1,
            "description": "创建游戏设计文档框架",
            "tool_name": "write_file",
            "tool_params": {{"file_path": "game_design.md"}},
            "expected_result": "创建空的GDD文件，内容将在执行阶段生成"
        }},
        {{
            "step_id": 2,
            "description": "实现玩家控制器",
            "tool_name": "write_file",
            "tool_params": {{"file_path": "player_controller.py"}},
            "expected_result": "创建空的代码文件，代码将在执行阶段生成"
        }}
    ]
}}"""
        return context
    
    def _parse_plan_from_llm(self, text: str) -> Optional[Plan]:
        """从LLM响应中解析规划 - 改进版，更健壮"""
        try:
            # 尝试找到JSON代码块
            json_patterns = [
                r'```json\s*([\s\S]*?)\s*```',  # Markdown代码块
                r'```\s*([\s\S]*?)\s*```',       # 普通代码块
                r'\{[\s\S]*"steps"[\s\S]*?\}(?=\s*$|\s*\n)',  # 直接JSON
            ]
            
            json_str = None
            for pattern in json_patterns:
                match = re.search(pattern, text, re.MULTILINE)
                if match:
                    json_str = match.group(1) if match.groups() else match.group(0)
                    break
            
            if not json_str:
                # 尝试直接解析整个文本
                json_str = text
            
            # 清理可能的注释和多余内容
            json_str = json_str.strip()
            
            # 找到最外层的JSON对象
            brace_count = 0
            start_idx = -1
            for i, char in enumerate(json_str):
                if char == '{':
                    if brace_count == 0:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx != -1:
                        json_str = json_str[start_idx:i+1]
                        break
            
            plan_data = json.loads(json_str)
            
            plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            plan = Plan(plan_id=plan_id, user_request="", steps=[])
            
            for step_data in plan_data.get("steps", []):
                step = Step(
                    step_id=step_data.get("step_id", 0),
                    description=step_data.get("description", ""),
                    tool_name=step_data.get("tool_name"),
                    tool_params=step_data.get("tool_params", {}),
                    expected_result=step_data.get("expected_result", "")
                )
                plan.steps.append(step)
            
            return plan
            
        except Exception:
            pass
        
        return None
    
    def _stream_llm_response(self, messages: List[Dict[str, str]], callback: Optional[Callable[[str], None]]) -> str:
        """
        流式调用LLM并实时输出
        
        Args:
            messages: 消息列表
            callback: 流式输出回调函数
            
        Returns:
            完整的响应文本
        """
        full_text = ""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_settings.model,
                messages=messages,
                temperature=self.model_settings.temperature,
                max_tokens=self.model_settings.max_tokens,
                stream=True  # 启用流式输出
            )
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_text += content
                    if callback:
                        callback(content)
        except Exception as e:
            error_msg = f"\n[流式输出错误: {e}]\n"
            if callback:
                callback(error_msg)
            # 回退到非流式调用
            response = self.client.chat.completions.create(
                model=self.model_settings.model,
                messages=messages,
                temperature=self.model_settings.temperature,
                max_tokens=self.model_settings.max_tokens
            )
            full_text = response.choices[0].message.content
            if callback:
                callback(full_text)
        
        return full_text
    
    def _generate_plan(self, user_input: str, agent_context: str, callback: Optional[Callable[[str], None]] = None) -> Optional[Plan]:
        """生成任务规划（支持流式输出）"""
        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": f"用户请求：{user_input}\n\n{agent_context}"}
        ]
        
        if callback:
            callback("\n[AI正在思考规划...]\n")
        
        text = self._stream_llm_response(messages, callback)
        
        if callback:
            callback("\n")  # 换行
        
        plan = self._parse_plan_from_llm(text)
        if plan:
            plan.user_request = user_input
        
        return plan
    
    def _execute_tool(self, tool_name: str, tool_params: Dict[str, Any]) -> str:
        """执行工具并返回结果"""
        if tool_name not in self.tools_by_name:
            return f"错误：未找到工具 '{tool_name}'"
        
        tool = self.tools_by_name[tool_name]
        
        try:
            result = tool.invoke(tool_params)
            return result
        except Exception as e:
            return f"工具执行错误：{str(e)}"
    
    def _validate_plan(self, plan: Plan) -> tuple[bool, str]:
        """校验规划的有效性"""
        if not plan.steps:
            return False, "规划中没有步骤"
        
        for step in plan.steps:
            if step.tool_name and step.tool_name not in self.tools_by_name:
                return False, f"步骤 {step.step_id} 使用了未知工具: {step.tool_name}"
        
        return True, "规划校验通过"
    
    def _check_plan_change(self, current_plan: Plan, llm_response: str) -> Optional[Plan]:
        """检查LLM响应中是否包含规划变更"""
        if '"steps"' in llm_response or "新的规划" in llm_response:
            new_plan = self._parse_plan_from_llm(llm_response)
            if new_plan:
                new_plan.user_request = current_plan.user_request
                for i, step in enumerate(new_plan.steps):
                    if i < len(current_plan.steps):
                        old_step = current_plan.steps[i]
                        if old_step.status == "completed":
                            step.status = "completed"
                            step.actual_result = old_step.actual_result
                return new_plan
        
        return None
    
    def _detect_step_from_response(self, text: str, expected_tool: Optional[str] = None) -> Optional[tuple[str, Dict[str, Any]]]:
        """从LLM响应中检测工具调用"""
        # 改进的正则表达式，支持更多格式
        patterns = [
            r'行动[：:]\s*(\w+)\s*[,，]?\s*参数[：:]\s*(\{[\s\S]*?\})',
            r'(?:工具|Action)[：:]\s*(\w+)\s*(?:参数|Input)[：:]\s*(\{[\s\S]*?\})',
            r'(?:使用|use)\s*(\w+).*?(?:参数|with).*?(\{[\s\S]*?\})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                tool_name = match.group(1).strip()
                tool_input = match.group(2).strip()
                
                try:
                    params = json.loads(tool_input)
                    return tool_name, params
                except:
                    pass
        
        # 如果没有匹配到JSON格式，尝试匹配简单格式
        simple_patterns = [
            r'行动[：:]\s*(\w+)\s*[,，]?\s*参数[：:]\s*(.+?)(?:\n|$)',
            r'(?:工具|Action)[：:]\s*(\w+)\s*(?:参数|Input)[：:]\s*(.+?)(?:\n|$)',
        ]
        
        for pattern in simple_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                tool_name = match.group(1).strip()
                tool_input = match.group(2).strip()
                
                params = {}
                if "|" in tool_input:
                    parts = tool_input.split("|")
                    if len(parts) >= 2:
                        params["file_path"] = parts[0].strip().strip('"').strip("'")
                        params["content"] = parts[1].strip().strip('"').strip("'")
                else:
                    # 尝试解析 key=value 格式
                    if "=" in tool_input:
                        for part in tool_input.split(","):
                            if "=" in part:
                                k, v = part.split("=", 1)
                                params[k.strip()] = v.strip().strip('"').strip("'")
                    else:
                        params["input"] = tool_input
                
                return tool_name, params
        
        # 如果指定了期望的工具，但没有检测到，尝试从文本中提取
        if expected_tool and expected_tool in text:
            # 尝试提取文件路径
            file_match = re.search(r'["\']?(\w+\.\w+)["\']?', text)
            if file_match:
                return expected_tool, {"file_path": file_match.group(1)}
        
        return None
    
    # ========== LangGraph节点函数 ==========
    
    def _plan_node(self, state: AgentState) -> AgentState:
        """规划节点：生成初始规划"""
        user_input = state["user_input"]
        agent_context = state["agent_context"]
        callback = state.get("stream_callback")
        
        # 只通过回调发送阶段信息，不打印到控制台
        if callback:
            callback(f"[阶段: 生成规划] 用户输入: {user_input[:50]}...\n")
        
        # 生成规划（流式）- LLM流式内容通过callback发送到前端
        plan = self._generate_plan(user_input, agent_context, callback)
        
        if plan and callback:
            callback(f"\n[规划完成] 共 {len(plan.steps)} 个步骤\n")
        
        return {
            **state,
            "current_plan": plan,
            "plan_validated": False
        }
    
    def _validate_node(self, state: AgentState) -> AgentState:
        """校验节点：校验规划有效性"""
        plan = state["current_plan"]
        callback = state.get("stream_callback")
        
        if not plan:
            if callback:
                callback("[错误] 未能生成有效规划\n")
            return {
                **state,
                "plan_validated": False,
                "final_answer": "未能生成有效规划"
            }
        
        is_valid, message = self._validate_plan(plan)
        
        if callback:
            callback(f"[校验: {message}]\n")
        
        if self.memory and is_valid:
            self.memory.add_plan(plan)
        
        return {
            **state,
            "plan_validated": is_valid
        }
    
    def _execute_step_node(self, state: AgentState) -> AgentState:
        """执行步骤节点：执行当前步骤"""
        plan = state["current_plan"]
        messages = state["messages"]
        callback = state.get("stream_callback")
        
        if not plan:
            return state
        
        current_step = plan.get_current_step()
        
        if not current_step:
            if callback:
                callback("[所有步骤已完成]\n")
            return {
                **state,
                "current_step": None
            }
        
        if callback:
            callback(f"[执行步骤 {current_step.step_id}] {current_step.description}\n")
        
        current_step.status = "in_progress"
        
        # 构建消息调用LLM
        step_messages = messages.copy()
        
        # 判断是否需要生成内容
        need_generate_content = (current_step.tool_name == "write_file" and 
                                 (not current_step.tool_params.get("content") or 
                                  current_step.tool_params.get("content") == ""))
        
        if need_generate_content:
            content_prompt = """【重要】此步骤需要写入文件，但content参数为空。
请你根据步骤描述和用户需求，生成完整的文件内容。
内容应该详细、完整，符合文件类型要求。

生成内容后，使用write_file工具写入文件。"""
        else:
            content_prompt = "请决定如何执行此步骤。"
        
        step_messages.append({
            "role": "user",
            "content": f"""当前步骤: {current_step.description}
预期结果: {current_step.expected_result}
可用工具: {', '.join(self.tools_by_name.keys())}

{content_prompt}

如果需要使用工具，请使用以下格式：
思考：你的思考过程
行动：[工具名称]，参数：[JSON格式的参数]

例如：
行动：write_file，参数：{{"file_path": "test.txt", "content": "Hello"}}"""
        })
        
        # 流式调用LLM - LLM思考过程流式输出到前端
        text = self._stream_llm_response(step_messages, callback)
        
        # 检测工具调用，传入期望的工具名称
        tool_call = self._detect_step_from_response(text, current_step.tool_name)
        
        observation = ""
        if tool_call:
            tool_name, tool_params = tool_call
            
            # 验证工具名称
            if tool_name != current_step.tool_name:
                if callback:
                    callback(f"[警告] 工具名称不匹配: 期望 {current_step.tool_name}, 实际 {tool_name}\n")
                # 如果检测到的工具可用，仍然执行
                if tool_name not in self.tools_by_name:
                    observation = f"错误: 工具 '{tool_name}' 不可用"
                    if callback:
                        callback(f"[错误] {observation}\n")
                    return {
                        **state,
                        "messages": messages,
                        "current_step": current_step,
                        "last_observation": observation
                    }
            
            # 确保file_path存在（从current_step.tool_params或tool_params中获取）
            file_path = tool_params.get('file_path') or current_step.tool_params.get('file_path', 'unknown')
            
            # 【新增】使用输出规范器规范化文件路径
            if tool_name in ['write_file', 'read_file']:
                original_path = file_path
                # 使用输出规范器的默认项目（如果已设置）或自动检测
                file_path = self.output_normalizer.normalize_path(
                    file_path, 
                    file_type=None  # 自动检测
                )
                tool_params['file_path'] = file_path
            else:
                tool_params['file_path'] = file_path
            
            # 如果是write_file且content为空，需要生成内容
            if tool_name == "write_file" and (not tool_params.get("content") or tool_params.get("content") == ""):
                if callback:
                    callback("\n[生成文件内容]\n")
                
                # 调用LLM生成内容 - 使用新的消息列表，避免上下文污染
                content_messages = [
                    {"role": "system", "content": "你是一个内容生成助手。根据用户需求生成完整的文件内容。直接返回内容，不要添加解释。"},
                    {"role": "user", "content": f"请为文件 {os.path.basename(file_path)} 生成完整的内容。\n\n步骤描述: {current_step.description}\n\n生成详细、完整、格式良好的内容。直接返回内容文本，不需要任何解释或说明。"}
                ]
                
                # 文件内容流式输出到前端
                generated_content = self._stream_llm_response(content_messages, callback)
                tool_params["content"] = generated_content.strip()
                
                if callback:
                    callback(f"\n[内容已生成，长度: {len(tool_params['content'])} 字符]\n")
            
            if tool_name in self.tools_by_name:
                if callback:
                    callback(f"[工具] {tool_name} - {file_path}\n")
                
                # 执行工具
                observation = self._execute_tool(tool_name, tool_params)
                
                if callback:
                    callback(f"[完成] {observation[:100]}{'...' if len(observation) > 100 else ''}\n")
                
                if self.memory:
                    self.memory.add_tool_result(tool_name, observation)
            else:
                observation = f"工具不匹配: 期望 {current_step.tool_name}, 实际 {tool_name}"
                if callback:
                    callback(f"[警告] {observation}\n")
        else:
            observation = "此步骤无需工具调用"
            if callback:
                callback(f"[信息] {observation}\n")
        
        current_step.status = "completed"
        current_step.actual_result = observation
        plan.update_step_status(current_step.step_id, "completed", observation)
        
        if self.memory:
            self.memory.update_current_plan(plan)
        
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": f"观察：{observation}"})
        
        return {
            **state,
            "messages": messages,
            "current_step": current_step,
            "last_observation": observation
        }
    
    def _observe_node(self, state: AgentState) -> AgentState:
        """观察节点：分析执行结果并检测规划变更"""
        plan = state["current_plan"]
        last_observation = state["last_observation"]
        messages = state["messages"]
        callback = state.get("stream_callback")
        
        # 调用LLM分析结果
        check_messages = messages.copy()
        check_messages.append({
            "role": "user",
            "content": f"""上一步的执行结果为：{last_observation}

请分析：
1. 结果是否符合预期？
2. 当前规划是否需要调整？
3. 是否需要添加新的步骤？

如果需要调整规划，请返回新的规划JSON。如果不需要调整，请回复"继续执行当前规划"。"""
        })
        
        # LLM分析结果流式输出到前端
        text = self._stream_llm_response(check_messages, callback)
        
        # 检查规划变更
        new_plan = self._check_plan_change(plan, text)
        if new_plan:
            if callback:
                callback("\n[规划已更新]\n")
            plan = new_plan
            if self.memory:
                self.memory.update_current_plan(plan)
        
        return {
            **state,
            "current_plan": plan
        }
    
    def _should_continue(self, state: AgentState) -> str:
        """决定下一步"""
        plan = state["current_plan"]
        iteration_count = state["iteration_count"]
        plan_validated = state["plan_validated"]
        
        if iteration_count >= self.config.max_iterations:
            return "finalize"
        
        if not plan_validated:
            return "finalize"
        
        if plan and plan.check_all_completed():
            return "finalize"
        
        return "continue"
    
    def _finalize_node(self, state: AgentState) -> AgentState:
        """最终节点：生成最终答案"""
        plan = state["current_plan"]
        messages = state["messages"]
        user_input = state["user_input"]
        callback = state.get("stream_callback")
        
        if callback:
            callback("\n[生成最终答案]\n")
        
        # 构建执行摘要
        execution_summary = ""
        if plan:
            execution_summary = "执行摘要:\n"
            for step in plan.steps:
                status_icon = "✓" if step.status == "completed" else "✗" if step.status == "failed" else "○"
                execution_summary += f"{status_icon} 步骤 {step.step_id}: {step.description}\n"
        
        # 调用LLM生成最终答案
        final_messages = messages.copy()
        final_messages.append({
            "role": "user",
            "content": f"""基于以上执行过程，请生成最终答案回复用户。

用户原始请求: {user_input}

{execution_summary}

请提供清晰、完整的最终答案。"""
        })
        
        # 最终答案流式输出到前端
        text = self._stream_llm_response(final_messages, callback)
        
        final_answer = text
        
        # 提取最终答案部分
        if "最终答案" in final_answer:
            match = re.search(r'最终答案[：:]\s*(.+)', final_answer, re.DOTALL)
            if match:
                final_answer = match.group(1).strip()
        
        if self.memory:
            self.memory.add_assistant_message(final_answer)
            if plan:
                plan.is_completed = True
        
        return {
            **state,
            "final_answer": final_answer
        }
    
    def _build_workflow(self) -> StateGraph:
        """构建LangGraph工作流"""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("validate", self._validate_node)
        workflow.add_node("execute_step", self._execute_step_node)
        workflow.add_node("observe", self._observe_node)
        workflow.add_node("finalize", self._finalize_node)
        
        workflow.set_entry_point("plan")
        workflow.add_edge("plan", "validate")
        workflow.add_conditional_edges(
            "validate",
            lambda state: "execute_step" if state["plan_validated"] else "finalize",
            {
                "execute_step": "execute_step",
                "finalize": "finalize"
            }
        )
        workflow.add_edge("execute_step", "observe")
        workflow.add_conditional_edges(
            "observe",
            self._should_continue,
            {
                "continue": "execute_step",
                "finalize": "finalize"
            }
        )
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def run(self, question: str) -> str:
        """运行Agent（非流式）"""
        return self.run_stream(question, callback=None)
    
    def run_stream(
        self,
        question: str,
        callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        流式运行Agent - 真正的逐字流式输出
        
        Args:
            question: 用户问题
            callback: 流式输出回调函数
            
        Returns:
            最终答案
        """
        # 规范化用户输入
        user_content, agent_context = self._normalize_input(question)
        
        # 保存用户问题到记忆
        if self.memory:
            self.memory.add_user_message(question)
        
        # 初始化消息列表
        messages = [
            {"role": "system", "content": self.config.system_prompt}
        ]
        
        # 添加历史记忆
        if self.memory:
            messages.extend(self.memory.get_messages()[:-1])
        
        # 初始化状态
        initial_state: AgentState = {
            "messages": messages,
            "user_input": user_content,
            "agent_context": agent_context,
            "iteration_count": 0,
            "final_answer": None,
            "current_plan": None,
            "current_step": None,
            "last_observation": "",
            "plan_validated": False,
            "stream_callback": callback
        }
        
        # 执行工作流
        final_state = self.workflow.invoke(initial_state)
        
        return final_state.get("final_answer", "执行完成，但未生成最终答案")
    
    def clear_memory(self):
        """清除记忆"""
        if self.memory:
            self.memory.clear()
    
    def get_memory_history(self) -> List[Dict]:
        """获取记忆历史"""
        if self.memory:
            return self.memory.messages
        return []
    
    def get_current_plan(self) -> Optional[Dict]:
        """获取当前规划"""
        if self.memory and self.memory.current_plan:
            return self.memory.current_plan.to_dict()
        return None
