from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "storyctl.py"


class StoryCtlTests(unittest.TestCase):
    def run_ctl(self, root: Path, *args: str, expected: int = 0) -> dict:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args, "--project-root", str(root)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def make_passing_stage(self, root: Path) -> None:
        workspace = root / ".web-story" / "staging" / "chapter-0001"
        (workspace / "draft.md").write_text("第一章\n\n" + "山" * 160, encoding="utf-8")
        (workspace / "summary.md").write_text("主角在山中发现一封改变命运的信。", encoding="utf-8")
        (workspace / "facts.json").write_text(json.dumps([{
            "subject": "主角", "predicate": "获得", "value": "神秘信件", "reader_visibility": "revealed"
        }], ensure_ascii=False), encoding="utf-8")
        (workspace / "hooks.json").write_text(json.dumps([{
            "promise": "信件寄件人的身份", "status": "open"
        }], ensure_ascii=False), encoding="utf-8")
        (workspace / "review.json").write_text(json.dumps({"status": "pass", "findings": []}, ensure_ascii=False), encoding="utf-8")

    def test_init_stage_commit_validate_and_build(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "book"
            created = self.run_ctl(root, "init", "--title", "测试书", "--mode", "short")
            self.assertTrue(created["ok"])
            self.run_ctl(root, "stage", "--chapter", "1", "--title", "山信")
            self.make_passing_stage(root)
            committed = self.run_ctl(root, "commit", "--chapter", "1")
            self.assertEqual(committed["facts_added"], 1)
            self.assertTrue((root / "正文" / "第001章-山信.md").exists())
            self.assertTrue(self.run_ctl(root, "validate")["ok"])
            built = self.run_ctl(root, "build", "--platform", "通用")
            self.assertEqual(built["chapters"], 1)
            self.assertTrue((root / "投稿包" / "全稿.md").exists())

    def test_commit_rejects_pending_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "book"
            self.run_ctl(root, "init", "--title", "测试书")
            self.run_ctl(root, "stage", "--chapter", "1", "--title", "未审")
            self.make_passing_stage(root)
            workspace = root / ".web-story" / "staging" / "chapter-0001"
            (workspace / "review.json").write_text('{"status": "pending", "findings": []}', encoding="utf-8")
            result = self.run_ctl(root, "commit", "--chapter", "1", expected=2)
            self.assertFalse(result["ok"])
            self.assertFalse((root / "正文" / "第001章-未审.md").exists())

    def test_reconcile_finds_missing_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "book"
            self.run_ctl(root, "init", "--title", "测试书")
            self.run_ctl(root, "stage", "--chapter", "1", "--title", "对账")
            self.make_passing_stage(root)
            self.run_ctl(root, "commit", "--chapter", "1")
            (root / ".web-story" / "summaries" / "chapter-0001.md").unlink()
            result = self.run_ctl(root, "reconcile", expected=3)
            self.assertEqual(result["discrepancies"][0]["type"], "missing-summary")


if __name__ == "__main__":
    unittest.main()
