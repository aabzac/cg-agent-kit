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
