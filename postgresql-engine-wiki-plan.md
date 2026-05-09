# PostgreSQL Engine LLM Wiki Implementation Plan

## Purpose

Build an LLM-maintained wiki for understanding PostgreSQL engine internals. Durable prose is backed by the pinned PostgreSQL source checkouts under `raw/postgres-NN/`.

## Core Goals

- Explain PostgreSQL internals through durable Markdown pages.
- Keep every behavioral claim tied to raw source files, symbols, documentation, commits, or saved design discussions.
- Use a per-version Graphify graph as the navigation layer, not as behavioral evidence.
- Query raw source only through `scripts/source_graph_query --version NN ...`.
- Preserve uncertainty instead of inventing intent.

## Plan Synchronisation Rule

**This plan is the source of truth for every script under `scripts/`. Any change to a script — new flag, renamed argument, altered behaviour, new dependency, removed file, new artifact, changed exit code — must be accompanied by an update to this plan in the same change.**

- The plan must be sufficient to recreate every script from scratch. If you cannot reconstruct the script from this document plus `wiki_tooling.py`, the plan is out of date.
- Apply the rule symmetrically: do not edit the plan to describe behaviour that is not yet implemented, and do not edit a script without updating the matching section here.
- Sections that must be kept in sync when a script changes:
  - `## Repository Structure` — when files are added, moved, or removed.
  - `## Pinned Tooling` — when any pinned version (uv, CPython, `graphifyy`, or any future binary) bumps.
  - `## Shared Helpers — scripts/wiki_tooling.py` — when helpers, constants, or regexes change.
  - `## Script Specifications` — when any script's CLI, side effects, exit codes, or pipeline change.
  - `## Testing` — when test scenarios or the fake-graphify contract change.
  - `## Implementation Steps` — when the rebuild order changes (e.g. a new script becomes a dependency).
- `README.md` and `AGENTS.md` follow this plan; update them in the same change when user-facing surfaces change.
- This plan covers both script architecture and agent-behavior rules (reading protocol, deep inquiry, citation discipline, verification fields, GUC and SQL discipline, operating mode, bookkeeping, version control). AGENTS.md restates these rules for the agent's quick reference; any change to either document must update the other in the same change.
- Reviewers should reject any pull request that touches `scripts/` without a corresponding edit to this plan, and vice versa.

## Repository Structure

```text
.wiki-runtime/
  bin/                       # Project-local uv binary (and uvx)
  python/                    # Managed CPython interpreter installed by uv
  uv-cache/                  # uv's package and metadata cache
  uv-tools/                  # uv tool installs (kept project-local)
  venv/                      # Project-local Python virtual environment
  graph/
    postgres-NN/
      manifest.md
      graph.json
      GRAPH_REPORT.md
      graph.html
      cache/
  cache/wiki_lint/           # wiki_lint last-run summaries
  indexes/                   # ctags / search / tree-sitter caches (reserved)
  logs/                      # Per-tool invocation logs
  tmp/version_diff/          # Materialised version diffs

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
  bootstrap_venv             # bash; creates .wiki-runtime/venv via uv + managed CPython
  recent_log                 # python; tail wiki/log.md
  source_graph               # python; generate per-version Graphify graph
  source_graph_query         # python; raw + graph query surface
  source_graph_check         # python; validate graph manifests/JSON/refs
  source_update              # python; clone or refresh raw/postgres-NN/
  source_rebuild             # python; reclone raw/postgres-NN/ at latest tag
  version_diff               # python; unified diff of one path across two versions
  wiki_lint                  # python; wiki link / front-matter / source-ref checks
  test_source_tools          # bash wrapper around tests/test_source_tools.py
  wiki_tooling.py            # shared helpers imported by every python script

tests/
  test_source_tools.py       # synthetic-repo unittest suite for the source tooling
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

`wiki/versions.md` must contain a Markdown table with columns in this exact order: `Version | Status | Wiki Home | Branch | Pinned Commit | Coverage`. Branch and Pinned Commit cells use backticks. The `load_versions()` helper parses this table; tooling depends on the cell layout.

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

## Reading Protocol

Before writing or editing any wiki content the agent must:

- Read `wiki/versions.md` to identify supported versions and the primary version.
- Read `wiki/index.md` to orient against the current wiki shape.
- Read the most recent ~20 entries of `wiki/log.md` for recent activity.
- Read the relevant `wiki/vNN/index.md` before editing any version-local page.
- Query the matching `raw/postgres-NN/` checkout only through `scripts/source_graph_query --version NN ...`. If `.wiki-runtime/graph/postgres-NN/graph.json` is absent and a graph subcommand is needed, the wrapper regenerates it via `scripts/source_graph --version NN --refresh`.

Treat `wiki/versions.md`, `wiki/index.md`, `wiki/log.md`, and version landing pages as navigation and bookkeeping context only — not independent evidence for PostgreSQL behavior. Do not use model memory, external websites, package documentation outside the repository, or uncited prior wiki prose as factual support for generated content.

## Deep Inquiry Default

All user questions, reports, and filed answers run in deep-inquiry mode unless the user explicitly asks for a quick answer.

For each question:

- Confirm the target PostgreSQL version and use explicit version-scoped source tools for every source operation.
- Locate the primary source files and symbols, then inspect adjacent callers, callees, structs, macros, includes, generated headers visible in raw source, reverse include users, graph paths, relevant tests, docs, catalogs, grammar, error paths, GUC definitions, and extension/contrib boundaries through `scripts/source_graph_query`.
- If any source or graph query used for evidence errors out or cannot produce trustworthy output, abort the current analysis before drafting. Fix and rerun when feasible; otherwise stop and report the exact command, target version, and error.
- Inspect file or symbol history when intent matters or when a regression/change claim is being made.
- Use `scripts/version_diff --from NN --to MM` only when the answer makes a cross-version claim or the user asks for a comparison.
- Draft from a claim-to-source evidence map. Every behavioral claim needs a matching raw citation; unresolved claims go under `## Open Questions`.

Minimum depth target for an engine-internals answer: normal path, relevant error or edge path, key data structures, caller/callee boundary, build or generated-header implications visible from raw source, and tests or explicit test absence. For planner, WAL, crash recovery, MVCC, storage, or corruption topics, missing caller/callee or data-structure context is a verification gap that must be resolved or recorded under `## Open Questions`.

## Citation Discipline

