# Automated review triage

Use GitHub CLI or the repository's preferred provider tooling. Capture the PR number, repository, and current head SHA before interpreting results.

## Polling

Run the watchers in the background and act when they exit; do not poll by hand in a loop.

- After commenting `@codex review`, run `scripts/watch-codex.sh <pr> [since] [timeout-minutes]`. It waits for Codex's answer to the newest request and prints one line per finding (priority, `file:line`, comment id, title), or `CLEAN` when Codex reacted 👍, then the CI state once. Exit 2: no answer before the timeout (default 30 minutes). Exit 3: Codex posted an error; wait about 30 seconds, then request again.
- After marking a PR ready, run `scripts/wait-ready-review.sh <pr> [timeout-minutes]`. Marking ready triggers another Codex review of the same SHA, which can raise new findings. A 👍 alone is not a finished review: the reliable signal is the row for "Draft marked ready" on the head's short SHA in the "Codex Review Summary" comment showing Completed. The script waits for that row and prints the findings on the head after the ready event, or `CLEAN`.

Codex answers in three shapes: inline review comments, a review whose body holds the finding, or an issue comment saying it found no major issues. Its live "Codex Review Summary" comment shows Running while it works and is not a verdict.

For CI and other bots:

```bash
gh pr checks <number>
gh pr view <number> --json headRefOid,isDraft,mergeable,reviews,reviewDecision,statusCheckRollup
```

Use `gh pr checks <number> --watch` only when the repository permits continuous monitoring. Review bots may post after CI settles, so a green CI result alone does not prove review completion.

## Fetching complete findings

Summary views truncate. Fetch all three GitHub comment surfaces:

```bash
gh api repos/{owner}/{repo}/pulls/{number}/reviews --paginate
gh api repos/{owner}/{repo}/pulls/{number}/comments --paginate
gh api repos/{owner}/{repo}/issues/{number}/comments --paginate
```

Filter by creation time and commit SHA to separate the current round from findings superseded by a push. Still inspect older unresolved comments when they may describe a defect that remains present.

## Deciding fix or report

Fix findings that identify reachable correctness failures, data-loss or security risks, crashes, misleading behavior introduced by the change, or small clear defects. Treat each valid finding as evidence of a defect category: inspect sibling paths before deciding the patch is complete.

Report a finding as non-actionable when code inspection shows it is factually wrong, pre-existing and outside the PR, conflicts with authoritative project requirements, or proposes a speculative refactor beyond scope. Include the specific evidence. Repository instructions may require fixing every substantive finding and always take precedence over this guidance.

## Stopping rule

- After a clean round, move to the merge gate. Do not add features to the branch.
- After three rounds, decide explicitly whether new findings are new risks or narrower variants of earlier ones. Record narrower variants as known limits (in the PR description or wherever the repository keeps them) and stop absorbing them.
- If the same edge cases keep returning across rounds, tell the user instead of continuing.

## Re-review

After a push, treat reviews tied to the old SHA as superseded. Inspect reviews and issue comments for the new SHA. If no hosted review is running or complete, post exactly one new issue comment:

```text
@codex review
```

Do not post it before a push, repeat it for the same SHA, or post it within about 30 seconds of a review finishing (Codex may ignore it).
