# PostgreSQL Engine Wiki Agent Instructions

This repository is an LLM-maintained wiki for PostgreSQL engine internals. The agent writes and maintains the wiki; raw PostgreSQL source is the factual evidence base.

## Read Before Writing

- Read `wiki/versions.md` first to identify supported PostgreSQL versions and the primary version.
- Read `wiki/index.md` before modifying or answering from the wiki.
- Read the last ~20 entries of `wiki/log.md` to understand recent activity.
- For version-specific work, read the relevant `wiki/vNN/index.md` before editing version-local pages.
- For any question, answer, report, or generated document, query the matching `raw/postgres-NN/` checkout only through `scripts/source_graph_query --version NN ...`.
- When graph exploration is useful, use `scripts/source_graph_query --version NN query|path|explain ...`; if `.wiki-runtime/graph/postgres-NN/graph.json` is absent, the query wrapper must generate it through `scripts/source_graph --version NN --refresh`.

## Environment Isolation

Tooling for this project must have minimal impact on the host system. Stay scoped to the repository.

- All Python scripts run from the project venv at `.wiki-runtime/venv/`. Activate it (`source .wiki-runtime/venv/bin/activate`) or invoke scripts as `.wiki-runtime/venv/bin/python scripts/<name>`. Scripts hard-fail with a clear message when run outside the venv.
- If the venv is missing, run `scripts/bootstrap_venv` to create it. That is the only script that may run with the host `python3`.
- Add new Python dependencies to `requirements.txt` at the repo root, with a pinned version. Do not `pip install`, `pipx install`, or otherwise install Python packages globally, into user site-packages, or with `--user`. Do not install packages with `sudo`.
- Read and write only inside this repository (`raw/`, `wiki/`, `.wiki-runtime/`, `scripts/`, `tests/`, `requirements.txt`, top-level docs). Do not touch `$HOME`, mutate global git config, or require root. Treat `raw/postgres-NN/` checkouts as read-only evidence.
- Do not call commands that escalate privilege (`sudo`, `chown` outside the repo, `chmod` on host paths). Network access is allowed only for the explicit source-fetch operations in `scripts/source_update` and `scripts/bootstrap_venv`.
- Never use the `WIKI_ALLOW_SYSTEM_PYTHON=1` bypass for normal work. It exists for the test wrapper, which copies scripts into a synthetic temp repo where the venv guard cannot resolve.
- Generated artifacts, caches, and the venv live under `.wiki-runtime/`. Removing that directory is always a safe reset; rebuild with `scripts/bootstrap_venv` and `scripts/source_graph --version NN --refresh`.

## Evidence Scope

For every answer, report, wiki page, diagram, or generated document, use only the target version's pinned checkout under `raw/postgres-NN/` as factual evidence. Graphify output under `.wiki-runtime/graph/postgres-NN/` is an orientation layer for finding likely files, symbols, and paths; it is not a citation source for PostgreSQL behavior.

- Treat `wiki/versions.md`, `wiki/index.md`, `wiki/log.md`, and version landing pages as navigation and bookkeeping context, not independent evidence for PostgreSQL behavior.
- Do not use model memory, external websites, package documentation outside the repository, or uncited prior wiki prose as factual support for generated content.
- Use `scripts/source_graph_query` raw subcommands for evidence gathering:
  - `symbol` for fixed-string or regex source search.
  - `file` for bounded raw source slices and directory listings.
  - `log` for source checkout git history.
  - `includes` for direct raw `#include` directives.
  - `included-by` for raw reverse include scans.
- Use `scripts/source_graph_query` graph subcommands only for orientation:
  - `query` for natural-language graph lookup.
  - `path` for exact graph paths between nodes.
  - `explain` for graph node summaries.
- Never answer about one PostgreSQL version using `raw/` files or `.wiki-runtime/graph/` artifacts from another version.
- If a graph artifact conflicts with the pinned raw source, the raw source wins. Record the discrepancy under `## Open Questions` or regenerate the graph with `scripts/source_graph --version NN --refresh`.

## Deep Inquiry Default

