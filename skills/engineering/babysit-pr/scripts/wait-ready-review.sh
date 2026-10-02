#!/usr/bin/env bash
# Waits until Codex's review triggered by "Draft marked ready" on the PR's
# current head is Completed in its summary comment, then prints the findings
# Codex left on that head after the ready event (or CLEAN).
# Usage: wait-ready-review.sh <pr> [timeout-minutes]
set -uo pipefail
pr="$1"; limit="${2:-40}"
repo="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
head="$(gh pr view "$pr" --json headRefOid -q .headRefOid)"
short="${head:0:7}"
ready="$(gh api "repos/$repo/issues/$pr/timeline?per_page=100" -q '[.[] | select(.event=="ready_for_review") | .created_at] | last')"
if [ -z "$ready" ] || [ "$ready" = null ]; then echo "PR $pr was never marked ready"; exit 2; fi
for _ in $(seq "$limit"); do
  row="$(gh api "repos/$repo/issues/$pr/comments?per_page=100" -q '.[] | select(.body|test("codex-pull-request-review-summary")) | .body' |
    grep -F 'Draft marked ready' | grep -F "\`$short\`" | tail -n 1)"
  if grep -q 'Completed' <<<"$row"; then
    findings="$(gh api "repos/$repo/pulls/$pr/comments?per_page=100" -q ".[] | select(.original_commit_id==\"$head\" and (.user.login|test(\"codex\")) and .created_at > \"$ready\") | \"FINDING \(.id) \(.path):\(.original_line) \(.body|split(\"\n\")[0]|gsub(\"<[^>]*>|!\\\\[[^]]*\\\\]\\\\([^)]*\\\\)\";\"\"))\"")"
    body="$(gh api "repos/$repo/pulls/$pr/reviews?per_page=100" -q "[.[] | select(.commit_id==\"$head\" and .submitted_at > \"$ready\" and (.body|test(\"Badge\")))] | length")"
    if [ -z "$findings" ] && [ "$body" = 0 ]; then echo "CLEAN: ready-state review of $short completed"; else echo "$findings"; [ "$body" = 0 ] || echo "BODY FINDINGS: $body review(s) with findings in the body"; fi
    exit 0
  fi
  grep -q -E 'Failed|Error' <<<"$row" && { echo "Codex ready-state review failed: $row"; exit 3; }
  sleep 60
done
echo "timed out waiting for the ready-state review of $short"; exit 2
