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
- `.wiki-runtime/hermes-agent/` - project-local Hermes Agent source checkout.
- `.wiki-runtime/env/hermes-agent/` - project-local Hermes Agent Python virtual environment.
- `.wiki-runtime/hermes-agent/venv` - symlink to `.wiki-runtime/env/hermes-agent/` for Hermes diagnostics.
- `.wiki-runtime/env/uvprefix/` - project-local `uv` installation used to create and maintain the Hermes virtual environment.
- `.wiki-runtime/llama/` - local llama.cpp server pid and command metadata.
- `.wiki-runtime/logs/` - tool invocation logs.
- `.wiki-runtime/tmp/` - temporary files.
- `.wiki-runtime/cache/` - tool caches.
- `.wiki-runtime/huggingface/`, `.wiki-runtime/ollama/`, and `.wiki-runtime/models/` - local model caches or model files when used.

## Project-Local Hermes Install

Hermes is installed inside `.wiki-runtime/`, not as a global command:

```bash
.wiki-runtime/env/hermes-agent/bin/hermes --help
.wiki-runtime/env/hermes-agent/bin/hermes doctor
```

The current local checkout is `NousResearch/hermes-agent` at commit `285e9efb3f2251f09cfbc9acb335c3d943d5a7b2`; the installed package version is `0.11.0`.

Bundled Hermes skills are synced into `.wiki-runtime/hermes/skills/`, using `.wiki-runtime/hermes/` as `HERMES_HOME`.

`.wiki-runtime/hermes/.env` is created from Hermes' example with `0600` permissions. Put provider keys or local endpoint settings there, or run the local setup command:

```bash
HERMES_HOME=/data/repos/pg-wiki/.wiki-runtime/hermes .wiki-runtime/env/hermes-agent/bin/hermes setup
```

### Project-Local PDF Export Skills

The project-local Hermes home includes `markdown-pdf` at `.wiki-runtime/hermes/skills/productivity/markdown-pdf/`. It converts Markdown files to PDFs with:

```bash
.wiki-runtime/env/hermes-agent/bin/python \
  .wiki-runtime/hermes/skills/productivity/markdown-pdf/scripts/md_to_pdf.py \
  input.md output.pdf
```

It also includes `html-pdf` at `.wiki-runtime/hermes/skills/productivity/html-pdf/`. It converts document-style HTML files to PDFs with:

```bash
.wiki-runtime/env/hermes-agent/bin/python \
  .wiki-runtime/hermes/skills/productivity/html-pdf/scripts/html_to_pdf.py \
  input.html output.pdf
```

The Markdown converter depends on `markdown-it-py` and `reportlab`; the HTML converter uses Python's standard HTML parser plus `reportlab`. `reportlab` pulls in `pillow`. Keep these dependencies in the project-local Hermes runtime rather than installing them globally.

## Local LLM Configuration

Hermes is configured to use a project-local custom provider named `pgwiki-local`, backed by `/data/ollamacpp/llama.cpp/build/bin/llama-server`:

```yaml
model:
  default: pgwiki-local
  provider: pgwiki-local
  base_url: http://127.0.0.1:8080/v1
  api_key: no-key-required
  api_mode: chat_completions
  context_length: 131072
```

The local server wrapper starts llama.cpp with alias `pgwiki-local`, a 128K context target, and the project-local model `.wiki-runtime/models/qwen3.5-9b-gguf/Qwen_Qwen3.5-9B-Q6_K.gguf`. This is the GGUF `Q6_K` variant of `Qwen/Qwen3.5-9B`, kept under this repository instead of another project's model directory. Override these with `LLAMA_MODEL`, `LLAMA_CTX_SIZE`, `LLAMA_PORT`, or `LLAMA_EXTRA_ARGS` when needed.

The default KV cache type is `q4_0` for both keys and values so the 9B `Q6_K` model can fit the 128K target on the expected 16 GB GPU profile. If startup fails due to VRAM pressure, reduce `LLAMA_CTX_SIZE` before changing to a smaller model.

Qwen3.5 thinking mode is disabled by default with `--reasoning off` and `--chat-template-kwargs '{"enable_thinking":false}'`, so normal chat completions return answer text instead of spending tokens in `reasoning_content`. Override with `LLAMA_REASONING` or `LLAMA_CHAT_TEMPLATE_KWARGS` for experiments.

Use:

```bash
scripts/llama_server start
scripts/llama_server status
scripts/llama_server logs --lines 80
scripts/llama_server stop
```

The endpoint can be checked with:

```bash
curl http://127.0.0.1:8080/v1/models
```

If a different local server is used, keep the endpoint OpenAI-compatible and update `.wiki-runtime/hermes/config.yaml` so `model.base_url` and `providers.pgwiki-local.base_url` point at that server.

## Configure The Agent Command

`scripts/wiki_agent` does not hard-code a Hermes command because local installations differ. Configure the Hermes command in one of two ways.

The durable template is `templates/wiki-agent-hermes.env.example`. Copy its contents into `.wiki-runtime/hermes/wiki-agent.env`, then edit the command if the local Hermes install path changes.

Use a one-shot command:

```bash
scripts/wiki_agent start -- /data/repos/pg-wiki/.wiki-runtime/env/hermes-agent/bin/hermes gateway run --replace
```

Or put a local command in `.wiki-runtime/hermes/wiki-agent.env`:

```bash
WIKI_AGENT_COMMAND=/data/repos/pg-wiki/.wiki-runtime/env/hermes-agent/bin/hermes gateway run --replace
```

Then run:

```bash
scripts/wiki_agent start
```

Replace the command only if the local Hermes path changes. That command should include any Hermes flags needed to start or connect to the local LLM.

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
scripts/llama_server status
```

Start the local llama.cpp server if it is not already running:

```bash
scripts/llama_server start
```

Start the agent:

```bash
scripts/wiki_agent start
```

This starts the configured Hermes command. Hermes is then responsible for the LLM lifecycle.

If no command is configured yet, pass the command after `--`:

```bash
scripts/wiki_agent start -- /data/repos/pg-wiki/.wiki-runtime/env/hermes-agent/bin/hermes gateway run --replace
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

## Clear Saved Sessions

Hermes conversation sessions are kept under `.wiki-runtime/hermes/sessions/` and in the `sessions` / `messages` tables of `.wiki-runtime/hermes/state.db`. List both with:

```bash
scripts/hermes_sessions list
```

Preview a cleanup:

```bash
scripts/hermes_sessions clear
```

Delete all saved session files:

```bash
scripts/hermes_sessions clear --yes
```

This deletes session files, purges session/message rows from `state.db`, resets the message autoincrement sequence, checkpoints the WAL, and vacuums the database while leaving schema and non-session metadata intact.

Deletion refuses to run while `scripts/wiki_agent` reports a live pid. Stop the agent first, or pass `--force` if the pid check is stale. Dry runs are allowed while the agent is live.

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
scripts/wiki_agent restart -- /data/repos/pg-wiki/.wiki-runtime/env/hermes-agent/bin/hermes gateway run --replace
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