- Cite source paths and symbols for every behavioral claim.
- Mandatory citation shape: `[[raw/postgres-NN/src/backend/executor/execMain.c#ExecutorRun]]`.
- For non-Markdown files include the full file extension (`.c`, `.py`, `.java`, etc.).
- Cite from the `raw/postgres-NN/` checkout matching the page's `version:` value.
- Use the same citation format for all code references, function names, and symbols mentioned in the text.
- Code references may use aliases for compact display: `[[raw/postgres-NN/path/file.c#symbol|file.c#symbol]]`.
- If a claim is not backed by a source file, symbol, documentation page, commit, or saved design discussion, do not write it as fact.
- Put uncertainty under `## Open Questions` instead of guessing.
- Never answer about one PostgreSQL version using `raw/` files or `.wiki-runtime/graph/` artifacts from another version.
- If a graph artifact conflicts with the pinned raw source, the raw source wins. Record the discrepancy under `## Open Questions` or regenerate the graph with `scripts/source_graph --version NN --refresh`.

## Verification Fields

Pages carry two distinct verification fields in front matter:

- `verified:` — human-verified. Only a human reviewer may set, change, or remove this field.
- `verified_by_agent:` — agent-verified. Agents may set or update this field only after re-checking every claim against the pinned raw source through graph scripts.

Rules:

- New question pages set `verified: false` and `verified_by_agent: not yet`.
- Do not set `verified_by_agent:` if any claim cannot be verified. Fix the claim, move it under `## Open Questions`, or leave the field absent.
- Unverified managed wiki documents must show `(unverified)` in the visible title and in index/landing-page link text until a human sets `verified: true`. The agent-set `verified_by_agent:` field does not affect the unverified tag — only the human-set `verified:` field does.

Title rule (one-line check before creating, editing, or filing any wiki page):

- If `verified:` is **not** `true`, the top-level title MUST end with ` (unverified)`.
- If `verified:` is `true`, the title MUST NOT contain `(unverified)`.

`verified_by_agent` format rule:

- Must be present and follow one of these exact forms:
  - Draft / not yet fully verified by agent: `verified_by_agent: not yet`
  - Agent-verified (after deep-inquiry, all claims cited, no `## Open Questions`): `verified_by_agent: <LLM-model-name> | YYYY-MM-DD HH:MM`
- Use the exact name of the model the agent is currently running and the current timestamp at filing time.

## Operating Mode

- Trace one source slice or question at a time using `scripts/source_graph_query` and the matching raw source checkout.
- Prefer `scripts/source_graph_query --version NN symbol|file|includes|included-by ...` over ad hoc shell searches.
- Do not create standalone call-chain or source-trace document families. Regenerate `.wiki-runtime/graph/postgres-NN/` when better graph navigation is needed.
- Treat generated pages as drafts until their source references are checked.
- Always use a unicode/ASCII tree for visual directory representations.

## GUC Configuration Changes

- Whenever a wiki page suggests changing a GUC (`postgresql.conf`, `SET`, `ALTER SYSTEM`, etc.), state whether the change requires a restart, reload, or only session/transaction scope.
- Determine the requirement from the GUC's context in the pinned raw source (`raw/postgres-NN/src/backend/utils/misc/guc*.c` or the version's equivalent) or from a validated `pg_settings` definition in the same version. Cite the source.
- Map context values explicitly:
  - `postmaster` → restart required.
  - `sighup` → reload.
  - `superuser` / `user` / `backend` → session or transaction scope, no restart or reload beyond changing defaults.

## Production SQL Snippets

Whenever a wiki page proposes SQL intended to be executed against production:

- Verify syntax, referenced catalogs, columns, functions, and GUCs against the pinned `raw/postgres-NN/` checkout before filing. If a snippet cannot be verified, move it under `## Open Questions`.
- Embed an inline block-comment tag immediately after the leading verb in every production-bound statement:

  ```sql
  SELECT /* wiki_capture_plan_inputs */ ...;
  UPDATE /* wiki_backfill_user_email */ users SET ...;
  ```

- Recommend reasonable session-scoped `statement_timeout` and `lock_timeout` values before the snippet, sized to the operation.

## Bookkeeping

After every meaningful wiki change:

- Update `wiki/index.md` whenever a page is created or substantially changed.
- Update `wiki/versions.md` whenever a supported version is added, removed, archived, re-pinned, or has a meaningful coverage change.
- Update the relevant `wiki/vNN/index.md` whenever version-local pages are created or substantially changed.
- Append an entry to `wiki/log.md` after each scaffold change, ingest, lint pass, filed answer, graph refresh, or version lifecycle event.

Log entry headings use one of these forms:

```md
## [YYYY-MM-DD] <kind> v<NN> | <subject>
```

For version-agnostic work:

```md
## [YYYY-MM-DD] <kind> | <subject>
```

## Version Control

- Never commit or push without asking for permission.

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

## Environment Isolation

**Hard rule — no system dependencies.** Every script, interpreter, library, and supporting binary used by this project must be contained inside the repository. The host is required to provide only a POSIX shell, `curl`, and `tar` — nothing else. No `brew install`, `apt install`, `pip install --user`, `pipx`, `npm -g`, `cargo install`, `go install`, `sudo`, `~/.local/`, `/usr/local/`, or any other host-level installation is permitted as part of setup, runtime, or testing. If a tool is needed, the project must fetch a pinned, project-local copy of it under `.wiki-runtime/` during bootstrap.

This rule is absolute. Documenting an "unavoidable host requirement" is not an option: if something cannot be vendored or fetched into `.wiki-runtime/`, the design must change. The rule applies equally to setup tooling, runtime tooling, optional features, tests, and CI.

How this is currently realized:

- Python tooling runs inside a project-local virtual environment at `.wiki-runtime/venv/`. Never install Python packages into the system or user site-packages, and never use `sudo pip`, `pipx --global`, or `--user` installs.
- `requirements.txt` (or `pyproject.toml` + lockfile) at the repo root is the single source of truth for Python dependencies. Scripts must fail fast with a clear message if invoked outside the project venv.
- The Python interpreter itself is also project-local. `scripts/bootstrap_venv` downloads a pinned `uv` release into `.wiki-runtime/bin/`, uses it to fetch a managed CPython into `.wiki-runtime/python/`, and creates the venv from there. Script shebangs and wrappers resolve the interpreter from `.wiki-runtime/venv/bin/python`; only `scripts/bootstrap_venv` itself runs as a plain `bash` script.
- Non-Python tooling (Graphify CLI, formatters, linters, language servers, anything else) is installed under `.wiki-runtime/` (e.g. `.wiki-runtime/bin/`, `.wiki-runtime/cache/`) rather than into `/usr/local`, Homebrew, or the user's global path.
- All third-party binaries fetched at bootstrap must be pinned to an exact version and target a specific platform tuple. Bumping a pin is an explicit, reviewed change.
- Scripts read and write only inside this repository: `raw/`, `wiki/`, `.wiki-runtime/`, `scripts/`, `tests/`, and the project venv. They must not touch `$HOME`, must not mutate global git config, and must not require root.
- Scripts run with the minimum permissions needed: read-only on `raw/postgres-NN/` checkouts, no network access except for explicit source-fetch and bootstrap operations, and no shell-out to commands that escalate privilege. Network-touching steps are gated behind explicit flags and logged.
- Generated artifacts, caches, vendored binaries, the managed Python, and the venv all live under `.wiki-runtime/` and must be covered by `.gitignore`. Removing `.wiki-runtime/` is always a safe reset; rerunning `scripts/bootstrap_venv` reproduces the full environment from scratch.
- `scripts/test_source_tools` and any future bootstrap script verify the venv exists, the interpreter resolves inside it, and required binaries are reachable from the project tree before doing real work.
- Never use the `WIKI_ALLOW_SYSTEM_PYTHON=1` bypass for normal work. It exists only for the test wrapper, which copies scripts into a synthetic temp repo where the project-venv guard cannot resolve.

## Pinned Tooling

These pins are reproduced verbatim by `scripts/bootstrap_venv` and `requirements.txt`. Bumping any pin is an explicit, reviewed change.

