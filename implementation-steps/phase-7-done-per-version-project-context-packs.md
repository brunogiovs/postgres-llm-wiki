# Phase 7 Done: Per-Version Project Context Packs

## Status

Done. `scripts/source_context` exists, both supported versions have generated minimum context packs under `.wiki-runtime/context/postgres-NN/`, and deferred heavyweight artifacts are recorded in each manifest and version landing page.

## Goal

Create and maintain reproducible project-context packs for every supported PostgreSQL version so agents can orient themselves before tracing source-backed claims.

The pack is generated context, not evidence by itself. Behavioral claims still require direct citations into the matching `raw/postgres-NN/` checkout.

## Inputs

- `postgresql-engine-wiki-plan.md`
- `wiki/versions.md`
- Existing supported source checkouts under `raw/postgres-NN/`
- Existing runtime storage policy under `.wiki-runtime/`

## Runtime Layout

```text
.wiki-runtime/
  build/
    postgres-NN/
  context/
    postgres-NN/
      manifest.md
      tree-L4.txt
      build-config/
      compile_commands.json
      include-deps.txt
      callgraphs/
      external-deps.txt
```

## Implementation Order

1. Add `scripts/source_context`.
2. Generate the always-cheap artifacts first: context directory, manifest skeleton, tree snapshot, build-configuration inventory, and external dependency inventory.
3. Add best-effort compiler database generation.
4. Add include-dependency generation, preferring the compiler database and falling back to direct compiler dependency output.
5. Add best-effort call/reference graph generation.
6. Run the tool for every supported version and update the matching version landing pages.
7. Run lint and record the work in `wiki/log.md`.

## Script Contract

Implement `scripts/source_context` as a project-local Python script that follows the existing maintenance script style.

Required behavior:

- Reuse `wiki_tooling.py` helpers: `REPO_ROOT`, `RUNTIME_ROOT`, `load_versions`, `primary_version`, `source_checkout`, `append_tool_log`, and `die`.
- Default to the primary version from `wiki/versions.md` when no version is provided.
- Accept `--version NN`, `--all`, `--refresh`, `--skip-callgraphs`, and `--dry-run`.
- Read only from `raw/postgres-NN/` and write generated output only under `.wiki-runtime/context/postgres-NN/` and `.wiki-runtime/build/postgres-NN/`.
- Never treat optional tooling failure as a total script failure when the minimum pack can still be written.
- Exit non-zero for missing source checkouts, unsupported versions, manifest write failures, or invalid arguments.

Suggested command shapes:

```bash
scripts/source_context
scripts/source_context --version 18
scripts/source_context --all
scripts/source_context --version 12 --skip-callgraphs
scripts/source_context --version 18 --refresh --dry-run
```

## Manifest Requirements

Generate `.wiki-runtime/context/postgres-NN/manifest.md`.

The manifest must record:

- PostgreSQL version, branch, and exact pinned commit from `wiki/versions.md`.
- Source checkout path and context-pack path.
- Regeneration timestamp in ISO-8601 format.
- Tool versions or missing-tool status for `git`, `tree`, compiler, `meson`, `ninja`, `bear`, `doxygen`, `dot`, `cflow`, `pkg-config`, and any other tool invoked.
- Every command attempted, with arguments redacted through the existing helper discipline where relevant.
- Generated artifact list.
- Per-artifact status: `generated`, `skipped`, `deferred`, or `failed`.
- Per-artifact failures with command attempted, exit code, and short stderr summary when available.
- Deferred or missing artifacts and the reason they are incomplete.

The manifest should be stable across repeated runs on an unchanged source pin. Aside from the timestamp, re-running `scripts/source_context --version NN` should produce textually equivalent manifest content.

## Artifact Requirements

### Project Structure

Capture a bounded directory tree:

```bash
tree -L 4 --dirsfirst -I 'build|target|.git|__pycache__|autom4te.cache|tmp_check' raw/postgres-NN
```

Write it to `.wiki-runtime/context/postgres-NN/tree-L4.txt`. If `tree` is unavailable, use an ASCII fallback and record the fallback in the manifest.

### Build Configuration

Capture PostgreSQL build inputs into `.wiki-runtime/context/postgres-NN/build-config/`.

Include available autoconf/Make and Meson inputs such as:

- `Makefile`
- `configure`
- `configure.ac`
- `GNUmakefile.in`
- `src/Makefile.global.in`
- `meson.build`
- `meson_options.txt`
- `config/*.m4`

The inventory should reflect that PostgreSQL uses autoconf/Make across supported versions and Meson in newer versions; do not add CMake assumptions.

### Compiler Database

