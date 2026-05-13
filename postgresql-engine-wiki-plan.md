# PostgreSQL Engine LLM Wiki Implementation Plan

## Purpose

Build an LLM-maintained wiki for PostgreSQL engine internals. Durable prose is backed by pinned PostgreSQL checkouts under `raw/postgres-NN/`.

## Authority

[AGENTS.md](AGENTS.md) is the source of truth for agent behavior. This plan records the current project shape and rebuild path. If this plan and `AGENTS.md` conflict, follow `AGENTS.md` and update this plan.

Update this plan when the repository structure, supported workflows, or user-facing tooling changes. Do not keep stale workflow steps for scripts or tools that are no longer part of `AGENTS.md`.

## Core Goals

- Explain PostgreSQL internals through durable Markdown pages.
- Tie every behavioral claim to pinned PostgreSQL evidence.
- Treat PostgreSQL implementation source as primary evidence.
- Allow PostgreSQL documentation and tests from the same pinned checkout as evidence for documented or tested behavior.
- Preserve uncertainty under `## Open Questions` instead of inventing intent.

## Repository Structure

```text
.wiki-runtime/
  venv/                      # Project-local Python virtual environment
  cache/                     # Project-local tool caches
  logs/                      # Project-local tool logs

raw/
  postgres-18/
  postgres-12/

wiki/
  index.md
  overview.md
  versions.md
  log.md
  v18/index.md
  v12/index.md
  v12/questions/

requirements.txt             # Pinned Python deps for the project venv

scripts/
  bootstrap_venv             # creates .wiki-runtime/venv
  recent_log                 # prints recent wiki/log.md entries
  wiki_lint                  # wiki health checks
  wiki_tooling.py            # shared helpers for local scripts
```

Top-level `run_*` files are local launcher scripts. They stay ignored and are not part of wiki maintenance unless the user explicitly names one.

## Evidence Scope

Use only the target version's pinned checkout under `raw/postgres-NN/` as factual evidence for PostgreSQL behavior.

Allowed evidence from the matching checkout:

- implementation source files;
- in-tree PostgreSQL documentation;
- in-tree PostgreSQL tests;
- source history from the same checkout.

Implementation source wins when it conflicts with documentation or tests. Record the discrepancy under `## Open Questions`.

Do not use model memory, external websites, package documentation outside this repository, or uncited prior wiki prose as factual support.

## Version Strategy

- `wiki/versions.md` is the source pin manifest.
- Each supported version has a pinned checkout under `raw/postgres-NN/`.
- Each supported version has a landing page at `wiki/vNN/index.md`.
- New answers default to the primary version unless the user specifies another version.
- Source citations must use the matching `raw/postgres-NN/` path.

`wiki/versions.md` keeps the supported-version table with columns:

```text
Version | Status | Wiki Home | Branch | Pinned Commit | Coverage
```

## Page Rules

- Keep version-local pages under `wiki/vNN/`.
- Question pages are pinned to a single version.
- Every behavioral claim needs a matching raw citation.
- Unverified managed pages must show `(unverified)` in the visible title and index or landing-page link text.
- Follow the tone and readability rules in [AGENTS.md](AGENTS.md): lead with the answer, use plain language, write short sentences, prefer active voice, and name conditions precisely.

New question pages use front matter in this order:

```yaml
type: question
version: NN
pinned_commit: abc123...
verified: false
verified_by_agent: not yet
```

## Reading Protocol

Before writing or editing wiki content, the agent must:

- read `wiki/versions.md`;
- read `wiki/index.md`;
- read the most recent ~20 entries of `wiki/log.md`;
- read the relevant `wiki/vNN/index.md` before editing version-local pages;
- use the matching `raw/postgres-NN/` checkout as the evidence base.

Treat `wiki/versions.md`, `wiki/index.md`, `wiki/log.md`, and version landing pages as navigation and bookkeeping context only.

## Deep Inquiry Default

All user questions, reports, and filed answers run in deep-inquiry mode unless the user explicitly asks for a quick answer.

For each question:

- Confirm the target PostgreSQL version.
- Locate the primary source files and symbols.
- Inspect adjacent callers, callees, structs, macros, includes, generated headers visible in raw source, reverse include users, relevant tests, docs, catalogs, grammar, error paths, GUC definitions, and extension/contrib boundaries.
- If evidence lookup errors or cannot produce trustworthy output, stop and report the target version and error.
- Inspect file or symbol history when intent matters or when a regression/change claim is being made.
- Draft from a claim-to-source evidence map.
- Move unresolved claims under `## Open Questions`.

Minimum depth for an engine-internals answer: normal path, relevant error or edge path, key data structures, caller/callee boundary, build or generated-header implications visible from raw source, and tests or explicit test absence.

## Citation Discipline

