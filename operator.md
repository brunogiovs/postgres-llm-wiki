# Operator Runbook

This runbook starts the project-local Hermes dashboard for the PostgreSQL wiki setup.

Run commands from the project root:

```bash
cd /data/repos/pg-wiki
```

## Prerequisites

Start or verify the local llama.cpp backend first. This project currently serves Qwen3.5-9B `Q6_K` at 128K context through the OpenAI-compatible alias `pgwiki-local`.

```bash
scripts/llama_server status
scripts/llama_server start
```

The expected endpoint is:

```text
http://127.0.0.1:8080/v1
```

Verify it directly:

```bash
curl http://127.0.0.1:8080/v1/models
```

## Start The Dashboard

Use the convenience wrapper. It starts the project-local Hermes dashboard and exposes the selected port to your tailnet with Tailscale Serve by default:

```bash
scripts/dashboard start
```

Local URL:

```text
http://127.0.0.1:9119
```

Tailnet URL:

```text
https://agentserver.tailda962e.ts.net/
```

`--tui` enables the browser Chat tab. `--no-open` avoids trying to launch a browser from a headless shell.

The wrapper keeps the dashboard bound to `127.0.0.1` and has Tailscale Serve proxy tailnet HTTPS traffic back to that loopback listener. That avoids binding the dashboard directly to `0.0.0.0`.

Environment overrides:

```bash
HERMES_DASHBOARD_PORT=9119 scripts/dashboard start
HERMES_DASHBOARD_TAILSCALE=0 scripts/dashboard start
HERMES_DASHBOARD_TAILSCALE_MODE=funnel scripts/dashboard start
HERMES_DASHBOARD_TAILSCALE_PATH=/pg-wiki scripts/dashboard start
```

`HERMES_DASHBOARD_TAILSCALE_MODE=serve` is the default and exposes the dashboard only inside your tailnet. `funnel` exposes it on the public internet and should be used only deliberately.

The dashboard auto-builds the React frontend on first launch via `npm`. Node 22 LTS lives at `.wiki-runtime/env/node-prefix/`; `scripts/dashboard` puts it ahead of any system Node (system `node` 18 is too old for Vite 7). To rebuild manually:

```bash
cd .wiki-runtime/hermes-agent/web && npm install && npm run build
```

## Status And Stop

```bash
scripts/dashboard status
scripts/dashboard stop
```

`scripts/dashboard stop` stops the Hermes dashboard. It leaves the Tailscale Serve config in place by default so it does not accidentally remove unrelated Serve config on the node. Remove the dashboard exposure explicitly with:

```bash
scripts/dashboard unserve
```

Or opt into cleanup during stop:

```bash
HERMES_DASHBOARD_TAILSCALE_RESET_ON_STOP=1 scripts/dashboard stop
```

## Remote Access

Prefer Tailscale Serve through `scripts/dashboard start`. It keeps access scoped to devices in the tailnet and avoids directly exposing the dashboard listener on the LAN. The dashboard can manage config and credentials, so only use `HERMES_DASHBOARD_TAILSCALE_MODE=funnel` when public internet exposure is genuinely intended.

## Agent Gateway

The dashboard is separate from the wiki agent lifecycle wrapper. Start the maintainer gateway only when you want the long-running agent process:

```bash
scripts/wiki_agent start
scripts/wiki_agent status
scripts/wiki_agent logs --lines 80
scripts/wiki_agent stop
```

The dashboard can be used without `scripts/wiki_agent start`, as long as the local LLM endpoint is running.

## Stop All Dependencies

Use the convenience wrapper to tear everything down in the right order (consumers first, LLM backend last):

```bash
scripts/stop_all              # graceful (SIGTERM)
scripts/stop_all --force      # escalate to SIGKILL if a step times out
```

The script runs every step even if a prior step fails and prints a final status block, so a stuck component will not block the rest of the teardown. It calls, in order:

1. `scripts/dashboard stop` — Hermes dashboard (browser UI + Chat tab).
2. `scripts/wiki_agent stop` — wiki agent gateway started via the lifecycle wrapper.
3. `scripts/llama_server stop` — local llama.cpp server.

Manual equivalents, if you need to run a single step:

```bash
scripts/dashboard stop
scripts/wiki_agent stop
scripts/llama_server stop
```

Verify nothing is left running:

```bash
scripts/dashboard status
scripts/wiki_agent status
scripts/llama_server status
```
