---
name: sinocode-mcp
description: 通过 MCP Server（npx 启动）提供联网搜索和图片理解能力，包含 models 探活 + web_search/understand_image 双地址校验。
argument-hint: <你想搜索的问题 或 图片路径>
user-invocable: true
allowed-tools: Bash, Read, AskUserQuestion
---

# sinocode-mcp

你是 `sinocode-mcp` 技能的使用助手。目标是指导用户配置并使用一个通过 `npx` 启动的 MCP Server，提供 `web_search` 和 `understand_image` 两个工具。

## 配置环境变量

在启动 MCP server 前，先确保这些环境变量可用：

- `SINOCODE_API_KEY`（必填）
- `SINOCODE_MCP_URL`（必填，例如 `http://192.168.113.44:8101`）
- `SINOCODE_IMAGE_BUCKET_URL`（可选，默认 `https://minio.app.copilot.shenyang-bridge.com/image`）
- `SINOCODE_TIMEOUT`（可选，默认 `30` 秒）

快速检查：

```bash
echo "API_KEY=${SINOCODE_API_KEY:+SET} MCP_URL=$SINOCODE_MCP_URL IMAGE_BUCKET=${SINOCODE_IMAGE_BUCKET_URL:-https://minio.app.copilot.shenyang-bridge.com/image} TIMEOUT=${SINOCODE_TIMEOUT:-30}"
```

若未配置：

```bash
export SINOCODE_API_KEY="your-api-key"
export SINOCODE_MCP_URL="http://192.168.113.44:8101"
export SINOCODE_IMAGE_BUCKET_URL="https://minio.app.copilot.shenyang-bridge.com/image"
export SINOCODE_TIMEOUT="30"
```

## 启动方式（npx）

MCP server 通过 npm 包直接启动：

```bash
npx sinocode-mcp
```

可先验证包可执行：

```bash
npx sinocode-mcp --version
```

## MCP 工具与调用链路

该 server 暴露两个工具：

### web_search
- 输入：`{ "query": "..." }`
- 调用链路：
  1. `GET $SINOCODE_MCP_URL/v1/models`（Header: `Authorization: Bearer $SINOCODE_API_KEY`）
  2. `POST $SINOCODE_MCP_URL/web_search`（Body: `{ "query": "..." }`）

### understand_image
- 输入：`{ "image_path": "...", "prompt": "..." }`
- `image_path`: 本地文件路径或图片 URL
- `prompt`: 可选，默认 "请描述这张图片"
- 调用链路：
  1. 若为本地文件，先上传到图床获取公开 URL
  2. `POST $SINOCODE_MCP_URL/understand_image`（Header: `Authorization: Bearer $SINOCODE_API_KEY`，Body: `{ "image_source": "...", "prompt": "..." }`）

每次调用任一工具时，都会先执行 models 探活（第 1 步）进行身份校验。若第 1 步失败，必须直接报错并停止。

## 验证建议

1. 在 Claude 中注册该 MCP server 后，确认 `tools/list` 可见 `web_search` 和 `understand_image`。
2. 使用正确 `SINOCODE_API_KEY` 调用一次搜索，确认成功返回结构化内容。
3. 故意使用错误 key，确认在 models 探活阶段即失败（例如 401/403），且不会触发后续 API。

## 当前用户请求

$ARGUMENTS
