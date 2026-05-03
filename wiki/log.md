# Wiki Log

Append one entry after every scaffold change, version lifecycle event, ingest, trace, lint pass, or filed answer.

Use this prefix shape:

```md
## [YYYY-MM-DD] <kind> v<NN> | <subject>
```

For version-agnostic work, omit the version segment:

```md
## [YYYY-MM-DD] <kind> | <subject>
```

## [2026-04-30] scaffold | initialized Phase 1 wiki structure

- Created version-agnostic wiki entry points.
- Created page templates.
- Created `AGENTS.md`.
- Created project-local runtime directory layout under `.wiki-runtime/`.
- Added `.gitignore` entries for project-local runtime state and local PostgreSQL source checkouts.

## [2026-04-30] add-version v18 | bootstrapped primary source checkout

- Added PostgreSQL 18 as the primary wiki version.
- Cloned official PostgreSQL source into `raw/postgres-18/`.
- Pinned `REL_18_STABLE` to `6cb307251c5c6261286c1566496920976640108e`.
- Created `wiki/v18/index.md`.
- Created empty version-local directories for subsystems, concepts, code paths, files, and questions.
- Updated `wiki/versions.md`, `wiki/index.md`, and `wiki/overview.md`.

## [2026-04-30] ingest v18 | parser subsystem

- Created `wiki/v18/subsystems/parser.md`.
- Verified entry points against `raw/postgres-18/src/backend/tcop/postgres.c:pg_parse_query`, `raw/postgres-18/src/backend/parser/parser.c:raw_parser`, and `raw/postgres-18/src/include/parser/parser.h`.

## [2026-04-30] ingest v18 | analyzer subsystem

- Created `wiki/v18/subsystems/analyzer.md`.
- Verified entry points against `raw/postgres-18/src/backend/tcop/postgres.c:pg_analyze_and_rewrite_fixedparams`, `raw/postgres-18/src/backend/parser/analyze.c:parse_analyze_fixedparams`, and `raw/postgres-18/src/include/parser/analyze.h`.

## [2026-04-30] ingest v18 | rewriter subsystem

- Created `wiki/v18/subsystems/rewriter.md`.
- Verified entry points against `raw/postgres-18/src/backend/tcop/postgres.c:pg_rewrite_query`, `raw/postgres-18/src/backend/rewrite/rewriteHandler.c:QueryRewrite`, and `raw/postgres-18/src/include/rewrite/rewriteHandler.h`.

## [2026-04-30] ingest v18 | planner subsystem

- Created `wiki/v18/subsystems/planner.md`.
- Verified entry points against `raw/postgres-18/src/backend/tcop/postgres.c:pg_plan_query`, `raw/postgres-18/src/backend/optimizer/plan/planner.c:planner`, and `raw/postgres-18/src/backend/optimizer/README`.

## [2026-04-30] ingest v18 | executor subsystem

- Created `wiki/v18/subsystems/executor.md`.
- Verified entry points against `raw/postgres-18/src/backend/executor/execMain.c`, `raw/postgres-18/src/backend/executor/execProcnode.c:ExecInitNode`, `raw/postgres-18/src/include/executor/executor.h:ExecProcNode`, and `raw/postgres-18/src/backend/executor/README`.

## [2026-04-30] trace v18 | simple-select-query

- Created `wiki/v18/code-paths/simple-select-query.md`.
- Traced simple Query protocol through `exec_simple_query`, `pg_parse_query`, `pg_analyze_and_rewrite_fixedparams`, `pg_plan_queries`, `PortalStart`, `PortalRunSelect`, `ExecutorRun`, and `ExecutePlan`.
- Linked the path from parser, analyzer, rewriter, planner, and executor subsystem pages.

## [2026-04-30] trace v18 | insert-path