| Tool       | Version    | Location                          | Notes |
|------------|------------|-----------------------------------|-------|
| `uv`       | `0.5.11`   | `.wiki-runtime/bin/uv`            | Fetched as a tarball from `github.com/astral-sh/uv/releases`. |
| CPython    | `3.12`     | `.wiki-runtime/python/`           | Installed by `uv python install 3.12`. graphifyy requires `>=3.10,<3.14`. |
| `graphifyy`| `0.7.10`   | `.wiki-runtime/venv/`             | Installed via `uv pip install -r requirements.txt`. PyPI dist is `graphifyy` (two y's), CLI is `graphify` (one y). |

Supported uv targets and their archive triples:

| `uname -s/uname -m` | uv release target               |
|---------------------|---------------------------------|
| `Darwin/arm64`      | `aarch64-apple-darwin`          |
| `Darwin/x86_64`     | `x86_64-apple-darwin`           |
| `Linux/x86_64`      | `x86_64-unknown-linux-gnu`      |
| `Linux/aarch64`     | `aarch64-unknown-linux-gnu`     |

Any other host fails bootstrap with `error: no prebuilt uv binary for <os>/<arch>`.

## Shared Helpers — `scripts/wiki_tooling.py`

`wiki_tooling.py` is the only module imported by other Python scripts. Implementing it correctly is a prerequisite for every other script. It must be importable from any script under `scripts/` (which `import wiki_tooling` after appending `scripts/` to `sys.path`, or rely on the fact that the script directory is automatically on `sys.path` when scripts are invoked directly).

### Constants

- `REPO_ROOT = Path(__file__).resolve().parents[1]`
- `WIKI_ROOT = REPO_ROOT / "wiki"`
- `RUNTIME_ROOT = (REPO_ROOT / ".wiki-runtime").resolve()`
- `PROJECT_VENV = RUNTIME_ROOT / "venv"`

### Regex constants

- `SECRET_KEY_RE` — case-insensitive, matches `token|password|secret|api[_-]?key|authorization|bearer`.
- `SECRET_VALUE_RE` — matches common provider tokens: `sk-...`, `ghp_...`, `github_pat_...`, `hf_...` (each at least 8 trailing chars).
- `INCLUDE_DIRECTIVE_RE` — `^\s*#\s*include\s+[<"]([^>"]+)[>"]`.
- `COMPILER_INCLUDE_DIR_FLAGS` — frozenset `{"-I", "-iquote", "-isystem", "-idirafter"}`.

### Project-venv guard

- `require_project_venv()` is invoked at module import time so every importing script enforces it. Logic:
  1. Return immediately if `WIKI_ALLOW_SYSTEM_PYTHON=1` is set in the environment (used by the test wrapper).
  2. Compute `prefix = Path(sys.prefix)`. **Do not resolve `sys.executable`** — Homebrew's CPython is a symlink whose target lies outside the venv.
  3. Require `sys.prefix != sys.base_prefix` (i.e. inside *some* venv) **and** `prefix == PROJECT_VENV`.
  4. On mismatch, call `die(...)` with a message that points at `scripts/bootstrap_venv`, suggests both invocation styles (direct `.../bin/python` and `source .../activate`), and mentions the `WIKI_ALLOW_SYSTEM_PYTHON=1` bypass.

### Path helpers

- `render_repo_path(path)` — resolve and return the POSIX path relative to `REPO_ROOT`, falling back to `str(path)` on failure.
- `source_checkout(version)` — return `REPO_ROOT/raw/postgres-<version>`, calling `die()` if it does not exist.
- `safe_source_path(version, rel_path)` — reject absolute paths, then resolve `<checkout>/<rel_path>`, calling `die()` if the result escapes the checkout root. Used to guard every CLI-supplied path.

### Filesystem helpers

- `ensure_private_dir(path)` — `mkdir -p` then best-effort `chmod 0o700` (ignore failures).
- `ensure_private_file(path)` — best-effort `chmod 0o600`.
- `write_private_text(path, text)` — `ensure_private_dir(path.parent)`, then open with `O_WRONLY|O_CREAT|O_TRUNC` mode `0o600`, write text, finally re-chmod the file.
- `append_private_text(path, text)` — same idea but `O_APPEND` semantics.
- `ensure_runtime_dirs()` — create `.wiki-runtime/` and the subtree `cache/wiki_lint`, `indexes/ctags`, `indexes/search`, `indexes/tree-sitter`, `logs`, `tmp`, all with mode `0o700`.

### Graphify discovery

- `find_graphify()`:
  1. Try `shutil.which("graphify")`.
  2. Fall back to `PROJECT_VENV/bin/graphify` if it exists and is executable.
  3. Return `None` otherwise.

### Logging and redaction

- `redact_arg(arg)` — if the arg has `key=value` form and `SECRET_KEY_RE` matches the key, return `key=<redacted>`; else replace any `SECRET_VALUE_RE` match inside the arg with `<redacted>`.
- `redact_args(argv)` — iterate, redacting each value, and if a token matches `SECRET_KEY_RE` (after stripping leading dashes) **and** has no `=`, replace the *next* arg with `<redacted>`. This handles `--api-key SECRET` invocations.
- `append_tool_log(tool, argv)` — `ensure_runtime_dirs()`, then append a single line `<ISO-second timestamp> <tool> <redacted argv>\n` to `.wiki-runtime/logs/<tool>.log` via `append_private_text`.
- `die(message, code=2)` — print `error: <message>` to stderr and `raise SystemExit(code)`.

### Include parsing

- `read_include_directives(path)` — read the file (errors `replace`), match lines against `INCLUDE_DIRECTIVE_RE`, return the list of header strings in order.
- `parse_compiler_include_dirs(args)` — scan a compiler argv: collect arguments after `-I`, `-iquote`, `-isystem`, `-idirafter`, and any standalone `-I<dir>` form. (Reserved for future build-info ingestion.)

### `wiki/versions.md` parser

- `strip_ticks(value)` — strip surrounding backticks if both ends are `` ` ``.
- `load_versions()`:
  1. Read `wiki/versions.md`; `die()` if missing.
  2. Iterate lines starting with `|`, split into trimmed cells.
  3. Skip rows whose first cell is not a digit string (the table header) — this is also how we skip `|---|...|` separators.
  4. Require ≥6 cells. Map columns 0..5 to `version`, `status`, `wiki_home`, `branch`, `commit`, `coverage`. `branch` and `commit` are stripped of backticks.
  5. Return `{version: {version, status, wiki_home, branch, commit, coverage}}`.
- `primary_version(versions=None)` — return the version whose status is `primary`, or the highest numeric version, or `die()` if empty.

### Wiki front matter / link helpers

These power `wiki_lint`:

- `wiki_markdown_files()` — recursively list `*.md` under `wiki/` (sorted).
- `wiki_slug(path)` — `path.relative_to(WIKI_ROOT)` without suffix, as POSIX.
- `parse_front_matter(text)` — return `(data, raw, has_fm)`. Recognise a leading `---` line and a closing `---`. Inside, accept `key: value` and one level of nested `key:` block (mapping). Ignore comments / blank lines. Strip surrounding `'` or `"` from values.
- `LINK_RE = re.compile(r"(?<!!)\[\[([^\]\n]+)\]\]")` — Obsidian-style links not preceded by `!`.
- `_CODE_SPAN_RE` and `_CODE_BLOCK_RE` — used to strip inline code and fenced blocks before link extraction.
- `extract_obsidian_links(text)` — strip code spans/blocks, then pull every link target. Support `target|alias`, `target#section`, and `target^anchor`. Drop trailing `.md`. Strip surrounding slashes.
- `section_text(text, heading)` — return the body of the first `## <heading>` block, terminating at the next `## ` heading.

## Script Specifications

These specifications are the source of truth for the scripts. If `scripts/` is deleted, every script must be reproducible from this document plus `wiki_tooling.py`.

Every Python script:

- Begins with `#!/usr/bin/env python3` and a docstring whose first line summarises the command.
- Sets `sys.dont_write_bytecode = True` before imports of `wiki_tooling` to keep `.pyc` files out of the source tree.
- Imports from `wiki_tooling` (which triggers the project-venv guard).
- Calls `append_tool_log(<tool name>, sys.argv[1:])` exactly once early in `main()`.
- Returns from `main()` and is wrapped by `if __name__ == "__main__": raise SystemExit(main())`.

### `scripts/bootstrap_venv` (bash)

Purpose: create or refresh the project-local venv with no system dependency beyond a POSIX shell, `curl`, `tar`. Idempotent; safe to re-run.

Layout:

```text
.wiki-runtime/
  bin/{uv,uvx}
  python/                  # UV_PYTHON_INSTALL_DIR
  uv-cache/                # UV_CACHE_DIR
  uv-tools/                # UV_TOOL_DIR
  venv/                    # the project venv
```

Behaviour:

1. `set -euo pipefail`. Compute `REPO_ROOT` from `BASH_SOURCE`.
2. Define pinned constants `UV_VERSION="0.5.11"` and `PYTHON_VERSION="3.12"`.
3. Export `UV_CACHE_DIR`, `UV_PYTHON_INSTALL_DIR`, `UV_TOOL_DIR`, `UV_TOOL_BIN_DIR=$UV_BIN_DIR`. `unset UV_PROJECT_ENVIRONMENT` so uv does not try to manage a project root.
4. `mkdir -p` `.wiki-runtime/` and `.wiki-runtime/bin/`. Best-effort `chmod 700` on `.wiki-runtime/`.
5. If `.wiki-runtime/bin/uv` is not executable:
   - `detect_uv_target` based on `uname -s/uname -m` (table above). On unknown combos: print `error: no prebuilt uv binary for <os>/<arch>` to stderr and exit non-zero.
   - Download `https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-$target.tar.gz` into a `mktemp -d` directory using `curl --fail --silent --show-error --location`.
   - `tar -xzf` and `install -m 0755` both `uv` and `uvx` into `.wiki-runtime/bin/`.
   - Use `trap` to remove the temp dir.
6. Always run `"$UV" python install "$PYTHON_VERSION"` (no-op when already installed).
7. If `.wiki-runtime/venv/bin/python` is missing, run `"$UV" venv --python "$PYTHON_VERSION" "$VENV_DIR"`.
8. If `requirements.txt` exists and contains a non-comment, non-blank line, run `"$UV" pip install --python "$VENV_DIR/bin/python" -r "$REQUIREMENTS"`.
9. Print the absolute-relative venv path and both invocation styles (`/bin/python ...` and `source .../activate`).

### `scripts/source_update`

Purpose: clone or update a pinned PostgreSQL source checkout under `raw/postgres-NN/`.

Constants: `MIRROR = "https://github.com/postgres/postgres.git"`, `RAW_ROOT = REPO_ROOT/"raw"`.

Arguments:

- `--version NN` — required unless `--list`.
- `--branch BRANCH` — defaults to the branch from `wiki/versions.md`.
- `--commit SHA` — defaults to the pinned commit from `wiki/versions.md`.
- `--list` — print every version, its status, whether `raw/postgres-NN/` exists, and the first 12 chars of the pinned commit, then exit 0.

Behaviour:

1. `append_tool_log("source_update", ...)`.
2. `versions = load_versions()`.
3. If `--list`, iterate sorted by integer version and print rows.
4. Resolve `branch` and `commit` from CLI overrides, falling back to `versions[args.version]`. If either is missing, `die()` with a message that suggests `--branch` / `--commit` and a sample branch (e.g. `REL_18_STABLE` or `master`).
5. If `raw/postgres-NN/` exists: `git fetch origin <branch>` then `git checkout --detach <commit>`.
6. Else: `git clone --filter=blob:none --branch <branch> https://github.com/postgres/postgres.git raw/postgres-NN`, then `git checkout --detach <commit>`.
7. Print `cloning postgres ...`, `resetting to <12-char sha> ...`, and `checkout ready: <full HEAD sha>`.

Network use is explicit and limited to `git clone`/`git fetch`. No writes outside `raw/`.

### `scripts/source_rebuild`

Purpose: wipe and reclone `raw/postgres-NN/` at the newest upstream release tag, then update `wiki/versions.md` and append to `wiki/log.md`.

Tag tiers (highest tier wins, then highest minor):

| Tier | Regex                      | Meaning |
|------|----------------------------|---------|
| 3    | `^REL_(\d+)_(\d+)$`        | Stable (e.g. `REL_18_2`). |
| 2    | `^REL_(\d+)_RC(\d+)$` (i)  | Release candidate. |
| 1    | `^REL_(\d+)_BETA(\d+)$` (i)| Beta. |

Arguments: `--version NN` (required), `--dry-run`.

Behaviour:

1. `append_tool_log("source_rebuild", ...)`.
2. `latest_release_tag(version)`:
   - `git ls-remote --tags MIRROR refs/tags/REL_<version>_*`.
   - Skip empty lines and `^{}` peeled lines.
   - Compute the tier/minor key for each candidate; keep the highest.
   - Resolve to the underlying *commit* SHA by running `git ls-remote MIRROR refs/tags/<tag>^{}` and reading the `^{}` line.
   - `die()` if no tags match.
3. Compare against the existing pin in `wiki/versions.md`; if equal, print `already pinned to <sha12> — nothing to do` and exit 0.
4. If `--dry-run`, print the planned delete + reclone + versions/log writes and call `append_log(... dry_run=True)` (which only prints the entry); return 0.
5. Otherwise:
   - `shutil.rmtree(raw/postgres-NN)` if present.
   - `git clone --filter=blob:none --branch <tag> MIRROR raw/postgres-NN`, then `git checkout --detach <commit>`.
   - `update_versions_md(...)` — find the table row whose first cell equals the version. Replace cell index 4 (Branch) with `` `<tag>` `` and cell index 5 (Pinned Commit) with `` `<commit>` ``. Preserve the `|...|` framing. Also rewrite any `- Branch:` / `- Pinned commit:` summary lines that were touched in the same change. Skip the write if the file is unchanged.
   - `append_log(...)` writes to `wiki/log.md`:
     ```
     ## [YYYY-MM-DD] source-rebuild vNN | pinned to <tag>

     - Deleted and recloned `raw/postgres-NN/` from the official mirror.
     - Resolved tag `<tag>` to commit `<commit>`.
     - Previous pin: `<old_commit>`.
     - Updated `wiki/versions.md` branch and pinned commit.
     ```

### `scripts/source_graph`

Purpose: generate per-version Graphify graph artifacts under `.wiki-runtime/graph/postgres-NN/`. Writes `manifest.md` even when generation fails so the failure is auditable.

Required artifacts: `graph.json` and `GRAPH_REPORT.md`. Optional: `graph.html` and `cache/`.

Arguments:

- Mutually-exclusive scope (required): `--version NN` or `--all`.
- `--refresh` — `rmtree` the version graph directory before generating.
- `--dry-run` — print the planned target paths and exit 0 without writing.
- `--semantic` — run `graphify extract` instead of `graphify update`.
- `--update` — deprecated no-op (AST-only is the default).
- `--cluster-only` — run `graphify cluster-only` against the existing output.
- `--no-viz` (default `True`) / `--with-viz` — toggle visualisation.
- `--backend {gemini,kimi,claude,openai,ollama}` — semantic backend.
- `--model MODEL` — model override for semantic extraction.
- `--no-cluster` — pass `--no-cluster` to semantic extract.
- `--timeout SECONDS` — Graphify command timeout, default 3600.

Data classes:

```python
@dataclass class CommandAttempt: argv, cwd, status, exit_code, stderr, note
@dataclass class ArtifactStatus: name, path, status, detail, failures
@dataclass class GraphRun: version, info, source, graph_dir, attempts, tools, artifacts
```

`GraphRun.add_artifact(name, path, status, detail, failures=())` appends a record (rendering `path` via `render_repo_path` if a `Path` is given).

Pipeline (per version):

1. Resolve `source = source_checkout(version)`; build `graph_dir = RUNTIME_ROOT/"graph"/f"postgres-{version}"`. Refuse to write outside `RUNTIME_ROOT` (`ensure_runtime_path`).
2. If `--dry-run`, print `v<version>: would write <graph_dir>` (and a refresh note when applicable) and return 0.
3. If `--refresh` and `graph_dir.exists()`, `shutil.rmtree(graph_dir)`.
4. `ensure_private_dir(graph_dir)`.
5. Build `GraphRun`, `probe_tools(run)` (records `graphify` and `git` paths or `"missing"`).
6. `generate_graph(run, args)`:
   - If `find_graphify()` returns `None`, add deferred `graph.json` and `GRAPH_REPORT.md` artifacts (and `graph.html` when `--with-viz`) explaining "graphify is not installed; install package `graphifyy` to provide the `graphify` CLI" and return.
   - Else build the argv via `graphify_command`:
     - Default (no `--semantic`, no `--cluster-only`): `[graphify, "update", str(source.resolve()), "--force"]`, env `{"GRAPHIFY_OUT": str(graph_dir/"graphify-out")}`.
     - `--cluster-only`: `[graphify, "cluster-only", ".", "--graph", "graph.json"]` and append `--no-viz` when applicable. No env override.
     - `--semantic`: `[graphify, "extract", <relpath of source from graph_dir>, "--out", "."]`, optionally appending `--backend B`, `--model M`, `--no-cluster`. Env `{"GRAPHIFY_OUT": str(graph_dir/"graphify-out")}`.
   - Run the command in `cwd=graph_dir` with the merged env, capturing stdout/stderr; record a `CommandAttempt`. Treat `FileNotFoundError` and `TimeoutExpired` as failures.
   - On non-zero exit, mark required artifacts deferred with detail "graphify command failed".
   - On success, `copy_graphify_output(run)` promotes children of `graph_dir/graphify-out/` up one level (replacing existing entries), then `rmtree` the now-empty `graphify-out/`. Failure to find/produce the directory marks artifacts deferred.
   - For each of `graph.json` (required), `GRAPH_REPORT.md` (required), `graph.html` (optional), `cache/` (optional): record `generated`, `deferred`, or `skipped` based on whether the path exists. Only required deferred artifacts cause a non-zero exit.
7. `source_head(run)` — `git -C <source> rev-parse HEAD`, fall back to `unknown`.
8. Write `<graph_dir>/manifest.md` via `write_runtime_text`. The manifest has these sections:
   - Title `# PostgreSQL <version> Graphify Source Graph`.
   - "This graph is generated orientation material. It is not evidence for behavioral wiki claims."
   - `## Source Pin` bullets: PostgreSQL version, Branch (from versions.md), Pinned commit, Source checkout (`render_repo_path`), Source checkout HEAD, Graph path, Regenerated (UTC ISO).
   - `## Tool Status` — `| Tool | Status |` table, sorted by tool name; pipes in status are escaped as `\|`.
   - `## Artifact Status` — `| Artifact | Path | Status | Details |` table.
   - `## Commands Attempted` — `| Status | CWD | Command | Exit | Notes |`. The command column uses `render_command(argv)` (redacted via `redact_args`, absolute paths rewritten relative to `REPO_ROOT`). Notes default to a 6-line `summarise_stderr` (≤700 chars, separated by `/ `).
   - `## Deferred Or Failed Artifacts` — bullet list of artifacts with `status in {"deferred","failed"}` or non-empty `failures`; falls back to "No deferred or failed artifacts."
9. Print `v<version>: wrote <manifest>` and one line per artifact (`status name - detail`).
10. Return 0 only if every required artifact (`graph.json`, `GRAPH_REPORT.md`) is non-deferred; else 1.

`--all` iterates versions sorted by integer descending and OR-s the per-version exit codes.

### `scripts/source_graph_query`

Purpose: the single source-query surface for agents.

Top-level argument: `--version NN` (required). One subcommand chosen via `subparsers(required=True)`.

Subcommands:

- `symbol SYMBOL [--regex] [--limit N=100]` — search raw source for text or a regex.
- `file PATH [--start N=1] [--limit N=100]` — print a slice of a raw source file, or list a directory.
- `log PATH [--limit N=20]` — `git log --oneline` for a path inside the raw checkout.
- `includes PATH [--format text|json]` — list direct `#include` directives (resolved).
- `included-by TARGET [--limit N=100] [--format text|json]` — list raw `*.c`/`*.h` files that include the target.
- `query QUESTION [--dfs] [--budget N]` — run `graphify query`.
- `path SOURCE TARGET` — run `graphify path`.
- `explain NODE` — run `graphify explain`.

Common behaviour:

1. `append_tool_log("source_graph_query", ...)`.
2. `versions = load_versions()`; `die()` on unknown version.
3. `root = source_checkout(args.version)`.

Raw subcommands:

- `symbol`:
  - If `<root>/.git` exists and `git` is on PATH: run `git -C <root> grep -n` plus `-E` (regex) or `-F` (literal), then `--`, then the query. `returncode > 1` is a real error and is forwarded; `returncode == 1` means "no matches".
  - Else if `rg` is on PATH: run `rg -n --hidden --glob '!.git'` plus `--fixed-strings` (when not regex), then `--`, query, `.` with `cwd=root`.
  - Else fall back to a pure-Python rglob walk that reads each non-`.git` file and searches line-by-line. Compile the regex if `--regex`; report a clear error on `re.error`.
  - Apply `--limit` (0 means no limit). Print one match per line; exit 1 with `no matches for '<symbol>'` on stderr when empty.
- `file`:
  - `safe_source_path(version, path)`. If the path is a directory, list immediate children (`name/` for sub-dirs).
  - Else open the file with `errors="replace"` and print lines `[start, start+limit-1]`. Format: `{lineno:6d}\t{rstripped line}`. `--limit 0` means all lines.
- `log`:
  - Require `<root>/.git`. Run `git -C <root> log --oneline --max-count=<limit> -- <path>`. Forward stdout/stderr.
- `includes`:
  - Resolve each `#include` from `read_include_directives(path)` against the include search roots (see below). Each row is `{include, resolved (or null), source}`; render as `<include> -> <resolved or "unresolved">` for text or as `{"includes": rows}` JSON.
- `included-by`:
  - Resolve target either as `<root>/<target>` (when it exists) or via `resolve_include`. `die()` if unresolved.
  - Iterate `raw_files(root)`:
    - When `<root>/.git` exists: `git -C <root> ls-files '*.c' '*.h'` (preserves only tracked files; this is the test that ignores untracked noise like `wiki/noise.md`). Fallback to `rglob` on `*.c`/`*.h`.
  - For each candidate, count include directives whose resolved path matches the target. Sort by `(-count, source)` and apply `--limit`. Render text `{source}` or JSON `{"sources": rows}`.

Include resolution:

- `include_search_roots(root, source=None)` — yield (in order) `source.parent` (when given), `<root>/src/include`, `<root>`. De-duplicate by resolved path.
- `resolve_include(root, include, source=None)` — try each search root; return the first existing file whose resolved path is inside `<root>`.

Graph subcommands:

- `ensure_graph(version)` — return `<runtime>/graph/postgres-<version>/graph.json`. If absent, run `python scripts/source_graph --version <version> --refresh` (using `sys.executable` for the inner call) with `cwd=REPO_ROOT`. Forward stdout/stderr on failure and `die()` with `could not generate Graphify graph: <relpath>`.
- `run_graphify(argv)` — locate the graphify CLI via `find_graphify()`; `die()` with `graphify is not installed; install package 'graphifyy' to provide the 'graphify' CLI` if missing. Pass through stdout/stderr.
- Build the inner argv by passing the subcommand verb plus its args (`query` adds `--dfs`/`--budget`, `path` adds `source target`, `explain` adds `node`), append `--graph <ensure_graph(version)>`, then run.

### `scripts/source_graph_check`

Purpose: validate every generated graph for pin alignment, JSON parseability, version-correct references, missing project paths, and (optionally) a query probe.

Arguments: `--version NN` or `--all`, `--probe-node NAME`, `--strict`.

Reference regex:

```
(?P<path>(?:raw|\.wiki-runtime/graph)/postgres-(?P<version>\d+)
         (?:/[^\s`'"<>|,:\])}]*)?)
```

`Reporter` accumulates `Issue(level, check, message)`. Levels: `ERROR`, `WARN`. Issues are printed in insertion order.

Per-version behaviour:

1. Resolve `graph_dir`, `manifest`, `graph.json`, `GRAPH_REPORT.md` paths under `.wiki-runtime/graph/postgres-NN/`.
2. Manifest checks:
   - Missing → `ERROR manifest: missing Graphify manifest: <relpath>`.
   - Else `parse_manifest_values(text)` extracts `- Key: value` lines, stripping single backtick wrappers from values.
   - If `Pinned commit` differs from the `wiki/versions.md` commit → `ERROR manifest`.
   - Compute `source_head(version)` (`git -C raw/postgres-NN rev-parse HEAD`); if known and `Source checkout HEAD` differs → `ERROR manifest`.
   - `scan_references(version, reporter, manifest, text, missing_level="ignore")` — wrong-version references still error; missing project paths are ignored (the manifest legitimately mentions paths inside `raw/...` that may not yet exist).
3. `graph.json` checks:
   - Missing → ERROR.
   - Else attempt `json.loads`; ERROR on failure.
   - `scan_references(... missing_level="error")`.
4. `GRAPH_REPORT.md` checks:
   - Missing → WARN.
   - Else `scan_references(... missing_level="error")`.
5. `--probe-node NAME`:
   - Locate graphify; if missing → WARN.
   - Else run `graphify explain <NAME> --graph <graph.json>`. Non-zero exit → ERROR.
6. Print every issue and a summary line `vNN: source_graph_check: errors=N warnings=M`.

Reference scanner details:

- Normalise text by replacing absolute REPO_ROOT prefixes with `.` and backslashes with forward slashes.
- For each match, `clean_reference()` trims trailing `:line[:col]` and any trailing `.`, `;`, `:`, `)`.
- If the matched version != expected version → ERROR (regardless of `missing_level`).
- Else if the path does not exist on disk: ERROR (`"error"`), WARN (`"warn"`), or skip (`"ignore"`).

Exit code: 1 if any error, or any warning when `--strict`; else 0.

### `scripts/version_diff`

Purpose: produce a deterministic unified diff of one source path between two pinned checkouts and persist it under `.wiki-runtime/tmp/version_diff/` for citation.

Arguments: `--from NN` (required), `--to MM` (required), `--path REL` (required), `--context N=3`.

Behaviour:

1. `append_tool_log("version_diff", ...)`.
2. `from_path = safe_source_path(from_version, path)`, `to_path = safe_source_path(to_version, path)`.
3. Validate both paths exist and neither is a directory; on error, print `error: ...` to stderr and return 2.
4. `difflib.unified_diff(from_lines, to_lines, fromfile=postgres-<from>/<path>, tofile=postgres-<to>/<path>, n=context)` over `splitlines(keepends=True)`.
5. Output filename: `safe_diff_name(from, to, path)` → `postgres-<from>_to_postgres-<to>_<sanitized path>.diff` where the path is run through `re.sub(r"[^A-Za-z0-9._-]+", "_", rel.strip("/"))`.
6. Write to `.wiki-runtime/tmp/version_diff/<safe name>` (`mkdir -p` first).
7. If diff non-empty: print the diff verbatim, then `\nwritten: <path>`, return 1. Else print `no differences for <path>`, then `written: <path>`, return 0.

### `scripts/wiki_lint`

Purpose: enforce wiki invariants — front matter on managed pages, version-pin alignment, citation discipline, link integrity, orphan detection, and version-landing index links.

Constants:

- `MANAGED_VERSION_DIRS = ("questions",)`.
- `SOURCE_REQUIRED_TYPES = {"question"}`.
- `ROOT_EXEMPT_SLUGS = {"index", "overview", "versions", "log"}`.

Helpers:

- `is_version_local(slug)` — slug `vNN/<dir>/...` returns `(NN, dir)` when `dir` is in `MANAGED_VERSION_DIRS`; else `(None, None)`.
- `requires_front_matter(slug)` — version-local pages require front matter.
- `has_source_references(text)` — `## Source References` body must contain `raw/postgres-\d+/` or `src/`.
- `resolve_link(target, current_slug, slugs)` — match exact slug; relative-to-current; or `<target>/index`.

