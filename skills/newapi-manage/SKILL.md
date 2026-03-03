---
name: newapi-manage
description: Manage new-api instances via HTTP API — users, channels, tokens, logs, settings, and more.
argument-hint: <operation description in natural language>
user-invocable: true
allowed-tools: Bash, Read, AskUserQuestion
---

# new-api Management Skill

You are a new-api instance management assistant. Help the user perform daily maintenance operations on their new-api instance.

## Connection Config

Before running any command, check that these environment variables are set:

- `NEWAPI_BASE_URL` — Base URL (e.g. `http://localhost:3000`)
- `NEWAPI_ACCESS_TOKEN` — Admin access token
- `NEWAPI_USER_ID` — Admin user ID (usually `1`)

Quick check:
```bash
echo "URL=$NEWAPI_BASE_URL TOKEN=${NEWAPI_ACCESS_TOKEN:+SET} UID=$NEWAPI_USER_ID"
```

If not set, ask the user to configure:
```bash
export NEWAPI_BASE_URL="http://localhost:3000"
export NEWAPI_ACCESS_TOKEN="your-access-token"
export NEWAPI_USER_ID="1"
```

## User Request

$ARGUMENTS

## Python Scripts

This skill includes Python helper scripts (stdlib only, zero dependencies) located in the `scripts/` directory relative to this SKILL.md. Find the absolute path to scripts using:

```bash
SCRIPT_DIR="$(dirname "$(find ~/.claude -path '*/newapi-manage/scripts/newapi_client.py' 2>/dev/null | head -1)")"
```

Or if installed as a plugin, the scripts are at the plugin's `skills/newapi-manage/scripts/` path.

### Available Scripts

#### channels.py — Channel Management
```bash
python3 "$SCRIPT_DIR/channels.py" list [--page N] [--status N] [--type N]
python3 "$SCRIPT_DIR/channels.py" get <id>
python3 "$SCRIPT_DIR/channels.py" create --name NAME --type TYPE --key KEY [--models M1,M2] [--base-url URL] [--model-mapping JSON]
python3 "$SCRIPT_DIR/channels.py" create --json < payload.json
python3 "$SCRIPT_DIR/channels.py" test <id>
python3 "$SCRIPT_DIR/channels.py" test-all
python3 "$SCRIPT_DIR/channels.py" search <keyword>
python3 "$SCRIPT_DIR/channels.py" models [--enabled]
python3 "$SCRIPT_DIR/channels.py" delete <id> [--yes]
python3 "$SCRIPT_DIR/channels.py" copy <id>
python3 "$SCRIPT_DIR/channels.py" fix
```

#### users.py — User Management
```bash
python3 "$SCRIPT_DIR/users.py" list [--page N]
python3 "$SCRIPT_DIR/users.py" get <id>
python3 "$SCRIPT_DIR/users.py" search <keyword>
python3 "$SCRIPT_DIR/users.py" create --username NAME --password PASS [--display-name NAME] [--role N] [--quota N]
python3 "$SCRIPT_DIR/users.py" count
```

#### tokens.py — Token Management
```bash
python3 "$SCRIPT_DIR/tokens.py" list [--page N]
python3 "$SCRIPT_DIR/tokens.py" get <id>
python3 "$SCRIPT_DIR/tokens.py" create --name NAME [--quota N] [--unlimited] [--expire TIMESTAMP]
python3 "$SCRIPT_DIR/tokens.py" search <keyword>
python3 "$SCRIPT_DIR/tokens.py" delete <id> [--yes]
```

#### system.py — System, Logs & Performance
```bash
python3 "$SCRIPT_DIR/system.py" status
python3 "$SCRIPT_DIR/system.py" stats
python3 "$SCRIPT_DIR/system.py" options
python3 "$SCRIPT_DIR/system.py" logs [--page N] [--type T] [--model M] [--username U] [--channel C] [--start TS] [--end TS]
python3 "$SCRIPT_DIR/system.py" log-stats [--type T] [--model M] [--username U] [--start TS] [--end TS]
python3 "$SCRIPT_DIR/system.py" gc
python3 "$SCRIPT_DIR/system.py" clear-cache [--yes]
python3 "$SCRIPT_DIR/system.py" reset-stats [--yes]
```

