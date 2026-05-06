from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class SyntheticSourceToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="source-tools-e2e-")
        self.repo = Path(self.tmp.name) / "synthetic-wiki"
        self.repo.mkdir()
        self._copy_scripts()
        self._write_synthetic_wiki()
        self._write_synthetic_source()
        self._write_synthetic_context()
        self._initialise_source_git_repo()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _copy_scripts(self) -> None:
        scripts = self.repo / "scripts"
        scripts.mkdir()
        for name in ("source_deps", "source_lookup", "wiki_tooling.py"):
            source = REPO_ROOT / "scripts" / name
            target = scripts / name
            shutil.copy2(source, target)
            target.chmod(source.stat().st_mode)

    def _write(self, rel_path: str, text: str) -> Path:
        path = self.repo / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
        return path

    def _write_synthetic_wiki(self) -> None:
        self._write(
            "wiki/versions.md",
            """
            # PostgreSQL Versions

            ## Supported Versions

            | Version | Status | Wiki Home | Branch | Pinned Commit | Coverage |
            |---|---|---|---|---|---|
            | 99 | primary | [[v99/index]] | `SYNTHETIC_STABLE` | `abc123synthetic` | Synthetic test fixture. |
            """,
        )

    def _write_synthetic_source(self) -> None:
        self._write(
            "raw/postgres-99/src/backend/storage/buffer/bufmgr.c",
            """
            #include "postgres.h"
            #include "storage/bufmgr.h"
            #include "generated/config.h"
            #include <sys/types.h>

            int
            SyntheticThing(int input)
            {
                return input + SYNTHETIC_FLAG;
            }
            """,
        )
        self._write(
            "raw/postgres-99/src/include/postgres.h",
            """
            #include "c.h"
            #define POSTGRES_SYNTHETIC 1
            """,
        )
        self._write(
            "raw/postgres-99/src/include/c.h",
            """
            #define C_SYNTHETIC 1
            """,
        )
        self._write(
            "raw/postgres-99/src/include/storage/bufmgr.h",
            """
            #include "storage/block.h"
            int SyntheticThing(int input);
            """,
        )
        self._write(
            "raw/postgres-99/src/include/storage/block.h",
            """
            #define SYNTHETIC_BLOCK 42
            """,
        )
        self._write(
            ".wiki-runtime/build/postgres-99/src/include/generated/config.h",
            """
            #define SYNTHETIC_FLAG 7
            """,
        )

    def _write_synthetic_context(self) -> None:
        build_include = self.repo / ".wiki-runtime/build/postgres-99/src/include"
        raw_include = self.repo / "raw/postgres-99/src/include"
        buffer_dir = self.repo / ".wiki-runtime/build/postgres-99/src/backend/storage/buffer"
        source_file = self.repo / "raw/postgres-99/src/backend/storage/buffer/bufmgr.c"
        self._write(
            ".wiki-runtime/context/postgres-99/manifest.md",
            """
            # PostgreSQL 99 Project Context Pack

            This synthetic pack is orientation material for tests.
            """,
        )
        self._write(
            ".wiki-runtime/context/postgres-99/include-deps.txt",
            """
            # Include Dependencies for PostgreSQL 99

            Derived from compile_commands.json source entries by recording direct #include directives.

            ## Build Include Directories

            - `.wiki-runtime/build/postgres-99/src/include`
            - `raw/postgres-99/src/include`

            ## Direct Include Edges

            raw/postgres-99/src/backend/storage/buffer/bufmgr.c: postgres.h
            raw/postgres-99/src/backend/storage/buffer/bufmgr.c: storage/bufmgr.h
            raw/postgres-99/src/backend/storage/buffer/bufmgr.c: generated/config.h
            raw/postgres-99/src/backend/storage/buffer/bufmgr.c: sys/types.h
            raw/postgres-99/src/include/postgres.h: c.h
            raw/postgres-99/src/include/storage/bufmgr.h: storage/block.h
            """,
        )
        compile_db = [
            {
                "file": str(source_file),
                "directory": str(buffer_dir),
                "output": "bufmgr.o",
                "arguments": [
                    "cc",
                    "-DBUILDING_SYNTHETIC",
                    "-DSYNTHETIC_MODE=1",
                    "-I",
                    str(build_include),
                    "-I",
                    str(raw_include),
                    "-c",
                    str(source_file),
                    "-o",
                    "bufmgr.o",
                ],
            }
        ]
        path = self.repo / ".wiki-runtime/context/postgres-99/compile_commands.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(compile_db, indent=2), encoding="utf-8")

    def _initialise_source_git_repo(self) -> None:
        source = self.repo / "raw/postgres-99"
        self._run(["git", "init"], cwd=source)
        self._run(["git", "add", "."], cwd=source)
        self._run(
            [
                "git",
                "-c",
                "user.name=Source Tools Test",
                "-c",
                "user.email=source-tools@example.invalid",
                "commit",
                "-m",
                "initial synthetic source",
            ],
            cwd=source,
        )

    def _run(
        self,
        argv: list[str],
        *,
        cwd: Path | None = None,
        check: bool = True,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(argv, cwd=cwd or self.repo, text=True, capture_output=True, env=env)
        if check and proc.returncode != 0:
            self.fail(
                "command failed\n"
                f"argv: {' '.join(argv)}\n"
                f"cwd: {cwd or self.repo}\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}"
            )
        return proc

    def _script(
        self,
        name: str,
        *args: str,
        check: bool = True,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return self._run([sys.executable, str(self.repo / "scripts" / name), *args], check=check, env=env)

    def _env_with_only_tools(self, *tool_names: str) -> dict[str, str]:
        tool_dir = self.repo / "tool-path"
        tool_dir.mkdir(exist_ok=True)
        for tool_name in tool_names:
            tool = shutil.which(tool_name)
            if tool is None:
                self.skipTest(f"{tool_name} is required for this test")
            target = tool_dir / tool_name
            if target.exists():
                continue
            try:
                target.symlink_to(tool)
            except OSError:
                shutil.copy2(tool, target)
                target.chmod(Path(tool).stat().st_mode)

        env = os.environ.copy()
        env["PATH"] = str(tool_dir)
        return env

    def test_source_lookup_requires_explicit_supported_version(self) -> None:
        missing = self._script("source_lookup", "--symbol", "SyntheticThing", check=False)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("--version", missing.stderr)

        unsupported = self._script("source_lookup", "--version", "100", "--symbol", "SyntheticThing", check=False)
        self.assertEqual(unsupported.returncode, 2)
        self.assertIn("unsupported PostgreSQL version: 100", unsupported.stderr)

    def test_source_deps_requires_explicit_version(self) -> None:
        missing = self._script(
            "source_deps",
            "--includes",
            "src/backend/storage/buffer/bufmgr.c",
            check=False,
        )
        self.assertEqual(missing.returncode, 2)
        self.assertIn("--version", missing.stderr)

    def test_source_lookup_symbol_path_and_log(self) -> None:
        by_path = self._script(
            "source_lookup",
            "--version",
            "99",
            "--path",
            "src/backend/storage/buffer/bufmgr.c",
            "--start",
            "1",
            "--limit",
            "4",
        )
        self.assertIn('#include "postgres.h"', by_path.stdout)
        self.assertIn("#include <sys/types.h>", by_path.stdout)

        by_symbol = self._script("source_lookup", "--version", "99", "--symbol", "SyntheticThing", "--limit", "10")
        self.assertIn("src/backend/storage/buffer/bufmgr.c", by_symbol.stdout)
        self.assertIn("SyntheticThing", by_symbol.stdout)

        by_log = self._script("source_lookup", "--version", "99", "--log", "src/backend/storage/buffer/bufmgr.c")
        self.assertIn("initial synthetic source", by_log.stdout)

    def test_source_deps_direct_includes_resolve_raw_build_and_system_headers(self) -> None:
        proc = self._script(
            "source_deps",
            "--version",
            "99",
            "--includes",
            "src/backend/storage/buffer/bufmgr.c",
            "--format",
            "json",
        )
        payload = json.loads(proc.stdout)
        rows = {row["include"]: row for row in payload["includes"]}

        self.assertEqual(rows["postgres.h"]["resolved"], "raw/postgres-99/src/include/postgres.h")
        self.assertEqual(rows["postgres.h"]["kind"], "raw")
        self.assertEqual(rows["generated/config.h"]["resolved"], ".wiki-runtime/build/postgres-99/src/include/generated/config.h")
        self.assertEqual(rows["generated/config.h"]["kind"], "build")
        self.assertIsNone(rows["sys/types.h"]["resolved"])
        self.assertEqual(rows["sys/types.h"]["kind"], "unresolved")

    def test_source_deps_reverse_lookup_compile_unit_and_transitive_tree(self) -> None:
        included_by = self._script(
            "source_deps",
            "--version",
            "99",
            "--included-by",
            "storage/bufmgr.h",
            "--format",
            "json",
        )
        payload = json.loads(included_by.stdout)
        self.assertEqual(payload["resolved_target"], "raw/postgres-99/src/include/storage/bufmgr.h")
        self.assertEqual(
            payload["sources"],
            [{"include_directives": 1, "source": "raw/postgres-99/src/backend/storage/buffer/bufmgr.c"}],
        )

        compile_unit = self._script(
            "source_deps",
            "--version",
            "99",
            "--compile-unit",
            "src/backend/storage/buffer/bufmgr.c",
        )
        self.assertIn("BUILDING_SYNTHETIC", compile_unit.stdout)
        self.assertIn("SYNTHETIC_MODE=1", compile_unit.stdout)
        self.assertIn("raw/postgres-99/src/include", compile_unit.stdout)

        transitive = self._script(
            "source_deps",
            "--version",
            "99",
            "--transitive-includes",
            "src/backend/storage/buffer/bufmgr.c",
            "--depth",
            "2",
            "--limit",
            "20",
        )
        self.assertIn("[1] raw/postgres-99/src/backend/storage/buffer/bufmgr.c: storage/bufmgr.h", transitive.stdout)
        self.assertIn("[2] raw/postgres-99/src/include/storage/bufmgr.h: storage/block.h", transitive.stdout)

    def test_source_lookup_regex_search(self) -> None:
        # Pattern is valid in ripgrep, git grep -E, and Python re alike.
        match = self._script(
            "source_lookup",
            "--version",
            "99",
            "--symbol",
            "Synthetic[A-Z][a-zA-Z]+",
            "--regex",
            "--limit",
            "5",
        )
        self.assertIn("SyntheticThing", match.stdout)

    def test_source_lookup_regex_search_uses_git_ere_when_ripgrep_is_unavailable(self) -> None:
        env = self._env_with_only_tools("git")
        self.assertIsNone(shutil.which("rg", path=env["PATH"]))
        self.assertIsNotNone(shutil.which("git", path=env["PATH"]))

        match = self._script(
            "source_lookup",
            "--version",
            "99",
            "--symbol",
            "Synthetic(A|Thing)+",
            "--regex",
            "--limit",
            "5",
            env=env,
        )
        self.assertIn("SyntheticThing", match.stdout)

    def test_source_deps_includes_text_truncation_message(self) -> None:
        proc = self._script(
            "source_deps",
            "--version",
            "99",
            "--includes",
            "src/backend/storage/buffer/bufmgr.c",
            "--limit",
            "2",
        )
        self.assertIn("truncated", proc.stdout)
        self.assertIn("raise --limit", proc.stdout)

    def test_source_deps_includes_json_honours_limit(self) -> None:
        proc = self._script(
            "source_deps",
            "--version",
            "99",
            "--includes",
            "src/backend/storage/buffer/bufmgr.c",
            "--format",
            "json",
            "--limit",
            "2",
        )
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["truncated"])
        self.assertEqual(len(payload["includes"]), 2)

    def test_source_deps_compile_unit_missing_returns_error_in_both_formats(self) -> None:
        text = self._script(
            "source_deps",
            "--version",
            "99",
            "--compile-unit",
            "src/include/postgres.h",
            check=False,
        )
        self.assertEqual(text.returncode, 1)
        self.assertIn("no compile_commands.json entry", text.stderr)

        as_json = self._script(
            "source_deps",
            "--version",
            "99",
            "--compile-unit",
            "src/include/postgres.h",
            "--format",
            "json",
            check=False,
        )
        self.assertEqual(as_json.returncode, 1)
        payload = json.loads(as_json.stdout)
        self.assertEqual(payload["compile_entries"], [])

    def test_source_deps_compile_unit_full_command_in_text_mode(self) -> None:
        proc = self._script(
            "source_deps",
            "--version",
            "99",
            "--compile-unit",
            "src/backend/storage/buffer/bufmgr.c",
            "--full-command",
        )
        self.assertIn("## Command", proc.stdout)
        self.assertIn("-DBUILDING_SYNTHETIC", proc.stdout)

    def test_source_deps_path_outside_raw_is_rejected(self) -> None:
        outside = self.repo / "outside.c"
        outside.write_text('#include "postgres.h"\n', encoding="utf-8")
        proc = self._script(
            "source_deps",
            "--version",
            "99",
            "--includes",
            str(outside),
            check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("could not resolve", proc.stderr)

    def test_source_deps_missing_context_pack_reports_actionable_error(self) -> None:
        manifest = self.repo / ".wiki-runtime/context/postgres-99/manifest.md"
        manifest.unlink()
        proc = self._script(
            "source_deps",
            "--version",
            "99",
            "--includes",
            "src/backend/storage/buffer/bufmgr.c",
            check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("missing context manifest", proc.stderr)
        self.assertIn("scripts/source_context", proc.stderr)

    def test_source_deps_transitive_handles_cycles(self) -> None:
        cycle_path = self.repo / ".wiki-runtime/context/postgres-99/include-deps.txt"
        original = cycle_path.read_text(encoding="utf-8")
        cycle_path.write_text(
            original
            + "raw/postgres-99/src/include/cycle_a.h: cycle_b.h\n"
            + "raw/postgres-99/src/include/cycle_b.h: cycle_a.h\n",
            encoding="utf-8",
        )
        self._write(
            "raw/postgres-99/src/include/cycle_a.h",
            """
            #include "cycle_b.h"
            """,
        )
        self._write(
            "raw/postgres-99/src/include/cycle_b.h",
            """
            #include "cycle_a.h"
            """,
        )
        proc = self._script(
            "source_deps",
            "--version",
            "99",
            "--transitive-includes",
            "src/include/cycle_a.h",
            "--depth",
            "5",
            "--limit",
            "20",
            "--format",
            "json",
        )
        payload = json.loads(proc.stdout)
        rows = payload["includes"]
        self.assertFalse(payload["truncated"])
        self.assertEqual(len(rows), 2)
        sources = {row["source"] for row in rows}
        self.assertEqual(
            sources,
            {
                "raw/postgres-99/src/include/cycle_a.h",
                "raw/postgres-99/src/include/cycle_b.h",
            },
        )

    def test_source_deps_included_by_sorts_by_count_desc(self) -> None:
        deps_path = self.repo / ".wiki-runtime/context/postgres-99/include-deps.txt"
        original = deps_path.read_text(encoding="utf-8")
        # heavy.c has three directives that resolve to bufmgr.h, light.c has one.
        # Alphabetically, heavy.c sorts after light.c, so a count-desc sort must
        # put heavy.c first to verify the ranking.
        extra = (
            "raw/postgres-99/src/backend/storage/buffer/heavy.c: storage/bufmgr.h\n"
            "raw/postgres-99/src/backend/storage/buffer/heavy.c: bufmgr.h\n"
            "raw/postgres-99/src/backend/storage/buffer/heavy.c: storage/bufmgr.h\n"
            "raw/postgres-99/src/backend/storage/buffer/light.c: storage/bufmgr.h\n"
        )
        deps_path.write_text(original + extra, encoding="utf-8")
        self._write("raw/postgres-99/src/backend/storage/buffer/heavy.c", "")
        self._write("raw/postgres-99/src/backend/storage/buffer/light.c", "")

        proc = self._script(
            "source_deps",
            "--version",
            "99",
            "--included-by",
            "storage/bufmgr.h",
            "--format",
            "json",
        )
        payload = json.loads(proc.stdout)
        ordered = [entry["source"] for entry in payload["sources"]]
        self.assertEqual(
            ordered,
            [
                "raw/postgres-99/src/backend/storage/buffer/heavy.c",
                "raw/postgres-99/src/backend/storage/buffer/bufmgr.c",
                "raw/postgres-99/src/backend/storage/buffer/light.c",
            ],
        )


class SourceContextEndToEndTest(unittest.TestCase):
    """Exercise scripts/source_context against a synthetic source tree.

    The fixture has no meson.build, no configure script, and no .git, so the
    pack generator must fall through to the textual include scan.  These tests
    pin the producer/consumer contract: source_context writes the structured
    `## Build Include Directories` / `## Direct Include Edges` format that
    source_deps parses, regardless of which generation path fires.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="source-context-e2e-")
        self.repo = Path(self.tmp.name) / "synthetic-wiki"
        self.repo.mkdir()
        self._copy_scripts()
        self._write_synthetic_wiki()
        self._write_synthetic_source()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _copy_scripts(self) -> None:
        scripts = self.repo / "scripts"
        scripts.mkdir()
        for name in ("source_context", "source_deps", "wiki_tooling.py"):
            source = REPO_ROOT / "scripts" / name
            target = scripts / name
            shutil.copy2(source, target)
            target.chmod(source.stat().st_mode)

    def _write(self, rel_path: str, text: str) -> Path:
        path = self.repo / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
        return path

    def _write_synthetic_wiki(self) -> None:
        self._write(
            "wiki/versions.md",
            """
            # PostgreSQL Versions

            ## Supported Versions

            | Version | Status | Wiki Home | Branch | Pinned Commit | Coverage |
            |---|---|---|---|---|---|
            | 99 | primary | [[v99/index]] | `SYNTHETIC_STABLE` | `abc123synthetic` | Synthetic test fixture. |
            """,
        )

    def _write_synthetic_source(self) -> None:
        self._write(
            "raw/postgres-99/src/backend/storage/buffer/bufmgr.c",
            """
            #include "postgres.h"
            #include "storage/bufmgr.h"

            int SyntheticThing(int input) { return input + 1; }
            """,
        )
        self._write(
            "raw/postgres-99/src/include/postgres.h",
            """
            #define POSTGRES_SYNTHETIC 1
            """,
        )
        self._write(
            "raw/postgres-99/src/include/storage/bufmgr.h",
            """
            int SyntheticThing(int input);
            """,
        )

    def _run(self, argv: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(argv, cwd=cwd or self.repo, text=True, capture_output=True)
        if check and proc.returncode != 0:
            self.fail(
                "command failed\n"
                f"argv: {' '.join(argv)}\n"
                f"cwd: {cwd or self.repo}\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}"
            )
        return proc

    def _script(self, name: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self._run([sys.executable, str(self.repo / "scripts" / name), *args], check=check)

    def _initialise_source_git_repo(self) -> None:
        source = self.repo / "raw/postgres-99"
        self._run(["git", "init"], cwd=source)
        self._run(["git", "add", "."], cwd=source)
        self._run(
            [
                "git",
                "-c",
                "user.name=Source Context Test",
                "-c",
                "user.email=source-context@example.invalid",
                "commit",
                "-m",
                "initial synthetic source",
            ],
            cwd=source,
        )

    def _read_artifact_status(self, manifest_text: str, artifact: str) -> str:
        for line in manifest_text.splitlines():
            if line.startswith(f"| `{artifact}` |"):
                cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
                # | name | path | status | details |
                if len(cells) >= 3:
                    return cells[2]
        return ""

    def test_source_context_requires_explicit_scope(self) -> None:
        proc = self._script("source_context", "--skip-callgraphs", check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--version", proc.stderr)

    def test_textual_fallback_writes_format_consumable_by_source_deps(self) -> None:
        self._script("source_context", "--version", "99", "--skip-callgraphs")

        context_dir = self.repo / ".wiki-runtime/context/postgres-99"
        manifest = context_dir / "manifest.md"
        deps = context_dir / "include-deps.txt"
        self.assertTrue(manifest.is_file())
        self.assertTrue(deps.is_file())

        deps_text = deps.read_text(encoding="utf-8")
        self.assertIn("## Build Include Directories", deps_text)
        self.assertIn("## Direct Include Edges", deps_text)
        self.assertIn("textual scan", deps_text)
        self.assertIn(
            "raw/postgres-99/src/backend/storage/buffer/bufmgr.c: postgres.h",
            deps_text,
        )
        self.assertIn(
            "raw/postgres-99/src/backend/storage/buffer/bufmgr.c: storage/bufmgr.h",
            deps_text,
        )

        manifest_text = manifest.read_text(encoding="utf-8")
        self.assertEqual(self._read_artifact_status(manifest_text, "compile_commands.json"), "deferred")
        self.assertEqual(self._read_artifact_status(manifest_text, "include-deps.txt"), "generated")
        self.assertEqual(self._read_artifact_status(manifest_text, "callgraphs/"), "skipped")

        consumed = self._script(
            "source_deps",
            "--version",
            "99",
            "--includes",
            "src/backend/storage/buffer/bufmgr.c",
            "--format",
            "json",
        )
        payload = json.loads(consumed.stdout)
        rows = {row["include"]: row for row in payload["includes"]}
        self.assertEqual(
            rows["postgres.h"]["resolved"],
            "raw/postgres-99/src/include/postgres.h",
        )
        self.assertEqual(rows["postgres.h"]["kind"], "raw")

        missing_compile_db = self._script(
            "source_deps",
            "--version",
            "99",
            "--compile-unit",
            "src/backend/storage/buffer/bufmgr.c",
            check=False,
        )
        self.assertEqual(missing_compile_db.returncode, 2)
        self.assertIn("compile_commands.json is not present", missing_compile_db.stderr)
        self.assertIn("scripts/source_context --version 99", missing_compile_db.stderr)

    def test_textual_fallback_uses_git_tracked_c_and_h_files_when_checkout_has_git(self) -> None:
        self._write(
            "raw/postgres-99/src/include/storage/bufmgr.h",
            """
            #include "postgres.h"
            int SyntheticThing(int input);
            """,
        )
        self._initialise_source_git_repo()
        self._write(
            "raw/postgres-99/src/include/untracked.h",
            """
            #include "postgres.h"
            """,
        )

        self._script("source_context", "--version", "99", "--skip-callgraphs")

        deps_text = (self.repo / ".wiki-runtime/context/postgres-99/include-deps.txt").read_text(encoding="utf-8")
        self.assertIn(
            "raw/postgres-99/src/backend/storage/buffer/bufmgr.c: storage/bufmgr.h",
            deps_text,
        )
        self.assertIn(
            "raw/postgres-99/src/include/storage/bufmgr.h: postgres.h",
            deps_text,
        )
        self.assertNotIn(
            "raw/postgres-99/src/include/untracked.h: postgres.h",
            deps_text,
        )

    def test_compile_db_path_writes_format_consumable_by_source_deps(self) -> None:
        context_dir = self.repo / ".wiki-runtime/context/postgres-99"
        context_dir.mkdir(parents=True)
        source_file = self.repo / "raw/postgres-99/src/backend/storage/buffer/bufmgr.c"
        raw_include = self.repo / "raw/postgres-99/src/include"
        compile_db = [
            {
                "file": str(source_file),
                "directory": str(source_file.parent),
                "arguments": [
                    "cc",
                    "-DBUILDING_SYNTHETIC",
                    "-I",
                    str(raw_include),
                    "-c",
                    str(source_file),
                ],
            }
        ]
        (context_dir / "compile_commands.json").write_text(
            json.dumps(compile_db, indent=2), encoding="utf-8"
        )

        self._script("source_context", "--version", "99", "--skip-callgraphs")

        deps_text = (context_dir / "include-deps.txt").read_text(encoding="utf-8")
        self.assertIn("Derived from compile_commands.json", deps_text)
        self.assertIn(
            f"- `{raw_include.relative_to(self.repo).as_posix()}`",
            deps_text,
        )
        self.assertIn(
            "raw/postgres-99/src/backend/storage/buffer/bufmgr.c: postgres.h",
            deps_text,
        )

        consumed = self._script(
            "source_deps",
            "--version",
            "99",
            "--includes",
            "src/backend/storage/buffer/bufmgr.c",
            "--format",
            "json",
        )
        payload = json.loads(consumed.stdout)
        rows = {row["include"]: row for row in payload["includes"]}
        self.assertEqual(
            rows["postgres.h"]["resolved"],
            "raw/postgres-99/src/include/postgres.h",
        )

        compile_unit = self._script(
            "source_deps",
            "--version",
            "99",
            "--compile-unit",
            "src/backend/storage/buffer/bufmgr.c",
        )
        self.assertIn("BUILDING_SYNTHETIC", compile_unit.stdout)


if __name__ == "__main__":
    unittest.main()
