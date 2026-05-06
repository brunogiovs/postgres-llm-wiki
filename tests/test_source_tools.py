from __future__ import annotations

import json
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


if __name__ == "__main__":
    unittest.main()
