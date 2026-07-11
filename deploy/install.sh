#!/bin/bash
# QuantInvest 一键安装脚本
# 适用于 Ubuntu 22.04+
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
apt-get update -qq
apt-get install -y python3.11 python3.11-venv python3.11-dev \
    nginx supervisor curl git

# 安装 Node.js 18+
if ! command -v node &>/dev/null || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt 18 ]; then
    echo ">>> 安装 Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y nodejs
fi

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
sudo -u $APP_USER python3.11 -m venv $APP_DIR/venv
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
    SECRET=$(python3.11 -c "import secrets; print(secrets.token_urlsafe(32))")
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
cp $APP_DIR/deploy/nginx.conf.example /etc/nginx/sites-available/quant-invest
ln -sf /etc/nginx/sites-available/quant-invest /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "=== 安装完成 ==="
echo "后端服务: systemctl status quant-invest"
echo "访问地址: http://$(hostname -I | awk '{print $1}')"
echo ""
echo "下一步:"
echo "  1. 编辑 /opt/quant-invest/.env 配置管理员密码和通知渠道"
echo "  2. 修改 /etc/nginx/sites-available/quant-invest 中的域名"
echo "  3. 配置 HTTPS: sudo certbot --nginx -d your-domain.com"
echo "  4. 重启服务: sudo systemctl restart quant-invest"
echo "  5. 初始化数据: sudo -u quant /opt/quant-invest/venv/bin/python -c \"..."
echo "     from core.data.fetcher import AKShareFetcher; ..."
echo "     \""
