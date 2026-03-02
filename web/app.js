/**
 * 矩阵游戏引擎 - 前端应用
 * 支持WebSocket实时通信和可视化节点展示
 */

// ==================== 配置 ====================
const CONFIG = {
    API_BASE: 'http://localhost:8000',
    WS_BASE: 'ws://localhost:8000',
    RECONNECT_INTERVAL: 3000,
    MAX_RECONNECT_ATTEMPTS: 5
};

// ==================== Markdown 渲染配置 ====================
if (typeof marked !== 'undefined') {
    marked.setOptions({
        gfm: true,
        breaks: true,
        headerIds: true,
        mangle: false,
        sanitize: false,
        smartLists: true,
        smartypants: true,
        xhtml: false,
        highlight: function(code, lang) {
            if (typeof hljs !== 'undefined') {
                if (lang && hljs.getLanguage(lang)) {
                    try {
                        return hljs.highlight(code, { language: lang }).value;
                    } catch (e) {
                        console.warn('代码高亮失败:', e);
                    }
                }
                return hljs.highlightAuto(code).value;
            }
            return code;
        }
    });
}

// ==================== 状态管理 ====================
const state = {
    workflowId: null,
    ws: null,
    isConnected: false,
    isRunning: false,
    isPaused: false,
    autoScroll: true,
    reconnectAttempts: 0,
    currentPhase: 'design',
    // 动态工种数据 - 由后端通知创建
    workers: new Map(),
    // 当前阶段的子工种列表
    currentSubWorkers: [],
    // 当前活跃的流式输出工种（正在接收流式数据的工种）
    activeStreamWorker: null,
    // 流式输出缓存 - 按工种存储完整输出内容
    streamCache: new Map(),
    // 用户手动关闭的面板，不要自动打开
    userClosedPanel: false,
    // 当前面板显示的工种（null表示面板关闭）
    currentPanelWorker: null
};

// ==================== DOM元素 ====================
const elements = {
    gameIdea: document.getElementById('gameIdea'),
    projectName: document.getElementById('projectName'),
    startBtn: document.getElementById('startBtn'),
    pauseBtn: document.getElementById('pauseBtn'),
    inputPanel: document.getElementById('inputPanel'),
    workflowPanel: document.getElementById('workflowPanel'),
    consoleOutput: document.getElementById('consoleOutput'),
    parallelWorkers: document.getElementById('parallelWorkers'),
    systemStatus: document.getElementById('systemStatus'),
    connectionStatus: document.getElementById('connectionStatus'),
    autoScrollBtn: document.getElementById('autoScrollBtn'),
    phaseBar: document.getElementById('phaseBar'),
    // 流式输出面板
    streamPanel: document.getElementById('streamPanel'),
    streamTitle: document.getElementById('streamTitle'),
    streamContent: document.getElementById('streamContent'),
    streamStatus: document.getElementById('streamStatus')
};

// ==================== 矩阵背景动画 ====================
class MatrixBackground {
    constructor() {
        this.canvas = document.getElementById('matrixCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.characters = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz@#$%^&*';
        this.fontSize = 14;
        this.columns = 0;
        this.drops = [];
        
        this.init();
        window.addEventListener('resize', () => this.init());
    }
    
    init() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        this.columns = Math.floor(this.canvas.width / this.fontSize);
        this.drops = Array(this.columns).fill(1);
    }
    
    draw() {
        this.ctx.fillStyle = 'rgba(10, 10, 15, 0.05)';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.ctx.fillStyle = '#00ff88';
        this.ctx.font = `${this.fontSize}px monospace`;
        
        for (let i = 0; i < this.drops.length; i++) {
            const char = this.characters[Math.floor(Math.random() * this.characters.length)];
            this.ctx.fillText(char, i * this.fontSize, this.drops[i] * this.fontSize);
            
            if (this.drops[i] * this.fontSize > this.canvas.height && Math.random() > 0.975) {
                this.drops[i] = 0;
            }
            this.drops[i]++;
        }
    }
    
    start() {
        const animate = () => {
            this.draw();
            requestAnimationFrame(animate);
        };
        animate();
    }
}

// ==================== WebSocket管理 ====================
class WebSocketManager {
    constructor() {
        this.ws = null;
        this.messageHandlers = new Map();
    }
    
    connect(workflowId) {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(`${CONFIG.WS_BASE}/ws/workflow/${workflowId}`);
                
                this.ws.onopen = () => {
                    console.log('WebSocket连接成功');
                    state.isConnected = true;
                    state.reconnectAttempts = 0;
                    updateConnectionStatus(true);
                    resolve();
                };
                
                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                };
                