- Created `wiki/v18/code-paths/insert-path.md`.
- Traced simple `INSERT ... VALUES` through `transformInsertStmt`, `preprocess_targetlist`, `create_modifytable_path`, `create_modifytable_plan`, `PortalRunMulti`, `ProcessQuery`, `ExecModifyTable`, and `ExecInsert`.
- Linked the path from parser, analyzer, rewriter, planner, and executor subsystem pages.

## [2026-04-30] trace v18 | update-path

- Created `wiki/v18/code-paths/update-path.md`.
- Traced simple `UPDATE` through `transformUpdateStmt`, `transformUpdateTargetList`, row-identity target-list preprocessing, `ModifyTable` planning, `ExecModifyTable`, and `ExecUpdate`.
- Linked the path from parser, analyzer, rewriter, planner, and executor subsystem pages.

## [2026-04-30] trace v18 | delete-path

- Created `wiki/v18/code-paths/delete-path.md`.
- Traced simple `DELETE` through `transformDeleteStmt`, row-identity target-list preprocessing, `ModifyTable` planning, `ExecModifyTable`, and `ExecDelete`.
- Linked the path from parser, analyzer, rewriter, planner, and executor subsystem pages.

## [2026-04-30] concept v18 | query-tree

- Created `wiki/shared/concepts/query-tree.md`.
- Verified against `raw/postgres-18/src/include/nodes/parsenodes.h:Query`, `raw/postgres-18/src/backend/parser/analyze.c:parse_analyze_fixedparams`, and planner/rewrite handoff functions in `raw/postgres-18/src/backend/tcop/postgres.c`.

## [2026-04-30] concept v18 | planned-statement

- Created `wiki/shared/concepts/planned-statement.md`.
- Verified against `raw/postgres-18/src/include/nodes/plannodes.h:PlannedStmt`, planner entry points, portal storage, and executor descriptors.

## [2026-04-30] concept v18 | plan-and-planstate

- Created `wiki/shared/concepts/plan-and-planstate.md`.
- Verified against `raw/postgres-18/src/include/nodes/plannodes.h:Plan`, `raw/postgres-18/src/include/nodes/execnodes.h:PlanState`, `raw/postgres-18/src/backend/executor/execProcnode.c:ExecInitNode`, and `raw/postgres-18/src/backend/executor/README`.

## [2026-04-30] concept v18 | path-and-reloptinfo

- Created `wiki/shared/concepts/path-and-reloptinfo.md`.
- Verified against `raw/postgres-18/src/include/nodes/pathnodes.h:RelOptInfo`, `raw/postgres-18/src/include/nodes/pathnodes.h:Path`, and `raw/postgres-18/src/include/nodes/pathnodes.h:ModifyTablePath`.

## [2026-04-30] concept v18 | executor-state

- Created `wiki/shared/concepts/executor-state.md`.
- Verified against `raw/postgres-18/src/include/nodes/execnodes.h:EState` and executor lifecycle functions in `raw/postgres-18/src/backend/executor/execMain.c`.

## [2026-04-30] concept v18 | tuple-table-slot

- Created `wiki/shared/concepts/tuple-table-slot.md`.
- Verified against `raw/postgres-18/src/include/executor/tuptable.h:TupleTableSlot`, `raw/postgres-18/src/include/executor/executor.h:ExecProcNode`, and tuple executor code.

## [2026-04-30] concept v18 | modifytable

- Created `wiki/shared/concepts/modifytable.md`.
- Verified against `raw/postgres-18/src/include/nodes/pathnodes.h:ModifyTablePath`, `raw/postgres-18/src/include/nodes/plannodes.h:ModifyTable`, `raw/postgres-18/src/include/nodes/execnodes.h:ModifyTableState`, and `raw/postgres-18/src/backend/executor/nodeModifyTable.c`.

## [2026-04-30] concept v18 | portal

- Created `wiki/shared/concepts/portal.md`.
- Verified against `raw/postgres-18/src/include/utils/portal.h:PortalData` and portal execution functions in `raw/postgres-18/src/backend/tcop/pquery.c`.

