#!/usr/bin/env python3
"""Synchronize committed cg-agent-kit rules and skills; Python 3.10+, Git required."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from contextlib import contextmanager


VERSION = 1
KIT_SOURCES = ("rules/common.md", "skills", "scripts/sync.py", "templates/project.md")
REQUIRED_SOURCES = ("rules/common.md", "scripts/sync.py", "templates/project.md")
# Control bytes that Git counts as nonprintable when deciding whether core.autocrlf may convert a file.
NONPRINTABLE = bytes(sorted(set(range(32)) - set(b"\b\t\n\x0c\r\x1b"))) + b"\x7f"
SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
# Skill directory each agent reads; kit.json "agents" picks the layouts (both when absent).
AGENT_LAYOUTS = {"claude": ".claude", "codex": ".agents"}
IGNORE_BEGIN = b"# BEGIN cg-agent-kit"
IGNORE_END = b"# END cg-agent-kit"


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


def is_text(data: bytes) -> bool:
    """Mirror Git's end-of-line text detection, which decides what core.autocrlf rewrites on checkout."""
    if b"\0" in data or data.count(b"\r") != data.count(b"\r\n"):
        return False
    special = len(data) - len(data.translate(None, NONPRINTABLE))
    printable = len(data) - special - data.count(b"\n") - data.count(b"\r")
    return printable >> 7 >= special - data.endswith(b"\x1a")