All user questions, reports, and filed answers run in deep-inquiry mode unless the user explicitly asks for a quick answer.

For each question:

- Confirm the target PostgreSQL version and use explicit version-scoped source tools for every source operation.
- Locate the primary source files and symbols, then inspect adjacent callers, callees, structs, macros, includes, generated headers visible in raw source, reverse include users, graph paths, relevant tests, docs, catalogs, grammar, error paths, GUC definitions, and extension/contrib boundaries through `scripts/source_graph_query`.
- If any project-local graph/source query used for evidence returns an error or cannot produce trustworthy output, abort the current analysis before drafting. Fix and rerun the command when feasible; otherwise stop and report the exact command, target version, and error.
- Inspect file or symbol history when the user asks why something exists, when intent matters, or when a regression/change claim is being made.
- Use `scripts/version_diff --from NN --to MM` only when the answer makes a cross-version claim or the user asks for a comparison.
- Draft from a claim-to-source evidence map. Every behavioral claim needs a matching raw citation; unresolved claims go under `## Open Questions`.

The minimum depth target for an engine-internals answer is: normal path, relevant error or edge path, key data structures, caller/callee boundary, build or generated-header implications visible from raw source, and tests or explicit test absence. For planner, WAL, crash recovery, MVCC, storage, or corruption topics, missing caller/callee or data-structure context is a verification gap that must be resolved or recorded under `## Open Questions`.

## Citation Discipline

- Cite source paths and symbols for every behavioral claim.
- Mandatory citation shape: `[[raw/postgres-NN/src/backend/executor/execMain.c#ExecutorRun]]`.
- For non-Markdown files you must include the full file extension (`.c`, `.py`, `.java`, etc.).
- Cite from the `raw/postgres-NN/` checkout matching the page's `version:`.
- Use the same citation format for all code references, function names, and symbols mentioned in the text.
- Code references may use aliases for compact display: `[[raw/postgres-NN/path/file.c#symbol|file.c#symbol]]`.
- If a claim is not backed by a source file, symbol, documentation page, commit, or saved design discussion, do not write it as fact.
- Put uncertainty under `## Open Questions` instead of guessing.

## Tone And Readability

Wiki pages are reference material for engineers under time pressure. Write so a reader can land cold on the page and leave with the answer.

- Lead with the answer. Put the direct conclusion in the first one or two sentences of each section, then the supporting evidence and citations. Do not bury the result under setup.
- Prefer plain language. When a PostgreSQL term of art is unavoidable (e.g. `relfrozenxid`, `XLogInsert`, `MultiXact`), define it on first use on the page or link to the page that does.
- Short sentences over long ones. One claim per sentence. Break a multi-clause sentence into a list when it carries more than one idea.
- Active voice and concrete subjects. "The checkpointer flushes dirty buffers" beats "Dirty buffers are flushed." Name the function, struct, or process doing the work.
- Use lists, tables, and small code blocks to break up dense prose. A table of GUC contexts or a four-row state-transition list is easier to scan than a paragraph.
- Make conditions explicit instead of vague. PostgreSQL behavior often genuinely depends on configuration, version, or state, so conditional phrasing is welcome — but name the condition. Prefer "when `wal_level >= replica`" over "generally," and "on a HOT update" over "tends to." If the condition itself is uncertain, move the claim under `## Open Questions`.
- Skip filler. No "in this section we will," no "it is important to note that," no restating the page title in the first paragraph.
- Examples earn their keep. A short SQL snippet, `EXPLAIN` fragment, or struct excerpt usually communicates faster than a paragraph describing the same thing — but every example must still be cited to the pinned `raw/postgres-NN/` source.
- Readability never overrides citation discipline. If approachable phrasing would require dropping a citation or softening a verified claim into vagueness, keep the citation and the precision.

## GUC Configuration Changes