## [2026-04-30] concept v18 | querydesc

- Created `wiki/shared/concepts/querydesc.md`.
- Verified against `raw/postgres-18/src/include/executor/execdesc.h:QueryDesc`, `raw/postgres-18/src/backend/tcop/pquery.c`, and executor lifecycle functions in `raw/postgres-18/src/backend/executor/execMain.c`.

## [2026-04-30] tooling | maintenance scripts

- Added `scripts/recent_log` for recent activity summaries from `wiki/log.md`.
- Added `scripts/wiki_lint` for broken Obsidian links, orphan pages, missing front matter, stale version pins, and missing source references.
- Added `scripts/source_lookup` for project-local PostgreSQL source search, file display, and git history lookup.
- Added `scripts/version_diff` for comparing one source path across two project-local PostgreSQL checkouts.
- Added shared script helpers in `scripts/wiki_tooling.py`.
- Updated `AGENTS.md` to reference the project-local tooling workflow.

## [2026-04-30] lint | maintenance tooling smoke check

- Ran `scripts/wiki_lint --warnings-as-errors`; result was 0 errors and 0 warnings after replacing a stale illustrative `v17/index` wiki link with plain text.
- Verified `scripts/recent_log`, `scripts/source_lookup`, and `scripts/version_diff` against the current PostgreSQL 18 checkout.

## [2026-04-30] tooling | agent lifecycle wrapper

- Added `scripts/wiki_agent` to start, stop, inspect, and tail logs for the wiki maintainer process.
- Added `wiki/operations/agent.md` as the start/stop runbook.
- Updated `AGENTS.md`, `wiki/index.md`, and `wiki/overview.md` with the agent lifecycle workflow.

## [2026-04-30] lint | agent lifecycle smoke check

- Verified `scripts/wiki_agent start`, `status`, `logs`, and `stop` with a temporary Python sleep process.
- Ran `scripts/wiki_lint --warnings-as-errors`; result was 0 errors and 0 warnings.

## [2026-04-30] decision | Hermes-managed LLM lifecycle

- Recorded the lifecycle choice that `scripts/wiki_agent` starts Hermes, and Hermes starts or connects to the local LLM backend.
- Added `templates/wiki-agent-hermes.env.example` as the durable template for `.wiki-runtime/hermes/wiki-agent.env`.
- Updated `wiki/operations/agent.md` and `AGENTS.md` with the Hermes-managed LLM startup model.

## [2026-04-30] tooling | wiki_agent hardening

- `scripts/wiki_agent` now refuses to read `.wiki-runtime/hermes/wiki-agent.env` when it is group- or world-writable, and only honors an allowlist of variables (`WIKI_AGENT_COMMAND` plus runtime/cache/model vars). Other keys are logged and ignored.
- The pid file records pid plus the kernel-recorded process start time; `stop` and `status` verify the live start time before signaling, so a tampered or stale pid file cannot redirect signals to an unrelated process.
- `wiki-agent.stdout.log` and `wiki-agent.stderr.log` rotate to `.log.1` once they exceed 50 MiB.
- Fixed the dotenv quote stripping in `scripts/wiki_agent` so values with embedded quotes survive parsing.
- Added a Threat Model section to `wiki/operations/agent.md` and updated `templates/wiki-agent-hermes.env.example` with chmod, allowlist, and absolute-path guidance.
- Verified end to end with a smoke test: start, status, stop, env-permission rejection, env-allowlist filtering, pid tampering rejection, and 50 MiB log rotation.

## [2026-04-30] tooling | project-local Hermes install

