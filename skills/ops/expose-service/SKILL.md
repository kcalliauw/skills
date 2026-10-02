---
name: expose-service
description: Expose local services via Tailscale or public Funnel.
---

# Expose Service

Route the request first, then execute one path. Protocol default depends on scope: **mesh = TCP, internet = HTTPS** (see Router).

## Router (decide before acting)

1. **Scope — default is mesh-only.** Only treat the request as internet exposure if the user explicitly says "internet", "public", "public URL", or similar. Words like "share", "expose", "publish" alone mean mesh-only (Tailscale tailnet).
2. **Protocol — scope-dependent default.** Mesh exposure (Paths A/B-serve): default **TCP** — if the user does not name a protocol, assume raw TCP (rinetd rule with no `/udp` suffix, `tailscale serve --tcp`). rinetd does no TLS automatically, so mesh forwarding is passthrough, not HTTPS termination. Internet exposure (Path B-funnel): default **HTTPS** — assume a TLS-terminating HTTPS proxy (`tailscale funnel --bg <port>`) unless the user asks for raw TCP. UDP in any path only when explicitly asked.
3. **Route:**
   - Mesh-only on Tailscale, raw TCP or any UDP → **Path A (rinetd)**. This is the default path. For UDP forwarding use rinetd — `tailscale serve`/`funnel` do not support UDP listeners.
   - Mesh-only HTTP(S) on Tailscale → **Path A (rinetd)** or **Path B (tailscale serve)**. Prefer rinetd when the user wants the same port on the mesh IP with raw passthrough; prefer `serve` for HTTPS with MagicDNS + TLS termination.

   - Internet via Tailscale → **Path B (`tailscale funnel`)**. Note: `tailscale serve` is tailnet-only; `funnel` is the internet path.

Use Tailscale as the mesh transport; no transport-choice prompt is needed. If scope is ambiguous, assume mesh-only and say so.

## Common pre-checks (all paths)

```bash
uname -s                          # Linux or Darwin
command -v rinetd tailscale
```

Verify the source service is listening on localhost before exposing it (replace 3773):

```bash
# Linux:
ss -tlnp | grep ':3773'           # TCP (default)
ss -ulnp | grep ':3773'           # only if user asked for UDP
# macOS:
lsof -iTCP:3773 -sTCP:LISTEN
lsof -iUDP:3773                   # only if user asked for UDP
```

If nothing listens on `127.0.0.1:<port>`, stop and tell the user.

Resolve mesh IPs dynamically every run — never hardcode (macOS `utun*` numbers are dynamic):

```bash
tailscale ip -4                   # Tailscale IPv4 (primary, both OSes)
tailscale ip -6                   # Tailscale IPv6

```

macOS quirks: Tailscale CLI may live at `/Applications/Tailscale.app/Contents/MacOS/Tailscale` (prefix with `TAILSCALE_BE_CLI=1` if it opens the GUI instead of acting as CLI). Cross-checks: Linux `ip -o -4 addr show dev tailscale0`; macOS `ifconfig` for the interface matching `tailscale ip`. Do not assume a fixed `utun` number.

Inventory existing listeners and `tailscale serve status` / `tailscale funnel status` before adding a mapping. Preserve unrelated services and request confirmation before interrupting an existing listener or changing its exposure scope.

## Path A: Mesh-only via rinetd (default)

Use `rinetd` v0.73 (`man 8 rinetd`) to bind the mesh IP and forward to localhost. One rule per line:

```text
bindaddress bindport connectaddress connectport
100.64.0.10 3773 127.0.0.1 3773
```

- Linux: binary `/usr/sbin/rinetd`, config `/etc/rinetd.conf`, `sudo apt install rinetd` if missing.
- macOS: `brew install rinetd`, config `$HOMEBREW_PREFIX/etc/rinetd.conf` (`/opt/homebrew/...` ARM, `/usr/local/...` Intel), service via `brew services start rinetd`.
- `bindaddress` = mesh IP from pre-checks. **Never `0.0.0.0` unless explicitly asked.**
- `connectaddress` = `127.0.0.1` (or `::1`) + local port.
- Protocol: default TCP = no suffix. UDP only when asked: `IP port/udp 127.0.0.1 port/udp [timeout=1200]` (default 72s timeout is usually too short).
- rinetd does no TLS — forwarding is raw passthrough. If the user wants HTTPS termination on the mesh, use Path B (`tailscale serve`) instead; rinetd just moves bytes.
- `allow`/`deny` lines take IP patterns only (`*`, `?`), no hostnames.
- Existing `tailscale serve` listeners on the same mesh IP are NOT rinetd — check `sudo ss -tlnp` owner before touching anything.

