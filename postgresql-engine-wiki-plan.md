# PostgreSQL Engine LLM Wiki Implementation Plan

## Purpose

Build an LLM-maintained wiki for understanding the PostgreSQL engine internals. The wiki should be a persistent, source-backed knowledge base over the PostgreSQL source tree, official documentation, relevant commit history, and selected design discussions.

This is not a wiki generated from a PostgreSQL database. It is a wiki about how PostgreSQL itself works.

## Core Goals

- Explain PostgreSQL internals through durable markdown pages.
- Keep every technical claim tied to source files, functions, documentation, commits, or mailing-list threads.
- Maintain a reproducible project-context pack for each supported PostgreSQL version so agents can inspect source layout, build configuration, compilation units, header dependencies, call graphs, and external dependency assumptions without re-discovering the whole project each time.
- Preserve uncertainty instead of inventing intent.
- Let the wiki compound over time as new source areas and questions are investigated.

## Non-Goals

- Do not summarize PostgreSQL behavior from memory without source support.
- Do not document user-facing SQL features unless they illuminate engine behavior.
- Do not ingest raw source code into prose indiscriminately; use generated source-context packs for navigation and synthesize around the questions they answer.
- Do not assume behavior is stable across PostgreSQL versions without checking the pinned source version.

## Proposed Repository Structure

The wiki tracks a fixed set of supported PostgreSQL versions and maintains content per version. Pages are born organically - directories are containers, not pre-declared trees.

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

  v17/
    index.md                # Landing page for the PG 17 wiki
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

AGENTS.md                   # Wiki maintenance instructions for the LLM agent
```

What goes where:

- **`wiki/versions.md`** — the main page for version navigation. It lists every PostgreSQL version covered by the wiki, its support status, source pin, and link to the per-version landing page.
- **`wiki/vNN/index.md`** — the landing page for one PostgreSQL major version. It summarizes coverage for that version, links to the generated source-context pack, and lists filed questions.
- **`wiki/vNN/questions/`** — answers tied to a single version. Questions are inherently snapshots of an investigation against a specific source pin (see Page Types).
- **`.wiki-runtime/context/postgres-NN/`** — generated, reproducible per-version project context: source tree snapshots, build metadata, compiler database, dependency graphs, call graphs, and external dependency notes. This is the source-navigation layer. Heavy artifacts stay out of `wiki/`; the version landing page links to the manifest once the pack exists.

Concrete starting pages and their seeding order are listed in the [Implementation Roadmap](#implementation-roadmap). Do not stub directories with empty files — pages should appear when the work that justifies them happens.

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
| 17      | primary | [[v17/index]] | REL_17_STABLE | abc1234       | query lifecycle, executor |
| 16      | active  | [[v16/index]] | REL_16_STABLE | def5678       | partial |
| 15      | active  | [[v15/index]] | REL_15_STABLE | 9012abc       | partial |
| 14      | legacy  | [[v14/index]] | REL_14_STABLE | 3456def       | archived-style coverage |

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
# PostgreSQL 17

## Source Pin

- Branch: `REL_17_STABLE`
- Commit: `abc1234`
- Status: `primary`

## Coverage

Generated source-context pack: `.wiki-runtime/context/postgres-17/manifest.md`

## Project Context

- Manifest: `.wiki-runtime/context/postgres-17/manifest.md`

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

### Per-Version Project Context Pack

Every supported PostgreSQL version should have a reproducible project-context pack generated from the matching pinned checkout. The pack is not a substitute for source citations; it is an orientation and indexing layer that helps agents navigate the checkout before tracing a claim.

Store generated artifacts under `.wiki-runtime/context/postgres-NN/`, with any build outputs under `.wiki-runtime/build/postgres-NN/`. Record the exact source commit, command lines, tool versions, failures, and regeneration timestamp in `.wiki-runtime/context/postgres-NN/manifest.md`. If a tool is missing or a graph is too expensive, record that as a gap in the manifest and in `wiki/vNN/index.md` under Open Questions instead of pretending the context is complete.

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

The context pack should be regenerated whenever a version is added, re-pinned, or substantially re-indexed. Do not commit the generated artifacts unless the repository policy changes; make the commands reproducible and keep durable human summaries in the wiki.

### What Counts as an Ingest

Unlike the article-shaped sources in the original LLM Wiki idea, PostgreSQL is a giant source tree. To keep the "ingest" concept meaningful, define an ingest as one of:

- **A source-context refresh**: regenerated or extended `.wiki-runtime/context/postgres-NN/` artifacts for a source area or entry point.
- **A filed question trace**: a bounded investigation that produces or updates a question page under `wiki/vNN/questions/`.
- **A doc chapter**: a chapter of `doc/src/sgml/` read for an architectural topic.
- **A mailing-list thread**: a saved thread in `raw/shared/mailing-list/` read to recover design intent.
- **A commit or commit range**: a saved commit or `git log` range in `raw/shared/commits/` read to explain why something is the way it is.

Each ingest defaults to the **primary** version and produces one log entry tagged with the version(s) touched. After producing durable question content on the primary, the agent does an active-version verification pass when active versions exist.

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
version: 17
pinned_commit: abc1234
verified: false
verified_by_agent: not yet
---
```

