# PostgreSQL Engine Wiki Agent Instructions

This repository is an LLM-maintained wiki for PostgreSQL engine internals. The agent writes and maintains the wiki; raw source material is treated as evidence.

## Read Before Writing

- Read `wiki/versions.md` first to identify supported PostgreSQL versions and the primary version.
- Read `wiki/index.md` before modifying or answering from the wiki.
- Read the last ~20 entries of `wiki/log.md` to understand recent activity.
- For version-specific work, read the relevant `wiki/vNN/index.md` before editing version-local pages.
- For any question, answer, report, or generated document, read the matching `.wiki-runtime/context/postgres-NN/manifest.md` and the relevant context artifacts before drafting.
- Search the matching PostgreSQL source tree and the matching `.wiki-runtime/context/postgres-NN/` pack before making any technical claim.

## Evidence Scope

For every question response, report, wiki page, diagram, or generated document, use only the target version's pinned source checkout under `raw/postgres-NN/` and its generated source context under `.wiki-runtime/context/postgres-NN/` as the factual evidence base.

- Treat `wiki/versions.md`, `wiki/index.md`, `wiki/log.md`, and version landing pages as navigation and bookkeeping context, not as independent evidence for PostgreSQL behavior.
- Do not use model memory, external websites, package documentation outside the repository, or uncited prior wiki prose as factual support for generated content.
- Use `.wiki-runtime/context/postgres-NN/` artifacts for source-tree shape, build context, include dependencies, compile database entries, external dependency inventory, and generated call/reference context. When a behavioral claim depends on code, trace it back to the matching file or symbol under `raw/postgres-NN/` and cite that raw path.
- If the matching `.wiki-runtime/context/postgres-NN/` pack is missing, stale against the pinned commit, or insufficient for the question, regenerate or extend the context pack before answering when feasible; otherwise put the gap under `## Open Questions` instead of filling it from another source.
- Never answer about one PostgreSQL version using `raw/` files or `.wiki-runtime/` context from another version.

## Using Source Context Packs

For a target version `NN`, start with `.wiki-runtime/context/postgres-NN/manifest.md`. Confirm the source path, pinned commit, generation commands, tool status, artifact list, and any recorded gaps before relying on the pack.

Use the context artifacts this way:

- `tree-L4.txt` - bounded source-tree orientation for finding files and drawing directory trees. Do not treat it as evidence for behavior by itself.
- `build-config/` and `build-config/inventory.md` - build-system context, copied configure/Meson/Makefile inputs, and generated-header/build assumptions.
- `compile_commands.json` - per-file compilation units, compiler flags, include paths, defines, and build-directory context. Use it to identify the correct headers and generated files for a source file.
- `include-deps.txt` - direct include relationships. Use it to trace structs, macros, declarations, and dependency direction before opening the matching `raw/postgres-NN/` files.
- `callgraphs/*.cflow.txt` - focused call-path navigation for known entry points. Use these to find likely edges, then verify every behavioral claim in the matching raw source.
- `external-deps.txt` - external library and tool inventory from the source/build configuration. Use it only for dependency context; do not infer PostgreSQL runtime behavior from it alone.

Use `scripts/source_deps` for targeted include/dependency queries over the context pack before ad hoc searching. It can show direct includes, reverse include users, per-file compile context, and bounded transitive include edges.

Context-pack artifacts may support claims about source-tree shape, build inputs, compiler flags, include relationships, generated callgraph availability, and external dependency inventory. Runtime, planner, executor, storage, WAL, MVCC, SQL grammar, catalog, GUC, and user-visible behavior claims still require citations to matching files or symbols under `raw/postgres-NN/`.

If a context artifact conflicts with the pinned raw source, the raw source wins. Record the context-pack discrepancy under `## Open Questions` or regenerate the pack with `scripts/source_context` before using the artifact.

## Citation Discipline