- Installed `NousResearch/hermes-agent` under `.wiki-runtime/hermes-agent/` at commit `285e9efb3f2251f09cfbc9acb335c3d943d5a7b2`.
- Added project-local `uv` under `.wiki-runtime/env/uvprefix/` and installed Hermes Agent `0.11.0` into `.wiki-runtime/env/hermes-agent/`.
- Added `.wiki-runtime/hermes-agent/venv` as a symlink to `.wiki-runtime/env/hermes-agent/` for Hermes diagnostics.
- Created `.wiki-runtime/hermes/.env` from the Hermes example with `0600` permissions.
- Synced bundled Hermes skills into `.wiki-runtime/hermes/skills/`.
- Updated `.wiki-runtime/hermes/wiki-agent.env` and `templates/wiki-agent-hermes.env.example` to launch `.wiki-runtime/env/hermes-agent/bin/hermes gateway run --replace`.
- Updated `wiki/operations/agent.md` and `wiki/index.md` with the project-local Hermes runtime layout and commands.

## [2026-04-30] tooling | Hermes local LLM config

- Configured `.wiki-runtime/hermes/config.yaml` to use the project-local custom provider `pgwiki-local`.
- Set the default local model to `qwen2.5-coder:14b` through `http://127.0.0.1:11434/v1` with `chat_completions`, `context_length: 65536`, and `ollama_num_ctx: 65536`.
- Verified Hermes runtime resolution selects provider `custom`, requested provider `pgwiki-local`, base URL `http://127.0.0.1:11434/v1`, and model `qwen2.5-coder:14b`.
- Verified `scripts/wiki_lint --warnings-as-errors`; result was 0 errors and 0 warnings.
- Local endpoint probe failed because no server was listening on `127.0.0.1:11434`; documented the required Ollama/OpenAI-compatible server step in `wiki/operations/agent.md`.

## [2026-04-30] tooling | project-local planned model

- Downloaded the planned local coder model into `.wiki-runtime/models/qwen2.5-coder-14b-instruct-gguf/qwen2.5-coder-14b-instruct-q4_k_m.gguf`.
- Switched `scripts/llama_server` away from the borrowed `/data/repos/image-private/` model and made the project-local Qwen2.5-Coder 14B `q4_K_M` GGUF the default.
- Set the default llama.cpp KV cache types to `q4_0` for the 14B model so the 64K context target can fit the expected 16 GB GPU profile.
- Restarted llama.cpp with the project-local model and verified the OpenAI-compatible `/v1/models` and `/v1/chat/completions` endpoints.

## [2026-04-30] tooling | llama.cpp local LLM backend

- Added `scripts/llama_server` to start, stop, inspect, and tail logs for `/data/ollamacpp/llama.cpp/build/bin/llama-server`.
- Configured Hermes provider `pgwiki-local` to use llama.cpp at `http://127.0.0.1:8080/v1` with model alias `pgwiki-local`.
- Set the llama.cpp default model path to `/data/repos/image-private/models/Qwen3-4B-Instruct-2507-Q8_0.gguf`, with `LLAMA_MODEL` available as an override.
- Verified llama.cpp serves model alias `pgwiki-local` with `n_ctx_train: 262144` and 65,536-token slots.
- Verified the OpenAI-compatible chat endpoint at `http://127.0.0.1:8080/v1/chat/completions` with a tiny request.
- Updated `wiki/operations/agent.md` and `wiki/index.md` with the llama.cpp lifecycle workflow.

## [2026-04-30] tooling | Qwen3.5-9B local model

- Downloaded `Qwen3.5-9B-Q4_K_M.gguf` into `.wiki-runtime/models/qwen3.5-9b-gguf/`.
- Switched `scripts/llama_server` from the Qwen2.5-Coder 14B GGUF to the project-local Qwen3.5-9B `Q4_K_M` GGUF.
- Kept the OpenAI-compatible model alias `pgwiki-local` and Hermes provider endpoint at `http://127.0.0.1:8080/v1`.

## [2026-04-30] tooling | Qwen3.5-9B Q6_K 128K

