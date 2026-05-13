# PostgreSQL Engine Wiki Agent Instructions

This repository is an LLM-maintained wiki for PostgreSQL engine internals. The agent writes and maintains the wiki; raw PostgreSQL source is the factual evidence base.

## MANDATORY Read Before Writing

- Read `wiki/versions.md` first to identify supported PostgreSQL versions and the primary version.
- Read `wiki/index.md` before modifying or answering from the wiki.
- Read the last ~20 entries of `wiki/log.md` to understand recent activity.
- For version-specific work, read the relevant `wiki/vNN/index.md` before editing version-local pages.
- For any question, answer, report, or generated document, use the matching `raw/postgres-NN/` checkout as the PostgreSQL evidence base.

## MANDATORY Environment Isolation

Tooling for this project must have minimal impact on the host system. Stay scoped to the repository.

- All Python scripts run from the project venv at `.wiki-runtime/venv/`. Activate it (`source .wiki-runtime/venv/bin/activate`) or invoke scripts as `.wiki-runtime/venv/bin/python scripts/<name>`. Scripts hard-fail with a clear message when run outside the venv.
- If the venv is missing, run `scripts/bootstrap_venv` to create it. That is the only script that may run with the host `python3`.
- Add new Python dependencies to `requirements.txt` at the repo root, with a pinned version. Do not `pip install`, `pipx install`, or otherwise install Python packages globally, into user site-packages, or with `--user`. Do not install packages with `sudo`.
- Read and write only inside this repository (`raw/`, `wiki/`, `.wiki-runtime/`, `scripts/`, `tests/`, `requirements.txt`, top-level docs). Do not touch `$HOME`, mutate global git config, or require root. Treat `raw/postgres-NN/` checkouts as read-only evidence.
- Do not call commands that escalate privilege (`sudo`, `chown` outside the repo, `chmod` on host paths). Network access is allowed only for `scripts/bootstrap_venv` or source-fetch work the user explicitly requests.
- Never use the `WIKI_ALLOW_SYSTEM_PYTHON=1` bypass for normal work. It exists for the test wrapper, which copies scripts into a synthetic temp repo where the venv guard cannot resolve.
- Generated artifacts, caches, and the venv live under `.wiki-runtime/`. Removing that directory is always a safe reset; rebuild the venv with `scripts/bootstrap_venv`.

## MANDATORY Evidence Scope

For every answer, report, wiki page, diagram, or generated document, use only the target version's pinned checkout under `raw/postgres-NN/` as factual evidence. Implementation source is primary evidence. PostgreSQL documentation and tests from the same pinned checkout may also be used as evidence for documented or tested behavior.

- Treat `wiki/versions.md`, `wiki/index.md`, `wiki/log.md`, and version landing pages as navigation and bookkeeping context, not independent evidence for PostgreSQL behavior.
- Do not use model memory, external websites, package documentation outside the repository, or uncited prior wiki prose as factual support for generated content.
- In-tree PostgreSQL documentation, tests, and source history from the same pinned checkout may support claims when they directly apply.
- If implementation source conflicts with documentation or tests, the implementation source wins. Record the discrepancy under `## Open Questions`.
- Never answer about one PostgreSQL version using `raw/` files from another version.

## MANDATORY Deep Inquiry Default

All user questions, reports, and filed answers run in deep-inquiry mode unless the user explicitly asks for a quick answer.

For each question:

- Confirm the target PostgreSQL version.
- Locate the primary source files and symbols, then inspect adjacent callers, callees, structs, macros, includes, generated headers visible in raw source, reverse include users, relevant tests, docs, catalogs, grammar, error paths, GUC definitions, and extension/contrib boundaries.
- If evidence lookup returns an error or cannot produce trustworthy output, abort the current analysis before drafting. Fix and rerun when feasible; otherwise stop and report the target version and error.
- Inspect file or symbol history when the user asks why something exists, when intent matters, or when a regression/change claim is being made.
- Cross-version claims or comparisons need evidence from each relevant version.
- Draft from a claim-to-source evidence map. Every behavioral claim needs a matching raw citation; unresolved claims go under `## Open Questions`.

The minimum depth target for an engine-internals answer is: normal path, relevant error or edge path, key data structures, caller/callee boundary, build or generated-header implications visible from raw source, and tests or explicit test absence. For planner, WAL, crash recovery, MVCC, storage, or corruption topics, missing caller/callee or data-structure context is a verification gap that must be resolved or recorded under `## Open Questions`.

## MANDATORY Citation Discipline

- Cite source paths and symbols for every behavioral claim.
- Mandatory citation shape: `[[raw/postgres-NN/src/backend/executor/execMain.c#ExecutorRun]]`.
- For non-Markdown files you must include the full file extension (`.c`, `.py`, `.java`, etc.).
- Cite from the `raw/postgres-NN/` checkout matching the page's `version:`.
- Use the same citation format for all code references, function names, and symbols mentioned in the text.
- Code references may use aliases for compact display: `[[raw/postgres-NN/path/file.c#symbol|file.c#symbol]]`.
- If a claim is not backed by a source file, symbol, test file, documentation page, commit, or saved design discussion, do not write it as fact.
- Put uncertainty under `## Open Questions` instead of guessing.

## MANDATORY Tone And Readability

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

## MANDATORY GUC Configuration Changes

