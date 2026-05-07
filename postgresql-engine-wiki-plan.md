# PostgreSQL Engine LLM Wiki Implementation Plan

## Purpose

Build an LLM-maintained wiki for understanding the PostgreSQL engine internals. The wiki should be a persistent, source-backed knowledge base over the PostgreSQL source tree, official documentation, relevant commit history, and selected design discussions.

This is not a wiki generated from a PostgreSQL database. It is a wiki about how PostgreSQL itself works.

## Core Goals

- Explain PostgreSQL internals through durable markdown pages.
- Keep every technical claim tied to source files, functions, documentation, commits, or mailing-list threads.
- Maintain a reproducible project-context pack for each supported PostgreSQL version so agents can inspect source layout, build configuration, compilation units, header dependencies, call graphs, and external dependency assumptions without re-discovering the whole project each time.
- Make every inquiry deep by default: before answering, assemble a broad version-pinned context envelope that covers the relevant source neighborhood, callers, callees, includes, build flags, generated context, tests, documentation, history, and known gaps.
- Preserve uncertainty instead of inventing intent.
- Let the wiki compound over time as new source areas and questions are investigated.

## Non-Goals

- Do not summarize PostgreSQL behavior from memory without source support.
- Do not document user-facing SQL features unless they illuminate engine behavior.
- Do not ingest raw source code into prose indiscriminately; use generated source-context packs for navigation and synthesize around the questions they answer.
- Do not assume behavior is stable across PostgreSQL versions without checking the pinned source version.

## Current Repository Structure

The wiki tracks a fixed set of supported PostgreSQL versions and maintains content per version. Pages are born organically - directories are containers, not pre-declared trees. The current supported versions are declared in `wiki/versions.md`; at the time of this plan sync they are PostgreSQL 18 as `primary` and PostgreSQL 12 as `legacy`.

```text
.wiki-runtime/
  build/
    postgres-NN/             # generated build tree for one pinned checkout
  context/
    postgres-NN/             # regenerated project-context pack for one pinned checkout
      manifest.md            # commands, tool versions, source pin, and artifact inventory
      tree-L4.txt            # bounded source tree snapshot
      build-config/          # copied or summarized build files
      compile_commands.json  # compiler database, when generation succeeds
      include-deps.txt       # header/source dependency graph
      callgraphs/            # generated call/reference graph outputs
      external-deps.txt      # dependency and pkg-config/configure/meson findings

raw/
  postgres-18/              # PG 18 checkout, pinned commit on REL_18_STABLE
  postgres-12/              # PG 12 checkout, pinned commit on REL_12_STABLE
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

  v18/
    index.md                # Landing page for the PG 18 wiki
  v12/
    index.md                # Landing page for the PG 12 wiki
    questions/              # Filed answers, pinned to v12
  _archive/
    vNN/                    # Archived content of removed versions

AGENTS.md                   # Wiki maintenance instructions for the LLM agent
scripts/
  recent_log                # Print recent activity from wiki/log.md
  wiki_lint                 # Link, metadata, verification, and source-reference lint
  source_lookup             # Version-pinned source lookup and source git history
  source_deps               # Version-pinned include/dependency and compile-unit lookup
  source_context            # Version-pinned context-pack generation
  source_context_check      # Raw-source-rooted context-pack sanity checker
  source_update             # Clone/update pinned PostgreSQL source checkouts
  source_rebuild            # Rebuild a checkout at the latest release tag for a major
  version_diff              # Diff one source path across two explicit versions
  test_source_tools         # Synthetic end-to-end tests for source tooling
```

What goes where:

- **`wiki/versions.md`** — the main page for version navigation. It lists every PostgreSQL version covered by the wiki, its support status, source pin, and link to the per-version landing page.
- **`wiki/vNN/index.md`** — the landing page for one PostgreSQL major version. It summarizes coverage for that version, links to the generated source-context pack, and lists filed questions.
- **`wiki/vNN/questions/`** — answers tied to a single version. Questions are inherently snapshots of an investigation against a specific source pin (see Page Types).
- **`.wiki-runtime/context/postgres-NN/`** — generated, reproducible per-version project context: source tree snapshots, build metadata, compiler database, dependency graphs, call graphs, and external dependency notes. This is the source-navigation layer. Heavy artifacts stay out of `wiki/`; the version landing page links to the manifest once the pack exists.