- Cite source paths and symbols for every behavioral claim.
- Mandatory citation shape: `[[raw/postgres-NN/src/backend/executor/execMain.c#ExecutorRun]]` (replace NN with the page's version).
- For non-Markdown files you must include the full file extension (.c, .py, .java, etc.).
- Cite from the `raw/postgres-NN/` checkout matching the page's `version:`.
- Use the same citation format for all code references, function names, and symbols mentioned in the text.
- Code references may use aliases for compact display: `[[raw/postgres-NN/path/file.c#symbol|file.c#symbol]]`.
- If a claim is not backed by a source file, symbol, documentation page, commit, or saved design discussion, do not write it as fact.
- Put uncertainty under `## Open Questions` instead of guessing.

## GUC Configuration Changes

- Whenever a wiki page suggests changing a GUC (postgresql.conf parameter, `SET`, `ALTER SYSTEM`, etc.), state whether the change requires a PostgreSQL restart, a reload (`pg_reload_conf()` / `SIGHUP`), or takes effect per-session.
- Determine the requirement from the GUC's `context` in `pg_settings` or its definition in `raw/postgres-NN/src/backend/utils/misc/guc_tables.c` (or the version's equivalent). Cite the source.
- Map `context` values explicitly: `postmaster` → restart required; `sighup` → reload; `superuser` / `user` / `backend` → session or transaction scope, no restart or reload needed beyond the usual reload to change the default.

## Production SQL Snippets

Whenever a wiki page proposes SQL intended to be executed against a production database (diagnostic queries, maintenance commands, one-off fixes, migrations, `ALTER`/`UPDATE`/`DELETE`, etc.):

- Every SQL statement in a report must be verified and correct before the page is filed. Check syntax against the version's grammar and check that referenced catalogs, columns, functions, and GUCs exist in the pinned `raw/postgres-NN/` checkout for the page's version. Do not include SQL that has not been validated; if a snippet cannot be verified, move it under `## Open Questions` rather than presenting it as runnable.

- Embed an inline block-comment tag inside the statement (immediately after the leading verb) that identifies the snippet's purpose so it can be traced from `pg_stat_activity`, logs, or `auto_explain` output. Use `/* snake_case_tag */` form — a short descriptive identifier, not free prose — so query-normalization tools and log greps preserve it. Example:

  ```sql
  SELECT /* wiki_capture_plan_inputs */ ...;
  UPDATE /* wiki_backfill_user_email */ users SET ...;
  ```

  A leading `--` line comment is not sufficient on its own, because many tools and `pg_stat_statements` normalization paths strip or truncate the leading line. The inline `/* ... */` tag must be present on every production-bound statement in the snippet.

- Recommend setting a reasonable `statement_timeout` and `lock_timeout` for the session before running the snippet, sized to the operation. The defaults should protect production from runaway queries and from queueing behind long locks. Example:

  ```sql
  SET statement_timeout = '30s';
  SET lock_timeout = '5s';
  ```

- State that timeouts are session-scoped (`SET`) unless the page explicitly justifies a different scope, and remind the reader to choose values appropriate for the workload (read-only diagnostic vs. DDL vs. bulk DML).

## Verification

Pages carry two distinct verification fields in front matter. They are not interchangeable.

- `verified:` — human-verified. Only a human reviewer may set, change, or remove this field. Agents must never write or modify it. Treat its presence and value as authoritative.
- `verified_by_agent:` — agent-verified. Agents may set or update this field after re-checking the page's claims against the pinned source. Format the value as `<agent-model> <ISO-8601-datetime-UTC>`, for example:

  ```yaml
  verified_by_agent: claude-opus-4-7 2026-05-03T14:30:00Z
  ```

  Use the exact model identifier the agent is running as, and a UTC timestamp in `YYYY-MM-DDTHH:MM:SSZ` form. Use the system-provided current date/time if available; otherwise omit the seconds component. Overwrite any prior `verified_by_agent:` value when re-verifying; do not accumulate history in front matter.

Rules for agents:

- Set `verified_by_agent:` only after a comprehensive review checking all claims and sources on the question, re-checking every behavioral claim on the page against the cited source paths in the matching `raw/postgres-NN/` checkout, and following all agent rules for the wiki.
- If verification fails for any claim, do not set `verified_by_agent:`. Either fix the claim, move it under `## Open Questions`, or leave the field absent.
- When creating new pages or reports (e.g., question pages under `wiki/vNN/questions/`), agents must set `verified: false` and `verified_by_agent: not yet` in front matter. Never change or remove a human-set `verified:`. Treat human-set values as authoritative.
- `verified:` and `verified_by_agent:` are independent. A page may have either, both, or neither.
- For any managed wiki document, including question pages under `wiki/vNN/questions/`, that is not yet verified (`verified: false` with `verified_by_agent: not yet`, missing, or invalid), include an explicit `(unverified)` hint in the visible document title and any index or landing-page link text that names the document. If the document has no visible title, add a first-level heading such as `# Corruption log entries (unverified)` before the body. Do not add a `title:` front-matter field to question pages; question front matter has a fixed schema. Remove the title hint only after the document has a valid agent verification timestamp or a human reviewer sets `verified: true`.