                this.ws.onclose = () => {
                    console.log('WebSocket连接关闭');
                    state.isConnected = false;
                    updateConnectionStatus(false);
                    this.attemptReconnect(workflowId);
                };
                
                this.ws.onerror = (error) => {
                    console.error('WebSocket错误:', error);
                    reject(error);
                };
                
            } catch (error) {
                reject(error);
            }
        });
    }
    
    handleMessage(data) {
        console.log('收到WebSocket消息:', data.type, data);
        
        switch (data.type) {
            case 'connected':
                logConsole('系统', '已连接到工作流', 'system');
                break;
            case 'status_update':
                updateWorkflowStatus(data.data);
                break;
            case 'phase_change':
                handlePhaseChange(data.data);
                break;
            case 'phase_update':
                // 阶段状态更新 - 由后端通知阶段完成状态
                handlePhaseUpdate(data.data);
                break;
            case 'sub_workers_created':
                // 后端通知创建子工种
                handleSubWorkersCreated(data.data);
                break;
            case 'sub_worker_update':
                // 子工种状态更新
                handleSubWorkerUpdate(data.data);
                break;
            case 'worker_output':
                // 工种输出更新 - 普通消息
                handleWorkerOutput(data.data);
                break;
            case 'stream_start':
                // 流式输出开始
                handleStreamStart(data.data);
                break;
            case 'stream_chunk':
                // 流式输出块
                handleStreamChunk(data.data);
                break;
            case 'stream_end':
                // 流式输出结束
                handleStreamEnd(data.data);
                break;
            case 'message':
                handleAgentMessage(data.data);
                break;
            case 'heartbeat':
                // 心跳响应
                break;
            default:
                console.log('收到未知类型消息:', data);
        }
    }
    
    attemptReconnect(workflowId) {
        if (state.reconnectAttempts < CONFIG.MAX_RECONNECT_ATTEMPTS) {
            state.reconnectAttempts++;
            logConsole('系统', `尝试重新连接... (${state.reconnectAttempts}/${CONFIG.MAX_RECONNECT_ATTEMPTS})`, 'system');
            setTimeout(() => this.connect(workflowId), CONFIG.RECONNECT_INTERVAL);
        } else {
            logConsole('错误', '连接失败，请刷新页面重试', 'error');
        }
    }
    
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

const wsManager = new WebSocketManager();

