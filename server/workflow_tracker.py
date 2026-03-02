"""
工作流跟踪器 - 支持流式输出和节点状态跟踪
用于将游戏开发工作流与WebSocket前端同步
"""

import asyncio
import json
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PhaseType(Enum):
    DESIGN = "design"
    SUB_DESIGN = "sub_design"
    MERGE_DESIGN = "merge_design"
    FRAMEWORK = "framework"
    SUB_CODE = "sub_code"
    MERGE_CODE = "merge_code"
    REVIEW = "review"
    TEST = "test"
    DEPLOY = "deploy"


@dataclass
class TaskNode:
    """任务节点"""
    node_id: str
    node_type: str
    title: str
    status: NodeStatus = NodeStatus.PENDING
    progress: float = 0.0
    output: str = ""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParallelZone:
    """并行任务区域"""
    zone_id: str
    title: str
    agents: List[str] = field(default_factory=list)
    active_agents: List[str] = field(default_factory=list)
    output: str = ""
    status: str = "等待中"


class WorkflowTracker:
    """
    工作流跟踪器
    跟踪游戏开发工作流的执行状态，并向前端发送更新
    """
    
    def __init__(self, workflow_id: str, broadcast_callback: Callable):
        self.workflow_id = workflow_id
        self.broadcast = broadcast_callback
        self.nodes: Dict[str, TaskNode] = {}
        self.zones: Dict[str, ParallelZone] = {}
        self.current_phase = PhaseType.DESIGN
        self.messages: List[Dict] = []
        
        # 初始化并行区域
        self._init_zones()
    
    def _init_zones(self):
        """初始化并行任务区域"""
        self.zones['design'] = ParallelZone(
            zone_id='design',
            title='📋 策划团队',
            agents=['主策划', '子策划A', '子策划B', '子策划C']
        )
        self.zones['code'] = ParallelZone(
            zone_id='code',
            title='💻 开发团队',
            agents=['主程序', '子程序A', '子程序B', '子程序C']
        )
        self.zones['test'] = ParallelZone(
            zone_id='test',
            title='🧪 测试团队',
            agents=['测试员']
        )
    
    async def create_node(self, node_id: str, node_type: str, title: str, **metadata) -> TaskNode:
        """创建新节点"""
        node = TaskNode(
            node_id=node_id,
            node_type=node_type,
            title=title,
            metadata=metadata
        )
        self.nodes[node_id] = node
        
        await self.broadcast({
            "type": "node_added",
            "data": self._node_to_dict(node)
        })
        
        return node
    
    async def update_node(self, node_id: str, **updates):
        """更新节点状态"""
        if node_id not in self.nodes:
            return
        
        node = self.nodes[node_id]
        
        if 'status' in updates:
            node.status = NodeStatus(updates['status'])
            if node.status == NodeStatus.RUNNING and not node.start_time:
                node.start_time = datetime.now().isoformat()
            elif node.status in [NodeStatus.COMPLETED, NodeStatus.FAILED]:
                node.end_time = datetime.now().isoformat()
        
        if 'progress' in updates:
            node.progress = updates['progress']
        
        if 'output' in updates:
            node.output += updates['output']
        
        await self.broadcast({
            "type": "node_updated",
            "data": self._node_to_dict(node)
        })
    
    async def start_node(self, node_id: str):
        """启动节点"""
        await self.update_node(node_id, status='running', progress=0)
    
    async def complete_node(self, node_id: str, output: str = ""):
        """完成节点"""
        await self.update_node(node_id, status='completed', progress=100, output=output)
    
    async def fail_node(self, node_id: str, error: str):
        """节点失败"""
        await self.update_node(node_id, status='failed', output=error)
    
    async def update_zone(self, zone_id: str, **updates):
        """更新并行区域"""
        if zone_id not in self.zones:
            return
        
        zone = self.zones[zone_id]
        
        if 'status' in updates:
            zone.status = updates['status']
        
        if 'active_agents' in updates:
            zone.active_agents = updates['active_agents']
        
        if 'output' in updates:
            zone.output += updates['output']
        
        await self.broadcast({
            "type": "zone_updated",
            "data": {
                "zone_id": zone_id,
                "title": zone.title,
                "status": zone.status,
                "agents": [
                    {"name": agent, "active": agent in zone.active_agents}
                    for agent in zone.agents
                ],
                "output": zone.output
            }
        })
    
    async def log_message(self, agent_role: str, content: str, msg_type: str = "info"):
        """记录消息"""
        message = {
            "type": msg_type,
            "agent_id": agent_role.lower().replace(' ', '_'),
            "agent_role": agent_role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        self.messages.append(message)
        
        await self.broadcast({
            "type": "message",
            "data": message
        })
        
        # 同时更新对应的并行区域
        if '策划' in agent_role:
            await self.update_zone('design', 
                status='工作中',
                active_agents=[agent_role],
                output=content + '\n'
            )
        elif '程序' in agent_role:
            await self.update_zone('code',
                status='工作中',
                active_agents=[agent_role],
                output=content + '\n'
            )
        elif '测试' in agent_role:
            await self.update_zone('test',
                status='工作中',
                active_agents=[agent_role],
                output=content + '\n'
            )
    
    async def set_phase(self, phase: PhaseType):
        """设置当前阶段"""
        self.current_phase = phase
        
        phase_names = {
            PhaseType.DESIGN: "策划阶段",
            PhaseType.SUB_DESIGN: "子策划并行",
            PhaseType.MERGE_DESIGN: "策划汇总",
            PhaseType.FRAMEWORK: "程序框架",
            PhaseType.SUB_CODE: "子程序并行",
            PhaseType.MERGE_CODE: "代码汇总",
            PhaseType.REVIEW: "代码审核",
            PhaseType.TEST: "测试阶段",
            PhaseType.DEPLOY: "部署阶段"
        }
        
        await self.broadcast({
            "type": "status_update",
            "data": {
                "current_phase": phase_names.get(phase, "未知阶段")
            }
        })
    
    def _node_to_dict(self, node: TaskNode) -> dict:
        """节点转换为字典"""
        return {
            "node_id": node.node_id,
            "node_type": node.node_type,
            "title": node.title,
            "status": node.status.value,
            "progress": node.progress,
            "output": node.output,
            "start_time": node.start_time,
            "end_time": node.end_time
        }


# 装饰器：跟踪函数执行
class TrackedExecution:
    """跟踪执行的上下文管理器"""
    
    def __init__(self, tracker: WorkflowTracker, node_id: str, node_type: str, title: str):
        self.tracker = tracker
        self.node_id = node_id
        self.node_type = node_type
        self.title = title
    
    async def __aenter__(self):
        await self.tracker.create_node(self.node_id, self.node_type, self.title)
        await self.tracker.start_node(self.node_id)
        await self.tracker.log_message("系统", f"开始执行: {self.title}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.tracker.fail_node(self.node_id, str(exc_val))
            await self.tracker.log_message("系统", f"执行失败: {self.title} - {exc_val}", "error")
        else:
            await self.tracker.complete_node(self.node_id)
            await self.tracker.log_message("系统", f"完成执行: {self.title}")


# 全局跟踪器存储
trackers: Dict[str, WorkflowTracker] = {}


def get_tracker(workflow_id: str) -> Optional[WorkflowTracker]:
    """获取跟踪器"""
    return trackers.get(workflow_id)


def create_tracker(workflow_id: str, broadcast_callback: Callable) -> WorkflowTracker:
    """创建跟踪器"""
    tracker = WorkflowTracker(workflow_id, broadcast_callback)
    trackers[workflow_id] = tracker
    return tracker


def remove_tracker(workflow_id: str):
    """移除跟踪器"""
    if workflow_id in trackers:
        del trackers[workflow_id]