def canonical(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n") if is_text(data) else data


def digest(data: bytes) -> str:
    return hashlib.sha256(canonical(data)).hexdigest()


def checksums(data: bytes) -> set[str]:
    """Lock entries that describe this file: exact bytes, or CRLF-normalized as earlier versions recorded them."""
    return {hashlib.sha256(data).hexdigest(), hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()}


def same_checkout(actual: bytes, content: bytes) -> bool:
    """Whether a file is the generated content as Git may check it out: core.autocrlf only adds CRs to LF text."""
    return actual == content or (b"\r" not in content and is_text(content) and actual == content.replace(b"\n", b"\r\n"))


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
    agents = config.get("agents", list(AGENT_LAYOUTS))
    if (not isinstance(agents, list) or not agents or not all(isinstance(a, str) and a in AGENT_LAYOUTS for a in agents)
            or len(set(agents)) != len(agents)):
        raise SyncError("agents (kit.json or --agents) must list one or more of: " + ", ".join(AGENT_LAYOUTS))
    if not isinstance(config.get("commit_skills", True), bool):
        raise SyncError("kit.json commit_skills must be true or false")


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
        dirty = b"" if bare else git(directory, "status", "--porcelain", "--", *KIT_SOURCES)
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


def check_kit_paths(names: Iterable[str]) -> None:
    """Apply the source layout rules shared with validate.py before any source is read."""
    names = set(names)
    seen = {}
    skill_names = set()
    for name in sorted(names):
        parts = safe_relative(name).split("/")
        for length in range(1, len(parts) + 1):
            prefix = "/".join(parts[:length])
            previous = seen.setdefault(prefix.casefold(), prefix)
            if previous != prefix:
                raise SyncError(f"Case-insensitive source path collision: {previous} and {prefix}")
        if parts[0] == "skills":
            if len(parts) < 3 or len(parts[1]) > 64 or not SKILL_NAME.fullmatch(parts[1]):
                raise SyncError(f"Invalid skill layout: {name}")
            skill_names.add(parts[1])
    for required in REQUIRED_SOURCES:
        if required not in names:
            raise SyncError(f"Kit sources are missing {required}")
    for name in sorted(skill_names):
        if f"skills/{name}/SKILL.md" not in names:
            raise SyncError(f"Missing SKILL.md for {name}")


def kit_files(directory: Path, commit: str) -> dict[str, bytes]:
    blobs = {}
    for entry in git(directory, "ls-tree", "-rz", commit, "--", *KIT_SOURCES).split(b"\0"):
        if not entry:
            continue
        metadata, raw_name = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        name = raw_name.decode("utf-8")
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise SyncError(f"Kit source must contain regular files, not links: {name}")
        blobs[name] = oid
    check_kit_paths(blobs)
    # Copies stay byte-for-byte: only Git knows whether a resource's line endings matter (-text).
    return {name: git(directory, "cat-file", "blob", oid) for name, oid in blobs.items()}


def kit_script(directory: Path, commit: str) -> bytes:
    """Read the commit's synchronizer before this copy applies its own, possibly older, rules."""
    metadata = git(directory, "ls-tree", "-z", commit, "--", "scripts/sync.py").split(b"\t", 1)[0].split()
    if len(metadata) != 3 or metadata[0] not in (b"100644", b"100755") or metadata[1] != b"blob":
        raise SyncError("Kit commit is missing scripts/sync.py")
    return git(directory, "cat-file", "blob", metadata[2].decode("ascii"))


def render(files: dict[str, bytes], project: bytes, commit: str, agents: list[str]) -> dict[str, bytes]:
    try:
        common = files["rules/common.md"].decode("utf-8-sig").replace("\r\n", "\n").strip()
        local = project.decode("utf-8-sig").replace("\r\n", "\n").strip()
    except UnicodeError as exc:
        raise SyncError("Rules and project.md must be UTF-8 text") from exc
    header = ("<!-- Generated by cg-agent-kit. Edit rules/common.md in the kit or .ai/project.md here.\n"
              f"Kit commit: {commit}\nRun: python .ai/sync.py sync .\n-->\n\n")
    instructions = header + common + "\n\n---\n\n" + local + "\n"
    generated = {"AGENTS.md": instructions.encode("utf-8"), ".ai/sync.py": files["scripts/sync.py"]}
    if "claude" in agents:
        generated["CLAUDE.md"] = b"@AGENTS.md\n"
    for name, data in files.items():
        if name.startswith("skills/"):
            for agent in agents:
                generated[f"{AGENT_LAYOUTS[agent]}/{name}"] = data
    return generated


def skill_copies(generated: Iterable[str]) -> list[str]:
    return sorted(name for name in generated if name.split("/", 2)[1:2] == ["skills"])


def ignore_patterns(agents: list[str]) -> list[str]:
    # Folder contents rather than the folders: a later "!/.claude/skills/<name>/" line can still re-include one.
    return sorted(f"/{AGENT_LAYOUTS[agent]}/skills/*" for agent in agents)


def ignore_rules(existing: bytes | None, patterns: list[str]) -> bytes | None:
    """Return .gitignore with only its marked kit block set to these patterns; an empty list removes the block."""
    data = existing or b""
    lines = data.split(b"\n")
    bare = [line.rstrip(b"\r") for line in lines]
    begins = [i for i, line in enumerate(bare) if line.startswith(IGNORE_BEGIN)]
    ends = [i for i, line in enumerate(bare) if line == IGNORE_END]
    if len(begins) > 1 or len(begins) != len(ends) or (begins and begins[0] > ends[0]):
        raise SyncError(".gitignore has a malformed cg-agent-kit block; keep one BEGIN line before one END line")
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    block = b""
    if patterns:
        block = b"".join(line + newline for line in (
            IGNORE_BEGIN + b": generated skills, recreated by python .ai/sync.py sync .",
            *(pattern.encode("utf-8") for pattern in patterns), IGNORE_END))
    if begins:
        return b"\n".join(lines[:begins[0]]) + (b"\n" if begins[0] else b"") + block + b"\n".join(lines[ends[0] + 1:])
    if not patterns:
        return existing
    return data + (newline if data and not data.endswith(b"\n") else b"") + block


def hidden_entries(root: Path, agents: list[str], kit_skills: set[str], ignore: bytes) -> list[str]:
    """Entries of ignored skill folders that the kit did not generate and no later !-line re-includes."""
    after = ignore.split(b"\n" + IGNORE_END, 1)[-1]
    included = {line.strip()[1:].strip(b"/") for line in after.split(b"\n") if line.strip().startswith(b"!")}
    hidden = []
    for agent in agents:
        folder = root / AGENT_LAYOUTS[agent] / "skills"
        for entry in sorted(folder.iterdir()) if folder.is_dir() else ():
            relative = f"{AGENT_LAYOUTS[agent]}/skills/{entry.name}"
            if entry.name not in kit_skills and relative.encode("utf-8") not in included:
                hidden.append(relative)
    return hidden


def preflight(root: Path, generated: dict[str, bytes], previous: dict[str, str]) -> list[str]:
    conflicts = []
    for relative in sorted(set(generated) | set(previous)):
        path = destination(root, relative)
        if path.exists():
            if not path.is_file():
                conflicts.append(relative + " (not a file)")
                continue
            actual = checksums(path.read_bytes())
            if relative not in previous:
                conflicts.append(relative + " (unmanaged file already exists)")
            elif previous[relative] not in actual and (relative not in generated or digest(generated[relative]) not in actual):
                conflicts.append(relative + " (local edits)")
    return conflicts


def describes(lock: dict, commit: str, generated: dict[str, bytes]) -> bool:
    """Whether a lock records this commit and content, accepting checksums written by earlier versions."""
    files = lock["files"]
    return (lock["commit"] == commit and files.keys() == generated.keys()
            and all(files[name] in checksums(data) for name, data in generated.items()))


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


def delegate(script: bytes, args: argparse.Namespace) -> int:
    """Hand the whole command, a run's launch included, to the synchronizer of the kit commit being applied."""
    command = [args.action, args.target, *(["--source", args.source] if args.source else [])]
    if args.action == "init":
        command += ["--ref", args.ref, *(["--repo", args.repo] if args.repo else []), *(["--pinned"] if args.pinned else []),
                    *(["--agents", args.agents] if args.agents else []), *(["--commit-skills"] if args.commit_skills else [])]
    if args.action == "run":
        command += ["--", *args.command]
    with tempfile.TemporaryDirectory(prefix="cg-kit-") as scratch:
        path = Path(scratch) / "sync.py"
        path.write_bytes(script)
        return subprocess.call([sys.executable, str(path), *command])


def synchronize(args: argparse.Namespace, action: str) -> int | None:
    """Return the exit status of the synchronizer that took over, or None once this copy did the work."""
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
        agents = [name.strip().lower() for name in args.agents.split(",")] if args.agents else list(AGENT_LAYOUTS)
        config = {"schema_version": VERSION, "repository": repository, "ref": args.ref,
                  "update": "pinned" if args.pinned else "tracking",
                  "agents": agents, "commit_skills": args.commit_skills}
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
        script = kit_script(directory, commit)
        same_script = canonical(script) == canonical(Path(__file__).read_bytes())
        files = kit_files(directory, commit) if same_script else None
    if files is None:
        # Each kit commit renders and launches with its own synchronizer; other copies only hand over.
        print(f"Note: using the synchronizer committed in kit {commit[:12]}.", file=sys.stderr, flush=True)
        return delegate(script, args)
    project = project_path.read_bytes() if project_path.exists() else files["templates/project.md"]
    agents = config.get("agents", list(AGENT_LAYOUTS))
    generated = render(files, project, commit, agents)
    new_lock = {"schema_version": VERSION, "commit": commit,
                "files": {name: digest(data) for name, data in sorted(generated.items())}}
    # Without commit_skills the skill copies stay out of Git: a fresh clone has none until sync recreates them.
    local_skills = not config.get("commit_skills", True)
    copies = set(skill_copies(generated))
    ignore_path = root / ".gitignore"
    old_ignore = ignore_path.read_bytes() if ignore_path.is_file() else None
    new_ignore = ignore_rules(old_ignore, ignore_patterns(agents) if local_skills else [])
    if new_ignore != old_ignore and action != "check":
        ignore_path = destination(root, ".gitignore")  # refuse links before anything is written
        if ignore_path.exists() and not ignore_path.is_file():
            raise SyncError(f"Expected regular file: {ignore_path}")
    if action == "check":
        absent = local_skills and bool(copies) and not any(destination(root, relative).exists() for relative in copies)
        changes = []
        for relative, content in generated.items():
            if absent and relative in copies:
                continue
            path = destination(root, relative)
            actual = path.read_bytes() if path.is_file() else None
            if actual is None or not same_checkout(actual, content):
                note = " (line endings differ)" if actual is not None and digest(actual) == digest(content) else ""
                changes.append(relative + note)
        for relative in previous.keys() - generated.keys():
            if destination(root, relative).exists():
                changes.append(relative + " (stale)")
        if new_ignore != old_ignore:
            changes.append(".gitignore (cg-agent-kit block)")
        if not describes(old_lock, commit, generated):
            changes.append(".ai/kit.lock.json")
        if changes:
            raise SyncError("Generated files differ from the locked kit/project rules:\n  " + "\n  ".join(changes) +
                            "\nRun sync after editing .ai/project.md; edit shared sources in the kit.")
        print(f"OK: {root.name} matches kit {commit[:12]}" + (" (skills not generated yet; run sync)" if absent else ""))
        return None
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
        if not path.exists() or not same_checkout(path.read_bytes(), content):  # keep autocrlf checkouts
            write_atomic(path, content)
    for relative in previous.keys() - generated.keys():
        path = destination(root, relative)
        if path.exists():
            path.unlink()
    if new_ignore != old_ignore:  # only the marked block changes; other .gitignore lines stay byte-for-byte
        write_atomic(ignore_path, new_ignore)
    if initialize:
        if not project_path.exists():
            write_atomic(project_path, canonical(project))
        write_atomic(destination(root, ".ai/kit.json"), json_bytes(config))
    if new_lock != old_lock:  # an unchanged lock keeps its checkout line endings, so Git sees no edit
        write_atomic(destination(root, ".ai/kit.lock.json"), json_bytes(new_lock))
    print(f"{action.capitalize()}: {root.name} uses kit {commit[:12]} ({len(generated)} generated files"
          + ("; skills are ignored by Git)" if local_skills else ")"), flush=True)
    if local_skills:
        kit_skills = {name.split("/")[1] for name in files if name.startswith("skills/")}
        for relative in hidden_entries(root, agents, kit_skills, new_ignore or b""):
            print(f"Note: {relative} is not a kit skill, and the cg-agent-kit block in .gitignore hides it from Git. "
                  f"Re-include it with a later line !/{relative}/ or set commit_skills to true.", file=sys.stderr)
    return None


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
            child.add_argument("--agents", help="Comma-separated agents to generate for: claude, codex (default: both)")
            child.add_argument("--commit-skills", action="store_true",
                               help="Keep generated skills in Git instead of listing them in .gitignore")
    args = parser.parse_args(argv)
    if args.action == "run" and not command:
        parser.error("run requires -- COMMAND [ARG ...]")
    if args.action != "run" and command:
        parser.error("Only run accepts a command after --")
    args.command = command
    return args


def batch_argument(value: str, force: bool = False) -> str:
    """Quote one argument for cmd.exe running a .cmd/.bat file, so that it arrives literally (BatBadBut)."""
    if any(c in value for c in "\0\r\n"):
        raise SyncError(f"Batch files cannot receive line breaks or NUL: {value!r}")
    if not force and re.fullmatch(r"[\w#$*+\-./:?@\\]*[\w#$*+\-./:?@]", value, re.ASCII):
        return value  # nothing that cmd.exe interprets, and no backslash before a closing quote
    # Quotes keep &|<>^() literal for cmd.exe; "" and doubled backslashes also suit the C runtime.
    # %cd:~,% expands to nothing, so cmd.exe's single expansion pass leaves %NAME% as typed.
    value = re.sub(r'(\\*)"', r'\1\1""', value)
    return '"' + re.sub(r"(\\+)\Z", r"\1\1", value).replace("%", "%%cd:~,%") + '"'


def launch(command: list[str], cwd: Path) -> int:
    if os.name != "nt":
        return subprocess.call(command, cwd=cwd)
    # CreateProcess ignores PATHEXT, so npm shims such as codex.cmd need an explicit lookup.
    executable = shutil.which(command[0]) or command[0]
    if not executable.lower().endswith((".bat", ".cmd")):
        return subprocess.call([executable, *command[1:]], cwd=cwd)
    line = " ".join([batch_argument(executable, force=True), *map(batch_argument, command[1:])])
    shell = os.environ.get("COMSPEC") or os.path.join(os.environ.get("SYSTEMROOT", r"C:\Windows"), "System32", "cmd.exe")
    return subprocess.call(f'cmd.exe /d /e:on /v:off /s /c "{line}"', executable=shell, cwd=cwd)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        status = synchronize(args, args.action)
        if status is not None:  # the kit commit's own synchronizer already ran everything, launch included
            return status
        return launch(args.command, Path(args.target).absolute()) if args.action == "run" else 0
    except (SyncError, OSError, UnicodeError, ValueError) as exc:
        print(f"cg-agent-kit: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