Concrete starting pages and their seeding order are listed in the [Implementation Roadmap](#implementation-roadmap). Do not stub directories with empty files — pages should appear when the work that justifies them happens.

## Current Implementation Snapshot

The repository has moved beyond the original scaffold plan in these areas:

- PostgreSQL 18 and PostgreSQL 12 are supported in `wiki/versions.md`, with pinned checkouts under `raw/postgres-18/` and `raw/postgres-12/`.
- Both supported versions have generated project-context packs under `.wiki-runtime/context/postgres-NN/`, including manifests, bounded source trees, build configuration inventories, compiler databases, include dependency extracts, external dependency inventories, and focused callgraphs where available.
- Source tooling is project-local and version-pinned. `scripts/source_lookup`, `scripts/source_deps`, and `scripts/source_context_check` require `--version NN`; `scripts/source_context` requires `--version NN` or intentional `--all`; `scripts/version_diff` requires `--from NN --to MM`.
- `scripts/test_source_tools` runs synthetic end-to-end tests that exercise lookup, dependency queries, context generation, raw-rooted context-pack sanity checks, fallback include scanning, compile database handling, and the explicit-version enforcement.
- `AGENTS.md` is the active maintenance contract. It now includes source-context evidence rules, citation discipline, GUC-change handling, production SQL snippet requirements, human and agent verification fields, unverified title hints, report-generation rules, lint checks, and the hard source-tool version-pin rule.

## Version Strategy

The wiki supports a fixed, declared set of PostgreSQL major versions. Each supported version has its own pinned source checkout and its own per-version wiki content.

### The Main Version Index

`wiki/versions.md` is both the human-facing version index and the source of truth for which versions the wiki supports. It should be easy to open this page in Obsidian and choose the PostgreSQL version to browse.

Example:

```md
# PostgreSQL Versions

This page indexes the PostgreSQL versions covered by the wiki.

| Version | Status  | Wiki Home | Branch        | Pinned Commit | Coverage |
|---------|---------|-----------|---------------|---------------|----------|
| 18      | primary | [[v18/index]] | REL_18_STABLE | 6cb307...     | generated context pack |
| 12      | legacy  | [[v12/index]] | REL_12_STABLE | 45b882...     | generated context pack; corruption-message catalog |

## Archived Versions

| Version | Removed On | Reason            |
|---------|------------|-------------------|
```

Status meanings:

- **primary** — exactly one. The default target for new ingests. New pages are written against this version first.
- **active** — kept close to the primary. New primary work should trigger an active-version verification pass.
- **legacy** — best-effort. Existing pages are preserved; new pages are not automatically checked here. Questions can still be filed.
- (archived — see the Remove a Supported Version workflow.)

Pins are commit hashes, not floating tags, so point releases do not silently shift claims.

Each supported version also has a landing page at `wiki/vNN/index.md`. That page is the version-local table of contents:

```md
# PostgreSQL 18

## Source Pin

- Branch: `REL_18_STABLE`
- Commit: `6cb307251c5c6261286c1566496920976640108e`
- Status: `primary`

## Coverage

Generated source-context pack: `.wiki-runtime/context/postgres-18/manifest.md`

## Project Context

- Manifest: `.wiki-runtime/context/postgres-18/manifest.md`

## Open Questions

- ...
```

### Source References

Every wiki page references its source from the matching `raw/postgres-NN/` checkout. Behavioral claims must cite the matching raw checkout, not another version's checkout and not uncited prior wiki prose.

Preferred citation form:

```md
[[raw/postgres-NN/src/backend/executor/execMain.c#ExecutorRun]]
```

Compact aliases are allowed when they still preserve the raw path target:

```md
[[raw/postgres-NN/src/backend/executor/execMain.c#ExecutorRun|execMain.c#ExecutorRun]]
```

Use full file extensions in citations and cite every code reference, function, struct, macro, GUC definition, grammar/catalog location, documentation page, commit, or saved design discussion that backs a claim. Put uncertainty under `## Open Questions` instead of filling gaps from memory.

### Per-Version Project Context Pack

Every supported PostgreSQL version should have a reproducible project-context pack generated from the matching pinned checkout. The pack is not a substitute for source citations; it is an orientation and indexing layer that helps agents navigate the checkout before tracing a claim.

Store generated artifacts under `.wiki-runtime/context/postgres-NN/`, with any build outputs under `.wiki-runtime/build/postgres-NN/`. Record the exact source commit, command lines, tool versions, failures, and regeneration timestamp in `.wiki-runtime/context/postgres-NN/manifest.md`. If a tool is missing or a graph is too expensive, record that as a gap in the manifest and in `wiki/vNN/index.md` under Open Questions instead of pretending the context is complete.

Implemented command contract:

```bash
scripts/source_context --version 18 --dry-run
scripts/source_context --version 18 --refresh --skip-callgraphs
scripts/source_context --all --skip-callgraphs
```

`scripts/source_context` requires an explicit scope: `--version NN` for one supported version or `--all` for every supported version. It probes tool availability, writes a manifest, captures a bounded tree, copies build-configuration inputs, inventories external dependencies, tries to generate or reuse `compile_commands.json`, derives `include-deps.txt`, and writes focused cflow/Doxygen callgraph artifacts when tooling permits. When no compiler database is available, it falls back to a textual scan of tracked `.c` and `.h` files so include-dependency queries remain useful even though compile-unit queries are deferred.

Agents query context packs through `scripts/source_deps --version NN` before doing ad hoc include chasing. It supports direct includes, reverse include users, per-file compile-unit context, bounded transitive include edges, text/JSON output, row limits, and full compiler-command display.

Agents sanity-check context packs through `scripts/source_context_check --version NN`, optionally with `--path <raw-relative-path>` for a focused raw artifact. The checker starts from raw `.c` / `.h` files, walks live include dependencies through the pack's compile/include context, cross-checks the raw-derived graph against `include-deps.txt`, scans all context artifacts for missing or wrong-version project references, validates manifest/build-config/compile-db/callgraph consistency, and probes the source navigation commands. Use `--strict` when raw dependency coverage warnings should fail the command.

### Source Context Tool Testing Requirements

The synthetic tests in `tests/test_source_tools.py` define the regression envelope for the source-context tools. Keep the tests synthetic enough to run quickly without depending on the real PostgreSQL checkouts, but realistic enough to exercise the producer/consumer contracts between `scripts/source_context`, `scripts/source_context_check`, `scripts/source_deps`, and `scripts/source_lookup`.

The test suite should prove these high-level requirements:

- **Explicit scope enforcement** - `scripts/source_lookup`, `scripts/source_deps`, and `scripts/source_context_check` reject omitted `--version NN`; `scripts/source_context` rejects omitted `--version NN` or `--all`; unsupported versions fail before source or context artifacts are used.
- **Source lookup behavior** - `scripts/source_lookup --version NN` can print bounded source slices, search fixed symbols, search regular expressions, and show per-file git history from the selected `raw/postgres-NN/` checkout. Regex lookup should still work through the git-grep fallback path when `rg` is unavailable.
- **Dependency resolution behavior** - `scripts/source_deps --version NN --includes` resolves raw headers, generated build headers, and unresolved system headers distinctly, and reports that distinction consistently in JSON output.
- **Reverse and transitive dependency behavior** - reverse include lookup reports source users in a stable order that prioritizes repeated include directives, while transitive include lookup respects depth and limit controls and terminates cleanly on include cycles.
- **Compile-unit behavior** - compile database queries expose defines, include paths, and the full compiler command when requested; missing compile database entries fail with actionable text and JSON responses.
- **Output contract behavior** - text and JSON modes both honor `--limit`; truncated text output tells the maintainer to raise the limit, and truncated JSON output sets a machine-readable `truncated` flag.
- **Path safety and missing-pack behavior** - dependency queries reject paths outside the selected `raw/postgres-NN/` checkout and report missing context manifests with a clear `scripts/source_context --version NN` remediation path.
- **Context-pack generation behavior** - `scripts/source_context --version NN --skip-callgraphs` writes a manifest and an `include-deps.txt` format consumable by `scripts/source_deps`, using compile-database-derived include edges when `compile_commands.json` exists and textual scanning of tracked `.c` and `.h` files when it does not.
- **Raw-rooted context-pack check behavior** - `scripts/source_context_check --version NN --path <raw-file>` starts from the raw artifact, walks live include dependencies, reports pack coverage gaps against `include-deps.txt`, scans all context artifacts for stale references, and exercises `source_lookup`, `source_deps`, `source_context --dry-run`, and cross-version diff probes when applicable.
- **Fallback status behavior** - textual fallback generation marks `compile_commands.json` as `deferred`, marks `include-deps.txt` as `generated`, marks skipped callgraphs as `skipped`, and makes compile-unit queries fail with a remediation message rather than silently inventing compile context.

The context pack should include:

1. **Project structure** - a bounded directory tree, using a unicode or ASCII tree format:

   ```bash
   tree -L 4 --dirsfirst -I 'build|target|.git|__pycache__|autom4te.cache|tmp_check' raw/postgres-NN \
     > .wiki-runtime/context/postgres-NN/tree-L4.txt
   ```

2. **Build configuration** - PostgreSQL-specific build inputs. PostgreSQL uses autoconf/Make across supported versions and Meson in newer versions, not CMake as its normal build system. Capture the available files for the pinned checkout, such as `Makefile`, `configure`, `configure.ac`, `GNUmakefile.in`, `src/Makefile.global.in`, `meson.build`, `meson_options.txt`, and relevant `config/*.m4` files.

3. **Compiler database** - generate `compile_commands.json` when feasible. For Meson-capable versions, prefer a project-local build tree:

   ```bash
   meson setup .wiki-runtime/build/postgres-NN raw/postgres-NN
   cp .wiki-runtime/build/postgres-NN/compile_commands.json \
     .wiki-runtime/context/postgres-NN/compile_commands.json
   ```

   For autoconf/Make-only versions, use a project-local VPATH build with Bear or an equivalent compiler-database tool:

   ```bash
   mkdir -p .wiki-runtime/build/postgres-NN
   cd .wiki-runtime/build/postgres-NN
   ../../../raw/postgres-NN/configure --prefix="$PWD/install"
   bear -- make -j
   cp compile_commands.json ../../context/postgres-NN/compile_commands.json
   ```

4. **Include dependency graph** - derive header-to-source relationships from the actual include paths when possible. Prefer using `compile_commands.json`; a fallback can use `gcc -MM -MG` over tracked C and header files, with `src/include` and generated build include directories on the include path:

   ```bash
   git -C raw/postgres-NN ls-files '*.c' '*.h' |
     sed 's#^#raw/postgres-NN/#' |
     xargs gcc -MM -MG -Iraw/postgres-NN/src/include \
       > .wiki-runtime/context/postgres-NN/include-deps.txt
   ```

5. **Function and call graphs** - keep at least one generated call/reference graph artifact per version. For whole-project orientation, Doxygen with Graphviz is useful; for focused traces, cflow roots should match PostgreSQL entry points such as `PostgresMain`, `exec_simple_query`, `standard_planner`, `ExecutorRun`, or the source area being investigated. Store outputs under `.wiki-runtime/context/postgres-NN/callgraphs/`.

6. **External dependency inventory** - capture project dependency assumptions from `configure --help`, `meson_options.txt`, build logs, and selected host probes such as `pkg-config --list-all`. The manifest should distinguish host-wide package availability from dependencies PostgreSQL actually checks or enables.

Future context-pack extensions should broaden answer context, not just make lookup faster:

- **Symbol/reference index** - definitions and bounded reference lists for functions, structs, macros, enums, global variables, GUCs, wait events, and error codes, generated from the pinned checkout and consumed through explicit `--version NN` tools.
- **Test and fixture index** - regression tests, isolation specs, TAP tests, expected files, and test helpers grouped by source area so answers can check intended behavior as well as implementation.
- **Documentation and catalog index** - relevant `doc/src/sgml/`, `src/include/catalog/`, generated catalog inputs, grammar files, system view definitions, and extension SQL files mapped to source areas.
- **History index** - bounded `git log` slices for cited files and symbols so agents can inspect why-sensitive changes without doing full history archaeology on every question.
- **Known-gap inventory** - manifest entries should distinguish unavailable tool output, untraced callers/callees, missing generated headers, absent tests, and unresolved source/version questions.

The context pack should be regenerated whenever a version is added, re-pinned, or substantially re-indexed. Do not commit the generated artifacts unless the repository policy changes; make the commands reproducible and keep durable human summaries in the wiki.

### Deep Inquiry Context Envelope

All user questions and filed reports run in deep-inquiry mode unless the user explicitly asks for a quick answer. Deep-inquiry mode is not permission to dump more prose; it is a requirement to inspect a wider evidence neighborhood before deciding what is true.

For each question, the agent builds a context envelope before drafting:

1. **Version and scope** - identify the target PostgreSQL version, state the primary-version assumption when needed, and keep every source command pinned to that version.
2. **Existing navigation** - read `wiki/versions.md`, `wiki/index.md`, the relevant `wiki/vNN/index.md`, recent `wiki/log.md` entries, and any existing related question pages for placement and duplicate avoidance only.
3. **Context-pack status** - read `.wiki-runtime/context/postgres-NN/manifest.md`, note artifact status and gaps, and regenerate or extend the pack when the missing artifact is needed for the question.
4. **Source neighborhood** - locate the primary files and symbols, then inspect adjacent callers, callees, structs, macros, includes, compile-unit flags, generated headers, and reverse include users through `scripts/source_lookup` and `scripts/source_deps`.
5. **Behavioral neighborhood** - check relevant tests, catalog definitions, grammar rules, documentation, error paths, GUC definitions, and extension/contrib boundaries when the question touches them.
6. **History and version boundary** - inspect file or symbol history when intent, regression risk, or "why" is part of the question. Use `scripts/version_diff --from NN --to MM` only when the answer claims cross-version behavior or the user asks for comparison.
7. **Evidence map** - draft the answer from a claim-to-source map: each behavioral claim has a matching raw citation, while unresolved claims move to `## Open Questions`.

The minimum depth target for an engine-internals answer is: normal path, relevant error or edge path, key data structures, caller/callee boundary, build/generated-header context when applicable, and tests or explicit test absence. For planner, WAL, crash recovery, MVCC, storage, or corruption topics, treat missing caller/callee or data-structure context as a blocker to verification unless it is called out under `## Open Questions`.

### What Counts as an Ingest

Unlike the article-shaped sources in the original LLM Wiki idea, PostgreSQL is a giant source tree. To keep the "ingest" concept meaningful, define an ingest as one of:

- **A source-context refresh**: regenerated or extended `.wiki-runtime/context/postgres-NN/` artifacts for a source area or entry point.
- **A filed question trace**: a bounded investigation that produces or updates a question page under `wiki/vNN/questions/`.
- **A doc chapter**: a chapter of `doc/src/sgml/` read for an architectural topic.
- **A mailing-list thread**: a saved thread in `raw/shared/mailing-list/` read to recover design intent.
- **A commit or commit range**: a saved commit or `git log` range in `raw/shared/commits/` read to explain why something is the way it is.

Each ingest targets an explicit PostgreSQL version in its source-tool operations. If the user did not name a version, the agent may assume the **primary** version only after stating that assumption, then every source command still uses `--version NN` or the relevant explicit cross-version flags. Each ingest produces one log entry tagged with the version(s) touched. After producing durable question content on the primary, the agent does an active-version verification pass when active versions exist.

### Pin Bumps Within a Supported Version

When the pin for an already-supported version is moved (e.g. PG 17 point release brings new commits), treat it as a lint trigger, not a re-ingest:

1. Update the pin in `wiki/versions.md`.
2. Regenerate or mark stale the `.wiki-runtime/context/postgres-NN/` project-context pack for that version.
3. Diff the previous and new commits for files cited by existing pages tagged with that version.
4. For each citation that points into a changed region, re-verify the claim and either update the page or flag it under Open Questions.
5. For question pages, also bump `pinned_commit:` only if the citation was actively re-verified.
6. Note the bump and resulting churn in `wiki/log.md`.

Do not blindly re-trace pages on every bump — only the ones whose cited code actually moved.

## Page Types

Every wiki page declares its version scope via YAML front matter. Pages under `wiki/vNN/` are single-version pages.

### Per-version front matter

Used by question pages under `wiki/vNN/`:

```yaml
---
type: question
version: NN
pinned_commit: abc123...
verified: false
verified_by_agent: not yet
---
```

- `version` — the PostgreSQL major version this page describes.
- `pinned_commit` — the exact source commit checked for this page. It must match `wiki/versions.md` unless the page explicitly records why it is stale.
- `verified` — human verification status. New question pages start with `verified: false`.
- `verified_by_agent` — agent verification status. New question pages start with `verified_by_agent: not yet` unless the agent has completed a full source review.

Question front matter uses exactly this key order: `type`, `version`, `pinned_commit`, `verified`, `verified_by_agent`. Agents must not add extra question front-matter fields such as `filed`.

`verified:` is human-controlled; agents never set, change, or remove it. `verified_by_agent:` may be set only after a comprehensive re-check of all page claims against the matching pinned source and context pack, using `<agent-model> <ISO-8601-datetime-UTC>`. Unverified managed wiki documents must show `(unverified)` in the visible title and in index or landing-page link text until either a human sets `verified: true` or an agent writes a valid `verified_by_agent:` timestamp after verification.

If the same question deserves an answer for another version, that is a new question page in that version's directory, cross-linked to the original.

### Generated Source Context

Source orientation, file maps, include relationships, and call-path discovery belong in generated context packs under `.wiki-runtime/context/postgres-NN/`, not in manually maintained source-trace page families.

When a source area needs better navigation, regenerate or extend the context pack. Durable prose should be filed as a question page only when it answers a specific investigation.

### Question Pages

Question pages preserve useful answers from investigation. Live under `wiki/vNN/questions/` and use the per-version front matter.

Recommended sections:

```md
# Question

## Short Answer

## Detailed Answer

## Context Reviewed

## Evidence Map

## Evidence

## Related Pages

## Follow-Up Questions
```

`## Context Reviewed` records the source/context envelope actually inspected: manifest, core files and symbols, dependency queries, callgraph artifacts, tests, docs, catalog or grammar files, and history/diffs when relevant. `## Evidence Map` lists the important claims and their backing raw citations so information gaps are visible before prose smooths them over.

A question page stays pinned to a single version, even if its answer happens to be identical across versions. If the user asks the same question against another version, the agent re-investigates it on that version's source and files a new question page with cross-links to the original.

## LLM Maintenance Rules (AGENTS.md)

`AGENTS.md` is the active maintenance contract for the repository. It is what makes the LLM a disciplined wiki maintainer rather than a chatty assistant, and it should be co-evolved with the wiki whenever tooling or evidence rules change. The current implemented rules include:

### Read before writing

- Read `wiki/versions.md` first to identify supported PostgreSQL versions and the primary version.
- Read `wiki/index.md` before modifying or answering from the wiki.
- Read `wiki/log.md`'s last ~20 entries to understand recent activity.
- For version-specific work, read the relevant `wiki/vNN/index.md` before editing version-local pages.
- Read the matching `.wiki-runtime/context/postgres-NN/manifest.md` and relevant context artifacts before drafting a question response or generated document.
- Search the matching PostgreSQL source tree and matching `.wiki-runtime/context/postgres-NN/` pack before making any technical claim.

### Evidence scope

- Use only the target version's pinned source checkout under `raw/postgres-NN/` and generated source context under `.wiki-runtime/context/postgres-NN/` as factual evidence for generated reports, answers, diagrams, and wiki pages.
- Treat `wiki/versions.md`, `wiki/index.md`, `wiki/log.md`, and version landing pages as navigation and bookkeeping context, not independent evidence for PostgreSQL behavior.
- Do not use model memory, external websites, package documentation outside the repository, or uncited prior wiki prose as factual support.
- Context-pack artifacts can support source-tree shape, build inputs, compiler flags, include relationships, generated callgraph availability, and external dependency inventory. Runtime, planner, executor, storage, WAL, MVCC, SQL grammar, catalog, GUC, and user-visible behavior claims still need citations to matching raw source.
- If a context pack is missing, stale against the pinned commit, or insufficient for a question, regenerate or extend it when feasible; otherwise record the gap under `## Open Questions`.

### Citation discipline

- Cite source paths and symbols for every behavioral claim.
- Mandatory citation shape: `[[raw/postgres-NN/src/backend/executor/execMain.c#ExecutorRun]]`.
- For non-Markdown files, include the full file extension.
- Cite from the `raw/postgres-NN/` checkout matching the page's `version:`.
- Use aliases only when the target still contains the full raw path, such as `[[raw/postgres-NN/path/file.c#symbol|file.c#symbol]]`.
- When uncertain, write the claim under `## Open Questions` rather than guessing intent.
- Never paraphrase code in a way that adds behavior the code does not exhibit.

### Version awareness

- Read `wiki/versions.md` first to know which versions are supported and which is primary.
- When browsing the wiki, use `wiki/versions.md` as the entry point, then follow the relevant `wiki/vNN/index.md` landing page.
- Default new ingests, traces, and answers to the **primary** version unless the user specifies another.
- If the user asks a question without naming a version, assume the primary version and state that assumption before answering.
- Hard rule: every source-tool operation must use an explicit version scope. Use `--version NN` for single-version tools, `--from NN --to MM` for cross-version diffs, and `--all` only when intentionally operating on every supported version.
- Do not rely on primary-version defaults for source tools.
- Never silently answer about one version using citations from another. If a page is verified for one version only, do not extend it to another without re-checking the source.
- Question pages are pinned to a single version. Filing the same question against another version creates a new question page, not an edit to the original.

### Wiki structure

- Use Obsidian-style links: `[[vNN/index]]`, `[[vNN/questions/simple-select-query]]`. Include the version segment for links into per-version directories.
- Keep `wiki/versions.md` as the top-level version index and keep each `wiki/vNN/index.md` as the version-local table of contents.
- A page is born when the work justifies it, not before. Do not create empty stubs.
- Do not create standalone code-path or source-trace document families; extend `.wiki-runtime/context/postgres-NN/` instead.

### Dependency locality

- Run wiki tooling from the project root.
- Store PostgreSQL source checkouts under `raw/postgres-NN/`.
- Store generated source-context packs under `.wiki-runtime/context/postgres-NN/`.
- Store generated build trees under `.wiki-runtime/build/postgres-NN/`.
- Do not rely on global source indexes for normal operation.
- If a system-level prerequisite is required, document it.

### GUC and production SQL rules

- Whenever a wiki page suggests changing a PostgreSQL GUC, state whether the change requires restart, reload, or session/transaction scope. Determine this from the GUC context in the matching version's source and cite it.
- Production-bound SQL snippets must be syntactically and catalog-verified against the pinned version before filing.
- Every production-bound SQL statement must include an inline block-comment tag immediately after the leading verb, such as `SELECT /* wiki_capture_plan_inputs */ ...`.
- Production snippets should recommend reasonable session-scoped `statement_timeout` and `lock_timeout` values and remind readers to choose values appropriate for the workload.

### Report generation and review

- Reports and generated documents must use only the target version's raw checkout and source-context pack as evidence.
- Reports and generated documents must be prepared through the Deep Inquiry Context Envelope. The filed page should include `## Context Reviewed` and `## Evidence Map` unless the document type has a stronger local template.
- When the user modifies or clarifies a prompt during generation, fold that into the page's `## Question` section before revising the answer body.
- Rewrite the `## Question` section coherently rather than appending transcript fragments.

### Bookkeeping (do these every time)

- Update `wiki/index.md` whenever a page is created or substantially changed. Tag entries with their version(s).
- Update `wiki/versions.md` whenever a supported version is added, removed, archived, re-pinned, or has a meaningful coverage change.
- Update the relevant `wiki/vNN/index.md` whenever version-local pages are created or substantially changed.
- Append an entry to `wiki/log.md` after each scaffold change, ingest, lint pass, filed answer, or version lifecycle event. Use `## [YYYY-MM-DD] <kind> v<NN> | <subject>` for version-specific work and `## [YYYY-MM-DD] <kind> | <subject>` for version-agnostic work.
- File durable answers as question pages under the investigated version's `questions/` directory when they should persist; do not let them disappear into chat history.
- Never edit `raw/` except when explicitly adding new source material via the Add a Supported Version workflow.

### When in doubt

- Trace, don't summarize. If asked something high-level, prefer to follow real code than to generalize.
- Preserve uncertainty. "I don't know yet" plus a logged Open Question is more valuable than a confident wrong answer.

### Local-model operating mode

When the wiki is maintained by a local model on a 16GB NVIDIA GPU, keep the agent workflow narrow:

- Trace one source slice or question at a time.
- Prefer `rg`, `git grep`, and short source excerpts over loading entire directories into context.
- Do not ask the model to ingest a large source area in one pass unless a stronger hosted model is being used.
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
AGENTS.md
```

Per-version directories (`wiki/vNN/...`) and `raw/postgres-NN/` checkouts are created via the Add a Supported Version workflow, not preemptively.

Add starter templates for each page type, including the front-matter blocks defined in Page Types. `wiki/versions.md` starts as the main version index, even if it initially has no supported versions.

### 2. Add a Supported Version

Trigger: a new PG major releases, or you decide to support an older one.

Inputs: version number, branch name, pinned commit, target status (`primary`, `active`, or `legacy`).

Agent flow:

1. **Add the source.** Create `raw/postgres-NN/` as a checkout of the pinned commit on `REL_NN_STABLE`, normally through `scripts/source_update --version NN`.
2. **Update the version index.** Add a row to `wiki/versions.md`. If the new version is being made `primary`, demote the previous primary to `active` in the same edit.
3. **Create the version landing page.** Create `wiki/vNN/index.md`. Create `wiki/vNN/questions/` only when a durable filed answer needs it. The landing page is real navigation, not a stub.
4. **Generate the project-context pack.** Create or refresh `.wiki-runtime/context/postgres-NN/` from the pinned checkout with `scripts/source_context --version NN`. At minimum, capture the source tree, build configuration inventory, and manifest; add compiler database, include dependency graph, call graph, and external dependency inventory as tools permit.
5. **Backfill verification pass.**
   - For per-version pages, create a new `wiki/vNN/...` page only when the content has actually been checked or intentionally copied with clear source references for NN.
   - If the behavior diverges, write the divergence in the new version page and cross-link related versions.
   - If it is not yet checked, leave it out of the new version's page set and add an Open Question on `wiki/vNN/index.md`.
   - **Question pages are excluded from automatic backfill.** They stay pinned to the version they were filed against.
6. **Re-lint.** Run the lint workflow to surface anything stale.
7. **Log.** One summary entry, e.g.:
   ```md
   ## [2026-04-30] add-version v18 | promoted to primary; v17 demoted to active; context generated
   ```

The backfill is the expensive step. Do not mark a new version as verified just because one cited file is unchanged; behavior can depend on headers, callees, macros, and nearby control flow. Batch the work and report a summary, do not pause on every page.

### 3. Remove a Supported Version

Trigger: a PG major reaches EOL, or you decide to stop maintaining it.

Inputs: version number, removal mode (`archive` or `drop`).

**Default to `archive` — never destructive.** `drop` is reserved for cleanup of an erroneously-added version and requires explicit user confirmation.

Agent flow (archive):

1. **Update the version index.** Move the row in `wiki/versions.md` from the active table to the "Archived Versions" table at the bottom. Record the archival date and reason.
2. **Move version-specific content.** `wiki/vNN/` → `wiki/_archive/vNN/`. Likewise `raw/postgres-NN/` → `raw/_archive/postgres-NN/`.
3. **Update the index.** Remove vNN entries from active sections; add a one-line pointer to the archive.
4. **Log.**
   ```md
   ## [2026-04-30] remove-version v14 | archived (EOL)
   ```

Agent flow (drop): same as archive but pages and source are deleted outright. Always confirm with the user before doing this.

#### Status transitions

The two workflows above are how versions enter and leave. Day-to-day status changes happen separately and are cheap:

- `active` → `primary`: bumping the default target for new ingests. One edit to `wiki/versions.md`, no content moves.
- `active` → `legacy`: stop checking new pages here by default, but still answer questions. Lint stops flagging it for missing active-version checks.
- `legacy` → archived: via the Remove workflow.

### 4. Refresh Source Context

Example request:

```text
Refresh source context for src/backend/executor.
```

Agent flow:

1. Read `wiki/versions.md` and select the explicit target version, using the primary version only after stating that assumption when the user did not specify one.
2. Read `wiki/vNN/index.md` to understand existing coverage for that version.
3. Read `.wiki-runtime/context/postgres-NN/manifest.md` and relevant context artifacts.
4. Inspect relevant directories and README files in `raw/postgres-NN/`.
5. Identify any missing context roots, include paths, generated-header needs, or callgraph roots.
6. Regenerate or extend `.wiki-runtime/context/postgres-NN/` with `scripts/source_context --version NN`.
7. **Active-version pass:** for each `active` version, refresh or mark stale its matching context pack before claiming comparable coverage.
8. Update `wiki/index.md`, `wiki/versions.md` if coverage changed, and the affected `wiki/vNN/index.md` pages. Append to `wiki/log.md` with the version tag.

### 5. Answer and File

Example request:

```text
Why does PostgreSQL use memory contexts?
```

Agent flow:

1. Determine which version the question is being asked against. If unclear, assume the primary version and state that assumption explicitly before answering.
2. Search existing wiki pages (start with `wiki/versions.md`, then the relevant `wiki/vNN/index.md`, then `wiki/index.md`).
3. Read the matching `.wiki-runtime/context/postgres-NN/manifest.md` and relevant context artifacts for orientation.
4. Build the Deep Inquiry Context Envelope: search the matching `raw/postgres-NN/` and generated context with explicit version-pinned tooling, inspect primary symbols plus callers/callees/includes/compile units, and check relevant tests, docs, catalogs, grammar, history, and context-pack gaps.
5. Draft an evidence map that ties each behavioral claim to a matching raw citation. Move anything not verified into `## Open Questions`.
6. Answer the user with citations, including the important context limits when they matter.
7. File durable answers as question pages under `wiki/vNN/questions/` with per-version front matter, `## Context Reviewed`, and `## Evidence Map` when the answer should persist.
8. Update `wiki/index.md`, the relevant `wiki/vNN/index.md`, `wiki/versions.md` if coverage changed, and `wiki/log.md`.

The bias toward filing is deliberate: explorations should compound in the wiki the same way ingested sources do.

### 6. Lint the Wiki

Periodic maintenance request:

```text
Lint the wiki.
```

Agent checks:

- Pages without source references.
- Pages under `wiki/vNN/` without matching `version:` and `pinned_commit:`.
- Pages whose `pinned_commit:` is stale relative to `wiki/versions.md`.
- Question pages without `version:` or `pinned_commit:`.
- Invalid or malformed `verified:` / `verified_by_agent:` fields.
- New reports and question pages missing `verified: false`.
- Managed pages missing verification fields.
- Question pages under `wiki/vNN/questions/` whose front matter is not exactly ordered as `type`, `version`, `pinned_commit`, `verified`, `verified_by_agent`.
- Unverified managed wiki documents missing `(unverified)` in the visible title or in index/landing-page link text.
- Filed question pages missing `## Context Reviewed`, `## Evidence Map`, or an explicit `## Open Questions` section when the context envelope found gaps.
- Question pages citing source from a different version's checkout than their pin.
- Pages under `wiki/vNN/` citing code from a different version's checkout.
- Orphan pages and broken wiki links (including version-qualified links).
- Pages that are too vague.
- Version landing pages missing links to existing version-local pages.
- `wiki/versions.md` coverage notes that disagree with the actual version-local pages.
- Pages that should have been checked for an `active` version but weren't.

## Suggested Tooling

Use the project-local scripts first. Source tools must be pinned to a PostgreSQL version:

```bash
scripts/recent_log --limit 20
scripts/wiki_lint
scripts/source_lookup --version 18 --symbol ExecutorRun
scripts/source_lookup --version 18 --symbol 'Executor(Run|Start)' --regex --limit 20
scripts/source_lookup --version 18 --path src/backend/executor/execMain.c --start 1 --limit 80
scripts/source_lookup --version 18 --log src/backend/executor/execMain.c --limit 20
scripts/source_deps --version 18 --includes src/backend/executor/execMain.c
scripts/source_deps --version 18 --included-by executor/executor.h --limit 50
scripts/source_deps --version 18 --compile-unit src/backend/executor/execMain.c --full-command
scripts/source_deps --version 18 --transitive-includes src/backend/executor/execMain.c --depth 2 --limit 100
scripts/source_context --version 18 --dry-run
scripts/source_context --version 18 --refresh --skip-callgraphs
scripts/source_context --all --skip-callgraphs
scripts/source_context_check --version 18 --path src/backend/executor/execMain.c --depth 3
scripts/source_context_check --all --strict
scripts/version_diff --from 18 --to 12 --path src/backend/executor/execMain.c
scripts/source_update --list
scripts/source_update --version 18
scripts/test_source_tools
```

Implemented script responsibilities:

- `scripts/recent_log` prints recent `wiki/log.md` entries.
- `scripts/wiki_lint` checks links, source references, version/pin metadata, verification fields, front-matter order, wrong-version citations, and unverified title/link hints.
- `scripts/source_lookup` searches symbols/text, prints source slices, and shows source git history for an explicit `--version NN`.
- `scripts/source_deps` queries `.wiki-runtime/context/postgres-NN/include-deps.txt` and `compile_commands.json` for direct includes, reverse include users, compile-unit details, and transitive include edges. It supports text/JSON output, limits, and full compile command display.
- `scripts/source_context` regenerates context packs with explicit `--version NN` or `--all`; it supports `--refresh`, `--skip-callgraphs`, and `--dry-run`.
- `scripts/source_context_check` starts from raw source artifacts, walks live include dependencies, cross-checks the generated context pack, and exercises source navigation commands.
- `scripts/source_update` clones or updates a checkout to the pin in `wiki/versions.md`, with optional branch/commit override.
- `scripts/source_rebuild` reclones a checkout at the latest release tag for a major and updates the source pin.
- `scripts/version_diff` compares one source path across two explicit source checkouts.
- `scripts/test_source_tools` runs the synthetic end-to-end source-tool test suite.

External tools used by the implemented scripts when available:

- `git`, `rg`, and Python for source lookup, git history, tests, and lint.
- `tree` for bounded source tree snapshots, with an ASCII fallback when missing.
- `cc`, `gcc`, `clang`, `make`, `meson`, `ninja`, and `bear` for build probing and compiler database generation.
- `doxygen`, Graphviz `dot`, and `cflow` for generated call/reference artifacts.
- `pkg-config` and PostgreSQL build files for external dependency inventory.

Additional optional tools such as `universal-ctags` and `tree-sitter` can still be added later, but source navigation currently comes from the generated context packs and the project-local scripts above.

Open `wiki/` as an Obsidian vault. Use the graph view during lint passes to spot orphan pages and isolated clusters. Source navigation itself should come from generated context packs under `.wiki-runtime/context/postgres-NN/`, not manually maintained call-chain page families.

Diagrams are optional. When they are useful, prefer Mermaid blocks inside the relevant page so the evidence and explanation stay together. Avoid binary image formats unless screenshotting documentation; Mermaid keeps everything diffable and grep-able.

## Implementation Roadmap

### Phase 1: Wiki Scaffold

- Create the version-agnostic wiki structure: `index.md`, `log.md`, `overview.md`, and `versions.md`.
- Ignore runtime directories from git if this repo uses git.
- Draft `AGENTS.md` with the maintenance rules.
- Add page templates with the per-version front matter block.
- Record the local-model operating profile in `AGENTS.md`: 16GB NVIDIA GPU, Hermes Agent, default model, context target, and narrow-source-tracing rules.

### Phase 2: Bootstrap Supported Versions

- Decide which PG majors to support at launch. A reasonable starting set is the latest stable as `primary` plus the previous major as `active`. Add older versions only when there's a real need — each one is real bookkeeping.
- Run the Add a Supported Version workflow for each, in newest-first order. The first version added becomes `primary`.
- Generate the per-version project-context pack for each supported version, or record the missing tools and deferred artifacts in the context manifest and version landing page.
- The active-version verification pass is trivial on the first add (no existing pages) and grows with each subsequent add.

### Phase 3: Query Lifecycle Source Context

Seed generated source context for the query lifecycle:

1. Parser
2. Analyzer
3. Rewriter
4. Planner
5. Executor

For each stage, make sure source orientation is available through `.wiki-runtime/context/postgres-NN/` artifacts such as `tree-L4.txt`, `compile_commands.json`, `include-deps.txt`, and focused callgraphs. Do not create standalone source-trace pages.

### Phase 6: Maintenance Tooling

Implemented scripts:

- `scripts/recent_log` for recent activity summaries from `wiki/log.md`.
- `scripts/wiki_lint` for broken links, orphan warnings, missing source references, version/pin drift, wrong-version citations, verification metadata, front-matter ordering, and unverified title/link hints.
- `scripts/source_lookup` for version-pinned source search, source slices, and source git history.
- `scripts/source_deps` for version-pinned include/dependency and compile-unit context queries over generated context packs.
- `scripts/source_context` for per-version project-context pack generation and refresh.
- `scripts/source_context_check` for raw-source-rooted source-context pack sanity checks.
- `scripts/source_update` and `scripts/source_rebuild` for checkout lifecycle operations.
- `scripts/version_diff` for explicit cross-version source path comparisons.
- `scripts/test_source_tools` for source-tool regression coverage.

### Phase 7: Source Context and Tool Contracts

Completed. The current contract is:

- Every supported version has a context pack or an explicit context-pack gap under `.wiki-runtime/context/postgres-NN/`.
- Context packs record source pin, source path, context path, generation timestamp, tool versions, attempted commands, artifact statuses, and deferred or failed artifacts.
- `include-deps.txt` uses a structured format consumable by `scripts/source_deps`, with compile-database-derived edges when available and textual scan fallback when not.
- Source tools enforce explicit version scope. Single-version tools require `--version NN`; cross-version diffs require `--from NN --to MM`; context generation across all versions requires explicit `--all`.
- Synthetic end-to-end tests cover source lookup, dependency queries, context generation fallback paths, compile database consumption, and missing-version enforcement.

## First Useful Milestone

The wiki is never "done" — it compounds as long as it's used. But there's a natural first milestone where it starts paying for itself:

- The wiki has a clear global index, overview, and `versions.md` main version index declaring at least one supported version (the primary).
- Each supported version has a `wiki/vNN/index.md` landing page.
- Each supported version has a `raw/postgres-NN/` checkout pinned to a specific commit.
- Each supported version has a generated or explicitly deferred project-context manifest under `.wiki-runtime/context/postgres-NN/`.
- The query lifecycle is navigable from parse through execute on the primary version through generated source-context artifacts.
- Each page has front matter declaring its version scope and includes source references or explicit open questions.
- The project-local source tools enforce explicit version pins and are covered by `scripts/test_source_tools`.
- The agent maintenance rules are documented in `AGENTS.md`, including source-context evidence scope, citation discipline, verification metadata, production SQL/GUC rules, lint rules, report-generation rules, and the hard source-tool version-pin rule.

After this point, growth is driven by the questions you ask, the source areas you investigate through generated context, and the versions you choose to support.
