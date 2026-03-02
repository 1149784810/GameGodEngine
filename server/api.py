"""
矩阵游戏引擎 - FastAPI后端服务
支持WebSocket流式输出和多Agent并行任务可视化
"""

import os
import sys
import json
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# 添加server目录到路径（确保相对导入正常工作）
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from agent_base import get_agent, list_available_agents, list_available_tools
from game_dev_core import run_game_development, game_dev_state
from game_dev_core.game_develop_workflow import game_workflow_graph


# ============ 数据模型 ============

class GameRequest(BaseModel):
    """游戏开发请求"""
    game_idea: str = Field(..., description="游戏想法描述")
    project_name: Optional[str] = Field(None, description="项目名称")


class AgentMessage(BaseModel):
    """Agent消息"""
    type: str = Field(..., description="消息类型: plan/execute/complete/error")
    agent_id: str = Field(..., description="Agent标识")
    agent_role: str = Field(..., description="Agent角色")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


class TaskNode(BaseModel):
    """任务节点"""
    node_id: str = Field(..., description="节点ID")
    node_type: str = Field(..., description="节点类型: design/program/test/fix/deploy")
    title: str = Field(..., description="节点标题")
    status: str = Field("pending", description="状态: pending/running/completed/failed")
    progress: float = Field(0.0, description="进度 0-100")
    parent_id: Optional[str] = Field(None, description="父节点ID")
    children: List[str] = Field(default_factory=list, description="子节点ID列表")
    output: Optional[str] = Field(None, description="输出内容")
    start_time: Optional[str] = Field(None, description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")


class WorkflowStatus(BaseModel):
    """工作流状态"""
    workflow_id: str = Field(..., description="工作流ID")
    status: str = Field(..., description="状态: idle/running/paused/completed/failed")
    current_phase: str = Field(..., description="当前阶段")
    game_idea: str = Field("", description="游戏想法")
    project_name: str = Field("", description="项目名称")
    nodes: List[TaskNode] = Field(default_factory=list, description="任务节点列表")
    messages: List[AgentMessage] = Field(default_factory=list, description="消息列表")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============ 全局状态管理 ============

class WorkflowManager:
    """工作流管理器 - 管理所有运行中的工作流"""
    
    def __init__(self):
        self.workflows: Dict[str, WorkflowStatus] = {}
        self.connections: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def create_workflow(self, game_idea: str, project_name: str) -> str:
        """创建新工作流"""
        workflow_id = str(uuid.uuid4())
        
        workflow = WorkflowStatus(
            workflow_id=workflow_id,
            status="idle",
            current_phase="初始化",
            game_idea=game_idea,
            project_name=project_name,
            nodes=[
                TaskNode(
                    node_id="root",
                    node_type="root",
                    title=f"项目: {project_name}",
                    status="pending"
                )
            ]
        )
        
        async with self._lock:
            self.workflows[workflow_id] = workflow
            self.connections[workflow_id] = []
        
        return workflow_id
    
    async def get_workflow(self, workflow_id: str) -> Optional[WorkflowStatus]:
        """获取工作流状态"""
        return self.workflows.get(workflow_id)
    
    async def update_workflow(self, workflow_id: str, updates: Dict[str, Any]):
        """更新工作流状态"""
        if workflow_id in self.workflows:
            workflow = self.workflows[workflow_id]
            for key, value in updates.items():
                if hasattr(workflow, key):
                    setattr(workflow, key, value)
            workflow.updated_at = datetime.now().isoformat()
            
            # 广播更新
            await self.broadcast(workflow_id, {
                "type": "status_update",
                "data": workflow.dict()
            })
    
    async def add_node(self, workflow_id: str, node: TaskNode):
        """添加任务节点"""
        if workflow_id in self.workflows:
            self.workflows[workflow_id].nodes.append(node)
            await self.broadcast(workflow_id, {
                "type": "node_added",
                "data": node.dict()
            })
    
    async def update_node(self, workflow_id: str, node_id: str, updates: Dict[str, Any]):
        """更新任务节点"""
        if workflow_id not in self.workflows:
            return
        
        for node in self.workflows[workflow_id].nodes:
            if node.node_id == node_id:
                for key, value in updates.items():
                    if hasattr(node, key):
                        setattr(node, key, value)
                
                await self.broadcast(workflow_id, {
                    "type": "node_updated",
                    "data": node.dict()
                })
                break
    
    async def add_message(self, workflow_id: str, message: AgentMessage):
        """添加消息"""
        if workflow_id in self.workflows:
            self.workflows[workflow_id].messages.append(message)
            await self.broadcast(workflow_id, {
                "type": "message",
                "data": message.dict()
            })
    
    async def connect(self, workflow_id: str, websocket: WebSocket):
        """连接WebSocket"""
        async with self._lock:
            if workflow_id not in self.connections:
                self.connections[workflow_id] = []
            self.connections[workflow_id].append(websocket)
    
    async def disconnect(self, workflow_id: str, websocket: WebSocket):
        """断开WebSocket"""
        async with self._lock:
            if workflow_id in self.connections:
                if websocket in self.connections[workflow_id]:
                    self.connections[workflow_id].remove(websocket)
    
    async def broadcast(self, workflow_id: str, message: Dict[str, Any]):
        """广播消息到所有连接"""
        if workflow_id not in self.connections:
            return
        
        disconnected = []
        for ws in self.connections[workflow_id]:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        
        # 清理断开的连接
        for ws in disconnected:
            await self.disconnect(workflow_id, ws)


# 全局工作流管理器
workflow_manager = WorkflowManager()


# ============ FastAPI应用 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    print("=" * 60)
    print("🎮 矩阵游戏引擎 - 后端服务启动")
    print("=" * 60)
    yield
    # 关闭
    print("\n服务关闭")


app = FastAPI(
    title="矩阵游戏引擎 API",
    description="支持多Agent并行游戏开发的流式API服务",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ WebSocket路由（必须在静态文件之前定义） ============

@app.websocket("/ws/workflow/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    """WebSocket连接 - 实时流式输出"""
    await websocket.accept()
    
    # 注册连接
    await workflow_manager.connect(workflow_id, websocket)
    
    try:
        # 发送当前状态
        workflow = await workflow_manager.get_workflow(workflow_id)
        if workflow:
            await websocket.send_json({
                "type": "connected",
                "data": workflow.dict()
            })
        
        # 保持连接
        while True:
            try:
                # 接收客户端消息（心跳或命令）
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0
                )
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
            except asyncio.TimeoutError:
                # 发送心跳
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        await workflow_manager.disconnect(workflow_id, websocket)
    except Exception as e:
        print(f"WebSocket错误: {e}")
        await workflow_manager.disconnect(workflow_id, websocket)


# ============ REST API ============

# 注意：根路径 / 留给静态文件（前端页面）
# API路由都使用 /api 前缀

@app.get("/api")
async def api_root():
    """API根路径"""
    return {
        "name": "矩阵游戏引擎 API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/agents")
async def get_agents():
    """获取所有可用Agent"""
    agents = list_available_agents()
    return {"agents": agents}


@app.get("/api/tools")
async def get_tools():
    """获取所有可用工具"""
    tools = list_available_tools()
    return {"tools": tools}


@app.post("/api/workflow/create")
async def create_workflow(request: GameRequest):
    """创建游戏开发工作流"""
    # 验证游戏想法不能为空
    if not request.game_idea or not request.game_idea.strip():
        raise HTTPException(status_code=400, detail="游戏想法不能为空，请输入游戏想法")
    
    game_idea = request.game_idea.strip()
    project_name = request.project_name.strip() if request.project_name else f"Game_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    workflow_id = await workflow_manager.create_workflow(
        game_idea=game_idea,
        project_name=project_name
    )
    
    return {
        "workflow_id": workflow_id,
        "project_name": project_name,
        "game_idea": game_idea,
        "status": "created"
    }


@app.get("/api/workflow/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """获取工作流状态"""
    workflow = await workflow_manager.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    return workflow


@app.post("/api/workflow/{workflow_id}/start")
async def start_workflow(workflow_id: str, background_tasks: BackgroundTasks):
    """启动工作流"""
    workflow = await workflow_manager.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    if workflow.status == "running":
        raise HTTPException(status_code=400, detail="工作流已在运行中")
    
    # 在后台启动工作流
    background_tasks.add_task(run_game_development_stream, workflow_id)
    
    return {"status": "started", "workflow_id": workflow_id}


@app.post("/api/workflow/{workflow_id}/stop")
async def stop_workflow(workflow_id: str):
    """停止工作流"""
    workflow = await workflow_manager.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    await workflow_manager.update_workflow(workflow_id, {"status": "paused"})
    return {"status": "paused", "workflow_id": workflow_id}


# ============ 静态文件（放在最后，作为fallback） ============
# 前端文件在server目录的父目录中的web文件夹
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")


# ============ 流式游戏开发执行 ============

class WebSocketStreamManager:
    """WebSocket流式输出管理器 - 管理LLM流式输出到前端的转发"""
    
    def __init__(self):
        self._callbacks: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
    
    def register_callback(self, workflow_id: str, callback: Callable):
        """注册流式输出回调"""
        self._callbacks[workflow_id] = callback
    
    def unregister_callback(self, workflow_id: str):
        """注销流式输出回调"""
        if workflow_id in self._callbacks:
            del self._callbacks[workflow_id]
    
    def get_callback(self, workflow_id: str) -> Optional[Callable]:
        """获取流式输出回调"""
        return self._callbacks.get(workflow_id)
    
    async def send_chunk(self, workflow_id: str, chunk: str, agent_role: str = "Agent"):
        """发送流式输出块到前端"""
        if workflow_id in self._callbacks:
            await self._callbacks[workflow_id](chunk, agent_role)


# 全局流式输出管理器
stream_manager = WebSocketStreamManager()


class AgentStreamCallback:
    """Agent流式输出回调 - 用于ReAct Agent的run_stream方法"""
    
    def __init__(self, workflow_id: str, agent_role: str):
        self.workflow_id = workflow_id
        self.agent_role = agent_role
        self.buffer = ""
    
    def __call__(self, content: str):
        """接收流式输出（同步回调）"""
        self.buffer += content
        # 使用asyncio.create_task来异步发送
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(
                stream_manager.send_chunk(self.workflow_id, content, self.agent_role)
            )
        except Exception:
            pass


async def broadcast_stream_chunk(workflow_id: str, chunk: str, agent_role: str):
    """广播流式输出块到所有连接的WebSocket客户端"""
    # 使用 agent_role 作为 worker_id（前端用它来关联同一个 Agent 的消息）
    worker_id = agent_role
    
    message = {
        "type": "stream_chunk",
        "data": {
            "worker_id": worker_id,
            "worker_name": agent_role,
            "chunk": chunk,
            "timestamp": datetime.now().isoformat()
        }
    }
    await workflow_manager.broadcast(workflow_id, message)


async def broadcast_phase_update(workflow_id: str, phase_id: str, phase_name: str, status: str):
    """广播阶段状态更新到所有连接的WebSocket客户端"""
    message = {
        "type": "phase_update",
        "data": {
            "phase_id": phase_id,
            "phase_name": phase_name,
            "status": status,  # running / completed / failed
            "timestamp": datetime.now().isoformat()
        }
    }
    await workflow_manager.broadcast(workflow_id, message)


async def run_game_development_stream(workflow_id: str):
    """流式运行游戏开发工作流"""
    workflow = await workflow_manager.get_workflow(workflow_id)
    if not workflow:
        return
    
    # 更新状态为运行中
    await workflow_manager.update_workflow(workflow_id, {
        "status": "running",
        "current_phase": "策划阶段"
    })
    
    # 注册流式输出回调
    async def stream_callback(chunk: str, agent_role: str):
        await broadcast_stream_chunk(workflow_id, chunk, agent_role)
    
    stream_manager.register_callback(workflow_id, stream_callback)
    
    try:
        # 从工作流状态中获取游戏想法和项目名称
        game_idea = workflow.game_idea
        project_name = workflow.project_name
        
        # 验证游戏想法不能为空
        if not game_idea:
            await workflow_manager.update_workflow(workflow_id, {
                "status": "failed",
                "current_phase": "错误: 游戏想法为空"
            })
            await workflow_manager.broadcast(workflow_id, {
                "type": "error",
                "data": {"message": "❌ 错误: 游戏想法不能为空"}
            })
            return
        
        # 验证项目名称不能为空
        if not project_name:
            project_name = f"Game_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 发送开始消息
        await workflow_manager.broadcast(workflow_id, {
            "type": "stream_start",
            "data": {
                "worker_id": "system",
                "worker_name": "系统",
                "description": "启动游戏开发流程"
            }
        })
        
        await broadcast_stream_chunk(workflow_id, f"🚀 启动游戏开发流程\n🎮 游戏想法: {game_idea}\n📁 项目名称: {project_name}\n\n", "系统")
        
        # 创建节点跟踪
        await create_phase_nodes(workflow_id)
        
        # 运行开发流程（使用异步方式，确保WebSocket消息可以实时发送）
        final_state = await run_game_development_async(
            game_idea=game_idea,
            project_name=project_name,
            workflow_id=workflow_id
        )
        
        # 发送流式输出结束
        await workflow_manager.broadcast(workflow_id, {
            "type": "stream_end",
            "data": {
                "worker_id": "system",
                "full_content": f"✅ 游戏开发完成!\n📁 项目位置: {final_state.get('project_dir', 'N/A')}\n🧪 测试通过: {final_state.get('all_tests_passed', False)}"
            }
        })
        
        # 更新完成状态
        await workflow_manager.update_workflow(workflow_id, {
            "status": "completed",
            "current_phase": "完成"
        })
        
    except Exception as e:
        # 更新失败状态
        await workflow_manager.update_workflow(workflow_id, {
            "status": "failed",
            "current_phase": f"错误: {str(e)}"
        })
        
        await workflow_manager.broadcast(workflow_id, {
            "type": "error",
            "data": {"message": f"❌ 错误: {str(e)}"}
        })
    finally:
        # 注销流式输出回调
        stream_manager.unregister_callback(workflow_id)


async def create_phase_nodes(workflow_id: str):
    """创建阶段节点"""
    phases = [
        ("design", "策划阶段", "主策划生成框架"),
        ("sub_design", "子策划并行", "子策划开发模块"),
        ("merge_design", "策划汇总", "主策划汇总GDD"),
        ("framework", "程序框架", "主程序搭建框架"),
        ("sub_code", "子程序并行", "子程序开发模块"),
        ("merge_code", "代码汇总", "主程序合并代码"),
        ("review", "代码审核", "主程序审核修复"),
        ("test", "测试阶段", "测试员运行测试"),
        ("deploy", "部署阶段", "部署游戏")
    ]
    
    for i, (node_type, title, desc) in enumerate(phases):
        node = TaskNode(
            node_id=f"phase_{i}",
            node_type=node_type,
            title=title,
            status="pending"
        )
        await workflow_manager.add_node(workflow_id, node)


async def run_game_development_async(
    game_idea: str,
    project_name: str,
    workflow_id: str
) -> dict:
    """异步运行游戏开发执行 - 支持流式输出和阶段跟踪"""
    from game_dev_core import run_game_development
    import threading
    import queue
    
    # 创建队列用于传递消息
    message_queue = queue.Queue()
    result_queue = queue.Queue()
    
    # 创建流式输出回调函数
    def stream_callback(content: str, agent_role: str):
        """同步流式输出回调，将内容放入队列"""
        message_queue.put({
            'type': 'stream_chunk',
            'content': content,
            'agent_role': agent_role
        })
    
    # 创建阶段完成回调函数
    def phase_callback(phase_id: str, phase_name: str, status: str):
        """阶段完成回调，将消息放入队列"""
        message_queue.put({
            'type': 'phase_update',
            'phase_id': phase_id,
            'phase_name': phase_name,
            'status': status
        })
    
    # 在后台线程中运行游戏开发
    def run_in_thread():
        try:
            result = run_game_development(
                game_idea=game_idea,
                project_name=project_name,
                stream_callback=stream_callback,
                phase_callback=phase_callback
            )
            result_queue.put(('success', result))
        except Exception as e:
            result_queue.put(('error', str(e)))
    
    # 启动后台线程
    thread = threading.Thread(target=run_in_thread)
    thread.start()
    
    # 在主事件循环中处理消息队列
    while thread.is_alive() or not message_queue.empty():
        # 处理队列中的消息
        try:
            while not message_queue.empty():
                msg = message_queue.get_nowait()
                msg_type = msg.get('type')
                
                if msg_type == 'stream_chunk':
                    await broadcast_stream_chunk(
                        workflow_id,
                        msg['content'],
                        msg['agent_role']
                    )
                elif msg_type == 'phase_update':
                    await broadcast_phase_update(
                        workflow_id,
                        msg['phase_id'],
                        msg['phase_name'],
                        msg['status']
                    )
        except queue.Empty:
            pass
        
        # 让出控制权，允许其他协程运行
        await asyncio.sleep(0.01)
    
    # 等待线程结束
    thread.join()
    
    # 获取结果
    status, result = result_queue.get()
    if status == 'error':
        raise Exception(result)
    
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
