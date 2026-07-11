# 常见问题排查

## 1. 前端构建时内存溢出（OOM Killed）

**症状**：`npm run build` 时 Node 进程被杀死，显示 `已杀死` 或 `Killed`

**原因**：服务器内存不足（<2GB），vite 打包 + vue-tsc 类型检查同时进行时内存峰值超限

**解决方案**：

### A. 使用快速构建模式（推荐）

```bash
cd frontend
npm run build:fast  # 跳过 vue-tsc，只用 vite 构建产物
```

### B. 增加 Node 内存上限

```bash
export NODE_OPTIONS="--max-old-space-size=2048"  # 2GB
npm run build
```

### C. 启用交换空间（swap）

```bash
# 临时启用 1GB swap
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 持久化（编辑 /etc/fstab）
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### D. 升级服务器配置
最低推荐 2GB 内存，或使用「按量付费+构建后销毁」的临时高配机器

---

## 2. Python 版本过低

**症状**：`ModuleNotFoundError: No module named 'tomllib'`（Python < 3.11）

**解决方案**：

```bash
# Alibaba Cloud Linux 3 / CentOS 8+
sudo yum install -y python3.11 python3.11-devel

# Ubuntu 22.04+
sudo apt install -y python3.11 python3.11-venv

# 确认版本
python3.11 --version
```

重新创建虚拟环境：

```bash
cd /opt/quant-invest
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 3. akshare 数据源失败

**症状**：`股票列表为空` 或 `K线加载失败`

**原因**：
- 网络限制（需要访问新浪财经、东方财富等公共接口）
- akshare 版本过旧（API 变动）

**解决方案**：

```bash
# 升级 akshare
pip install --upgrade akshare

# 检查网络（需能访问新浪财经）
curl -I https://finance.sina.com.cn

# 手动触发同步
curl -X POST http://localhost:8000/api/data/sync \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 4. Nginx 502 Bad Gateway

**症状**：前端可访问但 API 返回 502

**排查步骤**：

```bash
# 1. 检查后端服务状态
sudo systemctl status quant-invest

# 2. 查看后端日志
sudo journalctl -u quant-invest -n 50

# 3. 确认端口监听
sudo ss -tlnp | grep 8000

# 4. 测试后端直连
curl http://127.0.0.1:8000/health
```

**常见原因**：
- 后端启动失败（依赖缺失、Python 版本不符）
- SELinux 阻止 Nginx 连接 8000 端口

```bash
# 允许 Nginx 连接 8000
sudo setsebool -P httpd_can_network_connect 1
```

---

## 5. Systemd 服务无法启动

**症状**：`systemctl start quant-invest` 失败

**排查**：

```bash
# 查看详细错误
sudo journalctl -u quant-invest -xe

# 常见原因 1: .env 文件不存在
ls -la /opt/quant-invest/.env

# 常见原因 2: 虚拟环境路径错误
/opt/quant-invest/venv/bin/python --version

# 常见原因 3: 权限问题
sudo chown -R quant:quant /opt/quant-invest
```

---

## 6. HTTPS 证书自动续期失败

**症状**：证书过期，浏览器显示 `NET::ERR_CERT_DATE_INVALID`

**排查与修复**：

```bash
# 查看证书到期时间
sudo certbot certificates

# 手动续期
sudo certbot renew

# 测试自动续期（dry-run）
sudo certbot renew --dry-run

# 确认定时任务存在
sudo systemctl list-timers | grep certbot
```

---

## 7. 前端构建产物未更新

**症状**：代码已更新但浏览器显示旧版本

**解决方案**：

```bash
# 1. 清空浏览器缓存（Ctrl+Shift+Delete）

# 2. 重新构建前端
cd /opt/quant-invest/frontend
npm run build:fast

# 3. 重启 Nginx
sudo systemctl reload nginx

# 4. 检查 Nginx 缓存配置
grep -r "proxy_cache" /etc/nginx/sites-available/
```

---

## 8. 数据库锁定（SQLite）

**症状**：`database is locked`

**原因**：多个进程同时写入 SQLite

**解决方案**：

```bash
# 临时：重启服务
sudo systemctl restart quant-invest

# 长期：迁移到 PostgreSQL（生产环境推荐）
# 修改 config/settings.py 中 DB_URL 为 postgresql://...
```

---

## 9. 日志查看

```bash
# 后端日志（systemd journal）
sudo journalctl -u quant-invest -f

# Nginx 访问日志
sudo tail -f /var/log/nginx/access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/error.log

# 应用日志（如果启用了 loguru 文件输出）
tail -f /opt/quant-invest/logs/app.log
```

---

## 10. 性能优化

### A. 数据库迁移到 PostgreSQL

SQLite 在多并发下性能受限，生产环境推荐 PostgreSQL

```bash
# 安装 PostgreSQL
sudo yum install -y postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl enable postgresql --now

# 创建数据库与用户
sudo -u postgres psql
CREATE DATABASE quantinvest;
CREATE USER quantuser WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE quantinvest TO quantuser;
\q

# 修改 .env
DB_URL="postgresql://quantuser:your_password@localhost/quantinvest"

# 安装 Python 驱动
source venv/bin/activate
pip install psycopg2-binary

# 重启服务
sudo systemctl restart quant-invest
```

### B. 启用 Redis 缓存

```bash
# 安装 Redis
sudo yum install -y redis
sudo systemctl enable redis --now

# 修改代码使用 Redis 缓存热点数据（需自行实现）
```

### C. 前端 CDN 加速

```nginx
# nginx.conf 中启用 gzip 与缓存
gzip on;
gzip_types text/css application/javascript application/json;

location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

---

## 获取帮助

1. 检查 [README.md](README.md) 中的快速开始
2. 查看 [DEPLOY.md](DEPLOY.md) 中的部署指南
3. 提交 Issue 并附上：
   - 操作系统与版本（`cat /etc/os-release`）
   - Python 版本（`python --version`）
   - 错误日志（`journalctl` 输出）
   - 复现步骤