- Cite source paths and symbols for every behavioral claim.
- Mandatory citation shape: `[[raw/postgres-NN/src/backend/executor/execMain.c#ExecutorRun]]`.
- For non-Markdown files include the full file extension.
- Cite from the `raw/postgres-NN/` checkout matching the page's `version:`.
- Use aliases when useful: `[[raw/postgres-NN/path/file.c#symbol|file.c#symbol]]`.
- If a claim is not backed by a source file, symbol, test file, documentation page, commit, or saved design discussion, do not write it as fact.

## Verification Fields

Pages carry two verification fields:

- `verified:` is human-verified. Only a human reviewer may set, change, or remove it.
- `verified_by_agent:` is agent-verified. Agents may set or update it only after re-checking every claim against the pinned raw source.

Rules:

- New question pages set `verified: false` and `verified_by_agent: not yet`.
- Do not set `verified_by_agent:` if any claim cannot be verified.
- Unverified managed wiki documents must show `(unverified)` until a human sets `verified: true`.
- `verified_by_agent` must be either `not yet` or `<LLM-model-name> | YYYY-MM-DD HH:MM`.

## GUC Configuration Changes

Whenever a wiki page suggests changing a GUC, state whether the change requires restart, reload, or only session/transaction scope.

Determine the requirement from the GUC context in the pinned raw source or from a validated `pg_settings` definition in the same version:

- `postmaster` -> restart required;
- `sighup` -> reload;
- `superuser`, `user`, or `backend` -> session or transaction scope.

## Production SQL Snippets

Whenever a wiki page proposes SQL intended to run against production:

- Verify syntax, referenced catalogs, columns, functions, and GUCs against the pinned checkout.
- Recommend reasonable session-scoped `statement_timeout` and `lock_timeout` values.
- Add an inline block-comment tag immediately after the leading verb.

```sql
SELECT /* wiki_capture_plan_inputs */ ...;
UPDATE /* wiki_backfill_user_email */ users SET ...;
```

## Bookkeeping

After every meaningful wiki change:

- update `wiki/index.md` when a page is created or substantially changed;
- update `wiki/versions.md` when a supported version is added, removed, archived, re-pinned, or has a meaningful coverage change;
- update the relevant `wiki/vNN/index.md` when version-local pages are created or substantially changed;
- append an entry to `wiki/log.md` after each scaffold change, ingest, lint pass, filed answer, or version lifecycle event.

Log entry headings use one of these forms:

```md
## [YYYY-MM-DD] <kind> v<NN> | <subject>
## [YYYY-MM-DD] <kind> | <subject>
```

## Workflows

### Add A Supported Version

1. Add the source checkout under `raw/postgres-NN/`.
2. Pin the checkout to an exact commit.
3. Add the version to `wiki/versions.md`.
4. Create `wiki/vNN/index.md`.
5. Create `wiki/vNN/questions/` only when a filed answer needs it.
6. Update `wiki/index.md`.
7. Append to `wiki/log.md`.

### Answer And File

1. Determine the target version. Default to the primary version if the user does not specify one.
2. Build a source envelope from the pinned `raw/postgres-NN/` checkout.
3. Check relevant callers, callees, structs, macros, includes, tests, docs, catalogs, grammar, error paths, GUC definitions, and extension boundaries.
4. Draft from a claim-to-source evidence map.
5. Put gaps under `## Open Questions`.
6. File the answer and update indexes/log.
7. Apply the tone and readability rules from [AGENTS.md](AGENTS.md) before filing.

### Lint The Wiki

Use project-local scripts from the venv:

```bash
scripts/recent_log --limit 20
scripts/wiki_lint
```

The lint pass checks broken links, orphan pages, missing source references, stale version pins, wrong-version citations, invalid verification fields, unverified title hints, and version landing pages missing links.

## Environment Isolation

- Run Python scripts from `.wiki-runtime/venv/`.
- If the venv is missing, run `scripts/bootstrap_venv`.
- Pin new Python dependencies in `requirements.txt`.
- Do not install Python packages globally, with `--user`, via `pipx`, or with `sudo`.
- Read and write only inside this repository.
- Treat `raw/postgres-NN/` checkouts as read-only evidence.
- Keep generated artifacts, caches, and the venv under `.wiki-runtime/`.
- Network access is allowed only for `scripts/bootstrap_venv` or source-fetch work the user explicitly requests.

## Script Changes

- Keep durable project tooling under `scripts/`.
- Keep project-local runtime state under `.wiki-runtime/`.
- When changing script contents, update adjacent workflow examples, lint examples, or tests that depend on the changed behavior.
- Do not document or preserve workflows that are absent from `AGENTS.md`.

## First Useful Milestone

- Supported versions are pinned in `wiki/versions.md`.
- Each supported version has a `raw/postgres-NN/` checkout.
- Pinned checkout evidence is the primary evidence base.
- Wiki answers cite raw source paths and symbols.
- `scripts/wiki_lint` passes.

## Version Control

- Never commit or push without asking for permission.
