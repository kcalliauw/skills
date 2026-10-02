#!/usr/bin/env bash
# Waits for the Codex bot's answer to the latest `@codex review` request on a
# PR, then prints only what the babysit loop needs: each new finding
# (priority, title, file:line, comment id for the reply), or CLEAN when Codex
# reacted 👍, followed by the CI state once.
#
# Usage: watch-codex.sh <pr> [since-iso8601] [timeout-minutes]
#   since    defaults to the time of the newest `@codex review` comment.
#   timeout  defaults to 30; exit 2 on timeout, 3 when Codex reports an
#            error, 0 otherwise.
# Run it in the background; it polls every 60 seconds.
set -euo pipefail

pr="${1:?usage: watch-codex.sh <pr> [since] [timeout-minutes]}"
repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
bot='chatgpt-codex-connector[bot]'
since="${2:-$(gh api "repos/$repo/issues/$pr/comments" --paginate \
  --jq '[.[] | select(.body | test("^@codex review"))] | last | .created_at // empty')}"
since="${since:-1970-01-01T00:00:00Z}"
deadline=$(( $(date +%s) + ${3:-30} * 60 ))

print_ci() {
  echo '--- CI'
  gh pr checks "$pr" --json name,state,link \
    --jq '.[] | "\(.state)\t\(.name)\(if .state == "FAILURE" then "\t\(.link)" else "" end)"' \
    || true
}

while :; do
  reviews="$(gh api "repos/$repo/pulls/$pr/reviews" --paginate --jq \
    "[.[] | select(.user.login == \"$bot\" and .submitted_at > \"$since\") | .id] | join(\" \")")"
  if [ -n "$reviews" ]; then
    echo "Codex review since $since:"
    gh api "repos/$repo/pulls/$pr/comments" --paginate --jq \
      ".[] | select(.user.login == \"$bot\" and .created_at > \"$since\")
        | (.body | split(\"\n\")[0]) as \$head
        | (\$head | capture(\"(?<p>P[0-9])\") // {p: \"P?\"}).p as \$p
        | (\$head | sub(\"^\\\\*\\\\*(<sub>)*!\\\\[[^]]*\\\\]\\\\([^)]*\\\\)(</sub>)*\\\\s*\"; \"\") | sub(\"\\\\*\\\\*\$\"; \"\")) as \$title
        | \"\(\$p)\t\(.path):\(.line // .original_line)\tid=\(.id)\t\(\$title)\""
    print_ci
    exit 0
  fi
  errored="$(gh api "repos/$repo/issues/$pr/comments" --paginate --jq \
    "[.[] | select(.user.login == \"$bot\" and .created_at > \"$since\" and (.body | test(\"Something went wrong\")))] | length")"
  if [ "$errored" -gt 0 ]; then
    echo "ERROR: Codex failed to review since $since; comment @codex review again"
    print_ci
    exit 3
  fi
  clean="$(gh api "repos/$repo/issues/$pr/reactions" --jq \
    "[.[] | select(.user.login == \"$bot\" and .content == \"+1\" and .created_at > \"$since\")] | length")"
  if [ "$clean" -gt 0 ]; then
    echo "CLEAN: Codex reacted 👍 since $since"
    print_ci
    exit 0
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "TIMEOUT: no Codex answer since $since"
    print_ci
    exit 2
  fi
  sleep 60
done
