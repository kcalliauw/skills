# skills

Agent skills for Claude Code, Codex and OpenCode, installable with the
[`skills`](https://github.com/vercel-labs/skills) CLI.

| Skill | What it does |
|---|---|
| [`cross-review`](skills/engineering/cross-review/) | Reviews a diff locally with Codex and Claude Code side by side, in a code-review pass (the Codex `/review` rubric) and a security pass, and prints one merged list of prioritized findings. *Work in progress: hidden from install lists until released.* |
| [`babysit-pr`](skills/engineering/babysit-pr/) | Follows a pull request through local `open-code-review` iterations, CI and any hosted review bot, fixes actionable findings, and stops at the repository's merge gate. |
| [`expose-service`](skills/ops/expose-service/) | Exposes a local service on a Tailscale mesh (rinetd or `tailscale serve`) or to the internet (`tailscale funnel`). |

## Install

```bash
# All released skills, globally, for Claude Code, Codex and OpenCode
npx skills add kcalliauw/skills -g -a claude-code -a codex -a opencode

# One skill
npx skills add kcalliauw/skills --skill babysit-pr -g -a claude-code -a codex -a opencode

# Include work-in-progress skills
INSTALL_INTERNAL_SKILLS=1 npx skills add kcalliauw/skills --skill cross-review -g -a claude-code -a codex -a opencode
```

The repository is also a Claude Code plugin (`.claude-plugin/plugin.json`).

## Requirements

- `cross-review`: Python 3.10+, `git`, and at least one of the `codex` and `claude` CLIs, signed in. Each reviewer needs network access to its model API.
- `babysit-pr`: the GitHub CLI (`gh`), signed in.
- `expose-service`: Tailscale; `rinetd` for mesh forwarding.

## Layout

```
skills/<category>/<skill>/
  SKILL.md        instructions (name and description in the frontmatter)
  agents/         Codex display metadata
  scripts/        helpers the skill runs (standard library only)
  assets/ tests/  skill-specific files
```

`scripts/check-skills` lints every skill; CI runs it with the tests.

## License

MIT, except two vendored parts of `cross-review` (see its `NOTICE`):
`assets/rubric.md` from [OpenAI Codex](https://github.com/openai/codex)
(Apache License 2.0) and `assets/security/` from Cloudflare's
[security-audit skill](https://github.com/cloudflare/security-audit-skill) (MIT).