- `version` — the PostgreSQL major version this page describes.
- `pinned_commit` — the exact source commit checked for this page. It must match `wiki/versions.md` unless the page explicitly records why it is stale.
- `verified` — human verification status. New question pages start with `verified: false`.
- `verified_by_agent` — agent verification status. New question pages start with `verified_by_agent: not yet` unless the agent has completed a full source review.

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

## Evidence

## Related Pages

## Follow-Up Questions
```

A question page stays pinned to a single version, even if its answer happens to be identical across versions. If the user asks the same question against another version, the agent re-investigates it on that version's source and files a new question page with cross-links to the original.

## LLM Maintenance Rules (AGENTS.md)

The repository must include an `AGENTS.md` file. This file is the schema — it is what makes the LLM a disciplined wiki maintainer rather than a chatty assistant. It should be drafted as part of Phase 1 and co-evolved with the wiki. A starting draft:

### Read before writing

- Read `wiki/index.md` before modifying or answering from the wiki.
- Read `wiki/log.md`'s last ~20 entries to understand recent activity.
- Read the matching `.wiki-runtime/context/postgres-NN/manifest.md` and relevant context artifacts before drafting a question response or generated document.
- Search the PostgreSQL source tree before making any technical claim. Generated source-context artifacts can support source-shape and build-context claims, but behavioral claims require matching raw source citations. If a claim is not backed by the allowed evidence for that claim type, do not write it down.

### Citation discipline

- Cite source paths and symbols for every behavioral claim. Format: `src/backend/executor/execMain.c:ExecutorRun`.
- Always cite from the `raw/postgres-NN/` checkout matching the page's `version:`.
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

- Use Obsidian-style links: `[[v17/index]]`, `[[v17/questions/simple-select-query]]`. Include the version segment for links into per-version directories.
- Keep `wiki/versions.md` as the top-level version index and keep each `wiki/vNN/index.md` as the version-local table of contents.
- A page is born when the work justifies it, not before. Do not create empty stubs.
- Do not create standalone code-path or source-trace document families; extend `.wiki-runtime/context/postgres-NN/` instead.

### Dependency locality

- Run wiki tooling from the project root.
- Store PostgreSQL source checkouts under `raw/postgres-NN/`.
- Store generated source-context packs under `.wiki-runtime/context/postgres-NN/`.
- Do not rely on global source indexes for normal operation.
- If a system-level prerequisite is required, document it.

### Bookkeeping (do these every time)

- Update `wiki/index.md` whenever a page is created or substantially changed. Tag entries with their version(s).
- Update `wiki/versions.md` whenever a supported version is added, removed, archived, re-pinned, or has a meaningful coverage change.
- Update the relevant `wiki/vNN/index.md` whenever version-local pages are created or substantially changed.
- Append an entry to `wiki/log.md` after each ingest, lint pass, filed answer, or version lifecycle event. Use the prefix `## [YYYY-MM-DD] <kind> v<NN> | <subject>` (e.g. `## [2026-04-30] answer v17 | simple-select-question`).
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
3. **Create the version landing page.** Create `wiki/vNN/index.md`. Create `wiki/vNN/questions/` only when a durable filed answer needs it. The landing page is real navigation, not a stub.
4. **Generate the project-context pack.** Create or refresh `.wiki-runtime/context/postgres-NN/` from the pinned checkout. At minimum, capture the source tree, build configuration inventory, and manifest; add compiler database, include dependency graph, call graph, and external dependency inventory as tools permit.
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