- Downloaded `Qwen_Qwen3.5-9B-Q6_K.gguf` into `.wiki-runtime/models/qwen3.5-9b-gguf/`.
- Switched `scripts/llama_server` to the project-local Qwen3.5-9B `Q6_K` GGUF.
- Raised the llama.cpp default context and Hermes provider context metadata from 65,536 to 131,072 tokens.
- Restarted llama.cpp and verified `Q6_K`, 131,072-token slots, `/v1/models`, and `/v1/chat/completions`.

## [2026-04-30] tooling | Qwen3.5 thinking disabled

- Updated `scripts/llama_server` to start llama.cpp with `--reasoning off` and `--chat-template-kwargs '{"enable_thinking":false}'`.
- Documented the default and the `LLAMA_REASONING` / `LLAMA_CHAT_TEMPLATE_KWARGS` overrides in `wiki/operations/agent.md`.
- Restarted llama.cpp and verified the startup log reports `thinking = 0`; a plain `/v1/chat/completions` request returned answer text without per-request template overrides.

## [2026-04-30] docs | operator dashboard runbook

- Added top-level `operator.md` with commands for running `hermes dashboard` against the project-local Hermes home and llama.cpp backend.
- Documented dashboard status, stop, remote SSH tunnel access, and the distinction between the dashboard and `scripts/wiki_agent`.

## [2025-05-01] research | autovacuum history from v12 to v18

- Traced autovacuum evolution from PostgreSQL 12 to 18.
- Identified key commits from git history:
  - `b07642dbcd` - INSERT-based autovacuum triggers (v12)
  - `caf626b2cd` - Cost delay as floating-point GUC (v12)
  - `80d76be51c` - Temp table safety (v13)
  - `7526e10224` - BRIN auto-summarization (v11, enhanced in v14)
  - `306dc520b9` - autovacuum_vacuum_max_threshold (v16)
  - `c758119e5b` - Dynamic autovacuum_max_workers (v16)
  - `052026c9b9` - Aggressive vacuum optimization (v16)
  - `a9781ae11b` - Cost debug logging fix (v17)
  - `bfac8f8bc4` - Cost delay check fix (v17)
- Analyzed source files:
  - `src/backend/postmaster/autovacuum.c` (3475 lines)
  - `src/include/postmaster/autovacuum.h` (71 lines)
- Documented 17 GUC parameters and their evolution
| 2025-05-01 12:48 | **autovacuum-evolution** | Research | ✅ | Moved to `wiki/shared/autovacuum-evolution.md` for cross-version content. Added Open Questions section per AGENTS.md. Updated citations to use `raw/postgres-18/` source paths. Document now has 26 git commit references and follows citation discipline. |
  - Version-by-version feature breakdown
  - Git commit references for each major change
  - Source code line references
  - Default GUC values table
  - Summary table of all key changes

- Key features traced:
  - INSERT-based vacuum triggers (v12)
  - Cost-based vacuum delay (v12)
  - Temp table handling (v13)
  - BRIN auto-summarization integration (v14)
  - Memory leak fixes (v15)
  - AIO subsystem integration (v15)
  - Vacuum cost variable separation (v15)
  - Max threshold parameter (v16)
  - Dynamic worker management (v16)
  - Multi-xact freeze age improvements (v17)

## [2026-05-01] tooling | Hermes session cleanup

- Added `scripts/hermes_sessions` to list or clear project-local Hermes session files under `.wiki-runtime/hermes/sessions/`.
- Documented the cleanup workflow in `wiki/operations/agent.md`, `wiki/index.md`, and `wiki/overview.md`.
- The clear command defaults to a dry run and requires `--yes` to delete session files; it refuses to run while `scripts/wiki_agent` reports a live pid unless `--force` is supplied.

## [2026-05-01] tooling | Hermes session database purge

- Extended `scripts/hermes_sessions clear` to purge session rows from `.wiki-runtime/hermes/state.db` in addition to deleting files under `.wiki-runtime/hermes/sessions/`.
- The dry run now reports both session file items and `state.db` session/message row counts.
- The purge deletes `messages` and `sessions`, resets the message autoincrement sequence, checkpoints the WAL, and vacuums the database while keeping schema and non-session metadata intact; only destructive runs require the agent to be stopped or `--force`.

