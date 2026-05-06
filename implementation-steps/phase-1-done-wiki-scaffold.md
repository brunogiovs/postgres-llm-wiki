# Phase 1 Done: Wiki Scaffold

## Status

Done on 2026-04-30.

## Goal

Create the version-agnostic wiki structure and the agent rules that will keep future pages disciplined, source-backed, and version-aware.

## Inputs

- `postgresql-engine-wiki-plan.md`
- Existing `idea.md`
- Chosen local operating profile:
  - Hermes Agent
  - 16GB NVIDIA GPU
  - default local model: `Qwen2.5-Coder-14B-Instruct-AWQ` or another 4-bit 14B coder model
  - target context: 64K tokens when feasible

## Create Files and Directories

```text
 .wiki-runtime/
   env/
   models/
   huggingface/
   indexes/
    ctags/
    search/
    tree-sitter/
  cache/
  logs/
  tmp/

wiki/
  index.md
  log.md
  overview.md
  versions.md
  diagrams/

templates/
  subsystem.md
  file.md
  question.md

AGENTS.md
```

Do not create per-version directories yet. Those are created during Phase 2 when a PostgreSQL version is added.

`.wiki-runtime/` is for project-local runtime dependencies and generated state. It should normally be ignored by git. The durable wiki content lives in `wiki/`, `templates/`, `scripts/`, `AGENTS.md`, and the plan files.

## Tasks

1. Create the base `wiki/` directory structure.
2. Create the `.wiki-runtime/` directory structure for local dependencies, caches, indexes, logs, model state, and temporary files.
3. If the repo uses git, add `.wiki-runtime/` to `.gitignore`.
4. Create `wiki/index.md` as the global catalog.
5. Create `wiki/log.md` as an append-only activity log.
6. Create `wiki/overview.md` as the cross-version architecture entry point.
7. Create `wiki/versions.md` as the main version index.
8. Create page templates with the front matter defined in the plan.
9. Create `AGENTS.md` with the maintenance rules from the plan.
10. Add the local-model operating profile to `AGENTS.md`.
11. Add the project-local dependency policy to `AGENTS.md`.
12. Add an initial log entry for scaffold creation.

## Required `wiki/versions.md` Shape

```md
# PostgreSQL Versions

This page indexes the PostgreSQL versions covered by the wiki.

| Version | Status | Wiki Home | Branch | Pinned Commit | Coverage |
|---|---|---|---|---|---|

## Archived Versions

| Version | Removed On | Reason |
|---|---|---|
```

## Required Log Entry Shape

```md
## [YYYY-MM-DD] scaffold | initialized wiki structure

- Created version-agnostic wiki files.
- Created templates.
- Created AGENTS.md.
```

## Local Model Rules To Include In `AGENTS.md`

- Trace one subsystem slice or question at a time.
- Prefer `rg`, `git grep`, and short source excerpts over loading entire directories.
- Do not ingest a large subsystem in one pass with the 16GB local model.
- Treat generated pages as drafts until source references are checked.
- Defer active-version verification explicitly when it exceeds local context or latency budget.
- Escalate hard traces to a stronger model when the local model cannot keep the call chain straight.

## Project-Local Dependency Rules To Include In `AGENTS.md`

- Run wiki tooling from the project root.
- Store all wiki-specific runtime state under `.wiki-runtime/`.
- Store PostgreSQL source checkouts under `raw/postgres-NN/`.
- Store generated indexes under `.wiki-runtime/indexes/`.
- Store Hermes Agent config, state, and logs under `.wiki-runtime/hermes/`.
- Store model caches under `.wiki-runtime/models/`, `.wiki-runtime/ollama/`, or `.wiki-runtime/huggingface/`.
- Do not rely on global caches, global virtualenvs, global Hermes state, or global source indexes.
- Document unavoidable system prerequisites, but keep project-specific config and generated files inside the repo.

## Recommended Runtime Environment

When running Hermes Agent, model servers, or helper scripts from the project root:

```bash
export WIKI_RUNTIME="$PWD/.wiki-runtime"
export HERMES_HOME="$WIKI_RUNTIME/hermes"
export HF_HOME="$WIKI_RUNTIME/huggingface"
export TRANSFORMERS_CACHE="$WIKI_RUNTIME/huggingface"
export OLLAMA_MODELS="$WIKI_RUNTIME/ollama/models"
export XDG_CACHE_HOME="$WIKI_RUNTIME/cache"
export TMPDIR="$WIKI_RUNTIME/tmp"
```

## Definition Of Done

- The base wiki exists.
- `.wiki-runtime/` exists and is reserved for project-local dependencies and generated runtime state.
- `wiki/versions.md` is present and ready to index PostgreSQL versions.
- `AGENTS.md` contains source citation, version awareness, bookkeeping, local-model rules, and project-local dependency rules.
- Templates exist for every page type.
- `wiki/log.md` records the scaffold creation.
