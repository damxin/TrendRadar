#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TrendRadar 本地 Web 服务器（带认证支持）

用法：
  uv run python start_http_server.py [端口] [目录]

示例：
  uv run python start_http_server.py              # 默认 8080 端口，output 目录
  uv run python start_http_server.py 8888         # 指定端口
  uv run python start_http_server.py 8888 ./dist  # 指定端口和目录
"""

import os
import sys
import base64
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial

try:
    import yaml
except ImportError:
    print("警告：未安装 PyYAML，认证功能将被禁用")
    yaml = None

# 默认配置
DEFAULT_PORT = 8080
DEFAULT_DIR = "output"
CONFIG_FILE = "config/config.yaml"


def load_auth_config():
    """从 config.yaml 加载认证配置"""
    if yaml is None:
        return {"enabled": False, "username": "", "password": ""}
    
    config_path = Path(CONFIG_FILE)
    if not config_path.exists():
        print(f"配置文件不存在: {CONFIG_FILE}")
        return {"enabled": False, "username": "", "password": ""}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        app_config = config.get("app", {})
        auth_config = app_config.get("auth", {})
        return {
            "enabled": auth_config.get("enabled", False),
            "username": auth_config.get("username", "admin"),
            "password": auth_config.get("password", ""),
        }
    except Exception as e:
        print(f"读取认证配置失败: {e}")
        return {"enabled": False, "username": "", "password": ""}


class AuthHandler(SimpleHTTPRequestHandler):
    """带 HTTP Basic Auth 的请求处理器"""
    
    def __init__(self, *args, auth_config=None, **kwargs):
        self.auth_config = auth_config or {"enabled": False}
        super().__init__(*args, **kwargs)
    
    def do_HEAD(self):
        if self._check_auth():
            super().do_HEAD()
    
    def do_GET(self):
        if self._check_auth():
            # 特殊处理根目录访问，自动寻找最新的报告
            if self.path == '/' or self.path == '':
                index_path = Path(self.translate_path(self.path)) / 'index.html'
                if not index_path.exists():
                    latest_report = self._find_latest_report()
                    if latest_report:
                        # 内部重定向（不改变 URL，直接返回内容）
                        self.path = latest_report
                    else:
                        # 如果完全没有 HTML 报告，返回一个友好的提示页面，而不是目录列表
                        self._send_no_report_response()
                        return
            
            # 禁止直接列出目录（防止安全风险和用户困惑）
            full_path = Path(self.translate_path(self.path))
            if full_path.is_dir() and not (full_path / 'index.html').exists():
                self._send_no_report_response()
                return
            
            super().do_GET()
    
    def _send_no_report_response(self):
        """发送“暂无报告”的友好提示页面"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset='utf-8'>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>TrendRadar - 暂无报告</title>
            <style>
                body { font-family: -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #f9fafb; color: #374151; }
                .card { background: white; padding: 2rem; border-radius: 1rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }
                h1 { color: #4f46e5; margin-bottom: 1rem; }
                p { line-height: 1.5; color: #6b7280; }
                .btn { display: inline-block; margin-top: 1.5rem; padding: 0.5rem 1rem; background: #4f46e5; color: white; text-decoration: none; border-radius: 0.5rem; transition: background 0.2s; }
                .btn:hover { background: #4338ca; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>👋 欢迎使用 TrendRadar</h1>
                <p>目前还没有生成任何新闻分析报告。</p>
                <p>请确保爬虫程序已成功运行并生成了 HTML 文件。</p>
                <p>系统会自动监测并在报告生成后显示在这里。</p>
                <a href="javascript:location.reload()" class="btn">刷新页面</a>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))
    
    def _find_latest_report(self):
        """寻找最新的 HTML 报告文件路径（相对于服务根目录）"""
        try:
            root_dir = Path(self.translate_path('/')).resolve()
            
            # 优先级 1: html/latest/ 目录下的 html
            latest_dir = root_dir / 'html' / 'latest'
            if latest_dir.exists():
                html_files = list(latest_dir.glob('*.html'))
                if html_files:
                    return str(html_files[0].relative_to(root_dir)).replace('\\', '/')
            
            # 优先级 2: 递归搜索所有 html 文件，寻找最新的
            all_htmls = list(root_dir.rglob('*.html'))
            # 排除 index.html 自身（如果存在却由于某种原因没被处理）
            all_htmls = [f for f in all_htmls if f.name != 'index.html']
            
            if all_htmls:
                latest_file = max(all_htmls, key=lambda f: f.stat().st_mtime)
                return str(latest_file.relative_to(root_dir)).replace('\\', '/')
            
        except Exception as e:
            print(f"搜索最新报告失败: {e}")
        
        return None
    
    def _check_auth(self):
        """检查认证"""
        if not self.auth_config.get("enabled", False):
            return True
        
        auth_header = self.headers.get("Authorization")
        if auth_header is None:
            self._send_auth_request()
            return False
        
        try:
            # 解析 Basic Auth
            auth_type, auth_string = auth_header.split(" ", 1)
            if auth_type.lower() != "basic":
                self._send_auth_request()
                return False
            
            decoded = base64.b64decode(auth_string).decode("utf-8")
            username, password = decoded.split(":", 1)
            
            expected_username = self.auth_config.get("username", "")
            expected_password = self.auth_config.get("password", "")
            
            if username == expected_username and password == expected_password:
                return True
            else:
                self._send_auth_request()
                return False
        except Exception:
            self._send_auth_request()
            return False
    
    def _send_auth_request(self):
        """发送 401 认证请求"""
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="TrendRadar"')
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<!DOCTYPE html><html><head><meta charset='utf-8'><title>需要认证</title></head><body><h1>401 需要认证</h1><p>请输入用户名和密码访问此页面。</p></body></html>".encode("utf-8"))


def main():
    # 解析命令行参数
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    directory = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DIR
    
    # 检查目录
    serve_dir = Path(directory).resolve()
    if not serve_dir.exists():
        print(f"错误：目录不存在: {serve_dir}")
        sys.exit(1)
    
    # 加载认证配置
    auth_config = load_auth_config()
    
    print("=" * 50)
    print("  TrendRadar Web 服务器")
    print("=" * 50)
    print(f"  端口: {port}")
    print(f"  目录: {serve_dir}")
    if auth_config.get("enabled"):
        print(f"  认证: 已启用 (用户名: {auth_config.get('username')})")
    else:
        print("  认证: 未启用（公开访问）")
    print("=" * 50)
    print(f"  访问地址: http://0.0.0.0:{port}")
    print(f"  按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    # 切换到服务目录
    os.chdir(serve_dir)
    
    # 创建服务器
    handler = partial(AuthHandler, auth_config=auth_config, directory=str(serve_dir))
    server = HTTPServer(("0.0.0.0", port), handler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")


if __name__ == "__main__":
    main()
