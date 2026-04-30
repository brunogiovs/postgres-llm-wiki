# Wiki Maintainer Agent Operations

This page explains how to run the local agent process that maintains the PostgreSQL engine wiki.

The chosen lifecycle model is: `scripts/wiki_agent` starts Hermes, and Hermes starts or connects to the local LLM backend. The wrapper does not start a separate model server process on its own.

The repository now has a lifecycle wrapper:

```bash
scripts/wiki_agent start
scripts/wiki_agent status
scripts/wiki_agent logs --lines 80
scripts/wiki_agent stop
```

## Runtime Layout

All agent runtime state stays inside the project:

- `.wiki-runtime/hermes/` - agent pid file, command file, local env file, and process logs.
- `.wiki-runtime/logs/` - tool invocation logs.
- `.wiki-runtime/tmp/` - temporary files.
- `.wiki-runtime/cache/` - tool caches.
- `.wiki-runtime/huggingface/`, `.wiki-runtime/ollama/`, and `.wiki-runtime/models/` - local model caches or model files when used.

## Configure The Agent Command

`scripts/wiki_agent` does not hard-code a Hermes command because local installations differ. Configure the Hermes command in one of two ways.

The durable template is `templates/wiki-agent-hermes.env.example`. Copy its contents into `.wiki-runtime/hermes/wiki-agent.env`, then edit the command to match the local Hermes install.

Use a one-shot command:

```bash
scripts/wiki_agent start -- hermes-agent run --project /data/repos/pg-wiki
```

Or put a local command in `.wiki-runtime/hermes/wiki-agent.env`:

```bash
WIKI_AGENT_COMMAND=hermes-agent run --project /data/repos/pg-wiki
```

Then run:

```bash
scripts/wiki_agent start
```

Replace `hermes-agent run --project /data/repos/pg-wiki` with the actual Hermes command used on this machine. That command should include any Hermes flags needed to start or connect to the local LLM.

## Environment Provided To The Agent

The wrapper sets these project-local defaults before starting the command:

```bash
WIKI_RUNTIME=/data/repos/pg-wiki/.wiki-runtime
HERMES_HOME=/data/repos/pg-wiki/.wiki-runtime/hermes
HF_HOME=/data/repos/pg-wiki/.wiki-runtime/huggingface
TRANSFORMERS_CACHE=/data/repos/pg-wiki/.wiki-runtime/huggingface
OLLAMA_MODELS=/data/repos/pg-wiki/.wiki-runtime/ollama/models
XDG_CACHE_HOME=/data/repos/pg-wiki/.wiki-runtime/cache
TMPDIR=/data/repos/pg-wiki/.wiki-runtime/tmp
WIKI_AGENT_WORKDIR=/data/repos/pg-wiki
```

Shell environment variables override values from `.wiki-runtime/hermes/wiki-agent.env`.

## Start

Before starting a long-running agent, check the current wiki state:

```bash
scripts/recent_log --limit 10
scripts/wiki_lint
```

Start the agent:

```bash
scripts/wiki_agent start
```

This starts the configured Hermes command. Hermes is then responsible for the LLM lifecycle.

If no command is configured yet, pass the command after `--`:

```bash
scripts/wiki_agent start -- hermes-agent run --project /data/repos/pg-wiki
```

## Status And Logs

Use status to check the pid file and current command:

```bash
scripts/wiki_agent status
```

Use logs for recent lifecycle events, stdout, and stderr:

```bash
scripts/wiki_agent logs --lines 120
```

## Stop

Stop sends `SIGTERM` to the pid recorded in `.wiki-runtime/hermes/wiki-agent.pid`:

```bash
scripts/wiki_agent stop
```

This stops the Hermes process recorded by the wrapper. Any model process that Hermes started should be cleaned up by Hermes; if Hermes connects to an already-running external model server, that external server is outside this wrapper.

If the process ignores `SIGTERM`, use:

```bash
scripts/wiki_agent stop --force
```

## Restart

Restart stops the current pid and starts the configured command again:

```bash
scripts/wiki_agent restart
```

Or restart with an explicit command:

```bash
scripts/wiki_agent restart -- hermes-agent run --project /data/repos/pg-wiki
```

## Operating Rules

- Run the agent from this project root.
- Treat Hermes as the owner of the LLM lifecycle.
- Keep source evidence under `raw/postgres-NN/`.
- Keep generated state under `.wiki-runtime/`.
- Run `scripts/wiki_lint` after meaningful wiki edits.
- Append durable changes to `wiki/log.md`.
- Keep Hermes tasks narrow: one subsystem, code path, or question at a time.

## Threat Model

`scripts/wiki_agent` runs whatever binary `WIKI_AGENT_COMMAND` points at, with the operator's full uid/gid. The wrapper enforces a few defenses; the rest is on the operator.

What the wrapper enforces:

- `.wiki-runtime/hermes/wiki-agent.env` must not be group- or world-writable. The wrapper refuses to read it otherwise (`chmod 600` to fix).
- Only an allowlisted set of variables is read from `wiki-agent.env`: `WIKI_AGENT_COMMAND`, `WIKI_AGENT_WORKDIR`, `WIKI_RUNTIME`, `HERMES_HOME`, `HF_HOME`, `HF_TOKEN`, `TRANSFORMERS_CACHE`, `OLLAMA_HOST`, `OLLAMA_MODELS`, `XDG_CACHE_HOME`, `TMPDIR`, `CUDA_VISIBLE_DEVICES`. Anything else is logged and ignored, so a tampered env file cannot inject `LD_PRELOAD`, `PATH`, `PYTHONPATH`, etc.
- The pid file records both the pid and the kernel-recorded process start time. `stop` and `status` verify the live start time before signaling, so a stale or tampered pid file cannot redirect `SIGTERM`/`SIGKILL` to an unrelated pid (including a recycled one).
- `wiki-agent.stdout.log` and `wiki-agent.stderr.log` are rotated to `.log.1` once they exceed 50 MiB.

What the operator must own:

- Use an absolute path in `WIKI_AGENT_COMMAND`. Bare names are resolved through `PATH` and can be shadowed by anything earlier in the search path.
- Hermes runs autonomously with shell access to `rg`, `git grep`, file edits, and whatever else its tool surface provides. Treat repository content - PostgreSQL source comments, wiki pages, ingested docs - as a prompt-injection vector. A malicious string in `raw/postgres-NN/` could in principle steer the agent toward exfiltration or unwanted writes.
- The wrapper does not sandbox Hermes. If stronger isolation is needed (network egress, filesystem scope, capabilities), run Hermes inside a container, namespace, or seccomp profile and point `WIKI_AGENT_COMMAND` at that wrapper.
- Hermes stdout/stderr are written to plaintext logs. Do not pass secrets that Hermes might echo (model API keys are fine in env vars; do not paste them on the command line).
- Local model weights from HuggingFace, Ollama, or `models/` are trusted as-is. The wrapper does not verify signatures.
