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

## Plugin Structure

```
skillbox/
├── .claude-plugin/
│   └── plugin.json        # Plugin manifest
├── skills/
│   └── newapi-manage/
│       └── SKILL.md       # Skill definition (YAML frontmatter + instructions)
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