Lint pass (single iteration over all wiki Markdown files):

1. Front matter:
   - Required for version-local pages → ERROR if absent.
   - For version-local pages, `version` field must equal directory `NN`. `pinned_commit` must equal the wiki/versions.md commit for that version.
   - Search the page text for `raw/postgres-(\d+)/` references; any version other than the page's own version → ERROR.
   - `verified` must be `"true"`/`"false"` when present → ERROR otherwise.
   - `verified_by_agent` must be `not yet` or match `^[a-zA-Z0-9_-]+ \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`.
   - Type `question` requires `verified: false` → ERROR otherwise.
   - For type `question`, the actual front-matter key order must match the prefix of `[type, version, pinned_commit, verified, verified_by_agent]` (verified_by_agent is optional). Otherwise WARN.
   - WARN when both `verified` and `verified_by_agent` are absent.
2. `type in SOURCE_REQUIRED_TYPES` and missing source references → ERROR.
3. Resolve every Obsidian link. Targets prefixed `raw/` must exist on disk. Other targets must resolve via `resolve_link`. Track inbound counts.
4. After the file pass:
   - WARN every slug with zero inbound links unless it is in `ROOT_EXEMPT_SLUGS` or ends with `/index`.
   - For each version, ERROR if `wiki/vNN/index.md` is missing; WARN if any version-local page is not linked from the landing page (`[[<slug>` substring match).