## [2026-05-01] tooling | Hermes Markdown PDF skill

- Added the project-local Hermes skill `markdown-pdf` under `.wiki-runtime/hermes/skills/productivity/markdown-pdf/`.
- Added bundled converter script `scripts/md_to_pdf.py` for generating PDFs from Markdown through the Hermes Python runtime.
- Installed `reportlab==4.5.0` and `pillow==12.2.0` into `.wiki-runtime/env/hermes-agent/`; reused existing `markdown-it-py==4.0.0`.
- Documented the skill and dependency location in `wiki/operations/agent.md`.

## [2026-05-01] tooling | Hermes HTML PDF skill

- Added the project-local Hermes skill `html-pdf` under `.wiki-runtime/hermes/skills/productivity/html-pdf/`.
- Added bundled converter script `scripts/html_to_pdf.py` for generating document-style PDFs from local HTML through the Hermes Python runtime.
- Reused the existing project-local `reportlab==4.5.0` and `pillow==12.2.0` runtime dependencies instead of adding a browser or system-Cairo renderer.
- Documented the skill and dependency location in `wiki/operations/agent.md`.

## [2026-05-01] tooling | dashboard Tailscale exposure

- Updated `scripts/dashboard` so `start` exposes the dashboard port through Tailscale Serve by default while keeping the Hermes dashboard bound to loopback.
- Added `scripts/dashboard unserve` plus `HERMES_DASHBOARD_TAILSCALE_*` environment overrides for Serve/Funnel mode, HTTPS port, path, target, and stop cleanup.
- Updated `scripts/stop_all` and `operator.md` to use the dashboard wrapper instead of calling `hermes dashboard` directly.

## [2026-05-02] answer v18 | insert-row-disk-writes

- Created `wiki/v18/questions/insert-row-disk-writes.md` tracing disk writes on simple row insert txn: WAL sync at commit (XLogFlush in CommitTransaction@xact.c:2228/1502) only; heap/index async via bgwriter/checkpointer; cites heap_insert@heapam_handler.c:255/278, ExecInsert@nodeModifyTable.c; mermaid + excalidraw JSON seq diagrams; cross-links [[v18/code-paths/insert-path]].
- Updated `wiki/v18/index.md` and `wiki/index.md` question lists.

## [2026-05-02] tooling | model config alignment and unused model prune

- Renamed every Hermes auxiliary model id from `Qwen3.5-9B-Q8_0` to `pgwiki-local` in `.wiki-runtime/hermes/config.yaml` so the config matches the alias the running llama-server actually advertises.
- Made `scripts/llama_server`'s `thinking` mode actually toggle `--reasoning auto` and `enable_thinking:true`; the `precise` mode keeps reasoning off. Previously the mode flag only changed sampling and the chat template kept thinking disabled.
- Refreshed `wiki/operations/agent.md` to document the split hosted-main / local-aux design, the `pgwiki-local` server alias, the `q8_0` KV cache default, and the precise/thinking sampling modes.
- Updated `AGENTS.md` to reference the local model by alias rather than file-name quantization.
- Deleted `scripts/llama_server_old copy` leftover and pruned unused GGUFs under `.wiki-runtime/models/`: `Qwen3.5-9B-Q4_K_M.gguf`, `Qwen3.5-9B-Q8_0.gguf`, the `qwen2.5-coder-14b-instruct-gguf/` tree, and the `qwen3-coder-30b-a3b-instruct-gguf/` tree. The currently-loaded `Qwen_Qwen3.5-9B-Q6_K.gguf` is the only weights file kept.
- Restored `wiki/log.md` after an accidental truncation that had wiped historical entries.

## [2026-05-02] lint | fixed wiki_lint errors/warnings

- Created `wiki/operations/agent.md` runbook (Hermes/llama lifecycle).
