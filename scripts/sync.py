#!/usr/bin/env python3
"""Synchronize committed cg-agent-kit rules and skills; Python 3.10+, Git required."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager


VERSION = 1
TEXT_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".json", ".txt", ".sh", ".ps1",
                 ".toml", ".ini", ".cfg", ".csv", ".tsv", ".html", ".css", ".js", ".ts"}
SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class SyncError(Exception):
    pass


def git(directory: Path, *args: str) -> bytes:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never")
    try:
        result = subprocess.run(["git", "-C", str(directory), *args], capture_output=True,
                                env=env, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SyncError(f"Could not run Git: {exc}") from exc
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise SyncError(f"Git failed: {detail}")
    return result.stdout


def safe_relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or "\0" in value:
        raise SyncError(f"Unsafe relative path: {value!r}")
    if value.startswith("/") or any(p in ("", ".", "..") for p in value.split("/")):
        raise SyncError(f"Unsafe relative path: {value!r}")
    # These are ambiguous or illegal on Windows, even when generated on Linux.
    for part in value.split("/"):
        if part.casefold() == ".git":
            raise SyncError(f"Git metadata is not a kit asset: {value!r}")
        if part.endswith((".", " ")) or any(c in part for c in '<>"|?*') or any(ord(c) < 32 for c in part):
            raise SyncError(f"Nonportable path: {value!r}")
        if re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part, re.I):
            raise SyncError(f"Nonportable path: {value!r}")
    return value


def assert_plain_path(path: Path) -> None:
    """Reject links/junctions in every existing path component before accessing it."""
    for item in (*reversed(path.parents), path):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise SyncError(f"Refusing symlink or junction: {item}")


def destination(root: Path, relative: str) -> Path:
    path = root.joinpath(*safe_relative(relative).split("/"))
    assert_plain_path(path)
    for parent in path.parents:
        if parent == root.parent:
            break
        if parent.exists() and not parent.is_dir():
            raise SyncError(f"Expected directory: {parent}")
    return path


def canonical(relative: str, data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n") if PurePosixPath(relative).suffix.lower() in TEXT_SUFFIXES else data


def digest(relative: str, data: bytes) -> str:
    return hashlib.sha256(canonical(relative, data)).hexdigest()


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def read_json(root: Path, relative: str) -> dict:
    path = destination(root, relative)
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise SyncError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != VERSION:
        raise SyncError(f"Unsupported or invalid schema in {path}")
    return value


def managed_path(relative: str) -> bool:
    safe_relative(relative)
    if relative in {"AGENTS.md", "CLAUDE.md", ".ai/sync.py"}:
        return True
    parts = relative.split("/")
    return (len(parts) >= 4 and parts[0] in {".agents", ".claude"} and parts[1] == "skills"
            and len(parts[2]) <= 64 and bool(SKILL_NAME.fullmatch(parts[2])))


def validate_config(config: dict) -> None:
    repository = config.get("repository")
    if (not isinstance(repository, str) or not repository or repository.startswith("-")
            or "::" in repository or any(c in repository for c in "\r\n\0")):
        raise SyncError("kit.json needs a repository URL or local Git repository path")
    ref = config.get("ref")
    if not isinstance(ref, str) or not ref or ref.startswith("-") or any(c in ref for c in "\r\n\0"):
        raise SyncError("kit.json needs a nonempty Git ref")
    if config.get("update") not in ("tracking", "pinned"):
        raise SyncError("kit.json update must be 'tracking' or 'pinned'")


def validate_lock(lock: dict) -> None:
    if not isinstance(lock.get("commit"), str) or not COMMIT.fullmatch(lock["commit"]):
        raise SyncError("kit.lock.json needs a full Git commit hash")
    if not isinstance(lock.get("files"), dict):
        raise SyncError("kit.lock.json needs a file manifest")
    for relative, checksum in lock["files"].items():
        if not managed_path(relative) or not isinstance(checksum, str) or not SHA256.fullmatch(checksum):
            raise SyncError(f"Invalid managed file in lock: {relative!r}")


def local_location(value: str) -> bool:
    """Distinguish filesystem paths from URL and SCP-style Git remotes."""
    if re.match(r"^[A-Za-z]:[\\/]", value):
        return True
    return "://" not in value and ":" not in re.split(r"[/\\]", value, maxsplit=1)[0]


@contextmanager
def snapshot(repository: str, ref: str, source: str | None):
    local = source or (repository if local_location(repository) and Path(repository).is_dir() else None)
    if local:
        directory = Path(local).absolute()
        if not directory.is_dir():
            raise SyncError(f"Source repository does not exist: {directory}")
        bare = git(directory, "rev-parse", "--is-bare-repository").strip() == b"true"
        if not bare:
            top = git(directory, "rev-parse", "--show-toplevel").decode().strip()
            if Path(top).resolve() != directory.resolve():
                raise SyncError(f"Local source must be the kit repository root: {top}")
        commit = git(directory, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode().strip()
        dirty = b"" if bare else git(directory, "status", "--porcelain", "--", "rules", "skills", "scripts/sync.py", "templates/project.md")
        if dirty:
            print("Note: uncommitted kit edits are ignored; using the committed snapshot.", file=sys.stderr)
        yield directory, commit
    else:
        with tempfile.TemporaryDirectory(prefix="cg-kit-") as scratch:
            directory = Path(scratch)
            git(directory, "init", "--bare", "--quiet")
            git(directory, "fetch", "--quiet", "--depth=1", "--no-tags", "--", repository, ref)
            commit = git(directory, "rev-parse", "FETCH_HEAD^{commit}").decode().strip()
            yield directory, commit


def kit_files(directory: Path, commit: str) -> dict[str, bytes]:
    result = {}
    entries = git(directory, "ls-tree", "-rz", commit, "--", "rules/common.md", "skills", "scripts/sync.py", "templates/project.md")
    seen = {}
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        metadata, raw_name = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        name = safe_relative(raw_name.decode("utf-8"))
        parts = name.split("/")
        for length in range(1, len(parts) + 1):
            prefix = "/".join(parts[:length])
            previous = seen.setdefault(prefix.casefold(), prefix)
            if previous != prefix:
                raise SyncError(f"Case-insensitive source path collision: {previous} and {prefix}")
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise SyncError(f"Kit source must contain regular files, not links: {name}")
        result[name] = canonical(name, git(directory, "cat-file", "blob", oid))
    for required in ("rules/common.md", "scripts/sync.py", "templates/project.md"):
        if required not in result:
            raise SyncError(f"Kit commit is missing {required}")
    skill_names = set()
    for name in result:
        if name.startswith("skills/"):
            parts = name.split("/")
            if len(parts) < 3 or len(parts[1]) > 64 or not SKILL_NAME.fullmatch(parts[1]):
                raise SyncError(f"Invalid skill layout: {name}")
            skill_names.add(parts[1])
    for name in skill_names:
        if f"skills/{name}/SKILL.md" not in result:
            raise SyncError(f"Missing SKILL.md for {name}")
    return result


def render(files: dict[str, bytes], project: bytes, commit: str) -> dict[str, bytes]:
    try:
        common = files["rules/common.md"].decode("utf-8-sig").strip()
        local = project.decode("utf-8-sig").replace("\r\n", "\n").strip()
    except UnicodeError as exc:
        raise SyncError("Rules and project.md must be UTF-8 text") from exc
    header = ("<!-- Generated by cg-agent-kit. Edit rules/common.md in the kit or .ai/project.md here.\n"
              f"Kit commit: {commit}\nRun: python .ai/sync.py sync .\n-->\n\n")
    agents = header + common + "\n\n---\n\n" + local + "\n"
    generated = {"AGENTS.md": agents.encode("utf-8"), "CLAUDE.md": b"@AGENTS.md\n",
                 ".ai/sync.py": files["scripts/sync.py"]}
    for name, data in files.items():
        if name.startswith("skills/"):
            for agent in (".agents", ".claude"):
                generated[f"{agent}/{name}"] = data
    return generated


def preflight(root: Path, generated: dict[str, bytes], previous: dict[str, str]) -> list[str]:
    conflicts = []
    for relative in sorted(set(generated) | set(previous)):
        path = destination(root, relative)
        if path.exists():
            if not path.is_file():
                conflicts.append(relative + " (not a file)")
                continue
            actual = digest(relative, path.read_bytes())
            if relative not in previous:
                conflicts.append(relative + " (unmanaged file already exists)")
            elif actual != previous[relative] and (relative not in generated or actual != digest(relative, generated[relative])):
                conflicts.append(relative + " (local edits)")
    return conflicts


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".cg-kit-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def synchronize(args: argparse.Namespace, action: str) -> None:
    root = Path(args.target).absolute()
    assert_plain_path(root)
    if root.exists() and not root.is_dir():
        raise SyncError(f"Target is not a directory: {root}")
    initialize = action == "init"
    if initialize:
        for name in (".ai/kit.json", ".ai/kit.lock.json"):
            if destination(root, name).exists():
                raise SyncError(f"Already initialized: {root}; use sync or update")
        source = args.source
        repository = args.repo
        if not repository:
            if not source:
                raise SyncError("init requires --source PATH or --repo URL")
            try:
                repository = git(Path(source).absolute(), "remote", "get-url", "origin").decode().strip()
            except SyncError:
                repository = str(Path(source).absolute())
        if local_location(repository):
            base = Path(source).absolute() if source and not args.repo else Path.cwd()
            repository = os.path.abspath(base / repository)
        config = {"schema_version": VERSION, "repository": repository, "ref": args.ref,
                  "update": "pinned" if args.pinned else "tracking"}
        previous = {}
        old_lock = None
    else:
        config = read_json(root, ".ai/kit.json")
        old_lock = read_json(root, ".ai/kit.lock.json")
        validate_lock(old_lock)
        previous = old_lock["files"]
    validate_config(config)
    if action == "run":
        action = "update" if config["update"] == "tracking" else "sync"
    ref = config["ref"] if action in {"init", "update"} else old_lock["commit"]
    project_path = destination(root, ".ai/project.md")
    if project_path.exists() and not project_path.is_file():
        raise SyncError(f"Project rules are not a regular file: {project_path}")
    if not initialize and not project_path.exists():
        raise SyncError(f"Missing project rules: {project_path}")
    with snapshot(config["repository"], ref, args.source) as (directory, commit):
        files = kit_files(directory, commit)
    project = project_path.read_bytes() if project_path.exists() else files["templates/project.md"]
    generated = render(files, project, commit)
    new_lock = {"schema_version": VERSION, "commit": commit,
                "files": {name: digest(name, data) for name, data in sorted(generated.items())}}
    if action == "check":
        changes = []
        for relative, content in generated.items():
            path = destination(root, relative)
            if not path.is_file() or digest(relative, path.read_bytes()) != digest(relative, content):
                changes.append(relative)
        for relative in previous.keys() - generated.keys():
            if destination(root, relative).exists():
                changes.append(relative + " (stale)")
        if old_lock != new_lock:
            changes.append(".ai/kit.lock.json")
        if changes:
            raise SyncError("Generated files differ from the locked kit/project rules:\n  " + "\n  ".join(changes) +
                            "\nRun sync after editing .ai/project.md; edit shared sources in the kit.")
        print(f"OK: {root.name} matches kit {commit[:12]}")
        return
    conflicts = preflight(root, generated, previous)
    if conflicts:
        raise SyncError("No files changed. Resolve generated-file conflicts first:\n  " + "\n  ".join(conflicts) +
                        "\nMove existing project rules into .ai/project.md and preserve skill edits in their source kit.")
    # All paths, including metadata, are checked before the first write.
    for relative in (".ai/kit.json", ".ai/kit.lock.json", ".ai/project.md"):
        path = destination(root, relative)
        if path.exists() and not path.is_file():
            raise SyncError(f"Expected regular file: {path}")
    for relative, content in generated.items():
        path = destination(root, relative)
        if not path.exists() or path.read_bytes() != content:
            write_atomic(path, content)
    for relative in previous.keys() - generated.keys():
        path = destination(root, relative)
        if path.exists():
            path.unlink()
    if initialize:
        if not project_path.exists():
            write_atomic(project_path, canonical(".ai/project.md", project))
        write_atomic(destination(root, ".ai/kit.json"), json_bytes(config))
    write_atomic(destination(root, ".ai/kit.lock.json"), json_bytes(new_lock))
    print(f"{action.capitalize()}: {root.name} uses kit {commit[:12]} ({len(generated)} generated files)", flush=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    if "--" in argv:
        separator = argv.index("--")
        command = argv[separator + 1:]
        argv = argv[:separator]
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for action in ("init", "sync", "update", "check", "run"):
        child = commands.add_parser(action)
        child.add_argument("target", help="Contest repository directory")
        child.add_argument("--source", help="Use commits from this local kit Git repository (offline)")
        if action == "init":
            child.add_argument("--repo", help="Repository URL saved for future updates")
            child.add_argument("--ref", default="master", help="Branch/tag to track (default: master)")
            child.add_argument("--pinned", action="store_true", help="Do not auto-update on run")
    args = parser.parse_args(argv)
    if args.action == "run" and not command:
        parser.error("run requires -- COMMAND [ARG ...]")
    if args.action != "run" and command:
        parser.error("Only run accepts a command after --")
    args.command = command
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        synchronize(args, args.action)
        if args.action == "run":
            return subprocess.call(args.command, cwd=Path(args.target).absolute())
        return 0
    except (SyncError, OSError, UnicodeError, ValueError) as exc:
        print(f"cg-agent-kit: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
