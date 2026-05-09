"""Shared helpers for PostgreSQL engine wiki maintenance scripts."""

from __future__ import annotations

import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
WIKI_ROOT = REPO_ROOT / "wiki"
RUNTIME_ROOT = (REPO_ROOT / ".wiki-runtime").resolve()
PROJECT_VENV = RUNTIME_ROOT / "venv"


def find_graphify() -> str | None:
    """Locate the graphify CLI.

    PATH first so callers can override (and tests can isolate by clearing
    PATH). Falls back to the project venv's bin/, which `bootstrap_venv`
    populates — this lets scripts invoked via `.wiki-runtime/venv/bin/python`
    find graphify even when the venv is not activated.
    """
    found = shutil.which("graphify")
    if found:
        return found
    venv_bin = PROJECT_VENV / "bin" / "graphify"
    if venv_bin.is_file() and os.access(venv_bin, os.X_OK):
        return str(venv_bin)
    return None

SECRET_KEY_RE = re.compile(r"(token|password|secret|api[_-]?key|authorization|bearer)", re.IGNORECASE)
SECRET_VALUE_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9_]{8,}|github_pat_[A-Za-z0-9_]{8,}|hf_[A-Za-z0-9_]{8,})"
)

INCLUDE_DIRECTIVE_RE = re.compile(r"^\s*#\s*include\s+[<\"]([^>\"]+)[>\"]")
COMPILER_INCLUDE_DIR_FLAGS = frozenset({"-I", "-iquote", "-isystem", "-idirafter"})


def render_repo_path(path: Path | str) -> str:
    raw = path if isinstance(path, Path) else Path(path)
    try:
        return raw.resolve().relative_to(REPO_ROOT).as_posix()
    except (OSError, ValueError):
        return str(path)


def parse_compiler_include_dirs(args: Iterable[str]) -> list[str]:
    args_list = list(args)
    include_dirs: list[str] = []
    index = 0
    while index < len(args_list):
        arg = args_list[index]
        if arg in COMPILER_INCLUDE_DIR_FLAGS and index + 1 < len(args_list):
            include_dirs.append(args_list[index + 1])
            index += 2
            continue
        if arg.startswith("-I") and len(arg) > 2:
            include_dirs.append(arg[2:])
        index += 1
    return include_dirs


