#!/bin/bash
# ==========================================
# AI_OS VPS 一键部署脚本
# 用法: chmod +x setup_vps.sh && ./setup_vps.sh
# ==========================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}  AI_OS VPS 一键部署开始${NC}"
echo -e "${GREEN}==================================${NC}"

# ─── 1. 基础依赖 ───
echo -e "${YELLOW}[1/6] 更新系统 + 安装基础依赖...${NC}"
sudo apt-get update -qq
sudo apt-get install -y -qq curl git ufw ripgrep unzip python3 python3-pip python3-venv

# ─── 2. Docker ───
echo -e "${YELLOW}[2/6] 安装 Docker...${NC}"
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sudo bash
    sudo usermod -aG docker "$USER"
    echo -e "${GREEN}Docker installed.${NC}"
else
    echo -e "${GREEN}Docker already installed.${NC}"
fi

# ─── 3. 项目目录 + 数据卷 ───
echo -e "${YELLOW}[3/6] 创建项目目录...${NC}"
sudo mkdir -p /opt/ai_os /data/ai_os/screenshots /data/ai_os/knowledge
sudo chown -R "$USER":"$USER" /opt/ai_os /data/ai_os

# ─── 4. 克隆 / 复制项目 ───
echo -e "${YELLOW}[4/6] 部署项目代码...${NC}"
# 如果你已经把代码推到 GitHub，替换下面的 URL
# git clone https://github.com/YOUR_USER/ai_os.git /opt/ai_os
echo -e "${RED}请手动把 AI_OS 项目文件上传到 /opt/ai_os/${NC}"
echo -e "${RED}（用 scp 或 git clone）${NC}"

# ─── 5. 配置 .env ───
echo -e "${YELLOW}[5/6] 配置环境变量...${NC}"
if [ ! -f /opt/ai_os/.env ]; then
    cp /opt/ai_os/.env.example /opt/ai_os/.env
    echo -e "${RED}请编辑 /opt/ai_os/.env 填入你的 API Key 和 Bot Token${NC}"
    echo -e "${RED}nano /opt/ai_os/.env${NC}"
else
    echo -e "${GREEN}.env already exists.${NC}"
fi

# ─── 6. 防火墙 ───
echo -e "${YELLOW}[6/6] 配置防火墙...${NC}"
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (Dashboard)
sudo ufw allow 443/tcp     # HTTPS
sudo ufw --force enable
sudo ufw status verbose

echo ""
echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}  部署完成！下一步：${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""
echo "1. 编辑环境变量:  nano /opt/ai_os/.env"
echo "2. 构建并启动:    cd /opt/ai_os && docker compose up -d --build"
echo "3. 查看日志:      docker compose logs -f"
echo "4. 检查状态:      docker compose ps"
echo ""
echo -e "${YELLOW}首次启动后，在 Telegram 给你的 Bot 发 /start 验证${NC}"