- Whenever a wiki page suggests changing a GUC (`postgresql.conf`, `SET`, `ALTER SYSTEM`, etc.), state whether the change requires a restart, reload, or only session/transaction scope.
- Determine the requirement from the GUC's context in the pinned raw source (`raw/postgres-NN/src/backend/utils/misc/guc*.c` or the version's equivalent) or from a validated `pg_settings` definition in the same version. Cite the source.
- Map context values explicitly: `postmaster` -> restart required; `sighup` -> reload; `superuser` / `user` / `backend` -> session or transaction scope, no restart or reload beyond changing defaults.

## Production SQL Snippets

Whenever a wiki page proposes SQL intended to be executed against production:

- Verify syntax, referenced catalogs, columns, functions, and GUCs against the pinned `raw/postgres-NN/` checkout before filing. If a snippet cannot be verified, move it under `## Open Questions`.
- Embed an inline block-comment tag immediately after the leading verb in every production-bound statement:

  ```sql
  SELECT /* wiki_capture_plan_inputs */ ...;
  UPDATE /* wiki_backfill_user_email */ users SET ...;
  ```

- Recommend reasonable session-scoped `statement_timeout` and `lock_timeout` values before the snippet, sized to the operation.

## Verification

Pages carry two distinct verification fields in front matter:

- `verified:` — human-verified. Only a human reviewer may set, change, or remove this field.
- `verified_by_agent:` — agent-verified. Agents may set or update this field only after re-checking every claim against the pinned raw source through graph scripts.

Rules:

- When creating new question pages, set `verified: false` and `verified_by_agent: not yet`.
- Do not set `verified_by_agent:` if any claim cannot be verified. Fix the claim, move it under `## Open Questions`, or leave the field absent.
- Unverified managed wiki documents must show `(unverified)` in the visible title and in index or landing-page link text until a human sets `verified: true`. `verified_by_agent:` does not affect this tag — only the human-set `verified:` field does.
- For question pages under `wiki/vNN/questions/`, front matter must use exactly this order:

  ```yaml
  type: question
  version: NN
  pinned_commit: abc123...
  verified: false
  verified_by_agent: not yet
  ```

## Version Awareness

- `wiki/versions.md` is the source pin manifest.
- Each supported version has a landing page at `wiki/vNN/index.md`.
- Default new ingests and answers to the primary version unless the user specifies another.
- If the user asks without naming a version, assume the primary version and state that assumption before answering.
- Hard rule: every source operation must use an explicit version scope. Use `--version NN` for graph tools and `--from NN --to MM` for cross-version diffs.
- Never answer about one PostgreSQL version using citations from another version's checkout.

## Wiki Structure

- Keep version-specific pages under `wiki/vNN/`.
- Use Obsidian-style links, such as `[[versions]]` and `[[v18/index]]`.
- Include the version segment for links into per-version directories.
- A page is born when the work justifies it. Do not create empty content stubs.

## Operating Mode

- Trace one source slice or question at a time using `scripts/source_graph_query` and the matching raw source checkout.
- Prefer `scripts/source_graph_query --version NN symbol ...`, `file ...`, `includes ...`, and `included-by ...` over ad hoc shell searches.
- Do not create standalone call-chain or source-trace document families. Regenerate `.wiki-runtime/graph/postgres-NN/` when better graph navigation is needed.
- Treat generated pages as drafts until their source references are checked.
- Always use a unicode/ASCII tree for visual directory representations.

## Bookkeeping

Do these after every meaningful wiki change:

- Update `wiki/index.md` whenever a page is created or substantially changed.
- Update `wiki/versions.md` whenever a supported version is added, removed, archived, re-pinned, or has a meaningful coverage change.
- Update the relevant `wiki/vNN/index.md` whenever version-local pages are created or substantially changed.
- Append an entry to `wiki/log.md` after each scaffold change, ingest, lint pass, filed answer, graph refresh, or version lifecycle event.

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

1. Add the source checkout under `raw/postgres-NN/` using `scripts/source_update`.
2. Pin the checkout to an exact commit.
3. Add the version to `wiki/versions.md`.
4. Create `wiki/vNN/index.md`.
5. Generate the Graphify graph under `.wiki-runtime/graph/postgres-NN/` using `scripts/source_graph --version NN --refresh`.
6. Create `wiki/vNN/questions/` only when a filed answer needs it.
7. Update `wiki/index.md`.
8. Append to `wiki/log.md`.

