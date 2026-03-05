# Skillbox

A curated collection of Claude Code skills (plugin format) for DevOps, API management, and daily workflows.

## Install

```bash
# Add as marketplace source
/plugin marketplace add owner/skillbox

# Install a specific skill
/plugin install newapi-manage@skillbox
```

Or manually copy a skill into your project:

```bash
# Copy skill folder to your project
cp -r skills/newapi-manage/ your-project/.claude/skills/newapi-manage/
```

## Available Skills

| Skill | Description | Usage |
|-------|-------------|-------|
| [newapi-manage](skills/newapi-manage/) | Manage new-api instances via HTTP API | `/skillbox:newapi-manage 查看用户` |
| [sinocode-mcp](skills/sinocode-mcp/) | Guide setup and usage of the `sinocode-mcp` MCP server (npx) for web search and image understanding | `/skillbox:sinocode-mcp 最新 Claude 模型 2026` |

## sinocode-mcp MCP Server (npm / npx)

`sinocode-mcp` skill depends on an MCP server distributed as a public npm package and started with `npx`:

```bash
npx sinocode-mcp --version
npx sinocode-mcp
```

Required environment variables:

- `SINOCODE_API_KEY`
- `SINOCODE_MCP_URL` (example: `http://192.168.113.44:8101`)

Optional environment variables:

- `SINOCODE_IMAGE_BUCKET_URL` (default: `https://minio.app.copilot.shenyang-bridge.com/image`)
- `SINOCODE_TIMEOUT` (default: `30` seconds)

### MCP Tools

The server exposes two tools:

#### web_search
- Input: `{ "query": "..." }`
- Flow: probe models (GET `$SINOCODE_MCP_URL/v1/models`), then POST to `$SINOCODE_MCP_URL/web_search`

#### understand_image
- Input: `{ "image_path": "...", "prompt": "..." }`
- If `image_path` is a local file, it uploads to the image bucket first
- Then POST to `$SINOCODE_MCP_URL/understand_image`

Each tool validates credentials via models probe first. If it fails, the tool call fails immediately.

## Plugin Structure

```
skillbox/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── skills/
│   ├── newapi-manage/
│   │   ├── SKILL.md             # Skill definition (YAML frontmatter + instructions)
│   │   └── scripts/             # Python helper scripts (stdlib only)
│   │       ├── newapi_client.py # Shared HTTP client
│   │       ├── channels.py      # Channel management
│   │       ├── users.py         # User management
│   │       ├── tokens.py        # Token management
│   │       ├── system.py        # System, logs & performance
│   │       └── notice.py        # Notice & announcements
│   └── sinocode-mcp/
│       └── SKILL.md             # Skill entry for MCP server setup and usage
├── packages/
│   └── sinocode-mcp/
│       ├── package.json         # npm package manifest (public publishable)
│       └── src/
│           └── server.js        # MCP stdio server implementation
├── LICENSE
└── README.md
```

## Adding a New Skill

1. Create a folder under `skills/`:

```
skills/my-skill/
├── SKILL.md          # Required — YAML frontmatter + instructions
├── reference.md      # Optional — extra context docs
└── scripts/          # Optional — helper scripts
```

2. `SKILL.md` format:

```markdown
---
name: my-skill
description: What this skill does
argument-hint: <how to call it>
user-invocable: true
allowed-tools: Bash, Read, AskUserQuestion
---

Your skill instructions here...
$ARGUMENTS will be replaced with user input.
```

3. Update `README.md` skill table
4. Submit a PR

## Naming Conventions

- Folder name = skill name = slash command name
- Use lowercase with hyphens: `project-action` (e.g. `newapi-manage`, `docker-deploy`)
- Be specific to avoid conflicts with built-in commands

## License

MIT
