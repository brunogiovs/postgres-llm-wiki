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

Use the project-local Hermes install and Hermes home:

```bash
export WIKI_RUNTIME="$PWD/.wiki-runtime"
export HERMES_HOME="$WIKI_RUNTIME/hermes"
export HF_HOME="$WIKI_RUNTIME/huggingface"
export TRANSFORMERS_CACHE="$WIKI_RUNTIME/huggingface"
export OLLAMA_MODELS="$WIKI_RUNTIME/ollama/models"
export XDG_CACHE_HOME="$WIKI_RUNTIME/cache"
export TMPDIR="$WIKI_RUNTIME/tmp"
export PATH="$WIKI_RUNTIME/env/node-prefix/bin:$PATH"

.wiki-runtime/env/hermes-agent/bin/hermes dashboard \
  --host localhost \
  --port 9119 \
  --no-open \
  --tui \
  --insecure
```

`--insecure` is required when binding to a non-loopback host (`0.0.0.0`); see the warning under [Remote Access](#remote-access). Drop it (and switch back to `--host 127.0.0.1`) for loopback-only operation.

Open:

```text
http://127.0.0.1:9119
```

`--tui` enables the browser Chat tab. `--no-open` avoids trying to launch a browser from a headless shell.

**`--tui` requires loopback access.** The Chat tab's WebSocket endpoints (`/api/pty`, `/api/ws`) reject any client whose source IP isn't `127.0.0.1` / `::1`, regardless of `--insecure`. If you bind to `0.0.0.0` and access the dashboard from another machine over LAN, the dashboard renders but the Chat tab fails with `WebSocket connection failed` (close code 4403). Two ways out:

- **Use the SSH tunnel** under [Remote Access](#remote-access) — the connection then originates from loopback on the server and the Chat tab works.
- **Drop `--tui`** if you only need the HTTP dashboard surface remotely.

The dashboard auto-builds the React frontend on first launch via `npm`. Node 22 LTS lives at `.wiki-runtime/env/node-prefix/` — the `PATH` export above puts it ahead of any system Node (system `node` 18 is too old for Vite 7). To rebuild manually:

```bash
cd .wiki-runtime/hermes-agent/web && npm install && npm run build
```

## Status And Stop

```bash
HERMES_HOME="$PWD/.wiki-runtime/hermes" \
  .wiki-runtime/env/hermes-agent/bin/hermes dashboard --status

HERMES_HOME="$PWD/.wiki-runtime/hermes" \
  .wiki-runtime/env/hermes-agent/bin/hermes dashboard --stop
```

## Remote Access

Keep the dashboard bound to `127.0.0.1`. If accessing from another machine, use an SSH tunnel:

```bash
ssh -L 9119:127.0.0.1:9119 <user>@<host>
```

Then open `http://127.0.0.1:9119` locally. The tunnel is also the only way to use `--tui` from a remote machine, since the Chat tab's WebSocket is hard-gated to loopback clients.

Only use `--insecure` (and `--host 0.0.0.0`) when deliberately exposing the dashboard on a trusted network. The dashboard can manage config and credentials, so prefer the SSH tunnel above unless LAN exposure is genuinely intended. Note that `--insecure` opens the HTTP surface but does **not** unlock the `--tui` Chat WebSocket — that gate is independent.

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

1. `hermes dashboard --stop` — Hermes dashboard (browser UI + Chat tab).
2. `scripts/wiki_agent stop` — wiki agent gateway started via the lifecycle wrapper.
3. `scripts/llama_server stop` — local llama.cpp server.

Manual equivalents, if you need to run a single step:

```bash
HERMES_HOME="$PWD/.wiki-runtime/hermes" \
  .wiki-runtime/env/hermes-agent/bin/hermes dashboard --stop
scripts/wiki_agent stop
scripts/llama_server stop
```

Verify nothing is left running:

```bash
HERMES_HOME="$PWD/.wiki-runtime/hermes" \
  .wiki-runtime/env/hermes-agent/bin/hermes dashboard --status
scripts/wiki_agent status
scripts/llama_server status
```