- For question pages under `wiki/vNN/questions/`, front matter must use **exactly** this order:
  ```yaml
  type: question
  version: NN
  pinned_commit: abc123...
  verified: false
  verified_by_agent: model-name YYYY-MM-DDTHH:MM:SSZ
  ```
  Replace placeholders with actual values. Do not add extra fields like `filed`. Set `verified_by_agent` only after verifying claims.

## Version Awareness

- `wiki/versions.md` is the top-level version index and source pin manifest.
- Each supported version has a landing page at `wiki/vNN/index.md`.
- Default new ingests and answers to the primary version unless the user specifies another.
- If the user asks without naming a version, assume the primary version and state that assumption before answering.
- Never answer about one PostgreSQL version using citations from another version's checkout.
- Question pages are pinned to a single version. Filing the same question against another version creates a new question page.

## Wiki Structure

- Keep version-specific pages under `wiki/vNN/`.
- Use Obsidian-style links, such as `[[versions]]` and `[[v17/index]]`.
- Include the version segment for links into per-version directories.
- A page is born when the work justifies it. Do not create empty content stubs.

## Operating Mode

- Trace one source slice or question at a time using the matching generated source context and raw source checkout.
- Prefer `rg`, `git grep`, and short source excerpts over loading entire directories into context.
- Do not create standalone call-chain or source-trace document families. Extend or regenerate `.wiki-runtime/context/postgres-NN/` instead.
- Do not ingest a large source area in one pass unless the model is Opus-class or the user explicitly instructs a full-pass ingest.
- Treat generated pages as drafts until their source references are checked.
- Active-version verification means re-checking page claims against the live `raw/postgres-NN/` checkout rather than relying on the agent's prior context. Use it sparingly.
- Defer active-version verification on `wiki/vNN/index.md` when it exceeds the local context or latency budget.
- Escalate hard traces, such as planner internals, WAL, crash recovery, or MVCC visibility, when the local model cannot keep the call chain straight.
- Always use a unicode/ASCII tree for visual representation of directory trees.

## Bookkeeping

Do these after every meaningful wiki change:

- Update `wiki/index.md` whenever a page is created or substantially changed.
- Update `wiki/versions.md` whenever a supported version is added, removed, archived, re-pinned, or has a meaningful coverage change.
- Update the relevant `wiki/vNN/index.md` whenever version-local pages are created or substantially changed.
- Append an entry to `wiki/log.md` after each scaffold change, ingest, lint pass, filed answer, or version lifecycle event.

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
5. Generate the source-context pack under `.wiki-runtime/context/postgres-NN/` using `scripts/source_context`.
6. Create `wiki/vNN/questions/` only when a filed answer needs it.
7. Update `wiki/index.md`.
8. Append to `wiki/log.md`.

### Refresh Source Context

1. Read `wiki/versions.md` and select the primary version unless the user specified another.
2. Read `wiki/vNN/index.md`.
3. Read `.wiki-runtime/context/postgres-NN/manifest.md` to check the current pack status and gaps.
4. Regenerate or extend `.wiki-runtime/context/postgres-NN/` with `scripts/source_context` when source navigation is stale or insufficient.
5. Search relevant source files under `raw/postgres-NN/` to verify any claims that will be written.
6. Update `wiki/vNN/index.md`, `wiki/index.md`, `wiki/versions.md` when coverage status changes, and `wiki/log.md`.

### Answer And File

1. Assume the primary version unless the user specifies another.
2. Search `wiki/versions.md`, the relevant version landing page, and `wiki/index.md` for navigation and bookkeeping context only.
3. Read `.wiki-runtime/context/postgres-NN/manifest.md` and relevant context artifacts for the target version.
4. Search source evidence under `raw/postgres-NN/` and supporting generated context under `.wiki-runtime/context/postgres-NN/`.
5. Answer with citations to the matching `raw/postgres-NN/` paths and symbols.
6. File durable answers as question pages or fold them into existing pages.
7. Update indexes and log.

### Report Generation And Review

A report here means any answer or wiki page produced from a user prompt — most commonly a question page under `wiki/vNN/questions/` with a `## Question` section.

Reports and generated documents must be written only from the target version's `raw/postgres-NN/` checkout and `.wiki-runtime/context/postgres-NN/` source context. Existing wiki pages may guide placement and prevent duplication, but they are not sufficient evidence for report claims.

