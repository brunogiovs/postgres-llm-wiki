# PostgreSQL Engine LLM Wiki Implementation Plan

## Purpose

Build an LLM-maintained wiki for understanding the PostgreSQL engine internals. The wiki should be a persistent, source-backed knowledge base over the PostgreSQL source tree, official documentation, relevant commit history, and selected design discussions.

This is not a wiki generated from a PostgreSQL database. It is a wiki about how PostgreSQL itself works.

## Core Goals

- Explain PostgreSQL internals through durable markdown pages.
- Trace real code paths through the PostgreSQL source tree.
- Keep every technical claim tied to source files, functions, documentation, commits, or mailing-list threads.
- Preserve uncertainty instead of inventing intent.
- Let the wiki compound over time as new subsystems and questions are investigated.

## Non-Goals

- Do not summarize PostgreSQL behavior from memory without source support.
- Do not document user-facing SQL features unless they illuminate engine behavior.
- Do not ingest raw source code into prose indiscriminately; synthesize around concepts, subsystems, and code paths.
- Do not assume behavior is stable across PostgreSQL versions without checking the pinned source version.

## Proposed Repository Structure

The wiki tracks a fixed set of supported PostgreSQL versions and maintains content per version. Pages are born organically — directories are containers, not pre-declared trees.

```text
.wiki-runtime/              # Untracked project-local runtime dependencies and generated state
  env/                      # Python virtualenv or other local tool environments
  hermes/                   # Hermes Agent config, state, and logs for this wiki
  models/                   # Local model files when managed directly by this project
  ollama/                   # Optional project-local Ollama model store
  huggingface/              # Optional project-local Hugging Face cache
  indexes/
    ctags/                  # Generated symbol indexes
    search/                 # Generated markdown/source search indexes
    tree-sitter/            # Generated parser artifacts, if used
  cache/
  logs/
  tmp/

raw/
  postgres-17/              # PG 17 checkout, pinned commit on REL_17_STABLE
  postgres-16/              # PG 16 checkout, pinned commit on REL_16_STABLE
  postgres-15/              # PG 15 checkout, pinned commit on REL_15_STABLE
  postgres-14/              # PG 14 checkout, pinned commit on REL_14_STABLE
  shared/
    docs/                   # papers, official doc snapshots
    mailing-list/           # saved -hackers threads
    commits/                # saved commit messages or release notes
  _archive/
    postgres-NN/            # archived checkouts of removed versions

wiki/
  index.md                  # Global catalog of wiki pages, entries tagged with version
  log.md                    # Global append-only activity log, entries tagged with version
  overview.md               # Cross-version architecture map
  versions.md               # Main version index and supported-versions contract

  shared/
    concepts/               # Version-independent ideas (theory of memory contexts, MVCC, ...)

  v17/
    index.md                # Landing page for the PG 17 wiki
    subsystems/             # Per-version engine areas (parser, planner, wal, ...)
    concepts/               # Concepts whose behavior differs enough to be version-specific
    code-paths/             # Per-version traces of operations
    files/                  # Optional per-version maps of important source files
    questions/              # Filed answers, pinned to v17
  v16/
    ...
  v15/
    ...
  v14/
    ...

  diagrams/                 # Mermaid diagrams shared across versions or pages
  _archive/
    vNN/                    # Archived content of removed versions
    orphans/                # Pages that became orphaned by version removal

AGENTS.md                   # Wiki maintenance instructions for the LLM agent
```

What goes where:

- **`.wiki-runtime/`** — all untracked runtime dependencies, generated indexes, caches, local model files, Hermes state, and logs for this wiki. Tools should run with this project as their working directory and write their state here.
- **`wiki/versions.md`** — the main page for version navigation. It lists every PostgreSQL version covered by the wiki, its support status, source pin, and link to the per-version landing page.
- **`wiki/vNN/index.md`** — the landing page for one PostgreSQL major version. It summarizes coverage for that version and links to its subsystems, code paths, concepts, files, and filed questions.
- **`wiki/shared/concepts/`** — concepts that are genuinely version-independent (the *theory* of a snapshot, the *theory* of MVCC). Examples cite the primary version; version-specific deviations are flagged inline.
- **`wiki/vNN/subsystems/`, `vNN/concepts/`, `vNN/code-paths/`, `vNN/files/`** — anything that names specific functions, files, signatures, or version-specific behavior. These are version-specific because the source is.
- **`wiki/vNN/questions/`** — answers tied to a single version. Questions are inherently snapshots of an investigation against a specific source pin (see Page Types).