Output: print summary `wiki_lint: N error(s), M warning(s)` then each issue line `LEVEL <relpath>: <message>`. Cache to `.wiki-runtime/cache/wiki_lint/last-run.txt`. Return 1 on errors or (when `--warnings-as-errors`) on warnings; else 0.

### `scripts/recent_log`

Purpose: print recent entries from `wiki/log.md`.

Entry boundary regex: `^## \[(\d{4}-\d{2}-\d{2})\] (.+)$`.

Arguments: `--limit N=10`, `--kind STR` (substring of heading), `--version VV` (matches `vNN` substring of heading), `--oldest-first`.

Behaviour:

1. Read `wiki/log.md`; error 2 if absent.
2. Walk lines; whenever a heading matches, finalize the previous block and start a new one. Each entry is the heading plus subsequent lines until the next heading.
3. Filter by `--kind` and `--version` against the entry's heading.
4. Take the last `max(limit, 0)` entries; reverse them unless `--oldest-first`.
5. Print entries separated by a blank line.

### `scripts/test_source_tools` (bash)

Purpose: run `tests/test_source_tools.py` against the project venv.

1. `set -euo pipefail`.
2. Resolve `REPO_ROOT` and `VENV_PY=.wiki-runtime/venv/bin/python`. Fail with a setup hint when missing.
3. `cd "$REPO_ROOT"`. Export `PYTHONDONTWRITEBYTECODE=1` and `WIKI_ALLOW_SYSTEM_PYTHON=1` (the synthetic test repo lives outside the project venv guard).
4. Run `"$VENV_PY" -m unittest discover -s tests -p 'test_source_tools.py'`.

