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

# 3. 安装项目依赖
echo "📦 [依赖] 正在安装当前项目..."
uv pip install .

# 此处添加：运行爬虫获取最新数据 (可选)
echo "🔍 [爬虫] 正在获取最新热点新闻..."
uv run trendradar

# 从 config.yaml 读取认证信息并生成 Token
AUTH_ENABLED=$(grep -A3 "^  auth:" config/config.yaml | grep "enabled:" | awk '{print $2}' | tr -d '\r')
AUTH_USERNAME=$(grep -A3 "^  auth:" config/config.yaml | grep "username:" | awk '{print $2}' | tr -d '"' | tr -d '\r')
AUTH_PASSWORD=$(grep -A3 "^  auth:" config/config.yaml | grep "password:" | awk '{print $2}' | tr -d '"' | tr -d '\r')

# 生成 Bearer Token (base64 编码的 username:password)
if [ "$AUTH_ENABLED" = "true" ]; then
    BEARER_TOKEN=$(echo -n "${AUTH_USERNAME}:${AUTH_PASSWORD}" | base64)
else
    BEARER_TOKEN=""
fi

# 获取服务器 IP（优先获取非 localhost 的 IP）
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$SERVER_IP" ]; then
    SERVER_IP="YOUR_SERVER_IP"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              TrendRadar 服务启动中                       ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  [MCP 服务]  http://0.0.0.0:13333/mcp (供 AI 客户端调用)  ║"
echo "║  [网页服务]  http://0.0.0.0:18081     (用于浏览器访问)    ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  按 Ctrl+C 停止所有服务                                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 打印认证信息和 Cherry Studio 配置
if [ "$AUTH_ENABLED" = "true" ]; then
    echo "🔐 [认证信息]"
    echo "   用户名: $AUTH_USERNAME"
    echo "   Bearer Token: $BEARER_TOKEN"
    echo ""
fi

echo "📋 [Cherry Studio MCP 配置] - 可直接复制粘贴:"
echo "────────────────────────────────────────────────"
if [ "$AUTH_ENABLED" = "true" ]; then
    cat << EOF
{
  "TrendRadar": {
    "name": "TrendRadar",
    "type": "streamable-http",
    "url": "http://${SERVER_IP}:13333/mcp",
    "headers": {
      "Authorization": "Bearer ${BEARER_TOKEN}"
    },
    "isActive": true
  }
}
EOF
else
    cat << EOF
{
  "TrendRadar": {
    "name": "TrendRadar",
    "type": "streamable-http",
    "url": "http://${SERVER_IP}:13333/mcp",
    "isActive": true
  }
}
EOF
fi
echo "────────────────────────────────────────────────"
echo ""


# 定义清理函数，在脚本退出时终止后台进程
cleanup() {
    echo ""
    echo "🛑 正在停止所有服务..."
    if [ ! -z "$MCP_PID" ]; then
        kill $MCP_PID 2>/dev/null
        echo "   MCP 服务已停止 (PID: $MCP_PID)"
    fi
    echo "   所有服务已停止"
    exit 0
}

# 捕获 Ctrl+C 信号
trap cleanup SIGINT SIGTERM

# 4. 后台启动 MCP 服务 (端口 3333)
echo "🚀 [MCP] 正在启动 MCP 服务..."
uv run python -m mcp_server.server --transport http --host 0.0.0.0 --port 13333 &
MCP_PID=$!
echo "   MCP 服务已启动 (PID: $MCP_PID)"

# 等待 MCP 服务启动
sleep 2

# 5. 前台启动 Web 服务器 (端口 8080)
echo "🌐 [Web] 正在启动网页服务..."
uv run python start_http_server.py 18081
echo "🌐 [Web] 网页服务已启动"
