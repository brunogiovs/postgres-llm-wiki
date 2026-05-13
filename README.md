# PostgreSQL Engine Wiki

An LLM-maintained knowledge base for PostgreSQL engine internals, built with version-pinned raw source evidence.

## Overview

This repository documents PostgreSQL internals through source-cited wiki pages. Every behavioral claim should cite the matching PostgreSQL checkout under `raw/postgres-NN/`; uncertainty is preserved under `Open Questions`.

This wiki is based on the LLM wiki concept from [Andrej Karpathy's gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), adapted for maintaining technical documentation with version-pinned source evidence.

## Supported Versions

| Version | Status | Branch |
|---------|--------|--------|
| 18 | Primary | `REL_18_STABLE` |
| 12 | Legacy | `REL_12_STABLE` |

See [[wiki/versions]] for exact pinned commits.

## Getting Started

1. Bootstrap the environment: `./bootstrap_venv`
2. Activate the venv: `source .wiki-runtime/venv/bin/activate`
3. Read [AGENTS.md](AGENTS.md) before making wiki changes.
4. Run wiki maintenance commands through the project venv.

## Project Structure

- `wiki/`: Wiki content
- `raw/`: PostgreSQL source checkouts
- `scripts/`: Tooling scripts
- `.wiki-runtime/`: Generated artifacts and venv

## More Information

- [The Idea](idea.md): The core concept behind LLM-maintained wikis
- [Implementation Plan](postgresql-engine-wiki-plan.md): Detailed technical specifications and setup

Agents should read [AGENTS.md](AGENTS.md) before making wiki changes.

## Question in Focus

follow AGENTS.md. Question: in PostgreSQL 12, produce a comprehensive  analysis  on how foreign key joins are optimized by  query planner in cases of sql that joins two tables.
