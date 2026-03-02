# Claude Flow Setup Guide

Multi-agent orchestration for complex AI coding tasks.

## Prerequisites

- Node.js 18+
- npm or pnpm
- Anthropic API key

## Installation

### 1. Install globally

```bash
npm install -g claude-flow@alpha
```

### 2. Initialize in your project

```bash
cd /path/to/your-project
npx claude-flow@alpha init
```

This creates:
```
.claude-flow/
├── agents.json      # Agent registry (auto-managed)
└── hive-mind/       # Hive mind state
    └── state.json
```

### 3. Configure API key

```bash
npx claude-flow@alpha config
```

When prompted, enter your Anthropic API key.

Alternatively, set environment variable:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Usage

### Basic Swarm (simpler tasks)

```bash
npx claude-flow@alpha swarm "Refactor the auth module to use JWT tokens"
```

### Hive Mind (complex, parallel tasks)

```bash
npx claude-flow@alpha hive-mind spawn "Implement user dashboard with charts and settings"
```

### With JSON task input

```bash
npx claude-flow@alpha hive-mind spawn --claude -o "$(cat tasks.json)"
```

### Monitoring

```bash
# Check status
npx claude-flow@alpha hive-mind status

# View metrics
npx claude-flow@alpha hive-mind metrics

# List active agents
ls .claude-flow/agents/
```

## Claude Code Integration (Optional)

If using with Claude Code IDE, add permissions to `.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "SlashCommand(/claude-flow-swarm:*)"
    ]
  }
}
```

## Command Reference

| Command | Description |
|---------|-------------|
| `npx claude-flow@alpha --version` | Check version |
| `npx claude-flow@alpha init` | Initialize in project |
| `npx claude-flow@alpha config` | Configure API keys |
| `npx claude-flow@alpha swarm "objective"` | Run basic swarm |
| `npx claude-flow@alpha hive-mind spawn "objective"` | Run intelligent multi-agent |
| `npx claude-flow@alpha hive-mind status` | Monitor running agents |
| `npx claude-flow@alpha hive-mind metrics` | View performance stats |
| `npx claude-flow@alpha cleanup` | Clean transient files |

## Troubleshooting

### "No API key"
Run `npx claude-flow@alpha config` to set your Anthropic key.

### "Agent timeout"
Objective too complex—break it into smaller tasks.

### "Context limit exceeded"
Reduce the number of files in scope or simplify the objective.

## Resources

- **GitHub:** https://github.com/ruvnet/claude-flow
- **npm:** https://www.npmjs.com/package/claude-flow
