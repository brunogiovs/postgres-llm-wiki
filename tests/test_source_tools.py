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


class SourceGraphToolsTest(unittest.TestCase):
    """Exercise the graph-only source navigation contract."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="source-graph-e2e-")
        self.repo = Path(self.tmp.name) / "synthetic-wiki"
        self.repo.mkdir()
        self._copy_scripts()
        self._write_synthetic_source()
        self._initialise_source_git_repo()
        self.source_head = self._run(["git", "rev-parse", "HEAD"], cwd=self.repo / "raw/postgres-99").stdout.strip()
        self._write_synthetic_wiki(self.source_head)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _copy_scripts(self) -> None:
        scripts = self.repo / "scripts"
        scripts.mkdir()
        for name in ("source_graph", "source_graph_check", "source_graph_query", "wiki_tooling.py"):
            source = REPO_ROOT / "scripts" / name
            target = scripts / name
            shutil.copy2(source, target)
            target.chmod(source.stat().st_mode)

    def _write(self, rel_path: str, text: str) -> Path:
        path = self.repo / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
        return path

    def _write_synthetic_wiki(self, commit: str) -> None:
        self._write(
            "wiki/versions.md",
            f"""
            # PostgreSQL Versions

            ## Supported Versions

            | Version | Status | Wiki Home | Branch | Pinned Commit | Coverage |
            |---|---|---|---|---|---|
            | 99 | primary | [[v99/index]] | `SYNTHETIC_STABLE` | `{commit}` | Synthetic test fixture. |
            """,
        )

    def _write_synthetic_source(self) -> None:
        self._write(
            "raw/postgres-99/src/backend/storage/buffer/bufmgr.c",
            """
            #include "postgres.h"
            #include "storage/bufmgr.h"
            #include <sys/types.h>

            int
            SyntheticThing(int input)
            {
                return input + 1;
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

    def _initialise_source_git_repo(self) -> None:
        source = self.repo / "raw/postgres-99"
        self._run(["git", "init"], cwd=source)
        self._run(["git", "add", "."], cwd=source)
        self._run(
            [
                "git",
                "-c",
                "user.name=Source Graph Test",
                "-c",
                "user.email=source-graph@example.invalid",
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

    def _fake_graphify_env(self) -> dict[str, str]:
        tool_dir = self.repo / "tool-path"
        tool_dir.mkdir(exist_ok=True)
        graphify = tool_dir / "graphify"
        graphify.write_text(
            textwrap.dedent(
                f"""
                #!{sys.executable}
                import json
                import os
                import pathlib
                import sys

                args = sys.argv[1:]
                if args == ["--help"]:
                    print("Usage: graphify <command>")
                    raise SystemExit(0)

                if args and args[0] in {{"query", "path", "explain"}}:
                    if "--graph" not in args:
                        print("missing --graph", file=sys.stderr)
                        raise SystemExit(2)
                    graph_path = pathlib.Path(args[args.index("--graph") + 1])
                    if not graph_path.is_file():
                        print("missing graph", file=sys.stderr)
                        raise SystemExit(2)
                    command = args[0]
                    if command == "query":
                        print("QUERY " + args[1])
                    elif command == "path":
                        print("PATH " + args[1] + " -> " + args[2])
                    else:
                        print("EXPLAIN " + args[1])
                    raise SystemExit(0)

                if args and args[0] == "update":
                    out = pathlib.Path(os.environ.get("GRAPHIFY_OUT", pathlib.Path(args[1]) / "graphify-out"))
                elif args and args[0] == "extract":
                    out_base = pathlib.Path(args[args.index("--out") + 1]) if "--out" in args else pathlib.Path(args[1])
                    out = out_base / "graphify-out"
                else:
                    print("unexpected graphify command: " + " ".join(args), file=sys.stderr)
                    raise SystemExit(2)

                out.mkdir(parents=True, exist_ok=True)
                graph = {{
                    "nodes": [
                        {{"id": "SyntheticThing", "path": "raw/postgres-99/src/backend/storage/buffer/bufmgr.c"}}
                    ],
                    "edges": []
                }}
                (out / "graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")
                (out / "GRAPH_REPORT.md").write_text(
                    "# Synthetic Graph\\n\\nSource: raw/postgres-99/src/backend/storage/buffer/bufmgr.c\\n",
                    encoding="utf-8",
                )
                (out / "cache").mkdir(exist_ok=True)
                print("synthetic graphify build")
                """
            ).lstrip(),
            encoding="utf-8",
        )
        graphify.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = str(tool_dir) + os.pathsep + env.get("PATH", "")
        return env

    def test_source_graph_requires_explicit_scope_and_supported_version(self) -> None:
        missing = self._script("source_graph", check=False)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("--version", missing.stderr)

        unsupported = self._script("source_graph", "--version", "100", "--dry-run", check=False)
        self.assertEqual(unsupported.returncode, 2)
        self.assertIn("unsupported PostgreSQL version: 100", unsupported.stderr)

    def test_source_graph_query_raw_symbol_file_log_and_includes(self) -> None:
        by_path = self._script(
            "source_graph_query",
            "--version",
            "99",
            "file",
            "src/backend/storage/buffer/bufmgr.c",
            "--start",
            "1",
            "--limit",
            "4",
        )
        self.assertIn('#include "postgres.h"', by_path.stdout)
        self.assertIn("#include <sys/types.h>", by_path.stdout)

        by_symbol = self._script("source_graph_query", "--version", "99", "symbol", "SyntheticThing", "--limit", "10")
        self.assertIn("src/backend/storage/buffer/bufmgr.c", by_symbol.stdout)
        self.assertIn("SyntheticThing", by_symbol.stdout)

        by_log = self._script("source_graph_query", "--version", "99", "log", "src/backend/storage/buffer/bufmgr.c")
        self.assertIn("initial synthetic source", by_log.stdout)

        includes = self._script(
            "source_graph_query",
            "--version",
            "99",
            "includes",
            "src/backend/storage/buffer/bufmgr.c",
            "--format",
            "json",
        )
        include_rows = {row["include"]: row for row in json.loads(includes.stdout)["includes"]}
        self.assertEqual(include_rows["postgres.h"]["resolved"], "raw/postgres-99/src/include/postgres.h")
        self.assertEqual(include_rows["storage/bufmgr.h"]["resolved"], "raw/postgres-99/src/include/storage/bufmgr.h")
        self.assertIsNone(include_rows["sys/types.h"]["resolved"])

        included_by = self._script(
            "source_graph_query",
            "--version",
            "99",
            "included-by",
            "storage/bufmgr.h",
            "--format",
            "json",
        )
        sources = json.loads(included_by.stdout)["sources"]
        self.assertEqual(
            sources,
            [{"include_directives": 1, "source": "raw/postgres-99/src/backend/storage/buffer/bufmgr.c"}],
        )

    def test_source_graph_query_regex_uses_git_when_ripgrep_is_unavailable(self) -> None:
        env = self._env_with_only_tools("git")
        self.assertIsNone(shutil.which("rg", path=env["PATH"]))
        self.assertIsNotNone(shutil.which("git", path=env["PATH"]))

        match = self._script(
            "source_graph_query",
            "--version",
            "99",
            "symbol",
            "Synthetic(A|Thing)+",
            "--regex",
            "--limit",
            "5",
            env=env,
        )
        self.assertIn("SyntheticThing", match.stdout)

    def test_source_graph_query_symbol_ignores_untracked_checkout_files(self) -> None:
        self._write(
            "raw/postgres-99/wiki/noise.md",
            """
            This untracked file mentions SyntheticThing, but it is not part of
            the pinned source checkout.
            """,
        )

        match = self._script("source_graph_query", "--version", "99", "symbol", "SyntheticThing", "--limit", "20")
        self.assertIn("src/backend/storage/buffer/bufmgr.c", match.stdout)
        self.assertNotIn("wiki/noise.md", match.stdout)

    def test_source_graph_generates_and_queries_fake_graphify_output(self) -> None:
        env = self._fake_graphify_env()
        generated = self._script("source_graph", "--version", "99", "--refresh", env=env)
        self.assertIn("generated graph.json", generated.stdout)

        graph_dir = self.repo / ".wiki-runtime/graph/postgres-99"
        manifest = graph_dir / "manifest.md"
        graph = graph_dir / "graph.json"
        report = graph_dir / "GRAPH_REPORT.md"
        self.assertTrue(manifest.is_file())
        self.assertTrue(graph.is_file())
        self.assertTrue(report.is_file())
        self.assertIn("Pinned commit", manifest.read_text(encoding="utf-8"))

        query = self._script("source_graph_query", "--version", "99", "explain", "SyntheticThing", env=env)
        self.assertIn("EXPLAIN SyntheticThing", query.stdout)

        check = self._script(
            "source_graph_check",
            "--version",
            "99",
            "--probe-node",
            "SyntheticThing",
            env=env,
        )
        self.assertIn("errors=0 warnings=0", check.stdout)

    def test_source_graph_missing_tool_writes_deferred_manifest(self) -> None:
        empty_path = self.repo / "empty-path"
        empty_path.mkdir()
        env = os.environ.copy()
        env["PATH"] = str(empty_path)

        generated = self._script("source_graph", "--version", "99", "--refresh", env=env, check=False)
        self.assertEqual(generated.returncode, 1)
        manifest = self.repo / ".wiki-runtime/graph/postgres-99/manifest.md"
        self.assertTrue(manifest.is_file())
        text = manifest.read_text(encoding="utf-8")
        self.assertIn("graphify is not installed", text)
        self.assertIn("`graph.json`", text)

    def test_graph_query_generates_missing_graph_before_querying(self) -> None:
        env = self._fake_graphify_env()
        query = self._script("source_graph_query", "--version", "99", "explain", "SyntheticThing", env=env)
        self.assertIn("EXPLAIN SyntheticThing", query.stdout)
        self.assertTrue((self.repo / ".wiki-runtime/graph/postgres-99/graph.json").is_file())

    def test_graph_query_missing_tool_reports_generation_failure(self) -> None:
        empty_path = self.repo / "empty-path"
        empty_path.mkdir()
        env = os.environ.copy()
        env["PATH"] = str(empty_path)
        proc = self._script("source_graph_query", "--version", "99", "explain", "SyntheticThing", env=env, check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("graphify is not installed", proc.stderr)
        self.assertIn("could not generate Graphify graph", proc.stderr)

    def test_source_graph_check_rejects_wrong_version_reference(self) -> None:
        graph_dir = self.repo / ".wiki-runtime/graph/postgres-99"
        graph_dir.mkdir(parents=True)
        self._write(
            ".wiki-runtime/graph/postgres-99/manifest.md",
            f"""
            # PostgreSQL 99 Graphify Source Graph

            ## Source Pin

            - PostgreSQL version: 99
            - Branch: `SYNTHETIC_STABLE`
            - Pinned commit: `{self.source_head}`
            - Source checkout: `raw/postgres-99`
            - Source checkout HEAD: `{self.source_head}`
            - Graph path: `.wiki-runtime/graph/postgres-99`
            """,
        )
        (graph_dir / "graph.json").write_text(
            json.dumps({"nodes": [{"id": "wrong", "path": "raw/postgres-98/src/wrong.c"}]}),
            encoding="utf-8",
        )
        self._write(".wiki-runtime/graph/postgres-99/GRAPH_REPORT.md", "# Synthetic Graph\n")

        proc = self._script("source_graph_check", "--version", "99", check=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("references postgres-98, expected postgres-99", proc.stdout)


if __name__ == "__main__":
    unittest.main()
