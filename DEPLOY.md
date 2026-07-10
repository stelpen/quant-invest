# 部署指南

## 服务器选型建议

| 配置 | 推荐 | 备注 |
|------|------|------|
| CPU | 2 核 | AKShare 数据拉取和网络请求密集 |
| 内存 | 2 GB | pandas 数据处理 |
| 硬盘 | 20 GB+ | 日线数据每天约 50 MB，全市场 5 年约 5 GB |
| 系统 | Alibaba Cloud Linux 3 / RHEL 8+ / CentOS 8+ | 与 install.sh 配套（yum 生态） |
| 带宽 | 1 Mbps+ | AKShare 数据源调用 |

推荐云厂商：阿里云 / 腾讯云 / 华为云（轻量应用服务器）。

> 本项目 install.sh 适配 Alibaba Cloud Linux 3.2104（基于 OpenAnolis，RHEL/CentOS 生态），使用 `yum`/`dnf` 安装系统依赖。若使用 Ubuntu/Debian，请将脚本中的 `yum` 替换为 `apt-get`。

## 一键部署

```bash
# 1. SSH 登录服务器
ssh root@your-server-ip

# 2. 安装 git（如果还没有）
yum install -y git

# 3. 克隆代码
git clone <your-repo-url> /tmp/quant-invest
cd /tmp/quant-invest

# 4. 执行安装
sudo bash deploy/install.sh
```

安装脚本会自动完成：
- 通过 yum/dnf 安装 Python 3.10+、Node.js 18、Nginx、Supervisor
- 创建 quant 用户
- 部署代码到 `/opt/quant-invest`
- 创建虚拟环境并安装依赖
- 构建前端
- 配置 systemd 服务
- 配置 Nginx（RHEL 系放置于 `/etc/nginx/conf.d/`）
- 开放 firewalld 的 http/https 服务

## HTTPS 配置

```bash
# 安装 certbot
yum install -y certbot python3-certbot-nginx

# 申请证书（自动修改 nginx 配置）
certbot --nginx -d your-domain.com

# 自动续期（默认已启用）
certbot renew --dry-run
```

## 防火墙

Alibaba Cloud Linux / RHEL 系默认使用 firewalld：

```bash
# firewalld 配置
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

> 注意：阿里云还需在 ECS 控制台的**安全组**中放行 80/443 端口，否则外网无法访问。

## 数据备份

```bash
# 添加 cron 任务，每天凌晨备份数据
crontab -e
# 添加：
0 2 * * * tar czf /backup/quant-$(date +\%Y\%m\%d).tar.gz /opt/quant-invest/data
```

## 监控

### 查看服务状态

```bash
systemctl status quant-invest
journalctl -u quant-invest -f  # 实时日志
```

### 健康检查

```bash
curl http://localhost:8000/health
```

## 故障排查

### 服务无法启动

```bash
# 查看详细日志
journalctl -u quant-invest -n 100

# 手动启动查看错误
cd /opt/quant-invest
sudo -u quant venv/bin/python run.py
```

### 前端无法访问

```bash
# 检查 Nginx 错误日志
tail -f /var/log/nginx/error.log

# 检查 Nginx 配置
nginx -t
```

### 数据同步失败

- 检查 AKShare 是否可访问（在服务器上 `curl https://baidu.com` 测试网络）
- 检查 SQLite 数据库权限（`ls -la /opt/quant-invest/data/`）
- 调整 `AKSHARE_RATE_LIMIT` 增加请求间隔

### SELinux 导致 Nginx 502

Alibaba Cloud Linux / RHEL 系默认启用 SELinux，可能阻止 Nginx 反代到后端：

```bash
# 允许 Nginx 发起网络连接
setsebool -P httpd_can_network_connect 1
# 若访问前端静态文件报 403，恢复上下文
restorecon -Rv /opt/quant-invest/frontend/dist
```

## 升级

```bash
# 1. 备份数据
tar czf data-backup.tar.gz /opt/quant-invest/data

# 2. 拉取新代码
cd /opt/quant-invest
sudo -u quant git pull  # 或重新部署

# 3. 更新依赖
sudo -u quant venv/bin/pip install -r requirements.txt

# 4. 重新构建前端
cd frontend
sudo -u quant npm install
sudo -u quant npm run build
cd ..

# 5. 重启服务
systemctl restart quant-invest
```