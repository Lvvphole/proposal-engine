# Claude Code Skills

Skills define repeatable workflows for Claude Code. Each skill has a `SKILL.md` that acts as a system prompt — Claude reads it before executing the task.

| Skill | Purpose |
|---|---|
| `extract-supplier-quote` | Run extraction pipeline on a new supplier quote |
| `generate-proposal` | Generate a contractor-ready proposal from extraction results |
| `improve-extraction` | Diagnose and fix extraction accuracy issues |
| `onboard-contractor` | Set up a new contractor profile with markup rules and branding |

## Usage

From Claude Code, invoke a skill by name:

```
/skill extract-supplier-quote
```

Claude reads the `SKILL.md` file, follows the workflow, and produces the specified outputs.
