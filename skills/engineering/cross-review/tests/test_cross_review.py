"""Offline tests for cross-review: no network, fake reviewer binaries."""

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "cross-review"
loader = importlib.machinery.SourceFileLoader("cross_review", str(SCRIPT))
spec = importlib.util.spec_from_loader("cross_review", loader)
cr = importlib.util.module_from_spec(spec)
sys.modules["cross_review"] = cr
loader.exec_module(cr)


def review(*findings, verdict="patch is incorrect"):
    return {"findings": list(findings), "overall_correctness": verdict,
            "overall_explanation": "explanation", "overall_confidence_score": 0.9}


def finding(title, path, start, end=None, priority=1, confidence=0.8):
    return {"title": title, "body": f"Body of {title}.", "confidence_score": confidence,
            "priority": priority,
            "code_location": {"absolute_file_path": path, "line_range": {"start": start, "end": end or start}}}


def make_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    run = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)
    run("init", "-q", "-b", "main")
    run("config", "user.email", "t@example.com")
    run("config", "user.name", "t")
    (repo / "a.py").write_text("x = 1\n")
    run("add", ".")
    run("commit", "-qm", "init")
    run("checkout", "-qb", "feature")
    (repo / "a.py").write_text("x = 1\ny = x[3]\n")
    run("commit", "-qam", "change a")
    return repo


class PromptTests(unittest.TestCase):
    def test_base_prompt_matches_codex_wording(self):
        text = cr.BASE_BRANCH_PROMPT.format(base_branch="main", merge_base_sha="abc")
        self.assertEqual(
            text,
            "Review the code changes against the base branch 'main'. The merge base commit for this "
            "comparison is abc. Run `git diff abc` to inspect the changes relative to main. Provide "
            "prioritized, actionable findings.")

    def test_focus_is_appended(self):
        target = cr.Target("base", "x", "PROMPT")
        self.assertTrue(cr.build_prompt(target, "money paths").endswith("money paths"))


class NormalizeAndMergeTests(unittest.TestCase):
    def test_priority_from_title_prefix_when_field_missing(self):
        item = finding("[P2] Something", "/r/a.py", 3, priority=None)
        [f] = cr.normalize(review(item), "codex", Path("/r"))
        self.assertEqual((f.priority, f.title, f.path), (2, "Something", "a.py"))

    def test_same_location_from_both_reviewers_merges(self):
        a = cr.normalize(review(finding("Off-by-one in loop", "/r/a.py", 10, 11, 1)), "codex", Path("/r"))
        b = cr.normalize(review(finding("Loop bound is off by one", "/r/a.py", 11, 12, 0)), "claude", Path("/r"))
        [group] = cr.merge(a + b)
        self.assertEqual((group.priority, group.sources), (0, ["claude", "codex"]))

    def test_same_reviewer_findings_never_merge(self):
        a = cr.normalize(review(finding("One", "/r/a.py", 10), finding("Two", "/r/a.py", 10)), "codex", Path("/r"))
        self.assertEqual(len(cr.merge(a)), 2)

    def test_distant_findings_stay_separate(self):
        a = cr.normalize(review(finding("Off-by-one", "/r/a.py", 10)), "codex", Path("/r"))
        b = cr.normalize(review(finding("Off-by-one", "/r/a.py", 40)), "claude", Path("/r"))
        self.assertEqual(len(cr.merge(a + b)), 2)

    def test_parse_json_object_tolerates_prose(self):
        self.assertEqual(cr.parse_json_object('Result:\n{"a": 1}\nDone'), {"a": 1})


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = make_repo(self.root)
        self.env = dict(os.environ, PATH=f"{HERE / 'fake-bin'}:{os.environ['PATH']}",
                        FAKE_LOG=str(self.root / "calls.log"))
        path = str(self.repo / "a.py")
        self.write("codex.json", review(finding("[P1] Index out of range", path, 2)))
        self.write("claude.json", review(finding("Indexing past the end", path, 2, priority=1)))
        self.env["FAKE_CODEX_REVIEW"] = str(self.root / "codex.json")
        self.env["FAKE_CLAUDE_REVIEW"] = str(self.root / "claude.json")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, data):
        (self.root / name).write_text(json.dumps(data))

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "-C", str(self.repo), "--out", str(self.root / "out"), *args],
                              env=self.env, capture_output=True, text=True, timeout=60)

    def test_merged_blocking_finding_exits_1(self):
        result = self.run_tool("--base", "main", "--json")
        self.assertEqual(result.returncode, 1, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(len(data["findings"]), 1)
        self.assertEqual(data["findings"][0]["sources"], ["claude", "codex"])
        self.assertTrue((self.root / "out" / "review.json").exists())

    def test_both_reviewers_get_the_same_prompt_and_rubric(self):
        self.run_tool("--base", "main")
        log = (self.root / "calls.log").read_text()
        self.assertIn("model_instructions_file=", log)
        self.assertIn("--append-system-prompt-file", log)
        self.assertIn("--output-schema", log)
        self.assertIn("--json-schema", log)

    def test_usage_limit_skips_codex_and_keeps_claude(self):
        self.env["FAKE_CODEX_FAIL"] = "ERROR: You've hit your usage limit."
        result = self.run_tool("--base", "main", "--json")
        data = json.loads(result.stdout)
        codex = next(r for r in data["reviewers"] if r["name"] == "codex")
        self.assertEqual((codex["status"], codex["detail"]), ("skipped", "usage limit reached"))
        self.assertEqual(data["findings"][0]["sources"], ["claude"])

    def test_clean_review_exits_0(self):
        self.write("codex.json", review(verdict="patch is correct"))
        self.write("claude.json", review(verdict="patch is correct"))
        result = self.run_tool("--base", "main")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("No findings.", result.stdout)

    def test_no_reviewer_result_exits_2(self):
        self.env["FAKE_CODEX_FAIL"] = "boom"
        result = self.run_tool("--base", "main", "--reviewers", "codex")
        self.assertEqual(result.returncode, 2)

    def test_commit_target(self):
        result = self.run_tool("--commit", "HEAD", "--json")
        self.assertEqual(json.loads(result.stdout)["target"]["kind"], "commit")

    def test_unknown_reviewer_is_a_usage_error(self):
        self.assertEqual(self.run_tool("--reviewers", "gemini").returncode, 3)


if __name__ == "__main__":
    unittest.main()
