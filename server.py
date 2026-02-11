#!/usr/bin/env python3
"""
Time Sync MCP Server - 标准 MCP 协议实现
"""

import json
import sys
from datetime import datetime
import pytz

# MCP 工具定义
TOOLS = [
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
                    "description": "开始时间 (ISO 格式)"
                },
                "to": {
                    "type": "string",
                    "description": "结束时间 (ISO 格式)"
                }
            },
            "required": ["from", "to"]
        }
    }
]

def handle_request(request):
    """处理 MCP 请求"""
    method = request.get("method", "")
    params = request.get("params", {})
    request_id = request.get("id", 1)
    
    # 初始化
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "time-sync-mcp",
                    "version": "1.0.0"
                }
            }
        }
    
    # 工具列表
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": TOOLS
            }
        }
    
    # 调用工具
    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        return call_tool(tool_name, arguments, request_id)
    
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32600, "message": "Invalid request"}
    }

def call_tool(name, args, request_id):
    """调用工具"""
    try:
        if name == "get_current_time":
            timezone = args.get("timezone", "UTC")
            now = datetime.now(pytz.timezone(timezone)) if timezone != "UTC" else datetime.now()
            formatted = now.strftime("%Y-%m-%d %H:%M:%S")
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "iso": now.isoformat(),
                            "formatted": formatted,
                            "timezone": timezone,
                            "timestamp": int(now.timestamp())
                        }, ensure_ascii=False, indent=2)
                    }]
                }
            }
        
        elif name == "get_unix_timestamp":
            ms = args.get("milliseconds", False)
            now = datetime.now()
            timestamp = now.timestamp() * 1000 if ms else int(now.timestamp())
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({"timestamp": timestamp}, ensure_ascii=False)
                    }]
                }
            }
        
        elif name == "format_timestamp":
            ts = args.get("timestamp")
            timezone = args.get("timezone", "UTC")
            
            if ts > 9999999999:
                dt = datetime.fromtimestamp(ts / 1000, pytz.timezone(timezone))
            else:
                dt = datetime.fromtimestamp(ts, pytz.timezone(timezone))
            
            formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "original_timestamp": ts,
                            "formatted": formatted,
                            "timezone": timezone,
                            "iso": dt.isoformat()
                        }, ensure_ascii=False, indent=2)
                    }]
                }
            }
        
        elif name == "get_time_difference":
            from_time = args.get("from")
            to_time = args.get("to")
            
            dt1 = datetime.fromisoformat(from_time.replace('Z', '+00:00'))
            dt2 = datetime.fromisoformat(to_time.replace('Z', '+00:00'))
            
            diff_sec = abs(int((dt2 - dt1).total_seconds()))
            days = diff_sec // 86400
            hours = (diff_sec % 86400) // 3600
            minutes = (diff_sec % 3600) // 60
            seconds = diff_sec % 60
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "from": from_time,
                            "to": to_time,
                            "difference_seconds": diff_sec,
                            "human_readable": f"{days}天 {hours}小时 {minutes}分钟 {seconds}秒"
                        }, ensure_ascii=False, indent=2)
                    }]
                }
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unknown tool: {name}"}
            }
    
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": str(e)}
        }


class MCPHandler:
    """MCP 协议处理器 (stdio 模式)"""
    
    def __init__(self):
        self.buffer = ""
    
    def handle_line(self, line):
        """处理一行输入"""
        try:
            request = json.loads(line.strip())
            response = handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(json.dumps({
                "jsonrpc": "2.0",
                "id": 0,
                "error": {"code": -32603, "message": str(e)}
            }), flush=True)
    
    def run(self):
        """运行主循环"""
        for line in sys.stdin:
            self.handle_line(line)


if __name__ == "__main__":
    handler = MCPHandler()
    handler.run()
