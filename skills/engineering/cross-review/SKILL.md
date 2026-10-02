---
name: cross-review
description: Review a diff locally with Codex and Claude Code side by side, using the Codex review rubric, and get one merged list of prioritized findings. Use before opening a pull request, before requesting a hosted review round, or when asked for a local, second-opinion or cross-model review of a branch, a commit or uncommitted changes.
metadata:
  internal: true
---

# Cross-review

Run two independent reviewers on the same diff and act on their merged findings. Both get the Codex `/review` rubric as their system prompt, the same target prompt and the same JSON output schema, so their findings are comparable and merge by location.

## Run it

From the repository being reviewed, run the script next to this file:

```bash
python3 <this-skill-dir>/scripts/cross-review --base main        # branch vs. base (default: the default branch)
python3 <this-skill-dir>/scripts/cross-review --commit <sha>     # one commit
python3 <this-skill-dir>/scripts/cross-review --uncommitted      # staged, unstaged and untracked work
```

Options: `--focus "<text>"` adds a review focus; `--reviewers codex` or `--reviewers claude` runs one reviewer; `--json` prints the merged report; `--timeout <seconds>` per reviewer (default 900).

- The reviewers call their model APIs. In a sandbox without network access, run the command outside the sandbox (request escalated permissions) rather than letting it fail.
- A run takes about one to fifteen minutes; run it in the background when your environment allows, and wait for it rather than polling.
- Exit codes: `0` no P0/P1 findings, `1` P0/P1 findings, `2` no reviewer produced a result, `3` usage error. A reviewer that hit its usage limit is reported as `skipped` and the other reviewer's result still counts.

## Act on the result

Each row reads `P<n>  <reviewers>  <path:lines>  <title>`, followed by the explanation. A row found by both reviewers is stronger evidence; a row from one reviewer still counts.

1. Read every finding before changing anything; several rows often share one root cause.
2. Fix P0 and P1 findings. Fix P2 findings that are local and in scope. For each finding you decline, write a one-line reason (wrong about the code, pre-existing, outside the change's scope).
3. Treat each fixed finding as a class: check sibling code paths for the same defect.
4. Re-run cross-review after fixing. Stop when a run returns no P0/P1 findings, or after three runs; then report the remaining findings as known limits instead of continuing.

Done when the last run has no unaddressed P0/P1 findings and every declined finding has a written reason. This skill never posts to GitHub or other services; it only reads the repository.

## Repository rules

Reviewers apply the review rules in the `AGENTS.md` files that cover the changed paths, such as a `## Code Review Rules` section. Put repository-specific review policy there so local and hosted reviewers read the same rules.