1. Read `wiki/versions.md` and select the **primary** version unless the user specified another.
2. Read `wiki/vPRIMARY/index.md` to understand existing coverage for that version.
3. Read `.wiki-runtime/context/postgres-PRIMARY/manifest.md` and relevant context artifacts.
4. Inspect relevant directories and README files in `raw/postgres-PRIMARY/`.
5. Identify any missing context roots, include paths, generated-header needs, or callgraph roots.
6. Regenerate or extend `.wiki-runtime/context/postgres-PRIMARY/` with `scripts/source_context`.
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
4. Search the matching `raw/postgres-NN/` and docs for supporting evidence.
5. Answer the user with citations.
6. File durable answers as question pages under `wiki/vNN/questions/` with per-version front matter when the answer should persist.
7. Update `wiki/index.md`, the relevant `wiki/vNN/index.md`, `wiki/versions.md` if coverage changed, and `wiki/log.md`.

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
- Question pages citing source from a different version's checkout than their pin.
- Pages under `wiki/vNN/` citing code from a different version's checkout.
- Orphan pages and broken wiki links (including version-qualified links).
- Pages that are too vague.
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

- `universal-ctags` per checkout, for symbol navigation.
- `tree-sitter` for structured source exploration.
- `doxygen` for generated call/reference maps.
- `bear` or another compiler-database generator for autoconf/Make checkouts.
- `meson`, `ninja`, and Graphviz where the pinned PostgreSQL version and host toolchain support them.
- `cflow` for focused call graph generation around selected PostgreSQL entry points.
- A small `scripts/wiki_lint` tool to detect broken links, orphan pages, missing source references, version/pin mismatches, stale `pinned_commit:`, and stale `verified_against:` entries.
- A small `scripts/source_lookup` wrapper around `rg`, `git grep`, and `git log`, defaulting to the primary version's checkout.
- A small `scripts/version_diff` to compare cited files across two checkouts during active-version verification.
- A small `scripts/source_context` tool to regenerate `.wiki-runtime/context/postgres-NN/` from the pinned checkout and record tool availability, command lines, and incomplete artifacts in the manifest.


Open `wiki/` as an Obsidian vault. Use the graph view during lint passes to spot orphan pages and isolated clusters. Source navigation itself should come from generated context packs under `.wiki-runtime/context/postgres-NN/`, not manually maintained call-chain page families.

Diagrams should be authored as Mermaid blocks inside relevant pages (or in `wiki/diagrams/` if shared across pages). Avoid binary image formats unless screenshotting documentation; Mermaid keeps everything diffable and grep-able.

## Implementation Roadmap

### Phase 1: Wiki Scaffold

- Create the version-agnostic wiki structure: `index.md`, `log.md`, `overview.md`, `versions.md`, `wiki/diagrams/`.
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

Add scripts for:

- Broken wiki link detection
- Orphan page detection
- Missing source reference detection
- Per-version project-context pack generation
- Recent activity summaries from `wiki/log.md`
- Start, stop, status, and log inspection for the local wiki maintainer agent

## First Useful Milestone

The wiki is never "done" — it compounds as long as it's used. But there's a natural first milestone where it starts paying for itself:

- The wiki has a clear global index, overview, and `versions.md` main version index declaring at least one supported version (the primary).
- Each supported version has a `wiki/vNN/index.md` landing page.
- Each supported version has a `raw/postgres-NN/` checkout pinned to a specific commit.
- Each supported version has a generated or explicitly deferred project-context manifest under `.wiki-runtime/context/postgres-NN/`.
- The query lifecycle is navigable from parse through execute on the primary version through generated source-context artifacts.
- Each page has front matter declaring its version scope and includes source references or explicit open questions.
- The agent maintenance rules are documented in `AGENTS.md`, including the version-awareness section.

After this point, growth is driven by the questions you ask, the source areas you investigate through generated context, and the versions you choose to support.
