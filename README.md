# PostgreSQL Engine Wiki

An LLM-maintained knowledge base for PostgreSQL engine internals, built with version-pinned raw source evidence.

## Overview

This repository documents PostgreSQL internals through source-cited wiki pages. Every behavioral claim should cite the matching PostgreSQL checkout under `raw/postgres-NN/`; uncertainty is preserved under `Open Questions`.

Source navigation is graph-first:

- `scripts/source_graph` generates a per-version Graphify graph under `.wiki-runtime/graph/postgres-NN/`.
- `scripts/source_graph_query` is the single source query surface for agents. Its raw subcommands read `raw/postgres-NN/` directly, and its graph subcommands query `graph.json`.
- If a graph subcommand needs `graph.json` and it is absent, `scripts/source_graph_query` forces generation via `scripts/source_graph --version NN --refresh`.
- `scripts/source_graph_check` validates generated graph artifacts.

The PyPI package is `graphifyy` (two y's); the CLI it installs is `graphify` (one y). It is pinned in [requirements.txt](requirements.txt) and installed into the project venv by `scripts/bootstrap_venv` — no global or pipx install needed.

## Setup

All Python tooling runs inside a project-local virtual environment under `.wiki-runtime/venv/`. Nothing is installed into the system or user site-packages — not even the Python interpreter.

`scripts/bootstrap_venv` is fully self-contained: it downloads a pinned [`uv`](https://github.com/astral-sh/uv) release into `.wiki-runtime/bin/`, uses it to fetch a managed CPython into `.wiki-runtime/python/`, then creates the venv and installs `requirements.txt`. The only host requirements are a POSIX shell, `curl`, and `tar`. No system Python is needed.

```bash
./scripts/bootstrap_venv                     # creates .wiki-runtime/venv/ and installs requirements.txt
source .wiki-runtime/venv/bin/activate       # activate (one option)
.wiki-runtime/venv/bin/python scripts/<name> # or invoke directly
```

Scripts fail fast with a clear message when run outside the project venv. The bypass `WIKI_ALLOW_SYSTEM_PYTHON=1` exists for emergency use only — the test wrapper sets it because tests run scripts from a synthetic temp repo.

Removing `.wiki-runtime/` is always a safe reset; rerun `scripts/bootstrap_venv` to rebuild (it will re-download `uv` and Python).

## Supported Versions

| Version | Status | Branch |
|---------|--------|--------|
| 18 | Primary | `REL_18_STABLE` |
| 12 | Legacy | `REL_12_STABLE` |

See [[wiki/versions]] for exact pinned commits.

## Project Structure

```text
AGENTS.md                     # Required reading for any agent editing the wiki
LICENCE
requirements.txt              # Pinned Python deps installed into .wiki-runtime/venv/
wiki/                         # Wiki content
  index.md                    # Global wiki catalog
  overview.md                 # Architecture overview
  versions.md                 # Version index and pins
  log.md                      # Activity changelog
  operations/                 # Cross-version operational guidance
  v18/                        # PostgreSQL 18 content
  v12/                        # PostgreSQL 12 content
raw/
  postgres-18/                # PG 18 source checkout, pinned commit
  postgres-12/                # PG 12 source checkout, pinned commit
.wiki-runtime/                # Generated artifacts, tooling, and venv (gitignored)
  bin/                        # Project-local uv binary fetched by bootstrap_venv
  python/                     # Managed CPython interpreter installed by uv
  uv-cache/                   # uv's package and metadata cache
  venv/                       # Project-local Python venv
  graph/postgres-NN/          # Generated Graphify graph artifacts
  cache/, indexes/, logs/, tmp/
templates/                    # Page templates (question, version concept, shared concept)
tests/                        # Tooling tests driven by scripts/test_source_tools
scripts/
  bootstrap_venv              # Create/refresh .wiki-runtime/venv/ and install requirements.txt
  source_graph                # Generate per-version Graphify graphs
  source_graph_query          # Query raw source and Graphify graphs
  source_graph_check          # Validate graph artifacts
  source_update               # Clone/update pinned PostgreSQL source checkouts
  source_rebuild              # Re-clone a checkout pinned to the latest upstream release tag
  version_diff                # Compare source paths across versions
  wiki_lint                   # Wiki health checks
  recent_log                  # Recent wiki activity
  test_source_tools           # End-to-end test wrapper for the source tooling
  wiki_tooling.py             # Shared helpers imported by the scripts above
```

## Source Navigation

Python scripts must run inside the project venv. Either activate it
(`source .wiki-runtime/venv/bin/activate`) or invoke each script via
`.wiki-runtime/venv/bin/python`. The examples below use the explicit form;
they fail fast with a clear message if run outside the venv.

```bash
# Generate or refresh the graph
.wiki-runtime/venv/bin/python scripts/source_graph --version 18 --refresh
# Default generation is local AST-only and does not need an LLM API key
# Optional semantic extraction; requires a configured Graphify backend/API key
.wiki-runtime/venv/bin/python scripts/source_graph --version 18 --refresh --semantic --backend openai

# Raw source queries through the graph script
.wiki-runtime/venv/bin/python scripts/source_graph_query --version 18 symbol ExecutorRun
.wiki-runtime/venv/bin/python scripts/source_graph_query --version 18 symbol '\bExecutorRun\b' --regex --limit 20
.wiki-runtime/venv/bin/python scripts/source_graph_query --version 18 file src/backend/executor/execMain.c --start 1 --limit 80
.wiki-runtime/venv/bin/python scripts/source_graph_query --version 18 log src/backend/executor/execMain.c --limit 20
.wiki-runtime/venv/bin/python scripts/source_graph_query --version 18 includes src/backend/executor/execMain.c --format json
.wiki-runtime/venv/bin/python scripts/source_graph_query --version 18 included-by executor/executor.h --limit 50

# Graph queries; graph.json is generated automatically if absent
.wiki-runtime/venv/bin/python scripts/source_graph_query --version 18 explain ExecutorRun
.wiki-runtime/venv/bin/python scripts/source_graph_query --version 18 path PostgresMain ExecutorRun
.wiki-runtime/venv/bin/python scripts/source_graph_query --version 18 query "show the executor flow" --dfs

# Validate graph artifacts
.wiki-runtime/venv/bin/python scripts/source_graph_check --version 18 --probe-node ExecutorRun
```

Graph output is orientation material. Behavioral claims still need citations into `raw/postgres-NN/`.

## Citation Format

```md
[[raw/postgres-NN/src/backend/executor/execMain.c#ExecutorRun]]
```

## Maintenance

`scripts/test_source_tools` is a bash wrapper that uses the project venv
internally; the Python maintenance scripts must be invoked through the
venv directly.

```bash
.wiki-runtime/venv/bin/python scripts/recent_log --limit 20
.wiki-runtime/venv/bin/python scripts/wiki_lint
./scripts/test_source_tools

# Bump a checkout to the newest upstream release tag (updates wiki/versions.md and wiki/log.md)
.wiki-runtime/venv/bin/python scripts/source_rebuild --version 18
.wiki-runtime/venv/bin/python scripts/source_rebuild --version 18 --dry-run
```

Agents should read [AGENTS.md](AGENTS.md) before making wiki changes.
