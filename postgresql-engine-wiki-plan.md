# PostgreSQL Engine LLM Wiki Implementation Plan

## Purpose

Build an LLM-maintained wiki for understanding PostgreSQL engine internals. Durable prose is backed by the pinned PostgreSQL source checkouts under `raw/postgres-NN/`.

## Core Goals

- Explain PostgreSQL internals through durable Markdown pages.
- Keep every behavioral claim tied to raw source files, symbols, documentation, commits, or saved design discussions.
- Use a per-version Graphify graph as the navigation layer, not as behavioral evidence.
- Query raw source only through `scripts/source_graph_query --version NN ...`.
- Preserve uncertainty instead of inventing intent.

## Repository Structure

```text
.wiki-runtime/
  graph/
    postgres-NN/
      manifest.md
      graph.json
      GRAPH_REPORT.md
      graph.html
      cache/

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

scripts/
  recent_log
  wiki_lint
  source_graph
  source_graph_query
  source_graph_check
  source_update
  source_rebuild
  version_diff
  test_source_tools
```

## Source Navigation Contract

`scripts/source_graph_query` is the only source-query interface agents should use.

Raw subcommands read `raw/postgres-NN/` directly:

```bash
scripts/source_graph_query --version 18 symbol ExecutorRun
scripts/source_graph_query --version 18 symbol '\bExecutorRun\b' --regex --limit 20
scripts/source_graph_query --version 18 file src/backend/executor/execMain.c --start 1 --limit 80
scripts/source_graph_query --version 18 log src/backend/executor/execMain.c --limit 20
scripts/source_graph_query --version 18 includes src/backend/executor/execMain.c --format json
scripts/source_graph_query --version 18 included-by executor/executor.h --limit 50
```

Graph subcommands query `.wiki-runtime/graph/postgres-NN/graph.json`; if the graph is absent, the wrapper forces generation through `scripts/source_graph --version NN --refresh`:

```bash
scripts/source_graph_query --version 18 explain ExecutorRun
scripts/source_graph_query --version 18 path PostgresMain ExecutorRun
scripts/source_graph_query --version 18 query "show the executor flow" --dfs
```

`scripts/source_graph` generates per-version graphs:

```bash
scripts/source_graph --version 18 --dry-run
scripts/source_graph --version 18 --refresh
scripts/source_graph --all
```

Graph generation uses Graphify's local AST-only update path by default and does not require an LLM API key. Semantic extraction is opt-in with `--semantic --backend ...`.

`scripts/source_graph_check` validates graph manifests, pins, JSON parseability, wrong-version references, missing project references, and optional query probes:

```bash
scripts/source_graph_check --version 18 --probe-node ExecutorRun
```

Graphify graph output is orientation material only. Every PostgreSQL behavior claim must be verified against and cited to `raw/postgres-NN/`.

## Version Strategy

- `wiki/versions.md` is the source pin manifest.
- Each supported version has a pinned checkout under `raw/postgres-NN/`.
- Each supported version may have generated Graphify artifacts under `.wiki-runtime/graph/postgres-NN/`.
- New answers default to the primary version unless the user specifies another version.
- Cross-version claims require `scripts/version_diff --from NN --to MM`.

## Page Rules

- Keep version-local pages under `wiki/vNN/`.
- Question pages are pinned to a single version.
- Every behavioral claim needs a raw source citation.
- Unverified managed pages must show `(unverified)` in visible title/link text.
- Follow the tone and readability rules in [AGENTS.md](AGENTS.md) (`## Tone And Readability`): lead with the answer, plain language, short sentences, active voice, named conditions instead of vague hedges. Readability never overrides citation discipline.
- New question pages use front matter in this order:

```yaml
type: question
version: NN
pinned_commit: abc123...
verified: false
verified_by_agent: not yet
```

## Workflows

### Add A Supported Version

1. Add/update the source checkout with `scripts/source_update --version NN`.
2. Pin the checkout in `wiki/versions.md`.
3. Create or update `wiki/vNN/index.md`.
4. Generate the graph with `scripts/source_graph --version NN --refresh`.
5. Check the graph with `scripts/source_graph_check --version NN`.
6. Update `wiki/index.md` and `wiki/log.md`.

### Refresh A Source Graph

1. Read `wiki/versions.md`.
2. Run `scripts/source_graph --version NN --refresh`.
3. Run `scripts/source_graph_check --version NN`.
4. Update version landing-page graph status and `wiki/log.md`.

### Answer And File

1. Determine the target version.
2. Use `scripts/source_graph_query --version NN ...` raw and graph subcommands to build a source envelope.
3. Check relevant callers, callees, structs, macros, includes, tests, docs, catalogs, grammar, error paths, GUC definitions, and extension boundaries.
4. Draft from a claim-to-source evidence map.
5. Put gaps under `## Open Questions`.
6. File the answer and update indexes/log.
7. Apply the tone and readability rules from [AGENTS.md](AGENTS.md) (`## Tone And Readability`) on the drafted prose before filing.

## Testing

`scripts/test_source_tools` runs synthetic tests for:

- explicit version enforcement;
- raw source symbol/file/log/include queries;
- graph generation with a fake Graphify CLI;
- forced graph generation when `graph.json` is absent;
- missing Graphify handling;
- graph sanity checks and wrong-version reference detection.

## First Useful Milestone

- Supported versions are pinned in `wiki/versions.md`.
- Each supported version has a `raw/postgres-NN/` checkout.
- Source graph tooling is the only supported source-query path.
- Wiki answers cite raw source paths and symbols.
- `scripts/test_source_tools` and `scripts/wiki_lint` pass.
