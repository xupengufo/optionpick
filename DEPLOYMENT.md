# 部署指南

## 🚀 在线部署方案

### 方案一：Streamlit Community Cloud（推荐）

**优势：** 完全免费，自动部署，简单易用

**步骤：**

1. **准备GitHub仓库**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/options-tool.git
   git push -u origin main
   ```

2. **访问Streamlit Cloud**
   - 前往 [share.streamlit.io](https://share.streamlit.io)
   - 使用GitHub账号登录
   - 点击"New app"
   - 选择您的仓库和main.py文件
   - 点击"Deploy!"

3. **等待部署完成**
   - 通常需要2-5分钟
   - 完成后会分配一个URL如：https://yourapp.streamlit.app

**注意事项：**
- 免费版有资源限制
- 适合演示和轻量级使用
- 自动从GitHub同步更新

---

### 方案二：Heroku部署

**优势：** 稳定可靠，支持自定义域名

**步骤：**

1. **安装Heroku CLI**
   ```bash
   # Windows
   https://devcenter.heroku.com/articles/heroku-cli
   
   # 登录
   heroku login
   ```

2. **创建Heroku应用**
   ```bash
   heroku create your-options-tool
   ```

3. **设置环境变量**
   ```bash
   heroku config:set PYTHONPATH=/app
   ```

4. **部署应用**
   ```bash
   git add .
   git commit -m "Deploy to Heroku"
   git push heroku main
   ```

5. **打开应用**
   ```bash
   heroku open
   ```

**费用：** 基础套餐约$7/月

---

### 方案三：Docker + 云服务商

**支持的平台：**
- AWS ECS
- Google Cloud Run
- Azure Container Instances
- DigitalOcean App Platform

**Docker部署步骤：**

1. **构建镜像**
   ```bash
   docker build -t options-tool .
   ```

2. **本地测试**
   ```bash
   docker run -p 8501:8501 options-tool
   ```

3. **推送到容器注册表**
   ```bash
   # DockerHub示例
   docker tag options-tool yourusername/options-tool
   docker push yourusername/options-tool
   ```

4. **在云平台部署**
   - 使用各平台的容器服务
   - 配置环境变量和端口映射

---

### 方案四：VPS自建（高级用户）

**适合场景：** 需要完全控制，数据隐私要求高

**推荐服务商：**
- DigitalOcean ($5/月起)
- Vultr ($2.5/月起)
- Linode ($5/月起)

**部署步骤：**

1. **服务器设置**
   ```bash
   # 更新系统
   sudo apt update && sudo apt upgrade -y
   
   # 安装Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   
   # 安装Docker Compose
   sudo apt install docker-compose -y
   ```

2. **部署应用**
   ```bash
   # 克隆代码
   git clone https://github.com/yourusername/options-tool.git
   cd options-tool
   
   # 启动服务
   docker-compose up -d
   ```

3. **配置反向代理（Nginx）**
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       
       location / {
           proxy_pass http://localhost:8501;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```

---

## 🔧 部署前检查清单

### 必需文件
- ✅ `requirements.txt` - Python依赖
- ✅ `main.py` - 主应用文件
- ✅ `.streamlit/config.toml` - Streamlit配置
- ✅ `Dockerfile` - Docker配置（如需要）
- ✅ `Procfile` - Heroku配置（如需要）

### 代码优化
- ✅ 移除调试代码
- ✅ 添加错误处理
- ✅ 优化内存使用
- ✅ 添加缓存机制

### 安全考虑
- ✅ 不在代码中硬编码API密钥
- ✅ 使用环境变量
- ✅ 限制数据访问权限
- ✅ 添加输入验证

---

## 📊 性能优化建议

### 1. 数据缓存
```python
@st.cache_data(ttl=300)  # 5分钟缓存
def get_market_data():
    # 数据获取逻辑
    pass
```

### 2. 异步加载
```python
import asyncio
import aiohttp

# 异步获取多个股票数据
async def fetch_multiple_stocks(symbols):
    # 异步实现
    pass
```

### 3. 分页显示
```python
# 限制显示数量
max_results = st.selectbox("显示数量", [10, 20, 50, 100])
```

---

## 🔍 监控和维护

### 1. 应用健康检查
- 设置监控告警
- 定期检查数据源
- 监控响应时间

### 2. 日志管理
```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 3. 错误追踪
- 使用Sentry等服务
- 记录用户操作
- 分析错误模式

---

## 💰 成本对比

| 方案 | 月费用 | 优势 | 适用场景 |
|------|--------|------|----------|
| Streamlit Cloud | 免费 | 零成本，易部署 | 个人项目，演示 |
| Heroku | $7+ | 稳定，易扩展 | 小型商业应用 |
| DigitalOcean | $5+ | 完全控制 | 中型应用 |
| AWS/GCP | $10+ | 企业级 | 大型应用 |

---

## 🚀 快速开始

**最快部署方式（5分钟）：**

1. 将代码推送到GitHub
2. 访问 share.streamlit.io
3. 连接仓库并部署
4. 获得在线URL

**推荐部署流程：**
Streamlit Cloud (测试) → Heroku (生产) → 自建VPS (企业)