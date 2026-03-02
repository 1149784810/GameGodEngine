## 重构目标
使用Function Calling重构工具系统，使用LangGraph优化ReAct模式，让Agent真正可靠地执行工具。

## 核心改进

### 1. Function Calling 改造
- 使用 `@tool` 装饰器定义工具（替代原有类方式）
- 使用 `llm.bind_tools()` 绑定工具
- LLM 输出结构化 JSON 调用工具，不再是文本解析

### 2. LangGraph 架构
```
用户输入 → Agent节点(LLM决策) → 条件路由
                              ↓
                    有工具调用 → 工具节点(真正执行)
                              ↓
                         返回Agent节点
                              ↓
                    无工具调用 → 结束
```

### 3. 文件变更

**新增文件：**
- `agent_base/llm_provider_with_tools.py` - 支持Function Calling的LLM封装
- `agent_base/langgraph_agent.py` - LangGraph Agent实现

**修改文件：**
- `tools/file_tools.py` - 使用@tool装饰器重构
- `main.py` - 更新入口使用新Agent

**保留文件（向后兼容）：**
- `agent_base/react_agent.py` - 原有实现
- `tools/file_tools_legacy.py` - 原工具实现

### 4. 关键特性
- 类型安全：使用Pydantic自动验证工具参数
- 流式输出：保持流式响应能力
- 状态管理：LangGraph显式管理AgentState
- 可扩展：易于添加新工具

### 5. 依赖
需要安装：`pip install langgraph`

请确认这个方案后，我将开始实施具体的代码修改。