Procedure:

```bash
sudo cp /etc/rinetd.conf /etc/rinetd.conf.bak-$(date +%Y%m%d-%H%M%S)
grep -E '^[0-9a-fA-F.:]+[[:space:]]+3773' /etc/rinetd.conf  # duplicate check
echo '<meshIP> 3773 127.0.0.1 3773' | sudo tee -a /etc/rinetd.conf
sudo kill -HUP $(cat /run/rinetd.pid)   # graceful reload; or: sudo systemctl reload rinetd
sudo systemctl status rinetd
sudo ss -tlnp | grep ':3773'            # verify (macOS: lsof -iTCP:3773 -sTCP:LISTEN)
curl -v http://<meshIP>:3773/          # or: nc -vz <meshIP> 3773
```

## Path B: Tailscale serve (tailnet) / funnel (internet)

Native Tailscale alternative for TCP/HTTP(S). No config file; command permissions depend on the configured Tailscale operator (sudo may be required).

```bash
# Tailnet-only HTTPS endpoint, proxying the localhost HTTP service:
tailscale serve --bg 3773
# Tailnet-only, raw TCP (when user asked for raw TCP, or non-HTTP service):
tailscale serve --bg --tcp=3773 tcp://127.0.0.1:3773
# Internet, HTTPS (default when user asked for internet) — TLS-terminated:
tailscale funnel --bg 3773
# Internet TCP variants require an explicit request; consult current
# tailscale funnel --help and vendor docs for TLS and port restrictions.
# Inspect:
tailscale serve status
tailscale funnel status
# Undo only the owned TCP mapping (example):
tailscale serve --tcp=3773 off
# For HTTPS/Funnel, use the matching handler's off command after checking
# current CLI help. Never reset the host's entire configuration.
```

Choose `serve` vs `funnel` by scope from the Router. For `funnel` (internet) default to HTTPS unless the user asked for raw TCP; for `serve` (mesh) default to raw `--tcp` for non-HTTP services per the Router, HTTP proxy form for HTTP services. UDP is not supported here — send UDP requests back to Path A.


## Switching scope (migration)

When the user asks to move an already-exposed service to a different scope (e.g. mesh via rinetd → internet via `tailscale funnel`), do both halves: add the new path, tear down the old one.

1. **Inventory current exposure first:**
   ```bash
   grep -v '^#' /etc/rinetd.conf | grep -v '^$'   # rinetd rules (macOS: Homebrew-prefix conf)
   tailscale serve status
   tailscale funnel status

   ```
2. **Keep or replace? Ask.** Default to **replace** (remove the old exposure) and say so — keeping both scopes is valid but must be explicit, otherwise the service ends up reachable in two places.
3. **Add the new path** per the Router (including its protocol default).
4. **Tear down the old path:**
   - rinetd: back up the config, delete or comment out the rule, `sudo kill -HUP $(cat /run/rinetd.pid)`, verify the listener is gone (`sudo ss -tlnp | grep ':<port>'`).
   - `tailscale serve`/`funnel`: remove only that port's handler. **Do not `reset`** when other entries exist — `reset` wipes all serve/funnel config on the host. Confirm with `serve status` / `funnel status` afterwards.

5. **Verify both directions:** new endpoint reachable, old endpoint gone.

## Troubleshooting

- rinetd `bind: Address already in use` (`/var/log/rinetd.log`): port taken on that IP — pick another bind port or stop the conflicting listener.
- rinetd rule ignored: typo, missing trailing newline, or an `allow`/`deny` line rejecting the client.
- Reload didn't apply: confirm `/run/rinetd.pid` matches `systemctl status rinetd`; fall back to `sudo systemctl restart rinetd`. macOS: `brew services list`, and double-check the Homebrew-prefix config path vs `/etc/rinetd.conf`.
