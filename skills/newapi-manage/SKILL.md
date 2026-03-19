---
name: newapi-manage
description: Use when managing a new-api instance — channels, users, tokens, pricing/ratios, groups, redemption codes, logs, system settings, and announcements. Use this skill whenever the user wants to operate on their new-api platform, check channel status, manage model pricing, create redemption codes, or perform any admin operations. Also trigger for Chinese requests like 查看渠道、禁用渠道、创建用户、查日志、设置定价、创建兑换码、发公告、测试渠道 etc.
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

## Script Discovery

Scripts live alongside this SKILL.md in the `scripts/` directory. To see all available scripts and their descriptions:
```bash
python3 "$SCRIPT_DIR/newapi_client.py"
```

For detailed command help on any script:
```bash
python3 "$SCRIPT_DIR/<script>.py" --help
```

New scripts dropped into `scripts/` are automatically discoverable — no need to update this file.

## User Request

$ARGUMENTS

## Execution Guidelines

1. **Prefer Python scripts** over raw `curl`. They handle auth, timeouts, error messages, and response parsing correctly.
2. **For operations not covered by scripts**, use the Python pattern below with `urllib` (NOT `curl`, which has timeout issues with some new-api deployments).
3. **For destructive operations** (delete, clear-cache, reset-stats, cleanup), always confirm with the user first.
4. **Show a summary** after operations — e.g. total user count, channels tested OK vs failed, etc.
5. **Add `--dry-run`** to preview any mutation before executing.

### Fallback: Inline Python for Uncovered Operations

```python
python3 -c "
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname('$0'), '.claude/skills/newapi-manage/scripts'))
from newapi_client import make_client, print_json, check_success
client = make_client()
result = check_success(client.get('/api/endpoint/', {'param': 'value'}))
print_json(result)
"
```

## Pricing System

User pays = `ModelRatio × CompletionRatio(for output) × GroupRatio × 2 × token_count / 1M`

Key option names (set via `system.py set-option --key KEY --value VALUE`):
| Option Key | Purpose | Example |
|------------|---------|---------|
| `ModelRatio` | Base input price ratio per model (official_input_$/M ÷ 2) | `{"gpt-5": 0.625}` |
| `CompletionRatio` | Output/input multiplier override (only if hardcoded value is wrong) | `{"gemini-3-flash": 6}` |
| `GroupRatio` | Group discount/markup multiplier | `{"default":1,"vip":0.7}` |
| `group_ratio_setting.group_ratio` | Must match GroupRatio (internal sync) | same as above |
| `CacheRatio` | Cache read = input × this ratio | `{"gpt-5": 0.1}` |
| `CreateCacheRatio` | Cache write multiplier | `{"claude-opus-4-6": 1.25}` |
| `UserUsableGroups` | Groups visible to users with descriptions | `{"default":"默认分组"}` |
| `TopupGroupRatio` | Topup pricing per group | same structure as GroupRatio |

## Add New Channel Group Workflow

Standard steps when adding a new provider channel:

1. Create the channel in dashboard (or via `channels.py create`)
2. Create the group: `groups.py set-ratio --name GROUP --ratio RATIO`
3. Move channel to group: `channels.py update --id ID --group GROUP`
4. Strip model prefix: `channels.py update --id ID --strip-prefix PREFIX`
5. Set ModelRatio for new models: `pricing.py set --model NAME --ratio RATIO`
6. Set CacheRatio/CompletionRatio if needed: `system.py set-option --key KEY --value VALUE`
7. Fix abilities: `channels.py fix`

## Channel Creation Format

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

## Pagination Response Format

All list endpoints use `?p=N` (1-indexed page). Response format:
```json
{"data": {"items": [...], "total": 88, "page": 1, "page_size": 10}}
```