- Whenever a wiki page suggests changing a GUC (`postgresql.conf`, `SET`, `ALTER SYSTEM`, etc.), state whether the change requires a restart, reload, or only session/transaction scope.
- Determine the requirement from the GUC's context in the pinned raw source (`raw/postgres-NN/src/backend/utils/misc/guc*.c` or the version's equivalent) or from a validated `pg_settings` definition in the same version. Cite the source.
- Map context values explicitly: `postmaster` -> restart required; `sighup` -> reload; `superuser` / `user` / `backend` -> session or transaction scope, no restart or reload beyond changing defaults.

## MANDATORY Production SQL Snippets

Whenever a wiki page proposes SQL intended to be executed against production:

- Verify syntax, referenced catalogs, columns, functions, and GUCs against the pinned `raw/postgres-NN/` checkout before filing. If a snippet cannot be verified, move it under `## Open Questions`.
- Embed an inline block-comment tag immediately after the leading verb in every production-bound statement:

  ```sql
  SELECT /* wiki_capture_plan_inputs */ ...;
  UPDATE /* wiki_backfill_user_email */ users SET ...;
  ```

- Recommend reasonable session-scoped `statement_timeout` and `lock_timeout` values before the snippet, sized to the operation.

## MANDATORY Verification

Pages carry two distinct verification fields in front matter:

- `verified:` — human-verified. Only a human reviewer may set, change, or remove this field.
- `verified_by_agent:` — agent-verified. Agents may set or update this field only after re-checking every claim against the pinned raw source.

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

## MANDATORY Version Awareness

- `wiki/versions.md` is the source pin manifest.
- Each supported version has a landing page at `wiki/vNN/index.md`.
- Default new ingests and answers to the primary version unless the user specifies another.
- If the user asks without naming a version, assume the primary version and state that assumption before answering.
- Hard rule: every source citation must use the matching `raw/postgres-NN/` checkout.
- Never answer about one PostgreSQL version using citations from another version's checkout.

## MANDATORY Wiki Structure

- Keep version-specific pages under `wiki/vNN/`.
- Use Obsidian-style links, such as `[[versions]]` and `[[v18/index]]`.
- Include the version segment for links into per-version directories.
- A page is born when the work justifies it. Do not create empty content stubs.

## MANDATORY Operating Mode

- Trace one source slice or question at a time using the matching raw source checkout.
- Do not create standalone call-chain or source-trace document families.
- Treat generated pages as drafts until their source references are checked.
- Always use a unicode/ASCII tree for visual directory representations.

## MANDATORY Bookkeeping

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

### MANDATORY Add A Supported Version

1. Add the source checkout under `raw/postgres-NN/`.
2. Pin the checkout to an exact commit.
3. Add the version to `wiki/versions.md`.
4. Create `wiki/vNN/index.md`.
5. Create `wiki/vNN/questions/` only when a filed answer needs it.
6. Update `wiki/index.md`.
7. Append to `wiki/log.md`.

### MANDATORY Answer And File

1. Assume the primary version unless the user specifies another.
2. Search `wiki/versions.md`, the relevant version landing page, and `wiki/index.md` for navigation and bookkeeping context only.
3. Build the deep inquiry context envelope from the pinned `raw/postgres-NN/` checkout.
4. Draft a claim-to-source evidence map. Move anything not verified into `## Open Questions`.
5. Answer with citations to matching `raw/postgres-NN/` paths and symbols.
6. File durable answers as question pages or fold them into existing pages. Filed question pages should include `## Context Reviewed`, `## Evidence Map`, and `## Open Questions` when gaps exist.
7. Update indexes and log.

## MANDATORY Lint The Wiki

Check for broken links, orphan pages, missing source references, stale version pins, wrong-version citations, invalid verification fields, unverified title hints, and version landing pages missing links.

Use the project-local scripts first. The examples below assume the project venv is active (`source .wiki-runtime/venv/bin/activate`); otherwise prefix each Python script with `.wiki-runtime/venv/bin/python`.

```bash
scripts/recent_log --limit 20
scripts/wiki_lint
```

## MANDATORY Version Control

- Never commit or push without asking for permission.

## MANDATORY Script Changes

- Keep durable project tooling under `scripts/`, with project-local runtime state under `.wiki-runtime/`.
- When changing script contents, update any adjacent workflow examples, lint examples, or tests that depend on the changed behavior.
- Treat top-level `run_*` files as local launcher scripts. Keep them ignored, and do not edit, cite, or use them for wiki work unless the user explicitly names one.

### MANDATORY TITLE RULE (one-line check)

Before creating, editing, or filing ANY wiki page:
- Look at the frontmatter field `verified:`.
- If it is **not** set to `true`, the top-level title MUST end with ` (unverified)`.
- If it is `true`, the title MUST NOT contain `(unverified)`.

Correct examples:
```markdown
# ExecutorRun (unverified)
# MVCC Visibility (unverified)
# WAL Insertion
```

### MANDATORY verified_by_agent RULE (model name + timestamp)

Before creating, editing, or filing ANY wiki page:
- `verified_by_agent` MUST be present and follow one of these **exact** formats:
  - Draft / not yet fully verified by agent: `verified_by_agent: not yet`
  - Agent-verified (after deep-inquiry, all claims cited, no ## Open Questions): `verified_by_agent: <LLM-model-name> | YYYY-MM-DD HH:MM`
- Use the exact name of the model you are currently running and the current timestamp when you file the page.

Correct examples:
```yaml
verified_by_agent: not yet
verified_by_agent: GPT-5 | 2026-05-13 14:30
```
