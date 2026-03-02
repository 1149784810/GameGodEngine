"""
矩阵游戏引擎 - 服务启动脚本
一键启动后端API服务
"""

import os
import sys
import subprocess
import argparse


def check_dependencies():
    """检查依赖是否安装"""
    try:
        import fastapi
        import uvicorn
        print("✓ 依赖检查通过")
        return True
    except ImportError:
        print("✗ 缺少依赖，正在安装...")
        return False


def install_dependencies():
    """安装依赖"""
    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements-web.txt")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
    print("✓ 依赖安装完成")


def start_server(host="0.0.0.0", port=8000, reload=False):
    """启动服务器"""
    print("=" * 60)
    print("🎮 矩阵游戏引擎 - 启动服务")
    print("=" * 60)
    print(f"\n服务地址: http://{host}:{port}")
    print(f"API文档: http://{host}:{port}/docs")
    print(f"WebSocket: ws://{host}:{port}/ws/workflow/{'{workflow_id}'}")
    print("\n按 Ctrl+C 停止服务")
    print("=" * 60 + "\n")
    
    # 使用uvicorn启动
    import uvicorn
    # 添加当前目录到路径确保导入正常
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


def main():
    parser = argparse.ArgumentParser(description="矩阵游戏引擎服务")
    parser.add_argument("--host", default="0.0.0.0", help="主机地址")
    parser.add_argument("--port", type=int, default=8000, help="端口号")
    parser.add_argument("--reload", action="store_true", help="开发模式（自动重载）")
    parser.add_argument("--install", action="store_true", help="安装依赖")
    
    args = parser.parse_args()
    
    # 检查/安装依赖
    if args.install or not check_dependencies():
        install_dependencies()
    
    # 启动服务
    try:
        start_server(args.host, args.port, args.reload)
    except KeyboardInterrupt:
        print("\n\n服务已停止")


if __name__ == "__main__":
    main()
