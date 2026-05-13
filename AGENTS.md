# PostgreSQL Engine Wiki Agent Instructions

This repo is an LLM-maintained wiki for PostgreSQL internals. The pinned PostgreSQL checkout under `raw/postgres-NN/` is the evidence base.

## MANDATORY Read First

- Read `wiki/versions.md` before modifying or answering from the wiki.
- Read `wiki/index.md`.
- Read the last ~20 entries of `wiki/log.md`.
- For version-local work, read `wiki/vNN/index.md`.
- Use the matching `raw/postgres-NN/` checkout as the PostgreSQL evidence base.

## MANDATORY Environment Isolation

- Stay inside this repo.
- Read/write only `raw/`, `wiki/`, `.wiki-runtime/`, `scripts/`, `tests/`, `requirements.txt`, and top-level docs.
- Treat `raw/postgres-NN/` checkouts as read-only evidence.
- Run Python scripts from `.wiki-runtime/venv/`: activate it or call `.wiki-runtime/venv/bin/python scripts/<name>`.
- If the venv is missing, run `scripts/bootstrap_venv`. Only that script may use host `python3`.
- Pin new Python deps in `requirements.txt`.
- Do not install packages globally, with `--user`, via `pipx`, or with `sudo`.
- Do not use `sudo`, host-path `chown`, or host-path `chmod`.
- Use network only for `scripts/bootstrap_venv` or user-requested source fetches.
- Do not use `WIKI_ALLOW_SYSTEM_PYTHON=1` in normal work.
- Keep generated artifacts, caches, and the venv under `.wiki-runtime/`.

## MANDATORY Evidence

- Use only the target version's pinned `raw/postgres-NN/` checkout as factual evidence.
- Treat implementation source as primary evidence.
- Same-checkout PostgreSQL docs, tests, and source history may support claims when directly relevant.
- Treat `wiki/versions.md`, `wiki/index.md`, `wiki/log.md`, and version landing pages as navigation only.
- Do not use model memory, external websites, external package docs, or uncited prior wiki prose as factual support.
- If implementation source conflicts with docs or tests, source wins. Put the discrepancy under `## Open Questions`.
- Never answer one PostgreSQL version with evidence from another version.

## MANDATORY Deep Inquiry

Deep inquiry is the default unless the user explicitly asks for a quick answer.

- Confirm the target PostgreSQL version.
- Locate primary source files and symbols.
- Inspect adjacent callers, callees, structs, macros, includes, generated headers visible in raw source, reverse include users, tests, docs, catalogs, grammar, error paths, GUCs, and extension/contrib boundaries.
- If evidence lookup fails or is untrustworthy, stop before drafting. Fix it, rerun it, or report the target version and error.
- Inspect history when the user asks why, when intent matters, or when making a regression/change claim.
- For cross-version claims, collect evidence for each relevant version.
- Draft from a claim-to-source map. Put unresolved claims under `## Open Questions`.
- Minimum engine answer: normal path, edge/error path, key data structures, caller/callee boundary, build/generated-header implications visible from raw source, and tests or explicit test absence.
- For planner, WAL, crash recovery, MVCC, storage, or corruption topics, missing caller/callee or data-structure context is a verification gap.

## MANDATORY Citations

- Cite every behavioral claim.
- Use this citation shape: `[[raw/postgres-NN/src/backend/executor/execMain.c#ExecutorRun]]`.
- Include full extensions for non-Markdown files.
- Cite from the `raw/postgres-NN/` checkout matching the page `version:`.
- Use one citation style for code refs, function names, and symbols.
- Aliases are allowed: `[[raw/postgres-NN/path/file.c#symbol|file.c#symbol]]`.
- Do not state a claim as fact unless it is backed by a source file, symbol, test file, documentation page, commit, or saved design discussion.
- Put uncertainty under `## Open Questions`.

## MANDATORY Writing Style

- Lead with the answer.
- Use plain language and short sentences.
- Define PostgreSQL terms of art on first use or link to an existing page.
- Use active voice and name concrete subjects.
- Use lists, tables, and small code blocks for dense material.
- Name conditions precisely. Avoid vague hedges.
- Skip filler and setup prose.
- Cite every example.
- Never trade citation precision for readability.

## MANDATORY GUC Changes

- When suggesting any GUC change, state whether it needs restart, reload, or only session/transaction scope.
- Determine the requirement from the same-version raw GUC definition or a validated `pg_settings` definition.
- Map contexts explicitly: `postmaster` -> restart; `sighup` -> reload; `superuser`, `user`, `backend` -> session/transaction scope.

## MANDATORY Production SQL

- Verify production-bound SQL against the pinned checkout before filing.
- If syntax, catalogs, columns, functions, or GUCs cannot be verified, move the snippet under `## Open Questions`.
- Recommend reasonable session-scoped `statement_timeout` and `lock_timeout` values.
- Add an inline block-comment tag after the leading verb:

```sql
SELECT /* wiki_capture_plan_inputs */ ...;
UPDATE /* wiki_backfill_user_email */ users SET ...;
```

## MANDATORY Verification Fields

- `verified:` is human-only. Agents must not set, change, or remove it.
- `verified_by_agent:` records agent verification. Use `not yet` for drafts. Use the timestamp form only after re-checking every claim against pinned raw source.
- New filed answer pages use this exact front matter order:

```yaml
type: answer
version: NN
pinned_commit: abc123...
verified: false
verified_by_agent: not yet
```

- New filed question pages use the same field order with `type: question`, and must include a `## Question` section that restates the user prompt verbatim:

```yaml
type: question
version: NN
pinned_commit: abc123...
verified: false
verified_by_agent: not yet
```

- Do not set the timestamp form if any claim is unverified. Fix it, move it under `## Open Questions`, or leave `verified_by_agent: not yet`.
- Unverified managed pages must show `(unverified)` in the visible title and in index/landing-page link text until `verified: true`.

Title rule before creating, editing, or filing any wiki page:

- If `verified:` is not `true`, the top-level title must end with ` (unverified)`.
- If `verified:` is `true`, the title must not contain `(unverified)`.

`verified_by_agent` must be one of:

```yaml
verified_by_agent: not yet
verified_by_agent: <LLM-model-name> | YYYY-MM-DD HH:MM
```

Use the exact current model name and timestamp when filing an agent-verified page.

## MANDATORY Version Awareness

- `wiki/versions.md` is the source pin manifest.
- Each supported version has `wiki/vNN/index.md`.
- Default new ingests and answers to the primary version unless the user specifies another.
- If the user omits a version, assume the primary version and state that assumption.
- Every source citation must use the matching `raw/postgres-NN/` checkout.
- Never use citations from another PostgreSQL version.

## MANDATORY Wiki Structure

- Keep version-specific pages under `wiki/vNN/`.
- Within each `wiki/vNN/`, file pages by `type:` into a per-type subdirectory:
  - `wiki/vNN/questions/` for `type: question` pages.
  - `wiki/vNN/answers/` for `type: answer` pages.
  - `wiki/vNN/concepts/` for `type: concept` pages.
- The version landing page `wiki/vNN/index.md` stays at the version root and is the only page allowed there.
- Use Obsidian links, e.g. `[[versions]]`, `[[v18/index]]`, `[[v12/questions/fk-join-optimization-two-tables]]`.
- Include the version segment and the type subdirectory in links into per-version directories.
- Create a page only when the work justifies it.
- Do not create standalone call-chain or source-trace document families.
- Treat generated pages as drafts until source references are checked.
- Use a unicode/ASCII tree for visual directory representations.

## MANDATORY Bookkeeping

After each meaningful wiki change:

- Update `wiki/index.md` for created or substantially changed pages.
- Update `wiki/versions.md` for supported-version lifecycle, repin, or meaningful coverage changes.
- Update `wiki/vNN/index.md` for created or substantially changed version-local pages.
- Append to `wiki/log.md` after scaffold changes, ingests, lint passes, filed answers, or version lifecycle events.

Log heading format:

```md
## [YYYY-MM-DD] <kind> v<NN> | <subject>
## [YYYY-MM-DD] <kind> | <subject>
```

## Core Workflows

### MANDATORY Add A Supported Version

1. Add the source checkout under `raw/postgres-NN/`.
2. Pin it to an exact commit.
3. Add it to `wiki/versions.md`.
4. Create `wiki/vNN/index.md`.
5. Update `wiki/index.md`.
6. Append to `wiki/log.md`.

### MANDATORY Answer And File

1. Assume the primary version unless the user specifies another.
2. Use `wiki/versions.md`, `wiki/index.md`, and the version landing page as navigation only.
3. Build the deep-inquiry context envelope from the pinned checkout.
4. Draft a claim-to-source map.
5. Move unverified claims to `## Open Questions`.
6. Answer with matching-version raw citations.
7. File durable answers as version-local pages or fold them into existing pages.
8. Include `## Context Reviewed`, `## Evidence Map`, and `## Open Questions` in filed pages when gaps exist.
9. Update indexes and log.

## MANDATORY Lint

Check broken links, orphan pages, missing source references, stale pins, wrong-version citations, invalid verification fields, unverified title hints, and version landing-page links.

Use the project venv:

```bash
scripts/recent_log --limit 20
scripts/wiki_lint
```

## MANDATORY Version Control

- Never commit or push without permission.

## MANDATORY Script Changes

- Keep durable project tooling under `scripts/`.
- Keep runtime state under `.wiki-runtime/`.
- When changing script contents, update adjacent workflow examples, lint examples, or tests that depend on the change.
- Keep top-level `run_*` files ignored. Do not edit, cite, or use them for wiki work unless the user explicitly names one.
