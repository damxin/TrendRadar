#!/bin/bash

echo "╔════════════════════════════════════════╗"
echo "║  TrendRadar MCP Server (HTTP 模式)    ║"
echo "╚════════════════════════════════════════╝"
echo ""

# 1. 检查 uv 命令是否安装
if ! command -v uv &> /dev/null; then
    echo "🔍 [信息] 未找到 uv 命令，正在安装..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # 尝试将 uv 路径加入当前 PATH
    export PATH="$HOME/.cargo/bin:$PATH"
    export PATH="$HOME/.local/bin:$PATH"
fi

# 2. 创建/同步虚拟环境
echo "🛠️ [环境] 正在准备虚拟环境..."
uv venv

source .venv/bin/activate

# 3. 安装项目依赖
echo "📦 [依赖] 正在安装当前项目..."
uv pip install .

# 此处添加：运行爬虫获取最新数据 (可选)
echo "🔍 [爬虫] 正在获取最新热点新闻..."
uv run trendradar

echo ""
echo "[模式] HTTP (适合远程访问)"
echo "[地址] http://0.0.0.0:3333/mcp"
echo "[提示] 按 Ctrl+C 停止服务"
echo ""

# 4. 启动服务
uv run python start_http_server.py
