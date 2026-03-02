#!/bin/bash

echo "============================================"
echo "   矩阵游戏引擎 - Matrix Game Engine"
echo "============================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3，请确保Python已安装"
    exit 1
fi

echo "[1/3] 检查依赖..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "[2/3] 安装依赖..."
    pip3 install -r server/requirements-web.txt
else
    echo "[2/3] 依赖已安装"
fi

echo "[3/3] 启动服务..."
echo ""
echo "============================================"
echo "  服务启动中..."
echo "  访问 http://localhost:8000 查看界面"
echo "  API文档 http://localhost:8000/docs"
echo "============================================"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

cd server
python3 start_server.py
