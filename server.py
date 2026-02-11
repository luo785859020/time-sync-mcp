#!/usr/bin/env python3
"""
Time Sync MCP Server
提供时间相关工具
"""

import json
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# MCP 消息处理
def handle_mcp_request(request):
    """处理 MCP 请求"""
    method = request.get("method", "")
    params = request.get("params", {})
    
    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "get_current_time",
                    "description": "获取当前时间",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "timezone": {
                                "type": "string",
                                "description": "时区 (例如: Asia/Shanghai, UTC)",
                                "default": "UTC"
                            },
                            "format": {
                                "type": "string",
                                "description": "时间格式 (默认: YYYY-MM-DD HH:mm:ss)",
                                "default": "YYYY-MM-DD HH:mm:ss"
                            }
                        }
                    }
                },
                {
                    "name": "get_unix_timestamp",
                    "description": "获取 Unix 时间戳（秒或毫秒）",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "milliseconds": {
                                "type": "boolean",
                                "description": "是否返回毫秒级时间戳",
                                "default": False
                            }
                        }
                    }
                },
                {
                    "name": "format_timestamp",
                    "description": "格式化时间戳为可读时间",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "timestamp": {
                                "type": "number",
                                "description": "Unix 时间戳"
                            },
                            "timezone": {
                                "type": "string",
                                "description": "时区",
                                "default": "UTC"
                            },
                            "format": {
                                "type": "string",
                                "description": "时间格式",
                                "default": "YYYY-MM-DD HH:mm:ss"
                            }
                        },
                        "required": ["timestamp"]
                    }
                },
                {
                    "name": "get_time_difference",
                    "description": "计算两个时间的差值",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "from": {
                                "type": "string",
                                "description": "开始时间"
                            },
                            "to": {
                                "type": "string",
                                "description": "结束时间"
                            }
                        },
                        "required": ["from", "to"]
                    }
                }
            ]
        }
    
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = {}
        
        if tool_name == "get_current_time":
            timezone = arguments.get("timezone", "UTC")
            fmt = arguments.get("format", "YYYY-MM-DD HH:mm:ss")
            now = datetime.now()
            
            # 简单格式化
            formatted = now.strftime("%Y-%m-%d %H:%M:%S")
            if timezone != "UTC":
                try:
                    import pytz
                    tz = pytz.timezone(timezone)
                    now_tz = now.astimezone(tz)
                    formatted = now_tz.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
            
            result = {
                "iso": now.isoformat(),
                "formatted": formatted,
                "timezone": timezone,
                "timestamp": int(now.timestamp())
            }
        
        elif tool_name == "get_unix_timestamp":
            ms = arguments.get("milliseconds", False)
            now = datetime.now()
            result = now.timestamp() * 1000 if ms else int(now.timestamp())
        
        elif tool_name == "format_timestamp":
            ts = arguments.get("timestamp")
            timezone = arguments.get("timezone", "UTC")
            fmt = arguments.get("format", "YYYY-MM-DD HH:mm:ss")
            
            # 转换时间戳
            if ts > 9999999999:
                dt = datetime.fromtimestamp(ts / 1000)
            else:
                dt = datetime.fromtimestamp(ts)
            
            formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
            if timezone != "UTC":
                try:
                    import pytz
                    tz = pytz.timezone(timezone)
                    dt = dt.replace(tzinfo=pytz.UTC).astimezone(tz)
                    formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
            
            result = {
                "original_timestamp": ts,
                "formatted": formatted,
                "timezone": timezone,
                "iso": dt.isoformat()
            }
        
        elif tool_name == "get_time_difference":
            from_time = arguments.get("from")
            to_time = arguments.get("to")
            
            dt1 = datetime.fromisoformat(from_time.replace('Z', '+00:00'))
            dt2 = datetime.fromisoformat(to_time.replace('Z', '+00:00'))
            
            diff_ms = abs((dt2 - dt1).total_seconds() * 1000)
            diff_sec = int(diff_ms / 1000)
            
            days = diff_sec // 86400
            hours = (diff_sec % 86400) // 3600
            minutes = (diff_sec % 3600) // 60
            seconds = diff_sec % 60
            
            result = {
                "from": from_time,
                "to": to_time,
                "difference_ms": int(diff_ms),
                "difference_seconds": diff_sec,
                "human_readable": f"{days}天 {hours}小时 {minutes}分钟 {seconds}秒"
            }
        
        else:
            return {"error": f"未知工具: {tool_name}"}
        
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
    
    return {}


class MCPHandler(BaseHTTPRequestHandler):
    """MCP HTTP 处理"""
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            request = json.loads(body)
            response = handle_mcp_request(request)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
    
    def log_message(self, format, *args):
        pass  # 禁用日志


def main():
    """启动服务器"""
    # 从环境变量读取端口（阿里云 FC 会设置）
    port = int(os.environ.get("PORT", 8080))
    
    server = HTTPServer(('0.0.0.0', port), MCPHandler)
    print(f"Time Sync MCP Server 启动在端口 {port}", file=sys.stderr)
    server.serve_forever()


if __name__ == "__main__":
    import os
    main()
