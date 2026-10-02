---
name: babysit-pr
description: Follow a pull request through CI and automated review, fix actionable findings, and prepare it for its repository-defined merge gate. Use when asked to babysit, watch, follow, or shepherd a PR. Do not use for a one-time review or an immediate merge request.
---

# Babysit PR

Identify the PR from an explicit number or URL, otherwise from the current branch. Read the repository instructions before acting. When the environment provides thread-level PR linking, register the PR with the current thread.

The target state is:

- the PR has no merge conflict with its target branch;
- all required checks that should run at the current PR state have passed;
- every automated review finding has been read and either fixed or reported as non-actionable with a concrete reason;
- repository-specific review, draft, approval, and merge gates remain intact.

For polling, complete finding retrieval, triage and the stopping rule, read [references/bot-triage.md](references/bot-triage.md).

## Workflow

1. Inspect the PR, its head SHA, draft state, mergeability, required checks, reviews, and repository instructions. Do not mistake a skipped draft job for a passing check.
2. Watch CI and automated reviews with the scripts in `scripts/`, run in the background, at a cadence the repository allows. If repository instructions prohibit continuous monitoring, stop when only external results remain and give the user the exact command and output to report back.
3. Read every finding in full and group comments that share a root cause.
4. For actionable findings, reproduce the issue where practical, fix it, inspect sibling paths for the same defect category, and run proportionate tests. Preserve unrelated work in dirty worktrees.
5. Before each push that answers review findings, run a local review of the branch (the `cross-review` skill when installed) and fix what it finds, so the hosted round confirms rather than discovers.
6. Follow the repository's commit and push policy. A new commit invalidates a verdict tied to the previous SHA, so identify the new head explicitly. After each fix push, inspect current reviews and trigger comments for that SHA. If no hosted review is already running or complete, post an issue comment whose complete body is `@codex review`, then wait for that review round.
7. Repeat while the requested monitoring mode, repository policy and the stopping rule allow it. Do not weaken checks, use skip-CI markers, dismiss substantive findings, or resolve threads merely to make the PR appear green.
8. Report the fixes, checks, declined findings with reasons, remaining external gates, and a concise account of what the PR does. Give one concrete next action when human input is needed.

Never merge, deploy, mark a draft ready, spend money, or send other reviewer messages unless the user has authorized that exact action or repository instructions already grant it. A request to babysit authorizes normal local fixes and pushes to the named PR. It also authorizes the exact `@codex review` trigger comment after a push, even when repository defaults assign that trigger to the owner. Check first so retries and resumed sessions do not post duplicate comments. This authorization does not waive human approval gates.

When marking a PR ready is authorized, wait for the review that the ready event triggers before merging (see the reference); a draft-state "no issues" does not cover it.
