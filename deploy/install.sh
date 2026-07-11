#!/bin/bash
# QuantInvest 一键安装脚本
# 适用于 Alibaba Cloud Linux 3 / CentOS 8+ / RHEL 8+ (基于 OpenAnolis)
# 使用方式: sudo bash deploy/install.sh
set -e

APP_DIR="/opt/quant-invest"
APP_USER="quant"

echo "=== QuantInvest 安装脚本 ==="

# 1. 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 2. 安装系统依赖
echo ">>> 安装系统依赖..."
yum install -y epel-release 2>/dev/null || true
yum install -y python3 python3-devel python3-pip \
    nginx supervisor curl git gcc make

# 安装 Node.js 18+
if ! command -v node &>/dev/null || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt 18 ]; then
    echo ">>> 安装 Node.js 18..."
    curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
    yum install -y nodejs
fi

# 确认 Python 版本 >= 3.10
PYTHON_BIN="python3"
PY_VER=$($PYTHON_BIN --version 2>&1 | awk '{print $2}' | cut -d. -f1-2)
PY_MAJOR=$(echo $PY_VER | cut -d. -f1)
PY_MINOR=$(echo $PY_VER | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
    echo ">>> 系统 Python 版本 ($PY_VER) 过低，安装 Python 3.11..."
    yum install -y python3.11 python3.11-devel 2>/dev/null || {
        # 如果 yum 源没有 3.11，从源码编译
        echo ">>> yum 源无 python3.11，尝试从 AppStream 安装..."
        dnf module install -y python3.11 2>/dev/null || {
            echo "错误: 无法安装 Python 3.10+, 请手动安装后重试"
            exit 1
        }
    }
    PYTHON_BIN="python3.11"
fi
echo ">>> 使用 Python: $($PYTHON_BIN --version)"

# 3. 创建应用用户
if ! id "$APP_USER" &>/dev/null; then
    echo ">>> 创建用户 $APP_USER..."
    useradd -r -m -d /home/$APP_USER -s /bin/bash $APP_USER
fi

# 4. 部署代码
echo ">>> 部署代码到 $APP_DIR..."
mkdir -p $APP_DIR
\cp -rf . $APP_DIR/
chown -R $APP_USER:$APP_USER $APP_DIR

# 5. Python 虚拟环境
echo ">>> 创建 Python 虚拟环境..."
sudo -u $APP_USER $PYTHON_BIN -m venv $APP_DIR/venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt

# 6. 构建前端
echo ">>> 构建前端..."
cd $APP_DIR/frontend
sudo -u $APP_USER npm install
sudo -u $APP_USER npm run build
cd $APP_DIR

# 7. 配置文件
if [ ! -f $APP_DIR/.env ]; then
    echo ">>> 创建 .env 配置..."
    cp $APP_DIR/.env.example $APP_DIR/.env
    # 生成随机 SECRET_KEY
    SECRET=$($PYTHON_BIN -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i "s/change-me-in-production/$SECRET/" $APP_DIR/.env
    echo "⚠️  请编辑 $APP_DIR/.env 修改管理员密码和其他配置"
fi

# 8. 初始化数据目录
echo ">>> 初始化数据..."
sudo -u $APP_USER mkdir -p $APP_DIR/data/parquet/daily

# 9. systemd 服务
echo ">>> 配置 systemd 服务..."
cp $APP_DIR/deploy/quant-invest.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable quant-invest
systemctl start quant-invest

# 10. Nginx 配置
echo ">>> 配置 Nginx..."
# RHEL/CentOS 系列使用 /etc/nginx/conf.d/ 而非 sites-available
cp $APP_DIR/deploy/nginx.conf.example /etc/nginx/conf.d/quant-invest.conf
# 注释掉默认 server 块（如果存在）
if [ -f /etc/nginx/nginx.conf ]; then
    sed -i '/server {/,/}/s/^/#/' /etc/nginx/conf.d/default.conf 2>/dev/null || true
fi
nginx -t && systemctl reload nginx

# 11. 防火墙放行
echo ">>> 配置防火墙..."
if command -v firewall-cmd &>/dev/null; then
    firewall-cmd --permanent --add-service=http 2>/dev/null || true
    firewall-cmd --permanent --add-service=https 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
fi

echo ""
echo "=== 安装完成 ==="
echo "后端服务: systemctl status quant-invest"
echo "访问地址: http://$(hostname -I | awk '{print $1}')"
echo ""
echo "下一步:"
echo "  1. 编辑 /opt/quant-invest/.env 配置管理员密码和通知渠道"
echo "  2. 修改 /etc/nginx/conf.d/quant-invest.conf 中的域名"
echo "  3. 配置 HTTPS: yum install certbot python3-certbot-nginx && certbot --nginx -d your-domain.com"
echo "  4. 重启服务: sudo systemctl restart quant-invest"
echo "  5. 初始化数据: sudo -u quant /opt/quant-invest/venv/bin/python -c \\"
echo "     \"from core.data.fetcher import AKShareFetcher; from core.data.storage import DataStorage; from core.data.updater import DataUpdater; s=DataStorage(); s.init_db(); DataUpdater(AKShareFetcher(), s).init_data()\""
