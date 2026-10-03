---
name: babysit-pr
description: Follow a pull request through local review, CI and any automated review, fix actionable findings, and prepare it for its repository-defined merge gate. Use when asked to babysit, watch, follow, or shepherd a PR. Do not use for a one-time review or an immediate merge request.
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
5. Review locally before every push, and before the PR is first opened: run the `open-code-review` skill on the branch diff (`ocr review --audience agent -b "<context>" --from <target> --to HEAD --output <file>`; read the whole file) and iterate until its findings are fixed or declined with a reason. Review Markdown, JSON and test files by hand: `ocr` skips them by default. Opening or updating the PR comes after this loop, so mistakes are caught before anyone else sees them.
6. Follow the repository's commit and push policy. A new commit invalidates a verdict tied to the previous SHA, so identify the new head explicitly. Only if the repository uses a hosted review bot: after each fix push, inspect current reviews and trigger comments for that SHA, and if no hosted review is already running or complete, trigger it the way the repository prescribes (for Codex, an issue comment whose complete body is `@codex review`), then wait for that round. Without a hosted bot, the local review in step 5 is the review.
7. Repeat while the requested monitoring mode, repository policy and the stopping rule allow it. Do not weaken checks, use skip-CI markers, dismiss substantive findings, or resolve threads merely to make the PR appear green.
8. Report the fixes, checks, declined findings with reasons, remaining external gates, and a concise account of what the PR does. Give one concrete next action when human input is needed.

Never merge, deploy, mark a draft ready, spend money, or send other reviewer messages unless the user has authorized that exact action or repository instructions already grant it. A request to babysit authorizes normal local fixes and pushes to the named PR. Where the repository uses a hosted review bot, it also authorizes the exact trigger comment (such as `@codex review`) after a push, even when repository defaults assign that trigger to the owner. Check first so retries and resumed sessions do not post duplicate comments. This authorization does not waive human approval gates.

When a hosted review bot reviews on the ready event and marking a PR ready is authorized, wait for that review before merging (see the reference); a draft-state "no issues" does not cover it. Repositories that review locally can open PRs ready straight away.