// ==================== API调用 ====================
const API = {
    async createWorkflow(gameIdea, projectName) {
        const response = await fetch(`${CONFIG.API_BASE}/api/workflow/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game_idea: gameIdea, project_name: projectName })
        });
        return response.json();
    },
    
    async startWorkflow(workflowId) {
        const response = await fetch(`${CONFIG.API_BASE}/api/workflow/${workflowId}/start`, {
            method: 'POST'
        });
        return response.json();
    },
    
    async stopWorkflow(workflowId) {
        const response = await fetch(`${CONFIG.API_BASE}/api/workflow/${workflowId}/stop`, {
            method: 'POST'
        });
        return response.json();
    },
    
    async getWorkflowStatus(workflowId) {
        const response = await fetch(`${CONFIG.API_BASE}/api/workflow/${workflowId}`);
        return response.json();
    }
};

// ==================== UI更新函数 ====================
function updateConnectionStatus(connected) {
    const statusEl = elements.connectionStatus;
    if (connected) {
        statusEl.textContent = '● 在线';
        statusEl.className = 'stat-value online';
    } else {
        statusEl.textContent = '● 离线';
        statusEl.className = 'stat-value offline';
    }
}

function updateSystemStatus(status, isError = false) {
    const statusEl = elements.systemStatus;
    statusEl.textContent = `● ${status}`;
    statusEl.style.color = isError ? '#ff4444' : 'var(--primary-color)';
}

function logConsole(source, message, type = 'info') {
    const line = document.createElement('div');
    line.className = `console-line ${type}`;
    
    const timestamp = new Date().toLocaleTimeString('zh-CN', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    line.innerHTML = `
        <span class="timestamp">[${timestamp}]</span>
        <span class="content">[${source}] ${message}</span>
    `;
    
    elements.consoleOutput.appendChild(line);
    
    if (state.autoScroll) {
        elements.consoleOutput.scrollTop = elements.consoleOutput.scrollHeight;
    }
}

function updatePhase(phase) {
    state.currentPhase = phase;
    const steps = elements.phaseBar.querySelectorAll('.phase-step');
    
    const phaseMap = {
        'design': 0,
        'program': 1,
        'test': 2,
        'deploy': 3
    };
    
    const activeIndex = phaseMap[phase] || 0;
    
    steps.forEach((step, index) => {
        step.classList.remove('active', 'completed');
        if (index < activeIndex) {
            step.classList.add('completed');
        } else if (index === activeIndex) {
            step.classList.add('active');
        }
    });
}

function updateWorkflowStatus(data) {
    updateSystemStatus(data.status);
    
    if (data.current_phase) {
        const phaseMap = {
            '策划阶段': 'design',
            '程序框架': 'program',
            '测试阶段': 'test',
            '部署阶段': 'deploy'
        };
        updatePhase(phaseMap[data.current_phase] || 'design');
    }
}

// ==================== 子工种动态管理 ====================

// 处理后端通知创建子工种
function handleSubWorkersCreated(data) {
    const { phase, workers } = data;
    
    // 清空当前子工种显示
    elements.parallelWorkers.innerHTML = '';
    state.currentSubWorkers = [];
    
    if (!workers || workers.length === 0) {
        elements.parallelWorkers.style.display = 'none';
        return;
    }
    
    elements.parallelWorkers.style.display = 'flex';
    
    // 创建子工种按钮
    workers.forEach(workerData => {
        const workerId = workerData.id;
        
        // 存储工种数据
        state.workers.set(workerId, {
            id: workerId,
            name: workerData.name,
            description: workerData.description || '',
            status: workerData.status || 'pending',
            output: workerData.output || []
        });
        
        state.currentSubWorkers.push(workerId);
        
        // 创建按钮
        createSubWorkerButton(workerId, workerData);
    });
    
    logConsole('系统', `${phase === 'design' ? '策划' : '开发'}阶段并行任务已创建: ${workers.length}个`, 'system');
}

// 创建子工种按钮
function createSubWorkerButton(workerId, workerData) {
    const template = document.getElementById('subWorkerTemplate');
    const clone = template.content.cloneNode(true);
    const btn = clone.querySelector('.sub-worker-btn');
    
    btn.dataset.workerId = workerId;
    btn.querySelector('.worker-name').textContent = workerData.name;
    btn.querySelector('.worker-status').textContent = getStatusText(workerData.status || 'pending');
    
    if (workerData.status === 'running') {
        btn.classList.add('active');
    }
    
    elements.parallelWorkers.appendChild(btn);
}

// 处理子工种状态更新
function handleSubWorkerUpdate(data) {
    const { worker_id, status } = data;
    
    const worker = state.workers.get(worker_id);
    if (worker) {
        worker.status = status;
        
        // 更新按钮UI
        const btn = document.querySelector(`.sub-worker-btn[data-worker-id="${worker_id}"]`);
        if (btn) {
            btn.querySelector('.worker-status').textContent = getStatusText(status);
            if (status === 'running') {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        }
    }
}

// 处理工种输出更新（普通消息）
function handleWorkerOutput(data) {
    const { worker_id, content, timestamp } = data;
    
    let worker = state.workers.get(worker_id);
    
    // 如果工种不存在，创建一个（用于主工种）
    if (!worker) {
        worker = {
            id: worker_id,
            name: getWorkerNameById(worker_id),
            description: getWorkerDescriptionById(worker_id),
            status: 'running',
            output: []
        };
        state.workers.set(worker_id, worker);
    }
    
    // 添加输出
    worker.output.push({
        timestamp: timestamp || new Date().toLocaleTimeString('zh-CN'),
        content: content,
        type: 'message'
    });
    
    // 限制输出历史长度
    if (worker.output.length > 100) {
        worker.output.shift();
    }
    
    // 如果当前正在查看该工种的流式输出，也添加到流式面板
    if (state.activeStreamWorker === worker_id) {
        appendStreamLine(timestamp || new Date().toLocaleTimeString('zh-CN'), content, false);
    }
}

// ==================== 流式输出处理 ====================

// 流式输出开始
function handleStreamStart(data) {
    const { worker_id, worker_name, description } = data;
    
    console.log('流式输出开始:', worker_id, worker_name);
    
    // 确保工种存在
    let worker = state.workers.get(worker_id);
    if (!worker) {
        worker = {
            id: worker_id,
            name: worker_name || getWorkerNameById(worker_id),
            description: description || getWorkerDescriptionById(worker_id),
            status: 'running',
            output: []
        };
        state.workers.set(worker_id, worker);
    }
    
    // 设置当前活跃的流式工种
    state.activeStreamWorker = worker_id;
    
    // 初始化缓存（如果不存在）
    if (!state.streamCache.has(worker_id)) {
        state.streamCache.set(worker_id, {
            chunks: [],
            isStreaming: true,
            startTime: new Date().toLocaleTimeString('zh-CN')
        });
    } else {
        // 更新为流式中状态
        const cache = state.streamCache.get(worker_id);
        cache.isStreaming = true;
    }
    
    // 只有当用户没有手动关闭面板时才自动打开
    if (!state.userClosedPanel) {
        openStreamPanel(worker_id, worker.name);
        
        // 添加开始标记
        appendStreamLine(
            new Date().toLocaleTimeString('zh-CN'),
            `【${worker.name}】开始工作...`,
            false,
            'system'
        );
    }
}

// 流式输出块
function handleStreamChunk(data) {
    const { worker_id, worker_name, chunk, timestamp } = data;
    
    console.log('收到流式块:', worker_id, chunk?.substring(0, 50));
    
    // 如果没有活跃的流式工种，或者收到了不同工种的消息，切换到新工种
    if (!state.activeStreamWorker || state.activeStreamWorker !== worker_id) {
        // 如果之前有活跃的工种，先结束它
        if (state.activeStreamWorker && state.activeStreamWorker !== worker_id) {
            console.log('切换到新工种:', worker_id, '之前:', state.activeStreamWorker);
            // 将之前的缓存标记为非流式中
            const prevCache = state.streamCache.get(state.activeStreamWorker);
            if (prevCache) {
                prevCache.isStreaming = false;
            }
        }
        
        state.activeStreamWorker = worker_id;
        
        // 确保工种存在
        if (!state.workers.has(worker_id)) {
            state.workers.set(worker_id, {
                id: worker_id,
                name: worker_name || worker_id,
                description: '',
                status: 'running',
                output: []
            });
        }
        
        // 初始化新工种的缓存
        if (!state.streamCache.has(worker_id)) {
            state.streamCache.set(worker_id, {
                chunks: [],
                isStreaming: true,
                startTime: timestamp || new Date().toLocaleTimeString('zh-CN')
            });
        }
        
        // 只有当用户没有手动关闭面板时才自动打开
        if (!state.userClosedPanel) {
            openStreamPanel(worker_id, worker_name || worker_id);
            
            // 添加开始标记
            appendStreamLine(
                timestamp || new Date().toLocaleTimeString('zh-CN'),
                `【${worker_name || worker_id}】开始工作...`,
                false,
                'system'
            );
        }
    }
    
    // 获取缓存
    let cache = state.streamCache.get(worker_id);
    if (!cache) {
        cache = { 
            chunks: [], 
            isStreaming: true,
            startTime: timestamp || new Date().toLocaleTimeString('zh-CN')
        };
        state.streamCache.set(worker_id, cache);
    }
    
    // 添加块到缓存
    cache.chunks.push(chunk);
    
    // 更新 pendingStreamContent（用于实时渲染）
    pendingStreamContent = cache.chunks.join('');
    
    // 只有当面板打开且显示当前工种时才实时显示
    if (state.currentPanelWorker === worker_id && !state.userClosedPanel) {
        // 实时显示到流式面板
        appendStreamChunk(chunk);
        
        // 自动滚动到底部
        elements.streamContent.scrollTop = elements.streamContent.scrollHeight;
    }
}

// 流式输出结束
function handleStreamEnd(data) {
    const { worker_id, full_content, timestamp } = data;
    
    console.log('流式输出结束:', worker_id);
    
    const worker = state.workers.get(worker_id);
    const cache = state.streamCache.get(worker_id);
    
    // 获取完整内容（优先使用传入的，否则从缓存拼接）
    const completeContent = full_content || (cache ? cache.chunks.join('') : '');
    
    if (worker) {
        // 保存完整输出到工种历史
        worker.output.push({
            timestamp: timestamp || new Date().toLocaleTimeString('zh-CN'),
            content: completeContent,
            type: 'stream'
        });
        
        // 限制输出历史长度
        if (worker.output.length > 100) {
            worker.output.shift();
        }
        
        // 更新工种状态为已完成
        worker.status = 'completed';
    }
    
    // 更新缓存状态
    if (cache) {
        cache.isStreaming = false;
        cache.completeContent = completeContent;
        cache.endTime = timestamp || new Date().toLocaleTimeString('zh-CN');
    }
    
    // 只有当面板打开且显示当前工种时才更新UI
    if (state.currentPanelWorker === worker_id && !state.userClosedPanel) {
        updateStreamStatus('completed');
        
        // 添加结束标记
        appendStreamLine(
            timestamp || new Date().toLocaleTimeString('zh-CN'),
            `【${worker?.name || '未知工种'}】工作完成`,
            false,
            'system'
        );
    }
    
    // 如果当前活跃的工种完成了，重置它
    if (state.activeStreamWorker === worker_id) {
        state.activeStreamWorker = null;
    }
}

// 处理阶段变更
function handlePhaseChange(data) {
    const { phase, from_phase } = data;
    
    updatePhase(phase);
    
    // 清空上一个阶段的子工种
    if (from_phase) {
        elements.parallelWorkers.innerHTML = '';
        state.currentSubWorkers = [];
    }
}

// 处理阶段状态更新 - 由后端通知阶段完成状态
function handlePhaseUpdate(data) {
    const { phase_id, phase_name, status, timestamp } = data;
    
    console.log('阶段状态更新:', phase_id, phase_name, status);
    
    // 更新阶段状态到状态管理
    if (!state.phaseStatus) {
        state.phaseStatus = new Map();
    }
    state.phaseStatus.set(phase_id, {
        name: phase_name,
        status: status,
        timestamp: timestamp
    });
    
    // 根据状态更新UI
    if (status === 'running') {
        // 阶段开始
        logConsole('系统', `【${phase_name}】开始`, 'system');
        updatePhaseById(phase_id);
    } else if (status === 'completed') {
        // 阶段完成
        logConsole('系统', `【${phase_name}】✓ 完成`, 'success');
        markPhaseCompleted(phase_id);
    } else if (status === 'failed') {
        // 阶段失败
        logConsole('系统', `【${phase_name}】✗ 失败`, 'error');
    }
}

// 根据阶段ID更新当前阶段
function updatePhaseById(phaseId) {
    // 阶段到步骤的映射
    const phaseStepMap = {
        'design': 0,
        'sub_design': 0,
        'merge_design': 0,
        'framework': 1,
        'sub_code': 1,
        'merge_code': 1,
        'review': 1,
        'test': 2,
        'deploy': 3
    };
    
    const stepIndex = phaseStepMap[phaseId];
    if (stepIndex !== undefined) {
        updatePhaseByStepIndex(stepIndex);
    }
}

// 根据步骤索引更新阶段
function updatePhaseByStepIndex(stepIndex) {
    const steps = elements.phaseBar.querySelectorAll('.phase-step');
    
    steps.forEach((step, index) => {
        step.classList.remove('active', 'completed');
        if (index < stepIndex) {
            step.classList.add('completed');
        } else if (index === stepIndex) {
            step.classList.add('active');
        }
    });
}

// 标记阶段为已完成
function markPhaseCompleted(phaseId) {
    // 可以在这里添加完成动画或其他视觉效果
    const phaseStepMap = {
        'design': 0,
        'sub_design': 0,
        'merge_design': 0,
        'framework': 1,
        'sub_code': 1,
        'merge_code': 1,
        'review': 1,
        'test': 2,
        'deploy': 3
    };
    
    const stepIndex = phaseStepMap[phaseId];
    if (stepIndex !== undefined) {
        const steps = elements.phaseBar.querySelectorAll('.phase-step');
        if (steps[stepIndex]) {
            steps[stepIndex].classList.add('completed');
            steps[stepIndex].classList.remove('active');
        }
    }
}

function getStatusText(status) {
    const statusMap = {
        'pending': '等待中',
        'running': '进行中',
        'completed': '已完成',
        'failed': '失败'
    };
    return statusMap[status] || status;
}

function getWorkerNameById(workerId) {
    const nameMap = {
        'lead_designer': '主策划',
        'lead_programmer': '主程序',
        'tester': '测试员',
        'deployer': '部署员'
    };
    return nameMap[workerId] || workerId;
}

function getWorkerDescriptionById(workerId) {
    const descMap = {
        'lead_designer': '负责游戏整体框架设计和任务分配',
        'lead_programmer': '负责基础框架搭建和代码审核',
        'tester': '负责游戏测试和Bug反馈',
        'deployer': '负责游戏部署和发布'
    };
    return descMap[workerId] || '';
}

function handleAgentMessage(message) {
    const { agent_role, content, type } = message;
    
    // 根据消息类型设置日志类型
    let logType = 'info';
    if (type === 'error') logType = 'error';
    else if (type === 'system') logType = 'system';
    
    logConsole(agent_role, content, logType);
}

// ==================== 流式输出面板管理 ====================

// 打开流式输出面板
function openStreamPanel(workerId, workerName, renderHistory = true) {
    // 设置当前面板显示的工种
    state.currentPanelWorker = workerId;
    
    // 重置用户关闭标记（因为这是用户主动打开）
    state.userClosedPanel = false;
    
    // 设置标题
    elements.streamTitle.textContent = `${workerName} - 实时输出`;
    
    // 清空内容
    elements.streamContent.innerHTML = '';
    
    // 显示面板
    elements.streamPanel.classList.remove('hidden');
    // 使用setTimeout确保过渡动画生效
    setTimeout(() => {
        elements.streamPanel.classList.add('show');
    }, 10);
    
    // 获取缓存
    const cache = state.streamCache.get(workerId);
    const worker = state.workers.get(workerId);
    
    // 如果需要渲染历史且存在缓存
    if (renderHistory && cache && cache.chunks.length > 0) {
        // 添加开始标记
        appendStreamLine(
            cache.startTime,
            `【${workerName}】开始工作...`,
            false,
            'system'
        );
        
        // 渲染所有缓存的内容（使用 Markdown）
        const fullContent = cache.chunks.join('');
        
        // 创建 Markdown 容器
        const line = document.createElement('div');
        line.className = 'stream-line stream-markdown-container';
        line.innerHTML = `<span class="timestamp">[${cache.startTime}]</span><div class="content markdown-content">${renderMarkdown(fullContent)}</div>`;
        elements.streamContent.appendChild(line);
        
        // 如果已完成，添加结束标记
        if (!cache.isStreaming && cache.endTime) {
            appendStreamLine(
                cache.endTime,
                `【${workerName}】工作完成`,
                false,
                'system'
            );
            updateStreamStatus('completed');
        } else {
            updateStreamStatus('streaming');
            // 恢复 pendingStreamContent 以便继续接收新内容
            pendingStreamContent = fullContent;
        }
    } else if (renderHistory && worker && worker.output.length > 0) {
        // 从历史记录渲染
        worker.output.forEach(item => {
            if (item.type === 'stream') {
                const line = document.createElement('div');
                line.className = 'stream-line';
                line.innerHTML = `<span class="timestamp">[${item.timestamp}]</span><div class="content markdown-content">${renderMarkdown(item.content)}</div>`;
                elements.streamContent.appendChild(line);
            } else {
                appendStreamLine(item.timestamp, item.content, false);
            }
        });
        updateStreamStatus(worker.status === 'running' ? 'streaming' : 'completed');
    } else {
        updateStreamStatus('streaming');
    }
}

// 关闭流式输出面板
function closeStreamPanel() {
    // 标记为用户手动关闭
    state.userClosedPanel = true;
    
    // 完成当前流式渲染
    if (streamRenderTimeout) {
        clearTimeout(streamRenderTimeout);
        streamRenderTimeout = null;
    }
    
    elements.streamPanel.classList.remove('show');
    
    setTimeout(() => {
        elements.streamPanel.classList.add('hidden');
        elements.streamContent.innerHTML = '';
        state.currentPanelWorker = null;
        // 注意：不要重置 pendingStreamContent，保留缓存以便重新打开时恢复
    }, 300);
}

// 更新流式状态显示
function updateStreamStatus(status) {
    const statusDot = elements.streamStatus.querySelector('.status-dot');
    const statusText = elements.streamStatus.querySelector('.status-text');
    
    statusDot.className = 'status-dot ' + status;
    
    const statusMap = {
        'streaming': '正在接收流式输出...',
        'completed': '输出已完成',
        'waiting': '等待中...'
    };
    
    statusText.textContent = statusMap[status] || status;
}

// 当前正在流式渲染的容器
let currentStreamContainer = null;
let streamRenderTimeout = null;
let pendingStreamContent = '';

// 添加系统消息行
function appendStreamLine(timestamp, content, isChunk = false, type = 'normal') {
    const line = document.createElement('div');
    line.className = 'stream-line';
    
    if (type === 'system') {
        line.innerHTML = `<span class="timestamp">[${timestamp}]</span><span class="content system-message">${escapeHtml(content)}</span>`;
    } else {
        // 使用 Markdown 渲染
        const renderedContent = renderMarkdown(content);
        line.innerHTML = `<span class="timestamp">[${timestamp}]</span><div class="content markdown-content">${renderedContent}</div>`;
    }
    
    elements.streamContent.appendChild(line);
    elements.streamContent.scrollTop = elements.streamContent.scrollHeight;
}

// 追加流式块（实时追加到当前行，使用 Markdown 渲染）
function appendStreamChunk(chunk) {
    // 累积内容
    pendingStreamContent += chunk;
    
    // 使用防抖，避免过于频繁的渲染
    if (streamRenderTimeout) {
        clearTimeout(streamRenderTimeout);
    }
    
    streamRenderTimeout = setTimeout(() => {
        renderStreamContent();
    }, 100); // 100ms 防抖
}

// 渲染流式内容
function renderStreamContent() {
    if (!pendingStreamContent) return;
    
    // 查找或创建流式容器
    let streamContainer = elements.streamContent.querySelector('.stream-markdown-container');
    
    if (!streamContainer) {
        // 创建新的流式容器
        streamContainer = document.createElement('div');
        streamContainer.className = 'stream-line stream-markdown-container';
        streamContainer.innerHTML = `<span class="timestamp">[${new Date().toLocaleTimeString('zh-CN')}]</span><div class="content markdown-content"></div>`;
        elements.streamContent.appendChild(streamContainer);
    }
    
    const contentDiv = streamContainer.querySelector('.markdown-content');
    
    // 使用 Markdown 渲染累积的内容
    contentDiv.innerHTML = renderMarkdown(pendingStreamContent);
    
    // 自动滚动
    elements.streamContent.scrollTop = elements.streamContent.scrollHeight;
}

// Markdown 渲染函数
function renderMarkdown(content) {
    if (typeof marked === 'undefined') {
        // 如果 marked 未加载，使用 HTML 转义
        return escapeHtml(content);
    }
    
    try {
        // 使用 marked 渲染 Markdown
        const html = marked.parse(content);
        return html;
    } catch (e) {
        console.error('Markdown 渲染失败:', e);
        return escapeHtml(content);
    }
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 完成流式输出渲染
function finalizeStreamRender() {
    if (streamRenderTimeout) {
        clearTimeout(streamRenderTimeout);
        streamRenderTimeout = null;
    }
    
    // 最后一次渲染
    renderStreamContent();
    
    // 重置状态
    pendingStreamContent = '';
    currentStreamContainer = null;
}

// ==================== 阶段点击处理 ====================
function handlePhaseClick(phase) {
    const phaseMap = {
        'design': 'lead_designer',
        'program': 'lead_programmer',
        'test': 'tester',
        'deploy': 'deployer'
    };
    
    const workerId = phaseMap[phase];
    if (!workerId) return;
    
    // 检查是否是当前阶段或已完成阶段
    const stepElement = document.querySelector(`.phase-step[data-phase="${phase}"]`);
    
    if (!stepElement) return;
    
    // 只有当前活跃阶段或已完成阶段才能点击查看详情
    if (stepElement.classList.contains('active') || stepElement.classList.contains('completed')) {
        showWorkerStreamHistory(workerId);
    }
}

// 子工种点击处理
function handleSubWorkerClick(btn) {
    const workerId = btn.dataset.workerId;
    if (workerId) {
        showWorkerStreamHistory(workerId);
    }
}

// 显示工种流式历史
function showWorkerStreamHistory(workerId) {
    const worker = state.workers.get(workerId);
    const cache = state.streamCache.get(workerId);
    
    if (!worker) {
        // 如果工种数据不存在，创建一个空的
        const emptyWorker = {
            id: workerId,
            name: getWorkerNameById(workerId),
            description: getWorkerDescriptionById(workerId),
            status: 'pending',
            output: []
        };
        state.workers.set(workerId, emptyWorker);
        showWorkerStreamHistory(workerId);
        return;
    }
    
    // 打开面板（使用缓存渲染历史）
    openStreamPanel(workerId, worker.name, true);
}

// ==================== 事件处理 ====================
async function startDevelopment() {
    const gameIdea = elements.gameIdea.value.trim();
    const projectName = elements.projectName.value.trim();
    
    if (!gameIdea) {
        alert('请输入游戏想法');
        return;
    }
    
    try {
        elements.startBtn.disabled = true;
        elements.startBtn.innerHTML = '<span class="btn-icon">⏳</span> 创建中...';
        
        // 创建工作流
        const workflow = await API.createWorkflow(gameIdea, projectName);
        state.workflowId = workflow.workflow_id;
        
        logConsole('系统', `工作流已创建: ${workflow.workflow_id}`, 'system');
        
        // 连接WebSocket
        await wsManager.connect(state.workflowId);
        
        // 切换到工作流视图
        elements.inputPanel.classList.add('hidden');
        elements.workflowPanel.classList.remove('hidden');
        
        // 启动工作流
        await API.startWorkflow(state.workflowId);
        state.isRunning = true;
        
        updateSystemStatus('运行中');
        logConsole('系统', '游戏开发流程已启动', 'system');
        
        // 设置初始阶段
        updatePhase('design');
        
        // 等待后端WebSocket消息，不再使用模拟数据
        
    } catch (error) {
        console.error('启动失败:', error);
        logConsole('错误', `启动失败: ${error.message}`, 'error');
        elements.startBtn.disabled = false;
        elements.startBtn.innerHTML = '<span class="btn-icon">▶</span> 开始开发';
    }
}

async function togglePause() {
    if (!state.workflowId) return;
    
    try {
        if (state.isPaused) {
            await API.startWorkflow(state.workflowId);
            state.isPaused = false;
            elements.pauseBtn.innerHTML = '⏸ 暂停';
            logConsole('系统', '工作流已恢复', 'system');
        } else {
            await API.stopWorkflow(state.workflowId);
            state.isPaused = true;
            elements.pauseBtn.innerHTML = '▶ 继续';
            logConsole('系统', '工作流已暂停', 'system');
        }
    } catch (error) {
        logConsole('错误', `操作失败: ${error.message}`, 'error');
    }
}

function resetWorkflow() {
    if (confirm('确定要重置当前工作流吗？')) {
        wsManager.disconnect();
        state.workflowId = null;
        state.isRunning = false;
        state.isPaused = false;
        state.currentPhase = 'design';
        state.workers.clear();
        state.currentSubWorkers = [];
        state.activeStreamWorker = null;
        state.streamCache.clear();
        state.userClosedPanel = false;
        state.currentPanelWorker = null;
        
        elements.parallelWorkers.innerHTML = '';
        elements.consoleOutput.innerHTML = '';
        
        // 关闭流式面板
        closeStreamPanel();
        
        elements.workflowPanel.classList.add('hidden');
        elements.inputPanel.classList.remove('hidden');
        
        elements.startBtn.disabled = false;
        elements.startBtn.innerHTML = '<span class="btn-icon">▶</span> 开始开发';
        
        // 重置阶段显示
        const steps = elements.phaseBar.querySelectorAll('.phase-step');
        steps.forEach(step => {
            step.classList.remove('active', 'completed');
        });
        document.querySelector('.phase-step[data-phase="design"]').classList.add('active');
        
        updateSystemStatus('就绪');
        logConsole('系统', '工作流已重置', 'system');
    }
}

function clearConsole() {
    elements.consoleOutput.innerHTML = '';
}

function toggleAutoScroll() {
    state.autoScroll = !state.autoScroll;
    elements.autoScrollBtn.style.opacity = state.autoScroll ? '1' : '0.5';
}

// ==================== 初始化 ====================
function init() {
    // 启动矩阵背景
    const matrixBg = new MatrixBackground();
    matrixBg.start();
    
    // 检查API连接
    checkAPIConnection();
    
    // 定期发送心跳
    setInterval(() => {
        if (state.isConnected) {
            wsManager.send({ type: 'ping' });
        }
    }, 30000);
    
    // 设置初始阶段
    updatePhase('design');
    
    logConsole('系统', '矩阵游戏引擎前端已加载', 'system');
}

async function checkAPIConnection() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/`);
        if (response.ok) {
            updateConnectionStatus(true);
            logConsole('系统', '已连接到后端服务', 'system');
        }
    } catch (error) {
        updateConnectionStatus(false);
        logConsole('警告', '无法连接到后端服务，请确保服务已启动', 'error');
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);

// 页面关闭时清理
window.addEventListener('beforeunload', () => {
    wsManager.disconnect();
});

// ESC键关闭流式面板
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeStreamPanel();
    }
});

// 点击空白处关闭流式面板
document.addEventListener('click', (e) => {
    // 如果面板没有打开，不需要处理
    if (!state.currentPanelWorker) return;
    
    // 检查点击的是否在面板内部
    const streamPanel = elements.streamPanel;
    const isClickInsidePanel = streamPanel.contains(e.target);
    
    // 检查点击的是否是触发打开面板的元素
    const isClickOnTrigger = e.target.closest('.sub-worker-btn') || 
                              e.target.closest('.phase-step');
    
    // 如果点击在面板外部且不是触发元素，则关闭面板
    if (!isClickInsidePanel && !isClickOnTrigger) {
        closeStreamPanel();
    }
});