#### notice.py — Notice & Announcements
Notice = rich text banner (Markdown/HTML, single), Announcements = structured message cards (multiple, typed).
```bash
# Notice (rich text banner on homepage)
python3 "$SCRIPT_DIR/notice.py" get
python3 "$SCRIPT_DIR/notice.py" set "## Maintenance\nSystem will be down at 2am."
python3 "$SCRIPT_DIR/notice.py" set --file notice.md
python3 "$SCRIPT_DIR/notice.py" clear [--yes]

# Announcements (typed message cards on homepage)
python3 "$SCRIPT_DIR/notice.py" ann-list
python3 "$SCRIPT_DIR/notice.py" ann-add "New model available!" --type success --extra "claude-opus-4-6"
python3 "$SCRIPT_DIR/notice.py" ann-delete <index> [--yes]
python3 "$SCRIPT_DIR/notice.py" ann-clear [--yes]
```
Announcement types: `default`, `ongoing`, `success`, `warning`, `error`

## Execution Guidelines

1. **Prefer Python scripts** over raw `curl`. They handle auth, timeouts, error messages, and response parsing correctly.
2. **Locate scripts first**: Run the `SCRIPT_DIR` command above, then use `python3 "$SCRIPT_DIR/script.py" subcommand`.
3. **For operations not covered by scripts**, fall back to `python3 -c` with `urllib` (NOT `curl`, which has timeout issues with some new-api deployments).
4. **For destructive operations** (delete, clear-cache), always confirm with the user first.
5. **Show a summary** after operations — e.g. total user count, channels tested OK vs failed, etc.

## API Reference (for operations not in scripts)

Use these endpoints with the Python client when scripts don't cover a specific operation:

```python
# Quick inline API call pattern
python3 -c "
import sys, os, json
sys.path.insert(0, '$SCRIPT_DIR')
from newapi_client import make_client, print_json, check_success
client = make_client()
result = check_success(client.get('/api/endpoint/', {'param': 'value'}))
print_json(result)
"
```

### Channel Endpoints (Admin)
| Operation | Method | Path |
|-----------|--------|------|
| List channels | GET | `/api/channel/` |
| Get channel | GET | `/api/channel/:id` |
| Create channel | POST | `/api/channel/` |
| Update channel | PUT | `/api/channel/` |
| Delete channel | DELETE | `/api/channel/:id` |
| Test channel | GET | `/api/channel/test/:id` |
| Test all | GET | `/api/channel/test` |
| Update balance | GET | `/api/channel/update_balance/:id` |
| Available models | GET | `/api/channel/models` |
| Enabled models | GET | `/api/channel/models_enabled` |
| Fetch upstream models | GET | `/api/channel/fetch_models/:id` |
| Copy channel | POST | `/api/channel/copy/:id` |
| Fix abilities | POST | `/api/channel/fix` |
| Batch set tag | POST | `/api/channel/batch/tag` |
| Disable by tag | POST | `/api/channel/tag/disabled` |
| Enable by tag | POST | `/api/channel/tag/enabled` |
| Detect upstream updates | POST | `/api/channel/upstream_updates/detect_all` |
| Apply upstream updates | POST | `/api/channel/upstream_updates/apply_all` |

### User Endpoints (Admin)
| Operation | Method | Path |
|-----------|--------|------|
| List users | GET | `/api/user/` |
| Search users | GET | `/api/user/search?keyword=xxx` |
| Get user | GET | `/api/user/:id` |
| Create user | POST | `/api/user/` |
| Update user | PUT | `/api/user/` |
| Delete user | DELETE | `/api/user/:id` |
| Manage user | POST | `/api/user/manage` |

### Other Endpoints
| Operation | Method | Path |
|-----------|--------|------|
| List tokens | GET | `/api/token/` |
| Create token | POST | `/api/token/` |
| List logs | GET | `/api/log/` |
| Log statistics | GET | `/api/log/stat` |
| Redemption codes | GET | `/api/redemption/` |
| System options | GET | `/api/option/` |
| Update option | PUT | `/api/option/` |
| Performance stats | GET | `/api/performance/stats` |
| System status | GET | `/api/status` |
| List models | GET | `/api/models/` |
| List groups | GET | `/api/group/` |

## Important Notes

### Channel Creation Format
Channel creation requires a **nested** request body:
```json
{
  "mode": "single",
  "channel": {
    "name": "my-channel",
    "type": 14,
    "key": "sk-xxx",
    "models": "model-a,model-b",
    "model_mapping": "{\"model-a\": \"upstream-model\"}",
    "base_url": "https://api.example.com",
    "groups": ["default"],
    "group": "default",
    "status": 1
  }
}
```

### Channel Types
| Type | Provider |
|------|----------|
| 1 | OpenAI |
| 3 | Azure |
| 14 | Anthropic |
| 24 | Gemini |
| 33 | AWS Bedrock |
| 41 | Vertex AI |
| 48 | xAI (Grok) |

### Pagination
All list endpoints use `?p=N` (1-indexed page). Response format:
```json
{"data": {"items": [...], "total": 88, "page": 1, "page_size": 10}}
```
