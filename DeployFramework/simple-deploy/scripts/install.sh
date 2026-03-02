#!/bin/bash
# =====================================================
# GameGodEngine Linux 开发服务器一键安装脚本
# 支持 Ubuntu/Debian/CentOS
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

# 检测操作系统
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        print_error "无法检测操作系统"
        exit 1
    fi
    print_info "检测到操作系统: $OS $VERSION"
}

# 安装 Docker
install_docker() {
    print_info "安装 Docker..."
    
    if command -v docker &> /dev/null; then
        print_success "Docker 已安装"
        docker --version
        return
    fi
    
    case $OS in
        ubuntu|debian)
            # 安装依赖
            apt-get update
            apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
            
            # 添加 Docker GPG 密钥
            curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
            
            # 添加 Docker 仓库
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/$OS $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            # 安装 Docker
            apt-get update
            apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            ;;
            
        centos|rhel|fedora|rocky|almalinux)
            # 安装依赖
            yum install -y yum-utils
            
            # 添加 Docker 仓库
            yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            
            # 安装 Docker
            yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            ;;
            
        *)
            print_error "不支持的操作系统: $OS"
            exit 1
            ;;
    esac
    
    # 启动 Docker
    systemctl start docker
    systemctl enable docker
    
    print_success "Docker 安装完成"
    docker --version
}

# 安装 Docker Compose
install_docker_compose() {
    print_info "安装 Docker Compose..."
    
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        print_success "Docker Compose 已安装"
        docker compose version || docker-compose --version
        return
    fi
    
    # 安装 Docker Compose 插件
    case $OS in
        ubuntu|debian)
            apt-get install -y docker-compose-plugin
            ;;
        centos|rhel|fedora|rocky|almalinux)
            yum install -y docker-compose-plugin
            ;;
    esac
    
    print_success "Docker Compose 安装完成"
}

# 配置 Docker 用户组
configure_docker_user() {
    print_info "配置 Docker 用户组..."
    
    # 创建 docker 组（如果不存在）
    groupadd -f docker
    
    # 将当前用户添加到 docker 组
    if [ -n "$SUDO_USER" ]; then
        usermod -aG docker $SUDO_USER
        print_success "已将 $SUDO_USER 添加到 docker 组"
        print_warning "请重新登录或运行 'newgrp docker' 使更改生效"
    fi
}

# 创建项目目录
setup_project() {
    print_info "设置项目目录..."
    
    # 项目目录
    PROJECT_DIR="/opt/gamegodengine"
    
    # 创建目录
    mkdir -p $PROJECT_DIR
    
    # 复制部署文件
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"
    
    cp -r "$DEPLOY_DIR"/* $PROJECT_DIR/
    
    # 设置权限
    if [ -n "$SUDO_USER" ]; then
        chown -R $SUDO_USER:$SUDO_USER $PROJECT_DIR
    fi
    
    print_success "项目目录创建完成: $PROJECT_DIR"
}

# 配置环境变量
setup_env() {
    print_info "配置环境变量..."
    
    PROJECT_DIR="/opt/gamegodengine"
    
    # 复制示例文件
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        print_warning "请编辑 $PROJECT_DIR/.env 文件，填入你的 OpenAI API 密钥"
    fi
    
    print_success "环境变量配置完成"
}

# 创建系统服务
create_systemd_service() {
    print_info "创建系统服务..."
    
    cat > /etc/systemd/system/gamegodengine.service << 'EOF'
[Unit]
Description=GameGodEngine Development Server
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/gamegodengine
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable gamegodengine.service
    
    print_success "系统服务创建完成"
    print_info "可以使用以下命令管理服务:"
    echo "  sudo systemctl start gamegodengine   # 启动"
    echo "  sudo systemctl stop gamegodengine    # 停止"
    echo "  sudo systemctl status gamegodengine  # 查看状态"
}

# 创建管理脚本
create_manage_script() {
    print_info "创建管理脚本..."
    
    cat > /usr/local/bin/gge << 'EOF'
#!/bin/bash
# GameGodEngine 管理脚本

PROJECT_DIR="/opt/gamegodengine"

cd $PROJECT_DIR

case "$1" in
    start)
        echo "启动 GameGodEngine..."
        docker compose up -d
        ;;
    stop)
        echo "停止 GameGodEngine..."
        docker compose down
        ;;
    restart)
        echo "重启 GameGodEngine..."
        docker compose restart
        ;;
    status)
        echo "查看状态..."
        docker compose ps
        ;;
    logs)
        echo "查看日志..."
        docker compose logs -f ${2:-}
        ;;
    update)
        echo "更新代码并重启..."
        docker compose down
        docker compose pull
        docker compose up -d --build
        ;;
    shell)
        echo "进入容器 shell..."
        docker compose exec gamegodengine /bin/sh
        ;;
    *)
        echo "用法: gge [start|stop|restart|status|logs|update|shell]"
        echo ""
        echo "命令:"
        echo "  start    启动服务"
        echo "  stop     停止服务"
        echo "  restart  重启服务"
        echo "  status   查看状态"
        echo "  logs     查看日志"
        echo "  update   更新并重启"
        echo "  shell    进入容器"
        ;;
esac
EOF
    
    chmod +x /usr/local/bin/gge
    print_success "管理脚本创建完成: gge"
}

# 主安装流程
main() {
    echo "================================================"
    echo "  GameGodEngine Linux 开发服务器安装脚本"
    echo "================================================"
    echo ""
    
    # 检查 root 权限
    if [ "$EUID" -ne 0 ]; then
        print_error "请使用 sudo 运行此脚本"
        exit 1
    fi
    
    # 检测操作系统
    detect_os
    
    # 安装 Docker
    install_docker
    
    # 安装 Docker Compose
    install_docker_compose
    
    # 配置 Docker 用户组
    configure_docker_user
    
    # 设置项目
    setup_project
    
    # 配置环境变量
    setup_env
    
    # 创建系统服务
    create_systemd_service
    
    # 创建管理脚本
    create_manage_script
    
    echo ""
    echo "================================================"
    print_success "安装完成！"
    echo "================================================"
    echo ""
    echo "下一步:"
    echo "1. 编辑配置文件: sudo nano /opt/gamegodengine/.env"
    echo "2. 填入你的 OpenAI API 密钥"
    echo "3. 启动服务: sudo gge start"
    echo "4. 访问: http://<服务器IP>:8000"
    echo ""
    echo "管理命令:"
    echo "  sudo gge start    # 启动"
    echo "  sudo gge stop     # 停止"
    echo "  sudo gge logs     # 查看日志"
    echo "  sudo gge shell    # 进入容器"
    echo ""
    echo "如果使用 systemd:"
    echo "  sudo systemctl start gamegodengine"
    echo ""
}

main "$@"