### Refresh Source Graph

1. Read `wiki/versions.md` and select the explicit target version.
2. Read `wiki/vNN/index.md`.
3. Run `scripts/source_graph --version NN --refresh`.
4. Run `scripts/source_graph_check --version NN` and use `--probe-node <symbol>` when a focused source area has a known symbol.
5. Search relevant raw source files through `scripts/source_graph_query --version NN ...` before writing claims.
6. Update `wiki/vNN/index.md`, `wiki/index.md`, and `wiki/versions.md` when coverage status changes, and append to `wiki/log.md`.

### Answer And File

1. Assume the primary version unless the user specifies another.
2. Search `wiki/versions.md`, the relevant version landing page, and `wiki/index.md` for navigation and bookkeeping context only.
3. Build the deep inquiry context envelope with `scripts/source_graph_query --version NN` raw and graph subcommands.
4. Draft a claim-to-source evidence map. Move anything not verified into `## Open Questions`.
5. Answer with citations to matching `raw/postgres-NN/` paths and symbols.
6. File durable answers as question pages or fold them into existing pages. Filed question pages should include `## Context Reviewed`, `## Evidence Map`, and `## Open Questions` when gaps exist.
7. Update indexes and log.

## Lint The Wiki

Check for broken links, orphan pages, missing source references, stale version pins, wrong-version citations, invalid verification fields, unverified title hints, and version landing pages missing links.

Use the project-local scripts first. The examples below assume the project venv is active (`source .wiki-runtime/venv/bin/activate`); otherwise prefix each Python script with `.wiki-runtime/venv/bin/python`.

```bash
scripts/recent_log --limit 20
scripts/wiki_lint
scripts/source_graph --version 18 --dry-run
scripts/source_graph --version 18 --refresh
scripts/source_graph_query --version 18 symbol ExecutorRun
scripts/source_graph_query --version 18 symbol '\bExecutorRun\b' --regex --limit 20
scripts/source_graph_query --version 18 file src/backend/executor/execMain.c --start 1 --limit 80
scripts/source_graph_query --version 18 log src/backend/executor/execMain.c --limit 20
scripts/source_graph_query --version 18 includes src/backend/executor/execMain.c --format json
scripts/source_graph_query --version 18 included-by executor/executor.h --limit 50
scripts/source_graph_query --version 18 explain ExecutorRun
scripts/source_graph_query --version 18 path PostgresMain ExecutorRun
scripts/source_graph_check --version 18 --probe-node ExecutorRun
scripts/version_diff --from 18 --to 17 --path src/backend/executor/execMain.c
scripts/source_update --list
scripts/source_update --version 18
scripts/test_source_tools
```

`scripts/source_graph_query` requires `--version NN`. Raw subcommands (`symbol`, `file`, `log`, `includes`, `included-by`) query `raw/postgres-NN/` directly. Graph subcommands (`query`, `path`, `explain`) use `.wiki-runtime/graph/postgres-NN/graph.json` and force generation through `scripts/source_graph --version NN --refresh` when the graph is absent.

`scripts/source_graph` requires `--version NN` or explicit `--all`. It writes `.wiki-runtime/graph/postgres-NN/manifest.md`, `graph.json`, `GRAPH_REPORT.md`, optional visualization/export artifacts, and deferred artifact notes when `graphify` is unavailable. By default it uses Graphify's local AST-only update path and does not require an LLM backend/API key. Pass `--semantic --backend gemini|kimi|claude|openai|ollama` only when semantic extraction is explicitly desired.

`scripts/source_graph_check` validates graph manifests, source pins, JSON parseability, wrong-version references, missing project references, and optional query probes.

`scripts/test_source_tools` builds a synthetic temporary wiki/source/graph environment and runs end-to-end checks for graph generation, raw source queries, graph query auto-generation, missing-tool handling, and graph sanity checks.

## Version Control

- Never commit or push without asking for permission.
