#!/usr/bin/env node
/**
 * Time Sync MCP Server - 纯 Node.js 实现，无需依赖
 */

const TOOLS = [
  {
    name: "get_current_time",
    description: "获取当前时间",
    inputSchema: {
      type: "object",
      properties: {
        timezone: {
          type: "string",
          description: "时区 (例如: Asia/Shanghai, UTC)",
          default: "UTC"
        }
      }
    }
  },
  {
    name: "get_unix_timestamp",
    description: "获取 Unix 时间戳（秒或毫秒）",
    inputSchema: {
      type: "object",
      properties: {
        milliseconds: {
          type: "boolean",
          description: "是否返回毫秒级时间戳",
          default: false
        }
      }
    }
  },
  {
    name: "format_timestamp",
    description: "格式化时间戳为可读时间",
    inputSchema: {
      type: "object",
      properties: {
        timestamp: { type: "number", description: "Unix 时间戳" },
        timezone: { type: "string", description: "时区", default: "UTC" }
      },
      required: ["timestamp"]
    }
  },
  {
    name: "get_time_difference",
    description: "计算两个时间的差值",
    inputSchema: {
      type: "object",
      properties: {
        from: { type: "string", description: "开始时间 (ISO 格式)" },
        to: { type: "string", description: "结束时间 (ISO 格式)" }
      },
      required: ["from", "to"]
    }
  }
];

function formatDateInTimezone(date, timezone) {
  try {
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: timezone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
    
    const parts = formatter.formatToParts(date);
    const getPart = (type) => parts.find(p => p.type === type)?.value;
    
    return `${getPart('year')}-${getPart('month')}-${getPart('day')} ${getPart('hour')}:${getPart('minute')}:${getPart('second')}`;
  } catch (e) {
    return date.toISOString();
  }
}

function handleRequest(request) {
  const { method, params, id } = request || {};
  const requestId = id || 1;
  
  // 初始化
  if (method === 'initialize') {
    return {
      jsonrpc: '2.0',
      id: requestId,
      result: {
        protocolVersion: '2024-11-05',
        capabilities: { tools: {} },
        serverInfo: { name: 'time-sync-mcp', version: '1.0.0' }
      }
    };
  }
  
  // 工具列表
  if (method === 'tools/list') {
    return {
      jsonrpc: '2.0',
      id: requestId,
      result: { tools: TOOLS }
    };
  }
  
  // 调用工具
  if (method === 'tools/call') {
    const { name, arguments: args } = params || {};
    return callTool(name, args, requestId);
  }
  
  return {
    jsonrpc: '2.0',
    id: requestId,
    error: { code: -32600, message: 'Invalid request' }
  };
}

function callTool(name, args, requestId) {
  try {
    const now = new Date();
    
    if (name === 'get_current_time') {
      const timezone = args?.timezone || 'UTC';
      const formatted = formatDateInTimezone(now, timezone);
      
      return {
        jsonrpc: '2.0',
        id: requestId,
        result: {
          content: [{
            type: 'text',
            text: JSON.stringify({
              iso: now.toISOString(),
              formatted,
              timezone,
              timestamp: Math.floor(now.getTime() / 1000)
            }, null, 2)
          }]
        }
      };
    }
    
    if (name === 'get_unix_timestamp') {
      const ms = args?.milliseconds || false;
      return {
        jsonrpc: '2.0',
        id: requestId,
        result: {
          content: [{ type: 'text', text: JSON.stringify({ timestamp: ms ? now.getTime() : Math.floor(now.getTime() / 1000) }) }]
        }
      };
    }
    
    if (name === 'format_timestamp') {
      const ts = args?.timestamp;
      const timezone = args?.timezone || 'UTC';
      const date = ts > 9999999999 ? new Date(ts) : new Date(ts * 1000);
      const formatted = formatDateInTimezone(date, timezone);
      
      return {
        jsonrpc: '2.0',
        id: requestId,
        result: {
          content: [{
            type: 'text',
            text: JSON.stringify({
              original_timestamp: ts,
              formatted,
              timezone,
              iso: date.toISOString()
            }, null, 2)
          }]
        }
      };
    }
    
    if (name === 'get_time_difference') {
      const from = new Date(args?.from);
      const to = new Date(args?.to);
      const diffSec = Math.abs(Math.floor((to - from) / 1000));
      const days = Math.floor(diffSec / 86400);
      const hours = Math.floor((diffSec % 86400) / 3600);
      const minutes = Math.floor((diffSec % 3600) / 60);
      const seconds = diffSec % 60;
      
      return {
        jsonrpc: '2.0',
        id: requestId,
        result: {
          content: [{
            type: 'text',
            text: JSON.stringify({
              from: args?.from,
              to: args?.to,
              difference_seconds: diffSec,
              human_readable: `${days}天 ${hours}小时 ${minutes}分钟 ${seconds}秒`
            }, null, 2)
          }]
        }
      };
    }
    
    return {
      jsonrpc: '2.0',
      id: requestId,
      error: { code: -32601, message: `Unknown tool: ${name}` }
    };
    
  } catch (e) {
    return {
      jsonrpc: '2.0',
      id: requestId,
      error: { code: -32603, message: e.message }
    };
  }
}

// 主循环
process.stdin.on('data', (data) => {
  const lines = data.toString().split('\n');
  for (const line of lines) {
    if (line.trim()) {
      try {
        const request = JSON.parse(line.trim());
        const response = handleRequest(request);
        console.log(JSON.stringify(response));
      } catch (e) {
        // 忽略解析错误
      }
    }
  }
});
