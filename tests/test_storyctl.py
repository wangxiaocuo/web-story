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
        review = json.loads((workspace / "review.json").read_text(encoding="utf-8"))
        review.update({"status": "pass", "checks": {
            "perception": "测试夹具无对白，无人物信息交换。",
            "continuity": "首章测试夹具，无前章事实依赖。",
            "mobile_readability": "单段测试夹具，已记录其段落限制。",
            "prose_style": "此为提交流程夹具，不作文学质量保证。",
        }, "findings": []})
        (workspace / "review.json").write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")

    def make_finding(self, severity: str, resolution: str = "open") -> dict:
        return {
            "severity": severity, "resolution": resolution,
            "location": "第 1 章第 2 段", "type": "感知越界",
            "evidence": "角色回应了未传递给他的私有信息。",
            "reader_impact": "角色判断缺少信息来源。",
            "suggestion": "将回应改为基于角色实际听到的话。",
        }

    def test_review_gate_blocks_unresolved_or_unsupported_findings(self) -> None:
        for severity, resolution, note in (
            ("blocker", "open", ""),
            ("blocker", "accepted_by_author", "作者要求保留，仍不能冒充已修复。"),
            ("major", "open", ""),
            ("major", "accepted_by_author", ""),
            ("blocker", "fixed", ""),
            ("major", "fixed", ""),
        ):
            with self.subTest(severity=severity, resolution=resolution, note=note), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "book"
                self.run_ctl(root, "init", "--title", "测试书")
                self.run_ctl(root, "stage", "--chapter", "1", "--title", "审稿门槛")
                self.make_passing_stage(root)
                review_path = root / ".web-story/staging/chapter-0001/review.json"
                review = json.loads(review_path.read_text(encoding="utf-8"))
                finding = self.make_finding(severity, resolution)
                finding["resolution_note"] = note
                review["findings"] = [finding]
                review_path.write_text(json.dumps(review), encoding="utf-8")
                before = (root / ".web-story/canon.json").read_bytes()
                result = self.run_ctl(root, "commit", "--chapter", "1", expected=2)
                self.assertFalse(result["ok"])
                self.assertEqual(list((root / "正文").iterdir()), [])
                self.assertEqual((root / ".web-story/canon.json").read_bytes(), before)
                self.assertTrue(review_path.exists())

    def test_review_gate_allows_resolved_and_nonblocking_findings(self) -> None:
        for severity, resolution in (("blocker", "fixed"), ("major", "fixed"), ("major", "accepted_by_author"), ("minor", "open"), ("note", "open")):
            with self.subTest(severity=severity, resolution=resolution), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "book"
                self.run_ctl(root, "init", "--title", "测试书")
                self.run_ctl(root, "stage", "--chapter", "1", "--title", "可结算")
                self.make_passing_stage(root)
                review_path = root / ".web-story/staging/chapter-0001/review.json"
                review = json.loads(review_path.read_text(encoding="utf-8"))
                finding = self.make_finding(severity, resolution)
                if resolution == "fixed":
                    finding["resolution_note"] = "已修改回应；重读交流段落确认信息来自前一句对白。"
                elif resolution == "accepted_by_author":
                    finding["resolution_note"] = "测试中的作者明确接受该 major 风险。"
                review["findings"] = [finding]
                review_path.write_text(json.dumps(review), encoding="utf-8")
                self.assertTrue(self.run_ctl(root, "commit", "--chapter", "1")["ok"])

    def test_review_gate_rejects_incomplete_or_malformed_evidence(self) -> None:
        mutations = (
            lambda review: review.pop("checks"),
            lambda review: review["checks"].update(perception="  "),
            lambda review: review["checks"].update(continuity=True),
            lambda review: review.update(findings={}),
            lambda review: review.update(findings=[None]),
            lambda review: review.update(findings=[{"severity": "unknown"}]),
            lambda review: review.update(findings=[{"severity": "major", "resolution": "fixed", "resolution_note": "改好了"}]),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "book"
                self.run_ctl(root, "init", "--title", "测试书")
                self.run_ctl(root, "stage", "--chapter", "1", "--title", "缺依据")
                self.make_passing_stage(root)
                review_path = root / ".web-story/staging/chapter-0001/review.json"
                review = json.loads(review_path.read_text(encoding="utf-8"))
                mutate(review)
                review_path.write_text(json.dumps(review), encoding="utf-8")
                result = self.run_ctl(root, "commit", "--chapter", "1", expected=2)
                self.assertFalse(result["ok"])
                self.assertTrue(review_path.exists())

    def test_state_transition_preserves_entity_and_fact_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "book"
            self.run_ctl(root, "init", "--title", "测试书")
            self.run_ctl(root, "stage", "--chapter", "1", "--title", "取得")
            self.make_passing_stage(root)
            first_path = root / ".web-story/staging/chapter-0001/facts.json"
            first = {
                "id": "FACT-0001", "entity_id": "item-letter-01", "subject": "信件",
                "predicate": "持有者", "value": "主角", "kind": "state",
                "source_anchor": "主角捡起了信", "valid_from": "山中拾信",
            }
            first_path.write_text(json.dumps([first]), encoding="utf-8")
            self.run_ctl(root, "commit", "--chapter", "1")
            before = json.loads((root / ".web-story/canon.json").read_text(encoding="utf-8"))["facts"]["FACT-0001"]
            self.run_ctl(root, "stage", "--chapter", "2", "--title", "转交")
            second_workspace = root / ".web-story/staging/chapter-0002"
            archived = root / ".web-story/runs/chapter-0001-workspace"
            for name in ("summary.md", "hooks.json", "review.json"):
                (second_workspace / name).write_bytes((archived / name).read_bytes())
            (second_workspace / "draft.md").write_text("主角把信递给了船夫。", encoding="utf-8")
            second = {
                **first, "id": "FACT-0002", "value": "船夫", "valid_from": "渡口交接",
                "source_anchor": "主角把信递给了船夫", "supersedes": "FACT-0001",
                "change_reason": "主角当面交给船夫，请他送信。",
            }
            (second_workspace / "facts.json").write_text(json.dumps([second]), encoding="utf-8")
            self.run_ctl(root, "commit", "--chapter", "2")
            facts = json.loads((root / ".web-story/canon.json").read_text(encoding="utf-8"))["facts"]
            self.assertEqual(facts["FACT-0001"], before)
            self.assertEqual(facts["FACT-0002"]["entity_id"], before["entity_id"])
            self.assertEqual(facts["FACT-0002"]["supersedes"], "FACT-0001")
            self.assertEqual(facts["FACT-0002"]["source_chapter"], 2)

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

    def test_commit_blocks_halfwidth_punctuation_adjacent_to_cjk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "book"
            self.run_ctl(root, "init", "--title", "测试书")
            self.run_ctl(root, "stage", "--chapter", "1", "--title", "标点")
            self.make_passing_stage(root)
            workspace = root / ".web-story/staging/chapter-0001"
            (workspace / "draft.md").write_text(
                "他放下茶杯,低声道:\"走吧。\"屏幕上滚过Level 3.5的提示,又暗了下去...",
                encoding="utf-8",
            )
            result = self.run_ctl(root, "commit", "--chapter", "1", expected=2)
            self.assertFalse(result["ok"])
            self.assertTrue(any("半角标点" in error for error in result["errors"]))
            self.assertEqual(list((root / "正文").iterdir()), [])
            (workspace / "draft.md").write_text(
                "他放下茶杯，低声道：“走吧。”屏幕上滚过Level 3.5的提示，又暗了下去……",
                encoding="utf-8",
            )
            self.assertTrue(self.run_ctl(root, "commit", "--chapter", "1")["ok"])

    def test_commit_allows_halfwidth_only_through_explicit_author_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "book"
            self.run_ctl(root, "init", "--title", "测试书")
            self.run_ctl(root, "stage", "--chapter", "1", "--title", "半角")
            self.make_passing_stage(root)
            workspace = root / ".web-story/staging/chapter-0001"
            (workspace / "draft.md").write_text("他点头,转身离开。", encoding="utf-8")
            self.run_ctl(root, "commit", "--chapter", "1", "--allow-halfwidth", expected=0)
            self.assertTrue((root / "正文" / "第001章-半角.md").exists())

    def test_english_contexts_are_not_flagged_and_validate_warns_for_committed_prose(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "book"
            self.run_ctl(root, "init", "--title", "测试书")
            self.run_ctl(root, "stage", "--chapter", "1", "--title", "混排")
            self.make_passing_stage(root)
            workspace = root / ".web-story/staging/chapter-0001"
            (workspace / "draft.md").write_text(
                "He typed \"run\" at 12:30, scoring 3.5 out of 10. Don't stop! APP v2.0 works.\n\n"
                "他看了看屏幕，笑了笑。",
                encoding="utf-8",
            )
            self.assertTrue(self.run_ctl(root, "commit", "--chapter", "1")["ok"])
            chapter_path = next((root / "正文").glob("第001章-*.md"))
            chapter_path.write_text(chapter_path.read_text(encoding="utf-8") + "\n\n他说,\"明天见。\"",
                                    encoding="utf-8")
            result = self.run_ctl(root, "validate")
            self.assertTrue(result["ok"])
            self.assertTrue(any("半角标点" in warning for warning in result["warnings"]))

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

    def test_reconcile_reports_interrupted_commit_journal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "book"
            self.run_ctl(root, "init", "--title", "测试书")
            pending = root / ".web-story" / "runs" / "chapter-0001.pending.json"
            pending.write_text(json.dumps({"chapter": 1, "artifacts": ["正文/第001章.md"]}), encoding="utf-8")
            result = self.run_ctl(root, "reconcile", expected=3)
            self.assertEqual(result["discrepancies"][0]["type"], "pending-commit")


if __name__ == "__main__":
    unittest.main()
