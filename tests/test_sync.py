"""CLI integration tests using disposable, local Git repositories."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync.py"
VALIDATE = SCRIPT.with_name("validate.py")


class LocalLocationTests(unittest.TestCase):
    def test_filesystem_paths_are_distinguished_from_git_remotes(self):
        spec = importlib.util.spec_from_file_location("cg_sync_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for value in ("https://example.invalid/kit.git", "ssh://git@example.invalid/kit.git",
                      "git@example.invalid:owner/kit.git", "example.invalid:owner/kit.git", "file:///tmp/kit.git"):
            with self.subTest(value=value):
                self.assertFalse(module.local_location(value))
        for value in (r"C:\repos\kit", "C:/repos/kit", "/tmp/kit", "../kit", "./kit", "kit.git"):
            with self.subTest(value=value):
                self.assertTrue(module.local_location(value))


@unittest.skipUnless(shutil.which("git"), "Git is required")
class SyncIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="cg-kit-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.kit = self.root / "kit"
        self.kit.mkdir()
        self.target = self.root / "contest"
        self.git("init", "--quiet", "-b", "master")
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.put(self.kit, "scripts/sync.py", SCRIPT.read_bytes())
        self.put(self.kit, "rules/common.md", "# Shared rules\nUse deterministic seeds.\n")
        self.put(self.kit, "templates/project.md", "# Contest rules\nProject settings go here.\n")
        self.put(self.kit, "skills/compare-bots/SKILL.md",
                 "---\nname: compare-bots\ndescription: Compare bots on matched seeds.\n---\n# Compare bots\n")
        self.put(self.kit, "skills/compare-bots/references/seeds.txt", "1\n2\n")
        self.initial_commit = self.commit("Initial kit")

    @staticmethod
    def put(root, relative, content):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        return path

    def git(self, *arguments, input=None):
        result = subprocess.run(["git", "-C", str(self.kit), *arguments],
                                input=input, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        return result.stdout.decode().strip()

    def commit(self, message):
        self.git("add", "--all")
        self.git("commit", "--quiet", "-m", message)
        return self.git("rev-parse", "HEAD")

    def bare_repository(self):
        bare = self.root / "remote.git"
        shutil.copytree(self.kit / ".git", bare)
        result = subprocess.run(["git", "-C", str(bare), "config", "core.bare", "true"],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return bare

    def cli(self, action, *arguments, source=True, expected=0, script=SCRIPT, target=None, env=None):
        command = [sys.executable, str(script), action, str(target or self.target)]
        if source:
            command += ["--source", str(self.kit)]
        command += list(arguments)
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=30, env=env)
        self.assertEqual(result.returncode, expected,
                         f"Command: {command}\nstdout: {result.stdout}\nstderr: {result.stderr}")
        return result

    def lock(self):
        return json.loads((self.target / ".ai/kit.lock.json").read_text(encoding="utf-8"))

    def config(self):
        return json.loads((self.target / ".ai/kit.json").read_text(encoding="utf-8"))

    def target_git(self, *arguments):
        result = subprocess.run(["git", "-C", str(self.target), *arguments], capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        return result.stdout.decode()

    def files(self):
        if not self.target.exists():
            return {}
        return {str(p.relative_to(self.target)): p.read_bytes()
                for p in self.target.rglob("*") if p.is_file()}

    def test_init_and_sync_are_deterministic(self):
        self.cli("init")
        self.assertEqual(self.lock()["commit"], self.initial_commit)
        self.assertEqual((self.target / "CLAUDE.md").read_bytes(), b"@AGENTS.md\n")
        agents = (self.target / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Use deterministic seeds.", agents)
        self.assertIn("Project settings go here.", agents)
        for name in (".agents", ".claude"):
            self.assertEqual((self.target / name / "skills/compare-bots/SKILL.md").read_bytes(),
                             (self.kit / "skills/compare-bots/SKILL.md").read_bytes())
        before = self.files()
        self.cli("sync")
        self.cli("check")
        self.assertEqual(self.files(), before)

    def test_check_and_sync_use_lock_after_tracking_branch_advances(self):
        self.cli("init")
        before = self.files()
        self.put(self.kit, "rules/common.md", "# Shared rules\nNew rule.\n")
        self.commit("Advance shared rules")
        self.cli("check")
        self.cli("sync")
        self.assertEqual(self.files(), before)

    def test_project_edits_require_regeneration(self):
        self.cli("init")
        self.put(self.target, ".ai/project.md", "# Contest rules\nCompile with gcc.\n")
        before = self.files()
        self.cli("check", expected=1)
        self.assertEqual(self.files(), before)
        self.cli("sync")
        self.cli("check")
        self.assertIn("Compile with gcc.", (self.target / "AGENTS.md").read_text(encoding="utf-8"))

    def test_existing_project_source_is_preserved_on_init(self):
        project = self.put(self.target, ".ai/project.md", "# Existing contest\nCustom command.\n")
        self.cli("init")
        self.assertEqual(project.read_bytes(), b"# Existing contest\nCustom command.\n")
        self.assertIn("Custom command.", (self.target / "AGENTS.md").read_text(encoding="utf-8"))

    def test_update_removes_only_managed_stale_files(self):
        self.cli("init")
        for agent in (".agents", ".claude"):
            self.put(self.target, f"{agent}/skills/compare-bots/local.txt", "User note\n")
            self.put(self.target, f"{agent}/skills/project-skill/SKILL.md", "Project skill\n")
        (self.kit / "skills/compare-bots/references/seeds.txt").unlink()
        self.put(self.kit, "skills/compare-bots/SKILL.md", "---\nname: compare-bots\ndescription: Compare bots.\n---\nUpdated\n")
        latest = self.commit("Update skill")
        self.cli("update")
        self.assertEqual(self.lock()["commit"], latest)
        for agent in (".agents", ".claude"):
            self.assertFalse((self.target / f"{agent}/skills/compare-bots/references/seeds.txt").exists())
            self.assertEqual((self.target / f"{agent}/skills/compare-bots/local.txt").read_bytes(), b"User note\n")
            self.assertEqual((self.target / f"{agent}/skills/project-skill/SKILL.md").read_bytes(), b"Project skill\n")
            self.assertIn(b"Updated", (self.target / f"{agent}/skills/compare-bots/SKILL.md").read_bytes())
        self.cli("check")

    def test_init_collision_does_not_write_partial_files(self):
        self.put(self.target, "AGENTS.md", "User instructions\n")
        self.put(self.target, "bot.cpp", "int main() {}\n")
        before = self.files()
        result = self.cli("init", expected=1)
        self.assertIn("No files changed", result.stderr)
        self.assertEqual(self.files(), before)

    def test_update_local_edit_conflict_does_not_write_partial_files(self):
        self.cli("init")
        self.put(self.target, ".claude/skills/compare-bots/SKILL.md", "Local changes\n")
        self.put(self.kit, "rules/common.md", "# Updated shared rule\n")
        self.commit("New shared rule")
        before = self.files()
        result = self.cli("update", expected=1)
        self.assertIn("local edits", result.stderr)
        self.assertEqual(self.files(), before)

    def test_new_skill_collision_preserves_unmanaged_skill(self):
        self.cli("init")
        self.put(self.target, ".agents/skills/profile-bot/SKILL.md", "Local project skill\n")
        self.put(self.kit, "skills/profile-bot/SKILL.md", "---\nname: profile-bot\ndescription: Profile a bot.\n---\n")
        self.commit("Add shared skill")
        before = self.files()
        self.cli("update", expected=1)
        self.assertEqual(self.files(), before)

    def test_removed_source_does_not_delete_edited_generated_file(self):
        self.cli("init")
        self.put(self.target, ".agents/skills/compare-bots/references/seeds.txt", "User seed list\n")
        (self.kit / "skills/compare-bots/references/seeds.txt").unlink()
        self.commit("Remove bundled seeds")
        before = self.files()
        self.cli("update", expected=1)
        self.assertEqual(self.files(), before)

    def test_binary_skill_assets_are_preserved(self):
        payload = b"\x00\xff\r\n\x01\x80\r\n"
        self.put(self.kit, "skills/compare-bots/assets/sample.bin", payload)
        self.commit("Add binary fixture")
        self.cli("init")
        for agent in (".agents", ".claude"):
            self.assertEqual((self.target / f"{agent}/skills/compare-bots/assets/sample.bin").read_bytes(), payload)
        self.cli("check")

    def test_copied_script_works_without_source_option(self):
        self.cli("init")
        copied = self.target / ".ai/sync.py"
        config = json.loads((self.target / ".ai/kit.json").read_text(encoding="utf-8"))
        self.assertEqual(config["repository"], str(self.kit))
        self.cli("check", source=False, script=copied)
        self.put(self.kit, "rules/common.md", "# Updated via configured repository\n")
        latest = self.commit("Advance repository")
        self.cli("update", source=False, script=copied)
        self.assertEqual(self.lock()["commit"], latest)

    def test_relative_origin_is_saved_as_absolute_local_repository(self):
        bare = self.bare_repository()
        self.git("remote", "add", "origin", "../remote.git")
        self.cli("init")
        config = json.loads((self.target / ".ai/kit.json").read_text(encoding="utf-8"))
        self.assertTrue(Path(config["repository"]).is_absolute())
        self.assertEqual(Path(config["repository"]).resolve(), bare.resolve())
        self.cli("check", source=False, script=self.target / ".ai/sync.py")

    def test_local_bare_repository_supports_repo_and_source_options(self):
        bare = self.bare_repository()
        self.cli("init", "--repo", str(bare), source=False)
        self.assertEqual(self.lock()["commit"], self.initial_commit)
        self.cli("check", source=False)
        second_target = self.root / "second-contest"
        self.cli("init", "--source", str(bare), source=False, target=second_target)
        self.cli("check", "--source", str(bare), source=False, target=second_target)

    def test_uncommitted_source_is_not_published(self):
        self.put(self.kit, "rules/common.md", "# Uncommitted rule\n")
        result = self.cli("init")
        self.assertIn("uncommitted kit edits are ignored", result.stderr)
        self.assertNotIn("Uncommitted", (self.target / "AGENTS.md").read_text(encoding="utf-8"))

    def test_run_updates_tracking_and_uses_target_working_directory(self):
        self.cli("init")
        self.put(self.kit, "rules/common.md", "# Latest rule\n")
        latest = self.commit("Latest rule")
        result = self.cli("run", "--", sys.executable, "-c", "import os; print('CWD=' + os.getcwd())")
        self.assertIn("CWD=" + str(self.target), result.stdout)
        self.assertEqual(self.lock()["commit"], latest)

    def test_pinned_run_stays_locked_but_explicit_update_advances(self):
        self.cli("init", "--pinned")
        self.put(self.kit, "rules/common.md", "# Latest rule\n")
        latest = self.commit("Latest rule")
        self.cli("run", "--", sys.executable, "-c", "pass")
        self.assertEqual(self.lock()["commit"], self.initial_commit)
        self.cli("update")
        self.assertEqual(self.lock()["commit"], latest)

    def test_run_returns_command_exit_status(self):
        self.cli("init")
        self.cli("run", "--", sys.executable, "-c", "raise SystemExit(7)", expected=7)

    @unittest.skipUnless(os.name == "nt", "PATHEXT lookup is specific to Windows")
    def test_run_finds_windows_command_shims(self):
        # npm installs codex and claude as .cmd shims, which CreateProcess does not find by name.
        self.cli("init")
        shims = self.root / "bin"
        self.put(shims, "fake-agent.cmd", "@echo off\r\necho AGENT %*\r\nexit /b 3\r\n")
        env = dict(os.environ, PATH=f"{shims}{os.pathsep}{os.environ.get('PATH', '')}")
        result = self.cli("run", "--", "fake-agent", "hello", expected=3, env=env)
        self.assertIn("AGENT hello", result.stdout)

    @unittest.skipUnless(os.name == "nt", "cmd.exe quoting is specific to Windows")
    def test_run_passes_metacharacters_to_command_shims_literally(self):
        self.cli("init")
        shims = self.root / "bin"
        # Forwards %* the way npm shims such as codex.cmd do; Python then reports what arrived.
        self.put(shims, "forward.cmd", f'@"{sys.executable}" -c "import json, sys; print(json.dumps(sys.argv[1:]))" %*\r\n')
        env = dict(os.environ, PATH=f"{shims}{os.pathsep}{os.environ.get('PATH', '')}")
        arguments = ["report&ver", "a|b", "x>y", "(group)", "a^b", "100%", "%PATH%", "!PATH!",
                     'say "hi"', 'a"&ver', "C:\\dir\\", "two words", ""]
        result = self.cli("run", "--", "forward", *arguments, env=env)
        self.assertEqual(json.loads(result.stdout.splitlines()[-1]), arguments)
        self.assertIn("line breaks", self.cli("run", "--", "forward", "two\nlines", expected=1, env=env).stderr)

    def test_run_launches_with_the_new_synchronizer(self):
        self.cli("init")
        script = self.kit / "scripts/sync.py"
        script.write_bytes(script.read_bytes().replace(
            b"def launch(command: list[str], cwd: Path) -> int:\n",
            b"def launch(command: list[str], cwd: Path) -> int:\n    print('new launch', flush=True)\n"))
        self.assertIn(b"new launch", script.read_bytes())
        self.commit("Change the launcher")
        result = self.cli("run", "--", sys.executable, "-c", "print('agent')", script=self.target / ".ai/sync.py")
        self.assertEqual(result.stdout.splitlines()[-2:], ["new launch", "agent"])

    def test_update_renders_with_the_synchronizer_from_the_new_commit(self):
        self.cli("init")
        script = self.kit / "scripts/sync.py"
        script.write_bytes(script.read_bytes().replace(b"<!-- Generated by cg-agent-kit.",
                                                       b"<!-- Generated by cg-agent-kit (next)."))
        latest = self.commit("Change the generated header")
        copied = self.target / ".ai/sync.py"
        result = self.cli("run", "--", sys.executable, "-c", "print('launched')", script=copied)
        self.assertIn("launched", result.stdout)
        self.assertEqual(self.lock()["commit"], latest)
        self.assertIn("Generated by cg-agent-kit (next).", (self.target / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertEqual(copied.read_bytes(), script.read_bytes())
        self.cli("check", script=copied)

    def test_run_does_not_launch_when_the_new_synchronizer_fails(self):
        self.cli("init")
        self.put(self.kit, "scripts/sync.py", "raise SystemExit(5)\n")
        self.commit("Break the synchronizer")
        self.cli("run", "--", sys.executable, "-c",
                 "from pathlib import Path; Path('launched.txt').write_text('yes')",
                 expected=5, script=self.target / ".ai/sync.py")
        self.assertFalse((self.target / "launched.txt").exists())

    def test_autocrlf_checkouts_are_neither_conflicts_nor_rewritten(self):
        self.put(self.kit, "skills/compare-bots/assets/example.cpp", "int main() {\n    return 0;\n}\n")
        self.commit("Add C++ example")
        self.cli("init")
        for path in self.target.rglob("*"):
            if path.is_file():  # what core.autocrlf=true produces for text, whatever the suffix
                path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        before = self.files()
        self.cli("check")
        self.cli("sync")
        self.assertEqual(self.files(), before)

    def test_crlf_resources_are_copied_byte_for_byte_and_restored(self):
        # Like a kit file marked -text whose CRLF bytes matter, such as a PDF with xref offsets.
        pdf = b"%PDF-1.4\r\n1 0 obj << /Type /Catalog >> endobj\r\ntrailer << /Root 1 0 R >>\r\n%%EOF\r\n"
        self.put(self.kit, "skills/compare-bots/assets/rules.pdf", pdf)
        self.commit("Add CRLF resource")
        self.cli("init")
        copies = [self.target / agent / "skills/compare-bots/assets/rules.pdf" for agent in (".agents", ".claude")]
        self.assertEqual([path.read_bytes() for path in copies], [pdf, pdf])
        for path in copies:  # what cc0d996 or a normalizing Git configuration leaves behind
            path.write_bytes(pdf.replace(b"\r\n", b"\n"))
        self.assertIn("line endings differ", self.cli("check", expected=1).stderr)
        self.cli("sync")
        self.assertEqual([path.read_bytes() for path in copies], [pdf, pdf])
        self.cli("check")

    def test_locks_from_earlier_checksum_rules_are_accepted(self):
        source = self.put(self.kit, "skills/compare-bots/assets/example.cpp", b"int main() {\r\n    return 0;\r\n}\r\n")
        self.commit("Add CRLF C++ example")
        self.cli("init")
        lock = self.lock()
        for agent in (".agents", ".claude"):  # 7332a72 hashed unlisted suffixes without normalizing CRLF
            lock["files"][f"{agent}/skills/compare-bots/assets/example.cpp"] = hashlib.sha256(source.read_bytes()).hexdigest()
        self.put(self.target, ".ai/kit.lock.json", json.dumps(lock))
        self.cli("check")
        source.write_bytes(b"int main() {\r\n    return 1;\r\n}\r\n")
        self.commit("Change the C++ example")
        self.cli("update")
        self.assertIn(b"return 1;", (self.target / ".claude/skills/compare-bots/assets/example.cpp").read_bytes())
        self.cli("check")

    def test_validate_reports_layouts_that_sync_rejects(self):
        validate = self.put(self.kit, "scripts/validate.py", VALIDATE.read_bytes())
        result = subprocess.run([sys.executable, str(validate)], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.put(self.kit, "skills/README.md", "# Skills index\n")  # not inside a skill directory
        result = subprocess.run([sys.executable, str(validate)], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("Invalid skill layout: skills/README.md", result.stderr)
        self.commit("Add skills index")
        self.assertIn("Invalid skill layout", self.cli("init", expected=1).stderr)

    def test_run_does_not_launch_command_when_sync_fails(self):
        self.cli("init")
        self.put(self.target, "AGENTS.md", "Manually changed\n")
        self.cli("run", "--", sys.executable, "-c",
                 "from pathlib import Path; Path('launched.txt').write_text('yes')", expected=1)
        self.assertFalse((self.target / "launched.txt").exists())

    def test_unsafe_lock_path_is_rejected_without_writes(self):
        self.cli("init")
        outside = self.put(self.root, "outside.txt", "Preserve me\n")
        lock = self.lock()
        lock["files"]["../outside.txt"] = hashlib.sha256(outside.read_bytes()).hexdigest()
        self.put(self.target, ".ai/kit.lock.json", json.dumps(lock))
        before = self.files()
        self.cli("sync", expected=1)
        self.assertEqual(self.files(), before)
        self.assertEqual(outside.read_bytes(), b"Preserve me\n")

    def test_git_symlink_source_is_rejected_without_filesystem_symlink_privilege(self):
        # Git's object model can represent a symlink even on Windows without
        # Developer Mode; this checks committed source entries directly.
        blob = self.git("hash-object", "-w", "--stdin", input=b"../../outside.txt")
        self.git("update-index", "--add", "--cacheinfo", "120000", blob, "skills/compare-bots/link.txt")
        self.git("commit", "--quiet", "-m", "Add unsafe link")
        result = self.cli("init", expected=1)
        self.assertIn("regular files, not links", result.stderr)
        self.assertFalse(self.target.exists())

    def test_case_colliding_source_directories_are_rejected_before_writes(self):
        blob = self.git("hash-object", "-w", "--stdin", input=b"Example reference\n")
        for relative in ("skills/compare-bots/Refs/a.txt", "skills/compare-bots/refs/b.txt"):
            self.git("update-index", "--add", "--cacheinfo", "100644", blob, relative)
        self.git("commit", "--quiet", "-m", "Add case-colliding directories")
        result = self.cli("init", expected=1)
        self.assertIn("collision", result.stderr.lower())
        self.assertFalse(self.target.exists())

    def test_target_directory_symlink_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.target.mkdir()
        try:
            (self.target / ".agents").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Creating symlinks is unavailable: {exc}")
        self.cli("init", expected=1)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.target / "AGENTS.md").exists())

    def test_new_contests_keep_generated_skills_out_of_git(self):
        self.put(self.kit, "skills/compare-bots/references/table[1].md", "| seed |\n")
        self.commit("Add a reference whose name needs escaping")
        self.target.mkdir()
        self.target_git("init", "--quiet")
        self.put(self.target, ".claude/skills/project-skill/SKILL.md", "Project skill\n")
        self.cli("init")
        self.assertEqual((self.config()["agents"], self.config()["commit_skills"]), (["claude", "codex"], False))
        visible = sorted(line[3:] for line in self.target_git("status", "--porcelain", "--untracked-files=all").splitlines())
        self.assertEqual(visible, [".ai/kit.json", ".ai/kit.lock.json", ".ai/project.md", ".ai/sync.py",
                                   ".claude/skills/project-skill/SKILL.md", ".gitignore", "AGENTS.md", "CLAUDE.md"])
        for agent in (".agents", ".claude"):
            self.assertTrue((self.target / agent / "skills/compare-bots/references/table[1].md").is_file())
        self.put(self.target, ".claude/skills/compare-bots/notes.md", "User notes stay visible\n")
        self.assertIn(".claude/skills/compare-bots/notes.md", self.target_git("status", "--porcelain", "--untracked-files=all"))
        self.cli("check")

    def test_check_accepts_a_clone_without_ignored_skills(self):
        self.cli("init")
        for agent in (".agents", ".claude"):
            shutil.rmtree(self.target / agent)
        self.assertIn("skills not generated yet", self.cli("check").stdout)
        self.cli("sync")
        self.assertTrue((self.target / ".claude/skills/compare-bots/SKILL.md").is_file())
        (self.target / ".agents/skills/compare-bots/references/seeds.txt").unlink()
        self.assertIn(".agents/skills/compare-bots/references/seeds.txt", self.cli("check", expected=1).stderr)
        self.cli("sync")
        self.cli("check")
        self.put(self.target, ".claude/skills/compare-bots/SKILL.md", "Local changes\n")
        self.cli("check", expected=1)
        self.assertIn("local edits", self.cli("sync", expected=1).stderr)

    def test_agents_select_the_generated_layouts(self):
        self.cli("init", "--agents", "claude")
        self.assertTrue((self.target / ".claude/skills/compare-bots/SKILL.md").is_file())
        self.assertFalse((self.target / ".agents").exists())
        ignore = (self.target / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/.claude/skills/compare-bots/SKILL.md", ignore)
        self.assertNotIn(".agents", ignore)
        config = self.config()
        config["agents"] = ["codex"]
        self.put(self.target, ".ai/kit.json", json.dumps(config))
        self.cli("sync")
        self.assertFalse((self.target / "CLAUDE.md").exists())
        self.assertFalse((self.target / ".claude/skills/compare-bots/SKILL.md").exists())
        self.assertTrue((self.target / ".agents/skills/compare-bots/SKILL.md").is_file())
        self.assertIn("/.agents/skills/compare-bots/SKILL.md", (self.target / ".gitignore").read_text(encoding="utf-8"))
        self.cli("check")
        for agents in ([], ["cursor"], ["claude", "claude"], "claude", [1]):
            with self.subTest(agents=agents):
                config["agents"] = agents
                self.put(self.target, ".ai/kit.json", json.dumps(config))
                before = self.files()
                self.assertIn("agents", self.cli("sync", expected=1).stderr)
                self.assertEqual(self.files(), before)
        other = self.root / "other"
        self.assertIn("agents", self.cli("init", "--agents", "claude,cursor", expected=1, target=other).stderr)
        self.assertFalse(other.exists())

    def test_gitignore_block_preserves_user_lines_and_can_be_removed(self):
        self.put(self.target, ".gitignore", b"build/\r\n*.log")  # the user's own CRLF lines, no final newline
        self.cli("init")
        ignore = (self.target / ".gitignore").read_bytes()
        self.assertTrue(ignore.startswith(b"build/\r\n*.log\r\n# BEGIN cg-agent-kit"))
        self.assertNotIn(b"\n", ignore.replace(b"\r\n", b""))
        self.put(self.kit, "skills/profile-bot/SKILL.md", "---\nname: profile-bot\ndescription: Profile a bot.\n---\n")
        self.commit("Add shared skill")
        self.cli("update")
        self.assertIn(b"/.agents/skills/profile-bot/SKILL.md\r\n", (self.target / ".gitignore").read_bytes())
        self.put(self.target, ".gitignore", (self.target / ".gitignore").read_bytes() + b"replays/\r\n")
        self.cli("check")
        config = self.config()
        config["commit_skills"] = True
        self.put(self.target, ".ai/kit.json", json.dumps(config))
        self.assertIn(".gitignore (cg-agent-kit block)", self.cli("check", expected=1).stderr)
        self.cli("sync")
        self.assertEqual((self.target / ".gitignore").read_bytes(), b"build/\r\n*.log\r\nreplays/\r\n")
        self.cli("check")
        committed = self.root / "committed"
        self.cli("init", "--commit-skills", target=committed)
        self.assertFalse((committed / ".gitignore").exists())
        self.assertTrue(json.loads((committed / ".ai/kit.json").read_text(encoding="utf-8"))["commit_skills"])

    def test_configs_without_the_new_keys_keep_the_committed_layout(self):
        self.cli("init", "--commit-skills")
        config = self.config()
        del config["agents"], config["commit_skills"]
        self.put(self.target, ".ai/kit.json", json.dumps(config))
        before = self.files()
        self.cli("sync")
        self.cli("check")
        self.assertEqual(self.files(), before)
        self.assertFalse((self.target / ".gitignore").exists())
        for agent in (".agents", ".claude"):
            self.assertTrue((self.target / agent / "skills/compare-bots/SKILL.md").is_file())

    def test_malformed_gitignore_block_stops_before_writes(self):
        for content in ("# BEGIN cg-agent-kit: partial\n/.claude/skills/x/SKILL.md\n",
                        "# END cg-agent-kit\n# BEGIN cg-agent-kit\n"):
            with self.subTest(content=content):
                self.put(self.target, ".gitignore", content)
                before = self.files()
                self.assertIn("malformed cg-agent-kit block", self.cli("init", expected=1).stderr)
                self.assertEqual(self.files(), before)

    def test_init_options_reach_the_committed_synchronizer(self):
        script = self.kit / "scripts/sync.py"
        script.write_bytes(script.read_bytes().replace(b"<!-- Generated by cg-agent-kit.",
                                                       b"<!-- Generated by cg-agent-kit (next)."))
        self.commit("Change the generated header")
        result = self.cli("init", "--agents", "claude", "--commit-skills")  # SCRIPT now differs from the commit
        self.assertIn("using the synchronizer committed", result.stderr)
        self.assertEqual((self.config()["agents"], self.config()["commit_skills"]), (["claude"], True))
        self.assertFalse((self.target / ".agents").exists())
        self.assertFalse((self.target / ".gitignore").exists())


@unittest.skipUnless(shutil.which("git"), "Git is required")
class CommittedKitTests(unittest.TestCase):
    def test_committed_kit_initializes_and_checks_a_contest(self):
        # Synchronizes this repository's real HEAD exactly as consumers receive it.
        kit = SCRIPT.parents[1]
        head = subprocess.run(["git", "-C", str(kit), "rev-parse", "--verify", "--quiet", "HEAD"],
                              capture_output=True, timeout=20)
        if head.returncode:
            self.skipTest("The kit checkout has no commit")
        with tempfile.TemporaryDirectory(prefix="cg-kit-test-") as scratch:
            target = Path(scratch) / "contest"
            for action, extra in (("init", ["--ref", "HEAD"]), ("check", [])):
                result = subprocess.run([sys.executable, str(SCRIPT), action, str(target), "--source", str(kit), *extra],
                                        capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, f"{action}: {result.stderr}")


if __name__ == "__main__":
    unittest.main()
