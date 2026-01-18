# 修改 start-http.sh 实现自动环境准备

## 任务目标
修改 `start-http.sh` 脚本，使其能够自动检测并安装 `uv`，创建虚拟环境并安装项目依赖，最后启动服务。

## 修改步骤

1. **检查并安装 uv**：
   - 使用 `command -v uv` 检查 `uv` 是否已安装。
   - 如果未安装，使用官方推荐的安装脚本进行安装（`curl -LsSf https://astral.sh/uv/install.sh | sh`）。

2. **环境准备**：
   - 执行 `uv venv` 创建虚拟环境（如果已存在则跳过或同步）。
   - 执行 `uv pip install .` 安装当前项目的依赖。

3. **启动服务**：
   - 保持原有的启动命令 `uv run python start_http_server.py`。

## 预期效果
用户只需运行 `./start-http.sh`，脚本会自动完成所有准备工作并启动服务，无需手动执行繁琐的安装步骤。
