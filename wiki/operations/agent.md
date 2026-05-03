---
title: Wiki Maintainer Agent Runbook
---

# Wiki Maintainer Agent

Project-local Hermes + llama.cpp setup for LLM-maintained PostgreSQL wiki.

## Lifecycle (scripts/wiki_agent)

```
scripts/wiki_agent start
scripts/wiki_agent status
scripts/wiki_agent logs --lines 80
scripts/wiki_agent stop
```

- Stores pid/command/env/logs locally.
- Launches `WIKI_AGENT_COMMAND` (default: `agent run --project /data/repos/pg-wiki`).
- Hermes-managed LLM: agent → Hermes gateway → pgwiki-local (llama.cpp).
- Refuses unsafe .env (writable/group vars filtered).
- Pid validation by start time; log rotation at 50MiB.

## Local LLM Backend (scripts/llama_server)

```
scripts/llama_server start
scripts/llama_server status
scripts/llama_server logs
scripts/llama_server stop
```

- Default: `.wiki-runtime/models/qwen3.5-9b-gguf/Qwen_Qwen3.5-9B-Q6_K.gguf` (pgwiki-local alias).
- OpenAI-compatible `/v1` at 127.0.0.1:8080.
- Context: 131k tokens.
- `--reasoning off` / `enable_thinking: false` default.

## Hermes Runtime

- Install: `.wiki-runtime/hermes-agent/` (NousResearch/hermes-agent@285e9efb).
- Config: `.wiki-runtime/hermes/config.yaml` → pgwiki-local provider.
- Env: `.wiki-runtime/hermes/wiki-agent.env` (from template).
- Skills: `.wiki-runtime/hermes/skills/` (bundled + project-local html-pdf, markdown-pdf).
- Sessions: `scripts/hermes_sessions clear --yes`.
- Dashboard: `scripts/dashboard start` (Tailscale-exposed).

## Threat Model

- Env allowlist: WIKI_AGENT_COMMAND + model/cache vars.
- Pid tamper-proof.
- Session purge keeps schema.

See AGENTS.md (#local-model-operating-mode, #agent-lifecycle).