## Testing

`tests/test_source_tools.py` is a `unittest` suite that copies `source_graph`, `source_graph_check`, `source_graph_query`, and `wiki_tooling.py` into a synthetic temporary repo, builds a tiny PostgreSQL-shaped tree under `raw/postgres-99/`, initialises a git repo with one commit, and writes a matching `wiki/versions.md`. It runs each test in that sandbox to keep the project tree clean.

It exercises:

- explicit version enforcement (no scope, unsupported version);
- raw source `symbol`, `file`, `log`, `includes`, and `included-by` queries;
- regex symbol search falling back to git when ripgrep is unavailable (`PATH` is reduced to a tool-only directory);
- `symbol` ignoring untracked files (verifying the `git ls-files` filter);
- end-to-end graph generation using a fake `graphify` shim that mimics `update`/`extract`/`query`/`path`/`explain` and writes `graph.json`/`GRAPH_REPORT.md`/`cache/` into `graphify-out/`;
- forced graph generation when `graph.json` is absent (a graph subcommand triggers `source_graph --refresh` automatically);
- the deferred-manifest path when `graphify` is missing (manifest still written, return code 1);
- `source_graph_query` reporting graph-generation failure cleanly when `graphify` is missing;
- `source_graph_check` rejecting wrong-version references inside `graph.json`.