def read_include_directives(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    includes: list[str] = []
    for line in text.splitlines():
        match = INCLUDE_DIRECTIVE_RE.match(line)
        if match:
            includes.append(match.group(1))
    return includes


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        path.chmod(0o700)
    except OSError:
        pass


def ensure_private_file(path: Path) -> None:
    try:
        path.chmod(0o600)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def write_private_text(path: Path, text: str) -> None:
    ensure_private_dir(path.parent)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    ensure_private_file(path)


def append_private_text(path: Path, text: str) -> None:
    ensure_private_dir(path.parent)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(text)
    ensure_private_file(path)


def redact_arg(arg: str) -> str:
    if "=" in arg:
        key, _ = arg.split("=", 1)
        if SECRET_KEY_RE.search(key):
            return f"{key}=<redacted>"
    if SECRET_VALUE_RE.search(arg):
        return SECRET_VALUE_RE.sub("<redacted>", arg)
    return arg


def redact_args(argv: Iterable[str]) -> list[str]:
    redacted: list[str] = []
    redact_next = False
    for arg in argv:
        if redact_next:
            redacted.append("<redacted>")
            redact_next = False
            continue
        redacted_arg = redact_arg(arg)
        redacted.append(redacted_arg)
        if SECRET_KEY_RE.search(arg.lstrip("-")) and "=" not in arg:
            redact_next = True
    return redacted


def ensure_runtime_dirs() -> None:
    ensure_private_dir(RUNTIME_ROOT)
    for rel in (
        "cache/wiki_lint",
        "indexes/ctags",
        "indexes/search",
        "indexes/tree-sitter",
        "logs",
        "tmp",
    ):
        ensure_private_dir(RUNTIME_ROOT / rel)


def append_tool_log(tool: str, argv: Iterable[str]) -> None:
    ensure_runtime_dirs()
    log_path = RUNTIME_ROOT / "logs" / f"{tool}.log"
    timestamp = datetime.now().isoformat(timespec="seconds")
    rendered_args = " ".join(redact_args(argv))
    append_private_text(log_path, f"{timestamp} {tool} {rendered_args}\n")


def die(message: str, code: int = 2) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def require_project_venv() -> None:
    if os.environ.get("WIKI_ALLOW_SYSTEM_PYTHON") == "1":
        return
    # sys.prefix points at the venv root; sys.executable can be a symlink
    # to a system interpreter (e.g. Homebrew on macOS), so don't resolve it.
    prefix = Path(sys.prefix)
    expected = PROJECT_VENV
    in_some_venv = sys.prefix != sys.base_prefix
    if not in_some_venv or prefix != expected:
        venv_rel = expected.relative_to(REPO_ROOT).as_posix()
        die(
            "this script must run inside the project venv "
            f"({venv_rel}). Bootstrap with `scripts/bootstrap_venv`, then re-run via "
            f"`{venv_rel}/bin/python scripts/<name>` or after `source {venv_rel}/bin/activate`. "
            "Set WIKI_ALLOW_SYSTEM_PYTHON=1 to bypass (not recommended)."
        )


require_project_venv()


def strip_ticks(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == "`" and value[-1] == "`":
        return value[1:-1]
    return value


def load_versions() -> dict[str, dict[str, str]]:
    versions_path = WIKI_ROOT / "versions.md"
    if not versions_path.exists():
        die("wiki/versions.md does not exist")

    versions: dict[str, dict[str, str]] = {}
    for line in versions_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 6 or not cells[0].isdigit():
            continue
        version, status, wiki_home, branch, commit = cells[:5]
        versions[version] = {
            "version": version,
            "status": status,
            "wiki_home": wiki_home,
            "branch": strip_ticks(branch),
            "commit": strip_ticks(commit),
            "coverage": cells[5] if len(cells) > 5 else "",
        }
    return versions


def primary_version(versions: dict[str, dict[str, str]] | None = None) -> str:
    versions = versions or load_versions()
    for version, info in versions.items():
        if info.get("status") == "primary":
            return version
    if versions:
        return sorted(versions, key=int)[-1]
    die("no supported versions found in wiki/versions.md")


def source_checkout(version: str) -> Path:
    root = REPO_ROOT / "raw" / f"postgres-{version}"
    if not root.exists():
        die(f"source checkout does not exist: {root.relative_to(REPO_ROOT)}")
    return root


def safe_source_path(version: str, rel_path: str) -> Path:
    if Path(rel_path).is_absolute():
        die("--path must be relative to the selected PostgreSQL checkout")
    root = source_checkout(version).resolve()
    full = (root / rel_path).resolve()
    try:
        full.relative_to(root)
    except ValueError:
        die("--path must stay inside the selected PostgreSQL checkout")
    return full


def wiki_markdown_files() -> list[Path]:
    if not WIKI_ROOT.exists():
        return []
    return sorted(path for path in WIKI_ROOT.rglob("*.md") if path.is_file())


def wiki_slug(path: Path) -> str:
    rel = path.relative_to(WIKI_ROOT)
    return rel.with_suffix("").as_posix()


def parse_front_matter(text: str) -> tuple[dict[str, object], str, bool]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "", False

    end = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = index
            break
    if end is None:
        return {}, "", False

    raw = "\n".join(lines[1:end])
    data: dict[str, object] = {}
    current_map_key: str | None = None

    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        top = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if top:
            key, value = top.groups()
            if value == "":
                data[key] = {}
                current_map_key = key
            else:
                data[key] = value.strip().strip("'\"")
                current_map_key = None
            continue

        nested = re.match(r"^\s+([^:]+):\s*(.*)$", line)
        if nested and current_map_key and isinstance(data.get(current_map_key), dict):
            key, value = nested.groups()
            data[current_map_key][key.strip()] = value.strip().strip("'\"")  # type: ignore[index]

    return data, raw, True


LINK_RE = re.compile(r"(?<!!)\[\[([^\]\n]+)\]\]")
_CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
_CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)


def extract_obsidian_links(text: str) -> list[str]:
    # Strip fenced code blocks and inline code spans so we don't flag
    # example citations written in documentation prose.
    text = _CODE_BLOCK_RE.sub("", text)
    text = _CODE_SPAN_RE.sub("", text)
    links: list[str] = []
    for match in LINK_RE.finditer(text):
        target = match.group(1).split("|", 1)[0].strip()
        target = target.split("#", 1)[0].strip()
        target = target.split("^", 1)[0].strip()
        if target.endswith(".md"):
            target = target[:-3]
        target = target.strip("/")
        if target:
            links.append(target)
    return links


def section_text(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = None
    heading_line = f"## {heading}"
    for index, line in enumerate(lines):
        if line.strip() == heading_line:
            start = index + 1
            break
    if start is None:
        return ""

    collected: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected).strip()