When the user asks for a modification, clarification, or follow-up during generation or review, fold it into the report's `## Question` section before updating the answer body — treat it as part of the question itself, not just guidance for the answer.

- Rewrite the `## Question` section for coherence each round; do not append transcript fragments or stack changelogs.
- Update the answer, citations, and downstream sections only after the `## Question` section reflects the full, current scope.
- If the page has no `## Question` section yet, add one seeded from the user's original prompt plus the modification ask.

### Lint The Wiki

Check for:

- Broken Obsidian links.
- Orphan pages.
- Pages without source references.
- Version-local pages with missing or stale `version:` / `pinned_commit:`.
- Pages citing source from the wrong version checkout. If discovered mid-task, stop, flag the discrepancy under `## Open Questions`, and do not rewrite citations without user confirmation.
- Version landing pages missing links to existing version-local pages.
- `wiki/versions.md` coverage notes that disagree with actual pages.
- Invalid or malformed `verified:` / `verified_by_agent:` fields.
- New reports and question pages missing `verified: false`.
- Managed pages missing verification fields (both `verified:` and `verified_by_agent:` absent).
- Question pages under `wiki/vNN/questions/` with front matter not in exact order: `type`, `version`, `pinned_commit`, `verified`, `verified_by_agent`.
- Unverified managed wiki documents, including question pages, missing an `(unverified)` hint in the visible title or in index or landing-page link text.

Use the project-local scripts first:

```bash
scripts/recent_log --limit 20
scripts/wiki_lint
scripts/source_lookup --symbol ExecutorRun
scripts/source_lookup --symbol 'Executor(Run|Start)' --regex --limit 20
scripts/source_lookup --path src/backend/executor/execMain.c --start 1 --limit 80
scripts/source_lookup --log src/backend/executor/execMain.c --limit 20
scripts/source_deps --version 18 --includes src/backend/executor/execMain.c
scripts/source_deps --version 18 --includes src/backend/executor/execMain.c --format json --limit 0
scripts/source_deps --version 18 --included-by executor/executor.h --limit 50
scripts/source_deps --version 18 --compile-unit src/backend/executor/execMain.c --full-command
scripts/source_deps --version 18 --transitive-includes src/backend/executor/execMain.c --depth 2 --limit 100
scripts/test_source_tools
scripts/source_context --version 18 --dry-run
scripts/source_context --version 18 --refresh --skip-callgraphs
scripts/source_context --all --skip-callgraphs
scripts/version_diff --from 18 --to 17 --path src/backend/executor/execMain.c
scripts/source_update --list
scripts/source_update --version 18
scripts/source_update --version 18 --branch REL_18_STABLE --commit <sha>
```

`scripts/source_lookup` defaults to the primary version in `wiki/versions.md`. Use `--symbol` for fixed-string search, add `--regex` for regular expressions, use `--path` with `--start` / `--limit` to print a source slice, and use `--log` to show git history for a path in the checkout.

`scripts/source_deps` also defaults to the primary version. It reads `.wiki-runtime/context/postgres-NN/include-deps.txt` and, when present, `compile_commands.json`. Use `--includes` for direct include edges, `--included-by` for reverse include users, `--compile-unit` for compiler flags/defines/include directories, and `--transitive-includes` with `--depth` for bounded include traversal. Add `--format json` for machine-readable output, `--limit 0` for unlimited rows, and `--full-command` to print the compiler command in text output for `--compile-unit`. JSON compile-unit output always includes the full compile database entries. If a textual context pack has no compiler database, `--compile-unit` reports that gap; regenerate with `scripts/source_context` when compile flags are needed.

`scripts/source_context` generates `.wiki-runtime/context/postgres-NN/` packs. Use `--version NN` for one version, `--all` for every supported version, `--refresh` to clear existing generated context/build output first, `--skip-callgraphs` to avoid cflow/doxygen callgraph work, and `--dry-run` to show target paths without writing. When no compiler database can be produced, it can still generate include dependencies by textual scanning of tracked `.c` / `.h` files; those packs support include queries but not compile-unit queries.

`scripts/test_source_tools` builds a synthetic temporary wiki/source/context environment and runs end-to-end checks for `source_lookup`, `source_deps`, and the `source_context` producer/consumer contract. `scripts/version_diff` requires both source checkouts to exist under `raw/postgres-NN/`. `scripts/source_update` clones or updates a checkout to the commit pinned in `wiki/versions.md`; use `--list` for checkout status and pass `--branch` / `--commit` to override the manifest values.

## Version Control

- Never commit or push without asking for permission.