The fake graphify shim is the canonical contract for what `source_graph` expects from the real CLI: it must (a) accept the documented argv shapes, (b) write `graph.json`, `GRAPH_REPORT.md`, and `cache/` into the directory pointed to by `GRAPHIFY_OUT` (or `<cwd>/graphify-out/` for `update`, or `<--out>/graphify-out/` for `extract`), and (c) accept `--graph <path>` for the query subcommands.

## First Useful Milestone

- Supported versions are pinned in `wiki/versions.md`.
- Each supported version has a `raw/postgres-NN/` checkout.
- Source graph tooling is the only supported source-query path.
- Wiki answers cite raw source paths and symbols.
- `scripts/test_source_tools` and `scripts/wiki_lint` pass.

## Implementation Steps

These steps reproduce the project from a clean checkout (or after deleting `scripts/`). They are ordered by dependency: each step is fully exercisable before the next begins.

1. **Repository skeleton.**
   - Create `wiki/`, `raw/`, `scripts/`, `tests/`, `templates/`.
   - Add `.gitignore` covering `.wiki-runtime/` and `raw/postgres-*/`.
   - Seed `wiki/index.md`, `wiki/overview.md`, `wiki/versions.md` (with the canonical `Version | Status | Wiki Home | Branch | Pinned Commit | Coverage` table), and `wiki/log.md`.

2. **Pin tooling.**
   - Write `requirements.txt` with `graphifyy==0.7.10` (and a comment explaining venv-only installs).
   - Decide pinned `UV_VERSION` and `PYTHON_VERSION`; document them in this plan's "Pinned Tooling" section.

3. **Bootstrap the venv (`scripts/bootstrap_venv`).**
   - Implement the bash script per the spec above. Must be idempotent.
   - Smoke test: `rm -rf .wiki-runtime && ./scripts/bootstrap_venv && .wiki-runtime/venv/bin/python -c 'import sys; print(sys.prefix)'` should print the venv path.

4. **Shared module (`scripts/wiki_tooling.py`).**
   - Implement constants, regex tables, the project-venv guard (running at import time), filesystem helpers, Graphify discovery, secret redaction, tool log, the `wiki/versions.md` parser, and the wiki front-matter / link helpers. Order: constants → regexes → `die`/guard → filesystem helpers → graphify discovery → redaction/log → versions parser → front-matter/link helpers.
   - Smoke test: `from wiki_tooling import load_versions, find_graphify` inside the venv.

5. **Source pin maintenance (`scripts/source_update`, `scripts/source_rebuild`).**
   - Implement `source_update` (clone/update/list).
   - Implement `source_rebuild` (tag selection, table editing, log append, dry-run).
   - Smoke test: `--list` against a populated `wiki/versions.md`; `--dry-run` of `source_rebuild` for an existing version.

6. **Source query surface (`scripts/source_graph_query`).**
   - Implement raw subcommands first (`symbol`, `file`, `log`, `includes`, `included-by`). Wire include resolution exactly per `include_search_roots` / `resolve_include`.
   - Add `ensure_graph` and `run_graphify`, then graph subcommands (`query`, `path`, `explain`).
   - Smoke test against any populated `raw/postgres-NN/` checkout.

7. **Graph generation (`scripts/source_graph`).**
   - Implement the data classes, `probe_tools`, `graphify_command`, `copy_graphify_output`, `manifest_text`, `generate_graph`, `generate_version`, and the CLI.
   - Verify the deferred path: when `graphify` is absent the script still writes `manifest.md` and returns 1.

8. **Graph validation (`scripts/source_graph_check`).**
   - Implement `Reporter`, the reference regex, `clean_reference`, `path_from_context`, `parse_manifest_values`, `source_head`, and `check_version`.
   - Verify that wrong-version references inside a `graph.json` produce ERROR exits.

9. **Cross-version diff and log (`scripts/version_diff`, `scripts/recent_log`).**
   - Implement both per spec. `version_diff` always writes its output file even when no differences are found.

10. **Wiki linter (`scripts/wiki_lint`).**
    - Implement `lint()` exactly per the rules in "Script Specifications" → `wiki_lint`. Cache the last run under `.wiki-runtime/cache/wiki_lint/last-run.txt`.

11. **Test harness (`tests/test_source_tools.py`, `scripts/test_source_tools`).**
    - Reproduce the synthetic-repo `setUp`, the fake-graphify shim, and every scenario listed under "Testing".
    - Wire the bash wrapper to set `WIKI_ALLOW_SYSTEM_PYTHON=1` and dispatch to `unittest discover`.

12. **Validation pass.**
    - Run `./scripts/bootstrap_venv` from a clean state.
    - Run `./scripts/test_source_tools` — expect green.
    - Run `.wiki-runtime/venv/bin/python scripts/wiki_lint` — expect zero errors against the seeded wiki.
    - For each pinned version: `source_update`, `source_graph --refresh`, `source_graph_check`, then a sample `source_graph_query --version NN explain <symbol>`.

13. **Documentation.**
    - Per the "Plan Synchronisation Rule" above: every change to `scripts/` lands together with the matching edit to this plan in the same commit/PR. `README.md` and `AGENTS.md` follow. Treat any drift as a defect and fix it before merging.
