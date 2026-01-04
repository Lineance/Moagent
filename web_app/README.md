# MoAgent Web Application

基于Flask的MoAgent智能爬虫系统Web界面。

## 功能特性

✅ **智能爬虫界面** - 支持多种爬取模式
✅ **RAG系统** - 向量数据库和语义搜索
✅ **多Agent协作** - LangGraph工作流可视化
✅ **实时监控** - 系统状态和性能统计
✅ **响应式设计** - 支持桌面和移动设备

## 快速开始

### 1. 安装依赖

```bash
cd web_app
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 在项目根目录创建 configs/.env 文件
cp ../configs/.env.example ../configs/.env

# 编辑 configs/.env 并添加你的API密钥
```

### 3. 启动应用

```bash
# 开发模式
python app.py

# 或使用Flask命令
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```

### 4. 访问应用

打开浏览器访问: http://localhost:5000

## 页面说明

### 首页 (`/`)
- 系统概览
- 快速统计
- 功能导航

### 爬虫 (`/crawl`)
- URL爬取表单
- 实时结果展示
- 存储统计

### RAG系统 (`/rag`)
- RAG功能介绍
- 相似模式搜索
- 模式列表查看
- 统计信息

### 多Agent (`/multi-agent`)
- Agent工作流可视化
- 多Agent任务提交
- 各Agent结果展示

### 监控 (`/dashboard`)
- 系统概览统计
- 功能状态检查
- 最近爬取项目
- 系统日志
- 性能指标

## API接口

### 爬虫相关

**POST `/api/crawl`**
- 执行爬取任务
- 请求: `{"url": "...", "mode": "auto", "depth": 1, "use_rag": false}`
- 响应: `{"success": true, "items": [...], "stats": {...}}`

**GET `/api/storage/stats`**
- 获取存储统计
- 响应: `{"success": true, "stats": {"total_items": 100, ...}}`

**GET `/api/storage/items?limit=50&offset=0`**
- 获取已存储项目
- 响应: `{"success": true, "items": [...]}`

### RAG相关

**GET `/api/rag/stats`**
- 获取RAG统计
- 响应: `{"success": true, "stats": {"total_patterns": 50, ...}}`

**GET `/api/rag/patterns?limit=20`**
- 获取最佳模式
- 响应: `{"success": true, "patterns": [...]}`

**POST `/api/rag/similar`**
- 查找相似模式
- 请求: `{"url": "...", "limit": 5}`
- 响应: `{"success": true, "similar_patterns": [...]}`

### 多Agent相关

**POST `/api/multi-agent/execute`**
- 执行多Agent工作流
- 请求: `{"url": "...", "keywords": [...], "depth": 1, "enable_optimization": true, "enable_rag": false}`
- 响应: `{"success": true, "result": {...}}`

### 系统相关

**GET `/api/system/info`**
- 获取系统信息
- 响应: `{"success": true, "info": {"version": "...", "features": {...}}}`

## 配置选项

### 环境变量

```bash
# Flask配置
SECRET_KEY=your-secret-key
FLASK_ENV=development
FLASK_DEBUG=1

# RAG配置
RAG_ENABLED=true  # 是否启用RAG（初始化较慢）

# MoAgent配置（在configs/.env中）
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### 应用配置

在 `app.py` 中可以修改：

```python
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
```

## 生产部署

### 使用Gunicorn

```bash
# 安装gunicorn
pip install gunicorn gevent

# 启动应用
gunicorn -w 4 -k gevent --bind 0.0.0.0:5000 "app:app"
```

### 使用Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .
COPY .. /app/moagent

RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-k", "gevent", "--bind", "0.0.0.0:5000", "app:app"]
```

### 使用Nginx反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /path/to/web_app/static;
    }
}
```

## 性能优化

### RAG系统

RAG系统初始化较慢（特别是ChromaDB）：
- 开发环境可以设置 `RAG_ENABLED=false`
- 生产环境建议预加载：在应用启动时初始化
- 使用单例模式避免重复初始化

### 缓存

对于频繁访问的数据，可以添加缓存：

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/api/storage/stats')
@cache.cached(timeout=60)  # 缓存60秒
def api_storage_stats():
    ...
```

## 故障排除

### RAG初始化超时

如果RAG初始化超时：
1. 检查ChromaDB是否正确安装
2. 设置 `RAG_ENABLED=false` 禁用RAG
3. 确保有足够的内存和磁盘空间

### 爬虫失败

如果爬虫任务失败：
1. 检查目标URL是否可访问
2. 查看浏览器控制台的错误信息
3. 检查configs/.env中的API密钥

### 样式显示问题

如果CSS样式未加载：
1. 清除浏览器缓存
2. 检查 `/static/css/style.css` 是否存在
3. 检查Flask static文件夹配置

## 开发指南

### 添加新页面

1. 在 `templates/` 创建HTML模板
2. 在 `static/js/` 创建对应的JavaScript
3. 在 `app.py` 添加路由

```python
@app.route('/new-page')
def new_page():
    return render_template('new_page.html')
```

### 添加新API

```python
@app.route('/api/new-endpoint', methods=['POST'])
def api_new_endpoint():
    data = request.get_json()
    # 处理逻辑
    return jsonify({'success': True, 'result': ...})
```

### 自定义样式

修改 `static/css/style.css` 中的CSS变量：

```css
:root {
    --primary-color: #2563eb;
    --secondary-color: #64748b;
    /* ... */
}
```

## 技术栈

- **后端**: Flask, Python 3.12+
- **前端**: HTML5, CSS3, JavaScript (ES6+)
- **数据存储**: SQLite, ChromaDB
- **AI框架**: LangGraph, LangChain
- **爬虫**: Playwright, requests-html

## 许可证

与主项目相同

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

- 项目主页: https://github.com/your-repo/moagent
- 文档: 见项目根目录的 `CLAUDE.md`
