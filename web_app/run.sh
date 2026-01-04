#!/bin/bash
# MoAgent Web Application 启动脚本

echo "========================================"
echo "MoAgent Web Application"
echo "========================================"
echo ""

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 检查是否在虚拟环境中
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✓ 虚拟环境: $VIRTUAL_ENV"
else
    echo "⚠ 警告: 未检测到虚拟环境"
    echo "建议先激活虚拟环境: source ../.venv/bin/activate"
    echo ""
fi

# 检查Flask是否安装
if python3 -c "import flask" 2>/dev/null; then
    echo "✓ Flask已安装"
else
    echo "✗ Flask未安装"
    echo "请运行: pip install -r requirements.txt"
    exit 1
fi

# 检查configs/.env
if [ -f "../configs/.env" ]; then
    echo "✓ 配置文件存在 (configs/.env)"
else
    echo "⚠ 警告: configs/.env不存在"
    echo "请复制示例: cp ../configs/.env.example ../configs/.env"
    echo "然后编辑添加你的API密钥"
    echo ""
fi

echo ""
echo "========================================"
echo "启动Web服务器..."
echo "========================================"
echo ""
echo "服务器地址: http://localhost:5000"
echo "按 Ctrl+C 停止服务器"
echo ""
echo "可用页面:"
echo "  - http://localhost:5000/          : 首页"
echo "  - http://localhost:5000/crawl     : 爬虫"
echo "  - http://localhost:5000/rag       : RAG系统"
echo "  - http://localhost:5000/multi-agent: 多Agent"
echo "  - http://localhost:5000/dashboard : 监控"
echo ""
echo "========================================"
echo ""

# 启动应用
python3 app.py
