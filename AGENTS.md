# PostgreSQL Engine Wiki Agent Instructions

This repository is an LLM-maintained wiki for PostgreSQL engine internals. The agent writes and maintains the wiki; raw source material is treated as evidence.

## Read Before Writing

- Read `wiki/versions.md` first to identify supported PostgreSQL versions and the primary version.
- Read `wiki/index.md` before modifying or answering from the wiki.
- Read the last ~20 entries of `wiki/log.md` to understand recent activity.
- For version-specific work, read the relevant `wiki/vNN/index.md` before editing version-local pages.
- Search the PostgreSQL source tree before making any technical claim.

## Citation Discipline

- Cite source paths and symbols for every behavioral claim.
- Preferred citation shape: `src/backend/executor/execMain.c:ExecutorRun`.
- Cite from the `raw/postgres-NN/` checkout matching the page's `version:`.
- Shared concept pages may cite version examples through `verified_against:`.
- If a claim is not backed by a source file, symbol, documentation page, commit, or saved design discussion, do not write it as fact.
- Put uncertainty under `## Open Questions` instead of guessing.
- Never paraphrase code in a way that adds behavior the code does not exhibit.

## Version Awareness

- `wiki/versions.md` is the top-level version index and source pin manifest.
- Each supported version has a landing page at `wiki/vNN/index.md`.
- Default new ingests, traces, and answers to the primary version unless the user specifies another.
- If the user asks without naming a version, assume the primary version and state that assumption before answering.
- Never answer about one PostgreSQL version using citations from another version's checkout.
- Question pages are pinned to a single version. Filing the same question against another version creates a new question page.

## Wiki Structure

- Keep version-specific pages under `wiki/vNN/`.
- Keep genuinely cross-version concept theory under `wiki/shared/concepts/`.
- Use Obsidian-style links, such as `[[versions]]` and `[[v17/code-paths/simple-select-query]]`.
- Include the version segment for links into per-version directories.
- Prefer code-path pages over vague subsystem summaries.
- A page is born when the work justifies it. Do not create empty content stubs.
- A concept earns its own page when it is referenced from at least two other pages or repeatedly in conversation.

## Project-Local Dependency Policy

All wiki-specific dependencies must run from, and store state inside, this project directory.

- Run wiki tooling from the project root.
- Store PostgreSQL source checkouts under `raw/postgres-NN/`.
- Store runtime state under `.wiki-runtime/`.
- Store local tool environments under `.wiki-runtime/env/`.
- Store Hermes Agent config, state, and logs under `.wiki-runtime/hermes/`.
- Store model files or model-manager caches under `.wiki-runtime/models/`, `.wiki-runtime/ollama/`, or `.wiki-runtime/huggingface/`.
- Store generated ctags, search, tree-sitter, and documentation indexes under `.wiki-runtime/indexes/`.
- Store temporary files under `.wiki-runtime/tmp/`.
- Store run logs under `.wiki-runtime/logs/`.
- Do not rely on global caches, global virtualenvs, global Hermes state, global model stores, external source checkouts, or global source indexes for normal operation.
- If a system-level prerequisite is unavoidable, such as the NVIDIA driver, CUDA runtime, Docker, or a system package manager, document it separately and keep all wiki-specific config inside this repository.

Recommended environment when running local tooling:

```bash
export WIKI_RUNTIME="$PWD/.wiki-runtime"
export HERMES_HOME="$WIKI_RUNTIME/hermes"
export HF_HOME="$WIKI_RUNTIME/huggingface"
export TRANSFORMERS_CACHE="$WIKI_RUNTIME/huggingface"
export OLLAMA_MODELS="$WIKI_RUNTIME/ollama/models"
export XDG_CACHE_HOME="$WIKI_RUNTIME/cache"
export TMPDIR="$WIKI_RUNTIME/tmp"
```

## Local Model Operating Mode

The expected local hardware profile is a 16GB NVIDIA GPU with Hermes Agent orchestrating a local model.

Default local model target:

- `Qwen2.5-Coder-14B-Instruct-AWQ`, or another 4-bit 14B coder model.

Context target:

- Minimum: 64K tokens for Hermes multi-step workflows when feasible.
- Preferred: 64K to 128K if the serving stack and VRAM allow it.
- If 64K does not fit reliably, reduce task scope before accepting a tiny context window.

Operating rules:

