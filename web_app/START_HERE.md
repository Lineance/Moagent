# 🚀 Web应用快速启动

## ✅ RAG已禁用 - 应用可立即启动

### 启动步骤

```bash
# 1. 确保在项目根目录
cd /mnt/d/Code/MoAgent

# 2. 激活虚拟环境
source .venv/bin/activate

# 3. 安装Flask（如果还没安装）
pip install Flask flask-cors

# 4. 启动Web应用
cd web_app
python app.py
```

应用现在会**立即启动**（RAG已禁用），不会出现超时问题！

### 访问应用

打开浏览器: **http://localhost:5000**

### 功能说明

#### ✅ 可用功能（无需RAG）

1. **智能爬虫** (`/crawl`)
   - 输入URL进行爬取
   - 选择爬取模式
   - 查看实时结果

2. **多Agent工作流** (`/multi-agent`)
   - 启动多Agent协作
   - 查看各Agent结果
   - 监控工作流进度

3. **监控面板** (`/dashboard`)
   - 查看系统统计
   - 检查功能状态
   - 查看最近爬取

#### ⚠️ 受限功能（需要RAG）

**RAG系统** (`/rag`) - 显示"N/A"：
- 要启用RAG，需要：
  1. 安装ChromaDB: `pip install chromadb`
  2. 设置环境变量: `export RAG_ENABLED=true`
  3. 重启应用（首次需要30-60秒初始化）

---

## 🔧 配置说明

### 启用RAG（可选）

```bash
# 安装ChromaDB
pip install chromadb sentence-transformers

# 启用RAG并启动
export RAG_ENABLED=true
python web_app/app.py
```

**注意**: RAG首次初始化需要30-60秒

### 修改端口

编辑 `web_app/app.py`:
```python
app.run(
    host='0.0.0.0',
    port=8080,  # 改为8080或其他端口
    debug=True
)
```

---

## 📊 快速测试

### 测试1: 爬虫功能

1. 访问 http://localhost:5000/crawl
2. 输入URL: `https://example.com`
3. 点击"开始爬取"
4. 查看结果

### 测试2: 多Agent

1. 访问 http://localhost:5000/multi-agent
2. 输入URL和关键词
3. 点击"启动工作流"
4. 等待完成并查看结果

### 测试3: 监控面板

1. 访问 http://localhost:5000/dashboard
2. 点击"刷新统计"
3. 查看系统状态

---

## ❓ 常见问题

### Q1: 启动时显示"ModuleNotFoundError"

**A**: 确保设置了PYTHONPATH:
```bash
export PYTHONPATH=/mnt/d/Code/MoAgent:$PYTHONPATH
```

### Q2: 爬虫失败，提示API密钥错误

**A**: 配置API密钥:
```bash
cp configs/.env.example configs/.env
# 编辑configs/.env添加OPENAI_API_KEY或ANTHROPIC_API_KEY
```

### Q3: 页面显示"N/A"或"加载失败"

**A**: 这是正常的，RAG功能已禁用。核心功能（爬虫、多Agent）正常工作。

---

## 🎉 系统状态

### 当前配置

- ✅ Flask Web服务器: 运行中
- ✅ 爬虫系统: 可用
- ✅ 多Agent系统: 可用
- ✅ 存储系统: 可用
- ⚠️ RAG系统: 已禁用（可选启用）

### 功能完整度

| 功能 | 状态 | 说明 |
|------|------|------|
| 爬虫 | ✅ 100% | 完全可用 |
| 多Agent | ✅ 100% | 完全可用 |
| 监控面板 | ✅ 100% | 完全可用 |
| RAG系统 | ⚠️ 0% | 需要手动启用 |

---

**开始使用吧！** 🚀

更多信息请查看:
- `WEB_APP_QUICKSTART.md` - 完整快速启动指南
- `WEB_APP_COMPLETE.md` - 技术文档
