#!/bin/bash
# =====================================================
# GameGodEngine 快速启动脚本
# 适用于已安装 Docker 的环境
# =====================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        print_info "运行: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    
    if ! docker compose version &> /dev/null && ! docker-compose --version &> /dev/null; then
        print_error "Docker Compose 未安装"
        exit 1
    fi
    
    print_success "Docker 检查通过"
}

# 检查环境变量
check_env() {
    if [ ! -f ".env" ]; then
        print_warning ".env 文件不存在，从示例创建..."
        cp .env.example .env
        print_error "请先编辑 .env 文件，填入你的 OpenAI API 密钥"
        exit 1
    fi
    
    # 检查 OPENAI_API_KEY
    if ! grep -q "OPENAI_API_KEY=sk-" .env; then
        print_error "请在 .env 文件中设置有效的 OpenAI API 密钥"
        exit 1
    fi
    
    print_success "环境变量检查通过"
}

# 启动服务
start_services() {
    print_info "启动 GameGodEngine 服务..."
    
    # 构建并启动
    docker compose up -d --build
    
    print_success "服务已启动"
}

# 等待服务就绪
wait_for_ready() {
    print_info "等待服务就绪..."
    
    local retries=30
    local count=0
    
    while [ $count -lt $retries ]; do
        if curl -s http://localhost:8000/ > /dev/null 2>&1; then
            print_success "服务已就绪！"
            return 0
        fi
        
        count=$((count + 1))
        echo -n "."
        sleep 2
    done
    
    print_error "服务启动超时"
    return 1
}

# 显示访问信息
show_access_info() {
    local ip=$(hostname -I | awk '{print $1}')
    
    echo ""
    echo "================================================"
    print_success "GameGodEngine 启动成功！"
    echo "================================================"
    echo ""
    echo "访问地址:"
    echo "  - 本地: http://localhost:8000"
    echo "  - 局域网: http://$ip:8000"
    echo ""
    echo "API 文档:"
    echo "  - Swagger UI: http://$ip:8000/docs"
    echo "  - ReDoc: http://$ip:8000/redoc"
    echo ""
    echo "管理命令:"
    echo "  查看日志: docker compose logs -f"
    echo "  停止服务: docker compose down"
    echo "  重启服务: docker compose restart"
    echo "  进入容器: docker compose exec gamegodengine /bin/sh"
    echo ""
    echo "================================================"
}

# 主函数
main() {
    echo "================================================"
    echo "  GameGodEngine 快速启动"
    echo "================================================"
    echo ""
    
    # 切换到脚本所在目录
    cd "$(dirname "$0")/.."
    
    # 检查
    check_docker
    check_env
    
    # 启动
    start_services
    wait_for_ready
    
    # 显示信息
    show_access_info
}

main "$@"