Generate `.wiki-runtime/context/postgres-NN/compile_commands.json` when feasible.

For Meson-capable checkouts, prefer:

```bash
meson setup .wiki-runtime/build/postgres-NN raw/postgres-NN
cp .wiki-runtime/build/postgres-NN/compile_commands.json .wiki-runtime/context/postgres-NN/compile_commands.json
```

For autoconf/Make-only checkouts, use a VPATH build with Bear or an equivalent compiler-database tool:

```bash
mkdir -p .wiki-runtime/build/postgres-NN
cd .wiki-runtime/build/postgres-NN
../../../raw/postgres-NN/configure --prefix="$PWD/install"
bear -- make -j
cp compile_commands.json ../../context/postgres-NN/compile_commands.json
```

If Meson, Bear, the compiler, or the host build fails, mark this artifact as `deferred` and keep the rest of the pack.

### Include Dependencies

Generate `.wiki-runtime/context/postgres-NN/include-deps.txt`.

Prefer deriving include relationships from `compile_commands.json`. If no compiler database exists, use a compiler fallback over tracked source and header files:

```bash
git -C raw/postgres-NN ls-files '*.c' '*.h' |
  sed 's#^#raw/postgres-NN/#' |
  xargs gcc -MM -MG -Iraw/postgres-NN/src/include \
    > .wiki-runtime/context/postgres-NN/include-deps.txt
```

Record generated build include directories when they are available. If dependency generation cannot run, mark it as `deferred`.

### Call And Reference Graphs

Write generated graph outputs under `.wiki-runtime/context/postgres-NN/callgraphs/`.

Accept Doxygen plus Graphviz for broad project orientation, cflow for focused roots, or both. For cflow, start with PostgreSQL entry points that help future traces, such as `PostgresMain`, `exec_simple_query`, `standard_planner`, and `ExecutorRun`.

Record the graph tool, roots, scope, output files, and limitations in the manifest. If graph generation is too expensive or a tool is missing, mark the artifact as `deferred`.

### External Dependencies

Generate `.wiki-runtime/context/postgres-NN/external-deps.txt`.

Capture dependency assumptions from:

- `configure --help`
- `meson_options.txt` when present
- generated build logs when present
- selected host probes such as `pkg-config --list-all`

Separate host-wide package availability from dependencies PostgreSQL actually checks or enables.

## Deferred Artifact Rule

The minimum successful pack is:

- `manifest.md`
- `tree-L4.txt` or its recorded fallback
- `build-config/`
- `external-deps.txt` or a recorded reason it could not be generated

If compiler database, include-dependency, or callgraph generation cannot complete, do not abort. Record the deferred artifact in the manifest and add a matching `## Open Questions` entry to the relevant `wiki/vNN/index.md`.

## Version Run

Run the context pack for every currently supported version:

- PostgreSQL 18 primary: `scripts/source_context --version 18`
- PostgreSQL 12 legacy: `scripts/source_context --version 12`

Legacy versions may defer more artifacts because their build systems and compiler expectations can predate current host tooling. That is acceptable only when the deferral is explicit in the manifest and version landing page.

## Wiki Updates

After generating or refreshing a pack:

- Add or update a `## Project Context` section in the matching `wiki/vNN/index.md`.
- Link the manifest path, for example `.wiki-runtime/context/postgres-NN/manifest.md`.
- Add `## Open Questions` entries for deferred artifacts if the landing page does not already list them.
- Update `wiki/versions.md` only if the supported-version coverage note changes.
- Append a log entry per version:

```md
## [YYYY-MM-DD] context vNN | project context pack

- Generated or refreshed `.wiki-runtime/context/postgres-NN/manifest.md`.
- Recorded generated artifacts and deferred gaps.
```

## Git Ignore Check

Confirm `.gitignore` ignores generated runtime output. The current broad rule should cover both paths:

```text
.wiki-runtime/
```

Do not commit generated context packs unless the repository policy changes.

## Definition Of Done

- Every supported version has either a generated `.wiki-runtime/context/postgres-NN/manifest.md` or a clearly logged deferral.
- The context pack records source pin, regeneration timestamp, commands, tool versions, artifacts, per-artifact failures, and gaps.
- Re-running `scripts/source_context --version NN` on an unchanged pin is idempotent: artifacts and manifest content are textually equivalent aside from the timestamp.
- Heavy generated artifacts stay under `.wiki-runtime/` and remain ignored by git (`.gitignore` covers `.wiki-runtime/build/` and `.wiki-runtime/context/`).
- Version landing pages link to the manifest when the pack is generated, and list deferred artifacts under Open Questions when the pack is incomplete.
- `scripts/wiki_lint` runs after any wiki-facing edits.