- Trace one code path, subsystem slice, or question at a time.
- Prefer `rg`, `git grep`, and short source excerpts over loading entire directories into context.
- Do not ingest a large subsystem in one pass unless a stronger hosted model is being used.
- Treat generated pages as drafts until their source references are checked.
- Use active-version verification sparingly.
- Defer active-version verification explicitly on `wiki/vNN/index.md` when it exceeds the local context or latency budget.
- Escalate hard traces, such as planner internals, WAL, crash recovery, or MVCC visibility, when the local model cannot keep the call chain straight.

## Agent Lifecycle

Use the project-local lifecycle wrapper to run the wiki maintainer process:

```bash
scripts/wiki_agent start
scripts/wiki_agent status
scripts/wiki_agent logs --lines 80
scripts/wiki_agent stop
```

`scripts/wiki_agent` stores pid files, command metadata, local environment, and process logs under `.wiki-runtime/hermes/`. The chosen lifecycle model is that the wrapper starts Hermes, and Hermes starts or connects to the local LLM backend. Configure the real Hermes command with `WIKI_AGENT_COMMAND` or by passing it after `--`, for example:

```bash
scripts/wiki_agent start -- hermes-agent run --project /data/repos/pg-wiki
```

See [[operations/agent]] for the full start/stop runbook.

## Bookkeeping

Do these after every meaningful wiki change:

- Update `wiki/index.md` whenever a page is created or substantially changed.
- Update `wiki/versions.md` whenever a supported version is added, removed, archived, re-pinned, or has a meaningful coverage change.
- Update the relevant `wiki/vNN/index.md` whenever version-local pages are created or substantially changed.
- Append an entry to `wiki/log.md` after each scaffold change, ingest, trace, lint pass, filed answer, or version lifecycle event.

Log entry prefix:

```md
## [YYYY-MM-DD] <kind> v<NN> | <subject>
```

For version-agnostic work:

```md
## [YYYY-MM-DD] <kind> | <subject>
```

## Core Workflows

### Add A Supported Version

1. Add the source checkout under `raw/postgres-NN/`.
2. Pin the checkout to an exact commit.
3. Add the version to `wiki/versions.md`.
4. Create `wiki/vNN/index.md`.
5. Create `wiki/vNN/subsystems/`, `wiki/vNN/concepts/`, `wiki/vNN/code-paths/`, `wiki/vNN/files/`, and `wiki/vNN/questions/`.
6. Update `wiki/index.md`.
7. Append to `wiki/log.md`.

### Ingest A Subsystem

1. Read `wiki/versions.md` and select the primary version unless the user specified another.
2. Read `wiki/vNN/index.md`.
3. Search relevant source files under `raw/postgres-NN/`.
4. Create or update `wiki/vNN/subsystems/<name>.md`.
5. Create concept pages only when justified by repeated use.
6. Update `wiki/vNN/index.md`, `wiki/index.md`, and `wiki/log.md`.

### Trace A Code Path

1. Start from the target version's pinned source checkout.
2. Use source search to follow calls through the engine.
3. Record the flow under `wiki/vNN/code-paths/`.
4. Link related subsystem and concept pages.
5. Mark uncertain behavior under `Open Questions`.
6. Update indexes and log.

### Answer And File

1. Assume the primary version unless the user specifies another.
2. Search `wiki/versions.md`, the relevant version landing page, and `wiki/index.md`.
3. Search source evidence under `raw/postgres-NN/`.
4. Answer with citations.
5. File durable answers as question pages or fold them into existing pages.
6. Update indexes and log.

### Lint The Wiki

Check for:

- Broken Obsidian links.
- Orphan pages.
- Pages without source references.
- Version-local pages with missing or stale `version:` / `pinned_commit:`.
- Shared concept pages with stale `verified_against:`.
- Pages citing source from the wrong version checkout.
- Version landing pages missing links to existing version-local pages.
- `wiki/versions.md` coverage notes that disagree with actual pages.

Use the project-local scripts first:

```bash
scripts/recent_log --limit 20
scripts/wiki_lint
scripts/source_lookup --symbol ExecutorRun
scripts/source_lookup --path src/backend/executor/execMain.c
scripts/version_diff --from 18 --to 17 --path src/backend/executor/execMain.c
scripts/wiki_agent status
```

`scripts/source_lookup` defaults to the primary version in `wiki/versions.md`. `scripts/version_diff` requires both source checkouts to exist under `raw/postgres-NN/`. Tool caches, logs, and temporary diffs must stay under `.wiki-runtime/`.