Concrete starting pages and their seeding order are listed in the [Implementation Roadmap](#implementation-roadmap). Do not stub directories with empty files — pages should appear when the work that justifies them happens.

## Project-Local Dependency Policy

All wiki dependencies should run from, and store their project-specific state inside, this project directory.

This includes:

- PostgreSQL source checkouts under `raw/postgres-NN/`.
- Local tool environments under `.wiki-runtime/env/`.
- Hermes Agent config, state, and logs under `.wiki-runtime/hermes/`.
- Local model files or model-manager caches under `.wiki-runtime/models/`, `.wiki-runtime/ollama/`, or `.wiki-runtime/huggingface/`.
- Generated symbol, search, ctags, tree-sitter, and documentation indexes under `.wiki-runtime/indexes/`.
- Temporary files, run logs, and cache files under `.wiki-runtime/tmp/`, `.wiki-runtime/logs/`, and `.wiki-runtime/cache/`.

Avoid hidden global dependencies. Do not assume a globally-installed virtualenv, global Ollama model store, global Hugging Face cache, global Hermes state directory, or global source index. If an operating-system-level prerequisite is unavoidable, such as the NVIDIA driver, CUDA runtime, Docker, or a system package manager, document it as a system prerequisite and keep all wiki-specific config and generated state inside this repo.

Recommended environment variables when running local tooling from the project root:

```bash
export WIKI_RUNTIME="$PWD/.wiki-runtime"
export HERMES_HOME="$WIKI_RUNTIME/hermes"
export HF_HOME="$WIKI_RUNTIME/huggingface"
export TRANSFORMERS_CACHE="$WIKI_RUNTIME/huggingface"
export OLLAMA_MODELS="$WIKI_RUNTIME/ollama/models"
export XDG_CACHE_HOME="$WIKI_RUNTIME/cache"
export TMPDIR="$WIKI_RUNTIME/tmp"
```

`.wiki-runtime/` is runtime state, not durable wiki content. It should normally be ignored by git, while the instructions, scripts, templates, and markdown wiki pages remain tracked.

## Version Strategy

The wiki supports a fixed, declared set of PostgreSQL major versions. Each supported version has its own pinned source checkout and its own per-version wiki content. Cross-version concept theory lives in `wiki/shared/`.

### The Main Version Index

`wiki/versions.md` is both the human-facing version index and the source of truth for which versions the wiki supports. It should be easy to open this page in Obsidian and choose the PostgreSQL version to browse.

Example:

```md
# PostgreSQL Versions

This page indexes the PostgreSQL versions covered by the wiki.

| Version | Status  | Wiki Home | Branch        | Pinned Commit | Coverage |
|---------|---------|-----------|---------------|---------------|----------|
| 17      | primary | [[v17/index]] | REL_17_STABLE | abc1234       | query lifecycle, executor |
| 16      | active  | [[v16/index]] | REL_16_STABLE | def5678       | partial |
| 15      | active  | [[v15/index]] | REL_15_STABLE | 9012abc       | partial |
| 14      | legacy  | [[v14/index]] | REL_14_STABLE | 3456def       | archived-style coverage |

## Archived Versions

| Version | Removed On | Reason            |
|---------|------------|-------------------|
```

Status meanings:

- **primary** — exactly one. The default target for new ingests and code-path traces. New pages are written against this version first.
- **active** — kept close to the primary. New primary work should trigger an active-version verification pass.
- **legacy** — best-effort. Existing pages are preserved; new pages are not automatically checked here. Questions can still be filed.
- (archived — see the Remove a Supported Version workflow.)

Pins are commit hashes, not floating tags, so point releases do not silently shift claims.

Each supported version also has a landing page at `wiki/vNN/index.md`. That page is the version-local table of contents:

```md
# PostgreSQL 17

## Source Pin

- Branch: `REL_17_STABLE`
- Commit: `abc1234`
- Status: `primary`

## Coverage

- [[v17/code-paths/simple-select-query]]
- [[v17/subsystems/executor]]
- [[v17/subsystems/planner]]

## Open Questions

- ...
```

### Source References

Every wiki page references its source from the matching `raw/postgres-NN/` checkout. Preferred reference forms:

- Source file paths: `src/backend/executor/execMain.c`
- Header file paths: `src/include/executor/executor.h`
- Function or struct names: `ExecutorRun`, `MemoryContextData`
- Documentation paths: `doc/src/sgml/*.sgml`
- Commit hashes when discussing historical changes (these are version-independent and never drift)
- Mailing-list thread links or saved excerpts when discussing design intent

### What Counts as an Ingest

Unlike the article-shaped sources in the original LLM Wiki idea, PostgreSQL is a giant source tree. To keep the "ingest" concept meaningful, define an ingest as one of:

- **A subsystem sweep**: a directory under `src/backend/` (e.g. `src/backend/executor/`) read end-to-end to produce or update a subsystem page and its concept spinoffs.
- **A code-path trace**: an operation followed across files to produce a code-path page.
- **A doc chapter**: a chapter of `doc/src/sgml/` read for an architectural topic.
- **A mailing-list thread**: a saved thread in `raw/shared/mailing-list/` read to recover design intent.
- **A commit or commit range**: a saved commit or `git log` range in `raw/shared/commits/` read to explain why something is the way it is.

Each ingest defaults to the **primary** version and produces one log entry tagged with the version(s) touched. After producing the page on the primary, the agent does an active-version verification pass when active versions exist.

### Pin Bumps Within a Supported Version

When the pin for an already-supported version is moved (e.g. PG 17 point release brings new commits), treat it as a lint trigger, not a re-ingest:

1. Update the pin in `wiki/versions.md`.
2. Diff the previous and new commits for files cited by existing pages tagged with that version.
3. For each citation that points into a changed region, re-verify the claim and either update the page or flag it under Open Questions.
4. For question pages, also bump `pinned_commit:` only if the citation was actively re-verified.
5. Note the bump and resulting churn in `wiki/log.md`.

Do not blindly re-trace pages on every bump — only the ones whose cited code actually moved.

## Page Types

Every wiki page declares its version scope via YAML front matter. The default rule is simple: pages under `wiki/vNN/` are single-version pages, and pages under `wiki/shared/` are the only pages allowed to claim multiple versions.

### Per-version front matter

Used by subsystem, version-specific concept, code-path, file, and question pages under `wiki/vNN/`:

```yaml
---
type: subsystem | concept | code-path | file | question
version: 17
pinned_commit: abc1234
verified: true
---
```

- `version` — the PostgreSQL major version this page describes.
- `pinned_commit` — the exact source commit checked for this page. It must match `wiki/versions.md` unless the page explicitly records why it is stale.
- `verified` — whether the page has been checked against the pinned source. If false, the page must contain an `Open Questions` section explaining the gap.

Question pages add `filed`:

```yaml
---
type: question
version: 17
pinned_commit: abc1234
verified: true
filed: 2026-04-30
---
```

If the same question deserves an answer for another version, that is a new question page in that version's directory, cross-linked to the original.

### Shared concept front matter

Used only by genuinely cross-version concept pages under `wiki/shared/concepts/`:

```yaml
---
type: concept
scope: shared
verified_against:
  17: abc1234
  16: def5678
primary_example_version: 17
---
```

Shared concepts explain theory and cross-version continuity. They may cite specific source examples, but any function/file-specific behavior belongs in the matching `wiki/vNN/` page.

### Subsystem Pages

Subsystem pages explain a major area of the engine. Live under `wiki/vNN/subsystems/`.

Recommended sections:

```md
# Subsystem Name

## Role

## Major Entry Points

| Symbol | File | Purpose |
|---|---|---|

## Core Data Structures

## Related Concepts

## Important Code Paths

## Differences Across Supported Versions

## Source References

## Open Questions
```

The "Differences Across Supported Versions" section is for inline notes when a single page covers multiple versions. If divergence is large, fork into per-version copies instead.

### Concept Pages

Concept pages explain recurring engine ideas. Default location is `wiki/shared/concepts/` for theory; create per-version copies under `wiki/vNN/concepts/` only if the concept itself differs meaningfully between versions (rare).

Recommended sections:

```md
# Concept Name

## Definition

## Why It Exists

## Where It Appears

## Related Structures and Functions

## Interactions With Other Concepts

## Version Notes

## Source References

## Open Questions
```

### Code Path Pages

Code path pages are the highest-value artifact and are always per-version. Live under `wiki/vNN/code-paths/`.

Recommended sections:

```md
# Code Path Name

## Scope

## High-Level Flow

## Detailed Flow

| Step | Function | File | Notes |
|---|---|---|---|

## Key Data Structures

## Cross-Links

## Source References

## Open Questions
```

### File Pages

File pages should be used sparingly for source files central enough to deserve their own map. Live under `wiki/vNN/files/`. Always per-version because file contents are.

Recommended sections:

```md
# Source File Path

## Role

## Important Symbols

## Callers and Callees

## Related Wiki Pages

## Source References
```

### Question Pages

Question pages preserve useful answers from investigation. Live under `wiki/vNN/questions/` and use the per-version front matter.

Recommended sections:

```md
# Question

## Short Answer

## Detailed Answer

## Evidence

## Related Pages

## Follow-Up Questions
```

A question page is never moved to `shared/`, even if its answer happens to be identical across versions. If the user asks the same question against another version, the agent re-investigates it on that version's source and files a new question page with cross-links to the original.

## LLM Maintenance Rules (AGENTS.md)

The repository must include an `AGENTS.md` file. This file is the schema — it is what makes the LLM a disciplined wiki maintainer rather than a chatty assistant. It should be drafted as part of Phase 1 and co-evolved with the wiki. A starting draft:

### Read before writing

- Read `wiki/index.md` before modifying or answering from the wiki.
- Read `wiki/log.md`'s last ~20 entries to understand recent activity.
- Search the PostgreSQL source tree before making any technical claim. If a claim is not backed by a file, symbol, doc, commit, or mailing-list source, do not write it down.

### Citation discipline

- Cite source paths and symbols for every behavioral claim. Format: `src/backend/executor/execMain.c:ExecutorRun`.
- Always cite from the `raw/postgres-NN/` checkout matching the page's `version:`. Shared concept pages cite explicit version examples through `verified_against:`.
- When uncertain, write the claim under `## Open Questions` rather than guessing intent.
- Never paraphrase code in a way that adds behavior the code does not exhibit.

### Version awareness

- Read `wiki/versions.md` first to know which versions are supported and which is primary.
- When browsing the wiki, use `wiki/versions.md` as the entry point, then follow the relevant `wiki/vNN/index.md` landing page.
- Default new ingests, traces, and answers to the **primary** version unless the user specifies another.
- If the user asks a question without naming a version, assume the primary version and state that assumption before answering.
- Never silently answer about one version using citations from another. If a page is verified for v17 only, do not extend it to v16 without re-checking the source.
- Question pages are pinned to a single version. Filing the same question against another version creates a new question page, not an edit to the original.

### Wiki structure

- Prefer code-path pages over vague subsystem summaries. The trace is the artifact.
- Use Obsidian-style links: `[[memory-contexts]]`, `[[v17/code-paths/simple-select-query]]`. Include the version segment for links into per-version directories.
- Keep `wiki/versions.md` as the top-level version index and keep each `wiki/vNN/index.md` as the version-local table of contents.
- A page is born when the work justifies it, not before. Do not create empty stubs.
- A concept earns its own page when it is referenced from at least two other pages or repeatedly in conversation.

### Dependency locality

- Run wiki tooling from the project root.
- Store all wiki-specific runtime state under `.wiki-runtime/`.
- Store PostgreSQL source checkouts under `raw/postgres-NN/`.
- Do not rely on global caches, global virtualenvs, global Hermes state, or global source indexes for normal operation.
- If a system-level prerequisite is required, document it, but keep the project-specific configuration and generated files inside this repository.

### Bookkeeping (do these every time)

- Update `wiki/index.md` whenever a page is created or substantially changed. Tag entries with their version(s).
- Update `wiki/versions.md` whenever a supported version is added, removed, archived, re-pinned, or has a meaningful coverage change.
- Update the relevant `wiki/vNN/index.md` whenever version-local pages are created or substantially changed.
- Append an entry to `wiki/log.md` after each ingest, trace, lint pass, filed answer, or version lifecycle event. Use the prefix `## [YYYY-MM-DD] <kind> v<NN> | <subject>` (e.g. `## [2026-04-30] trace v17 | simple-select-query`).
- File durable answers as question pages (under the investigated version's `questions/` directory) or fold them into existing concept/subsystem pages — do not let them disappear into chat history.
- Never edit `raw/` except when explicitly adding new source material via the Add a Supported Version workflow.

### When in doubt

- Trace, don't summarize. If asked something high-level, prefer to follow real code than to generalize.
- Preserve uncertainty. "I don't know yet" plus a logged Open Question is more valuable than a confident wrong answer.

### Local-model operating mode

When the wiki is maintained by a local model on a 16GB NVIDIA GPU, keep the agent workflow narrow:

- Trace one code path, subsystem slice, or question at a time.
- Prefer `rg`, `git grep`, and short source excerpts over loading entire directories into context.
- Do not ask the model to ingest a large subsystem in one pass unless a stronger hosted model is being used.
- Treat generated pages as drafts until their source references are checked.
- Use active-version verification sparingly; defer it explicitly on `wiki/vNN/index.md` when it would exceed the local context or latency budget.
- Escalate hard traces, such as planner internals, WAL, crash recovery, or MVCC visibility, to a stronger model when the local model cannot keep the call chain straight.

## Core Workflows

### 1. Initialize Wiki

Create the base structure:

```text
wiki/index.md
wiki/log.md
wiki/overview.md
wiki/versions.md
wiki/shared/concepts/
wiki/diagrams/
AGENTS.md
```

Per-version directories (`wiki/vNN/...`) and `raw/postgres-NN/` checkouts are created via the Add a Supported Version workflow, not preemptively.

Add starter templates for each page type, including the front-matter blocks defined in Page Types. `wiki/versions.md` starts as the main version index, even if it initially has no supported versions.

### 2. Add a Supported Version

Trigger: a new PG major releases, or you decide to support an older one.

Inputs: version number, branch name, pinned commit, target status (`primary`, `active`, or `legacy`).

Agent flow:

1. **Add the source.** Create `raw/postgres-NN/` as a checkout of the pinned commit on `REL_NN_STABLE`.
2. **Update the version index.** Add a row to `wiki/versions.md`. If the new version is being made `primary`, demote the previous primary to `active` in the same edit.
3. **Create the version landing page and directory tree.** Create `wiki/vNN/index.md`, then `wiki/vNN/subsystems/`, `wiki/vNN/concepts/`, `wiki/vNN/code-paths/`, `wiki/vNN/files/`, `wiki/vNN/questions/`. Directories start empty; the landing page is real navigation, not a stub.
4. **Backfill verification pass.**
   - For `wiki/shared/concepts/`, add NN to `verified_against:` only after checking representative source examples against the new version.
   - For per-version pages, create a new `wiki/vNN/...` page only when the content has actually been checked or intentionally copied with clear source references for NN.
   - If the behavior diverges, write the divergence in the new version page and cross-link related versions.
   - If it is not yet checked, leave it out of the new version's page set and add an Open Question on `wiki/vNN/index.md`.
   - **Question pages are excluded from automatic backfill.** They stay pinned to the version they were filed against.
5. **Re-lint.** Run the lint workflow to surface anything stale.
6. **Log.** One summary entry, e.g.:
   ```md
   ## [2026-04-30] add-version v18 | promoted to primary; v17 demoted to active; 47 pages backfilled, 12 forked, 8 open questions
   ```

The backfill is the expensive step. Do not mark a new version as verified just because one cited file is unchanged; behavior can depend on headers, callees, macros, and nearby control flow. Batch the work and report a summary, do not pause on every page.

### 3. Remove a Supported Version

Trigger: a PG major reaches EOL, or you decide to stop maintaining it.

Inputs: version number, removal mode (`archive` or `drop`).

**Default to `archive` — never destructive.** `drop` is reserved for cleanup of an erroneously-added version and requires explicit user confirmation.

Agent flow (archive):

1. **Update the version index.** Move the row in `wiki/versions.md` from the active table to the "Archived Versions" table at the bottom. Record the archival date and reason.
2. **Move version-specific content.** `wiki/vNN/` → `wiki/_archive/vNN/`. Likewise `raw/postgres-NN/` → `raw/_archive/postgres-NN/`.
3. **Update shared pages.** For every shared concept page, remove NN from `verified_against:`. Pages that no longer apply to any active version go to `wiki/_archive/orphans/` rather than being deleted.
4. **Update the index.** Remove vNN entries from active sections; add a one-line pointer to the archive.
5. **Log.**
   ```md
   ## [2026-04-30] remove-version v14 | archived (EOL); 31 pages updated, 4 orphaned to _archive/orphans/
   ```

Agent flow (drop): same as archive but pages and source are deleted outright. Always confirm with the user before doing this.

#### Status transitions

The two workflows above are how versions enter and leave. Day-to-day status changes happen separately and are cheap:

- `active` → `primary`: bumping the default target for new ingests. One edit to `wiki/versions.md`, no content moves.
- `active` → `legacy`: stop checking new pages here by default, but still answer questions. Lint stops flagging it for missing active-version checks.
- `legacy` → archived: via the Remove workflow.

### 4. Ingest a Subsystem

Example request:

```text
Ingest src/backend/executor and create the executor subsystem page.
```

Agent flow:

1. Read `wiki/versions.md` and select the **primary** version unless the user specified another.
2. Read `wiki/vPRIMARY/index.md` to understand existing coverage for that version.
3. Inspect relevant directories and README files in `raw/postgres-PRIMARY/`.
4. Identify key source files, headers, entry points, and structs.
5. Create or update the subsystem page under `wiki/vPRIMARY/subsystems/` with per-version front matter.
6. Create concept pages for recurring ideas. Default to `wiki/shared/concepts/` for theory; use `wiki/vPRIMARY/concepts/` for version-specific behavior.
7. Add links to related code-path pages if known.
8. **Active-version pass:** for each `active` version, re-check the cited symbols and call relationships before creating or updating that version's subsystem page. If not checked, add an Open Question to the active version's landing page instead of claiming coverage.
9. Update `wiki/index.md`, `wiki/versions.md` if coverage changed, and the affected `wiki/vNN/index.md` pages. Append to `wiki/log.md` with the version tag.

### 5. Trace a Code Path

Example request:

```text
Trace how a simple SELECT query moves through the engine.
```

Agent flow:

1. Default to the **primary** version.
2. Read `wiki/vPRIMARY/index.md` to understand existing coverage.
3. Start from likely frontend/backend entry points in `raw/postgres-PRIMARY/`.
4. Use source search to follow calls through parser, analyzer, rewriter, planner, and executor.
5. Record the flow under `wiki/vPRIMARY/code-paths/`.
6. Link to subsystem and concept pages with version-qualified Obsidian links.
7. Mark uncertain behavior under Open Questions.
8. **Active-version pass:** for each `active` version, walk the same call chain in that version's checkout. If it matches, create or update that version's code-path page with its own `version:` and `pinned_commit:`. If it diverges, write the divergent path under `wiki/vNN/code-paths/` with cross-links.
9. Update `wiki/index.md`, `wiki/versions.md` if coverage changed, affected `wiki/vNN/index.md` pages, and `wiki/log.md`.

### 6. Answer and File

Example request:

```text
Why does PostgreSQL use memory contexts?
```

Agent flow:

1. Determine which version the question is being asked against. If unclear, assume the primary version and state that assumption explicitly before answering.
2. Search existing wiki pages (start with `wiki/versions.md`, then the relevant `wiki/vNN/index.md`, then `wiki/index.md`).
3. Search the matching `raw/postgres-NN/` and docs for supporting evidence.
4. Answer the user with citations.
5. **Default to filing.** Decide where:
   - Fold into an existing concept/subsystem page if it fits.
   - Otherwise file as a question page under `wiki/vNN/questions/` with per-version front matter.
   The decision is *where* to file, not *whether*.
6. Update `wiki/index.md`, the relevant `wiki/vNN/index.md`, `wiki/versions.md` if coverage changed, and `wiki/log.md`.

The bias toward filing is deliberate: explorations should compound in the wiki the same way ingested sources do.

### 7. Lint the Wiki

Periodic maintenance request:

```text
Lint the wiki.
```

Agent checks:

- Pages without source references.
- Pages under `wiki/vNN/` without matching `version:` and `pinned_commit:`.
- Pages whose `pinned_commit:` is stale relative to `wiki/versions.md`.
- Shared concept pages whose `verified_against:` pins are stale relative to `wiki/versions.md`.
- Question pages without `version:` or `pinned_commit:`.
- Question pages citing source from a different version's checkout than their pin.
- Pages under `wiki/vNN/` citing code from a different version's checkout.
- Concepts mentioned repeatedly but lacking pages.
- Orphan pages and broken wiki links (including version-qualified links).
- Pages that are too vague.
- Code-path pages that should be cross-linked from subsystem pages.
- Version landing pages missing links to existing version-local pages.
- `wiki/versions.md` coverage notes that disagree with the actual version-local pages.
- Pages that should have been checked for an `active` version but weren't.

## Suggested Tooling

Start with simple local tools, scoped to the relevant version's checkout:

```bash
rg "ExecutorRun" raw/postgres-17
rg "typedef struct.*Snapshot" raw/postgres-17/src
git -C raw/postgres-17 log -- src/backend/executor/execMain.c
git -C raw/postgres-17 grep "MemoryContext"

# Cross-version diff for active-version verification
diff <(git -C raw/postgres-17 show HEAD:src/backend/executor/execMain.c) \
     <(git -C raw/postgres-16 show HEAD:src/backend/executor/execMain.c)
```

Optional later tools:

- `universal-ctags` per checkout, for symbol navigation, with generated tags stored under `.wiki-runtime/indexes/ctags/`.
- `tree-sitter` for structured source exploration.
- `doxygen` for generated call/reference maps, with output stored under `.wiki-runtime/indexes/` or another `.wiki-runtime/` subdirectory.
- A small `scripts/wiki_lint` tool to detect broken links, orphan pages, missing source references, version/pin mismatches, stale `pinned_commit:`, and stale `verified_against:` entries.
- A small `scripts/source_lookup` wrapper around `rg`, `git grep`, and `git log`, defaulting to the primary version's checkout.
- A small `scripts/version_diff` to compare cited files across two checkouts during active-version verification.

### Local LLM and Hermes Agent setup

Target hardware:

```text
NVIDIA GPU: 16GB VRAM
System RAM: enough for CPU offload and source indexing, preferably 32GB+
```

Hermes Agent should act as the orchestrator. Run Hermes Agent and the model server from the project root with project-local runtime paths. The local model should not be trusted as a PostgreSQL authority from memory; it should repeatedly search the pinned source checkout, cite files and symbols, edit markdown, and preserve uncertainty.

Project-local runtime layout:

```text
.wiki-runtime/
  hermes/                   # Hermes config/state/logs
  models/                   # Directly managed model files
  ollama/models/            # Ollama model store when using Ollama
  huggingface/              # HF/vLLM/SGLang model cache
  logs/                     # Model-server and agent logs
  tmp/                      # Temporary files
```

Recommended model profile:

| Model | Fit on 16GB | Use |
|---|---:|---|
| `Qwen2.5-Coder-14B-Instruct-AWQ` or other 4-bit quant | Good | Default local model for this wiki |
| `Qwen3-14B` 4-bit | Good | Alternative when agent/tool behavior is better than code-specialization |
| `Qwen3-Coder-30B-A3B-Instruct` 4-bit | Stretch | Try only with CPU offload and enough RAM |
| `Qwen3-Coder-Next` / larger coder models | Poor | Do not use as the primary local model on 16GB VRAM |
| 7B/8B coder models | Easy | Acceptable for formatting and small edits, weak for autonomous source tracing |

Context target:

```text
minimum: 64K tokens for Hermes multi-step workflows
preferred: 64K to 128K if the serving stack and VRAM allow it
fallback: reduce task scope rather than silently accepting a tiny context window
```

On 16GB VRAM, 64K context may require quantized KV cache, reduced batch/concurrency, or CPU offload. If the model server cannot hold 64K reliably, keep the individual source reads smaller and make the agent summarize intermediate findings into the wiki before continuing.

Serving options:

- **Easiest:** Ollama or llama.cpp with a 4-bit Qwen coder model. Good for local iteration.
- **More agentic/tool-friendly:** vLLM or SGLang with an OpenAI-compatible endpoint. Use this if tool-call reliability matters more than setup simplicity.
- **Avoid:** trying to force large 30B+ dense models into 16GB VRAM without accepting heavy CPU offload and slow responses.

Example vLLM shape, if the AWQ model and context fit:

```bash
export WIKI_RUNTIME="$PWD/.wiki-runtime"
export HERMES_HOME="$WIKI_RUNTIME/hermes"
export HF_HOME="$WIKI_RUNTIME/huggingface"
export TRANSFORMERS_CACHE="$WIKI_RUNTIME/huggingface"
export XDG_CACHE_HOME="$WIKI_RUNTIME/cache"
export TMPDIR="$WIKI_RUNTIME/tmp"

vllm serve Qwen/Qwen2.5-Coder-14B-Instruct-AWQ \
  --max-model-len 65536 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

If this does not fit in memory, first try lower concurrency, quantized cache, or CPU offload. Lower the context only as a last resort. For this project, a smaller, source-grounded task with adequate context is better than a larger model with too little working memory.

Acceptance test for the local setup:

1. Ask Hermes to trace one narrow path, such as a simple `SELECT`, on the primary PostgreSQL version.
2. Confirm it uses `rg` or `git grep` rather than relying on memory.
3. Confirm every behavioral claim cites a real file or symbol.
4. Confirm it updates `wiki/vNN/index.md`, `wiki/index.md`, and `wiki/log.md`.
5. Confirm it marks unclear behavior under `Open Questions` instead of inventing intent.

### Obsidian setup

Open `wiki/` as an Obsidian vault. The graph view is the highest-leverage navigation tool for this domain — subsystems should be hubs, concepts should be densely cross-linked, and code-path pages should connect across both. Use the graph view during lint passes to spot orphan pages and isolated clusters.

Diagrams should be authored as Mermaid blocks inside relevant pages (or in `wiki/diagrams/` if shared across pages). Avoid binary image formats unless screenshotting documentation; Mermaid keeps everything diffable and grep-able.

## Implementation Roadmap

### Phase 1: Wiki Scaffold

- Create the version-agnostic wiki structure: `index.md`, `log.md`, `overview.md`, `versions.md`, `wiki/shared/concepts/`, `wiki/diagrams/`.
- Create the project-local runtime directory layout under `.wiki-runtime/` and ignore it from git if this repo uses git.
- Draft `AGENTS.md` with the maintenance rules.
- Add page templates with the per-version and shared-concept front matter blocks.
- Record the local-model operating profile in `AGENTS.md`: 16GB NVIDIA GPU, Hermes Agent, default model, context target, and narrow-source-tracing rules.

### Phase 2: Bootstrap Supported Versions

- Decide which PG majors to support at launch. A reasonable starting set is the latest stable as `primary` plus the previous major as `active`. Add older versions only when there's a real need — each one is real bookkeeping.
- Run the Add a Supported Version workflow for each, in newest-first order. The first version added becomes `primary`.
- The active-version verification pass is trivial on the first add (no existing pages) and grows with each subsequent add.

### Phase 3: Query Lifecycle Spine

Phases 3 and 4 are interleaved in practice — concept pages emerge as a side effect of subsystem sweeps and code-path traces, not as a separate up-front pass.

Start by walking the query lifecycle:

1. Parser
2. Analyzer
3. Rewriter
4. Planner
5. Executor

For each stage, do a subsystem sweep (one log entry, one subsystem page) and let concept pages spin off as the recurring ideas reveal themselves (e.g. plan nodes, executor state, memory contexts).

### Phase 4: First Code Paths

Trace these end-to-end across the subsystems from Phase 3:

1. Simple `SELECT`
2. `INSERT`
3. `UPDATE`
4. `DELETE`

These pages become the navigational spine of the wiki and tend to surface the foundational concepts (snapshots, tuple visibility, transaction IDs, locks, WAL basics) as cross-links along the way. Create concept pages on demand, not preemptively.

### Phase 5: Backfill Concepts

After the first code paths exist, do a pass to give every recurring concept its own page if it doesn't have one yet. By this point, which concepts deserve pages will be clear from how often they were referenced as Obsidian-style links during Phases 3–4.

### Phase 6: Maintenance Tooling

Add scripts for:

- Broken wiki link detection
- Orphan page detection
- Missing source reference detection
- Recent activity summaries from `wiki/log.md`
- Start, stop, status, and log inspection for the local wiki maintainer agent

## First Useful Milestone

The wiki is never "done" — it compounds as long as it's used. But there's a natural first milestone where it starts paying for itself:

- The wiki has a clear global index, overview, and `versions.md` main version index declaring at least one supported version (the primary).
- `.wiki-runtime/` exists and contains all project-local runtime dependencies, generated indexes, caches, model state, logs, and temporary files.
- Each supported version has a `wiki/vNN/index.md` landing page.
- Each supported version has a `raw/postgres-NN/` checkout pinned to a specific commit.
- The query lifecycle is covered from parse through execute on the primary version.
- At least one complete code-path page exists for the primary, with active-version checks filed or explicitly deferred where applicable.
- At least five foundational concept pages exist in `wiki/shared/concepts/`.
- Each page has front matter declaring its version scope and includes source references or explicit open questions.
- The agent maintenance rules are documented in `AGENTS.md`, including the version-awareness section.

After this point, growth is driven by the questions you ask, the subsystems you investigate, and the versions you choose to support.
