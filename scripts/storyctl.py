#!/usr/bin/env python3
"""Deterministic project operations for the web-story skill.

This tool intentionally does not judge prose. It validates and persists the
artifacts that let an agent and author keep a long fiction project coherent.
All commands print a JSON object and return a meaningful exit status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
CHAPTER_RE = re.compile(r"^第(\d{3,})章(?:-.+)?\.md$")
REQUIRED_STAGE_FILES = ("draft.md", "summary.md", "facts.json", "hooks.json", "review.json")


class StoryError(Exception):
    pass


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def emit(payload: dict[str, Any], code: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return code


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temp_name, path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StoryError(f"缺少 {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StoryError(f"{label} 不是合法 JSON: {path}: {exc.msg}") from exc


def project_root(args: argparse.Namespace) -> Path:
    return Path(getattr(args, "project_root", ".")).expanduser().resolve()


def state_dir(root: Path) -> Path:
    return root / ".web-story"


def manifest_path(root: Path) -> Path:
    return state_dir(root) / "manifest.json"


def require_project(root: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path(root), "书籍清单 manifest")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise StoryError("manifest schema_version 不受支持")
    return manifest


def chapter_files(root: Path) -> list[tuple[int, Path]]:
    result: list[tuple[int, Path]] = []
    for path in (root / "正文").glob("*.md"):
        match = CHAPTER_RE.match(path.name)
        if match:
            result.append((int(match.group(1)), path))
    return sorted(result, key=lambda pair: pair[0])


def word_count(text: str) -> int:
    # CJK characters approximate Chinese manuscript length; non-CJK words count once.
    cjk = len(re.findall(r"[\u3400-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*", text))
    return cjk + latin


def chapter_name(number: int, title: str) -> str:
    safe_title = re.sub(r"[\\/:*?\"<>|\n\r]", "-", title).strip(" .-") or "未命名"
    return f"第{number:03d}章-{safe_title}.md"


def hash_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def validate_fact(fact: Any, chapter: int) -> dict[str, Any]:
    if not isinstance(fact, dict):
        raise StoryError("facts.json 的每项必须是对象")
    required = ("subject", "predicate", "value")
    missing = [name for name in required if not str(fact.get(name, "")).strip()]
    if missing:
        raise StoryError(f"事实缺少字段: {', '.join(missing)}")
    result = dict(fact)
    result.setdefault("status", "confirmed")
    if result["status"] not in {"proposed", "confirmed", "retconned", "disputed"}:
        raise StoryError(f"事实 status 不合法: {result['status']}")
    result.setdefault("reader_visibility", "unknown")
    if result["reader_visibility"] not in {"unknown", "hinted", "revealed"}:
        raise StoryError(f"事实 reader_visibility 不合法: {result['reader_visibility']}")
    result.setdefault("source_chapter", chapter)
    result.setdefault("confidence", "high")
    return result


def validate_hook(hook: Any, chapter: int) -> dict[str, Any]:
    if not isinstance(hook, dict):
        raise StoryError("hooks.json 的每项必须是对象")
    if not str(hook.get("promise", "")).strip():
        raise StoryError("伏笔必须包含 promise")
    result = dict(hook)
    result.setdefault("seed_chapter", chapter)
    result.setdefault("status", "open")
    if result["status"] not in {"open", "hinted", "triggered", "resolved", "retired"}:
        raise StoryError(f"伏笔 status 不合法: {result['status']}")
    result.setdefault("stakes", "normal")
    return result


def next_id(prefix: str, existing: dict[str, Any]) -> str:
    maximum = 0
    for key in existing:
        match = re.match(rf"^{prefix}-(\d+)$", key)
        if match:
            maximum = max(maximum, int(match.group(1)))
    return f"{prefix}-{maximum + 1:04d}"


def command_init(args: argparse.Namespace) -> int:
    root = project_root(args)
    if root.exists() and any(root.iterdir()):
        raise StoryError(f"目标目录并非空目录: {root}")
    root.mkdir(parents=True, exist_ok=True)
    for relative in (
        "正文", "大纲/卷纲", "大纲/章节意图", "设定集", "素材", "投稿包",
        ".web-story/summaries", ".web-story/reviews", ".web-story/runs", ".web-story/staging",
        ".web-story/index",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    book_id = "book-" + hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:12]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "book_id": book_id,
        "title": args.title,
        "mode": args.mode,
        "status": "planning",
        "created_at": now(),
        "updated_at": now(),
        "accepted_chapters": [],
    }
    canon = {"schema_version": SCHEMA_VERSION, "facts": {}, "updated_at": now()}
    timeline = {"schema_version": SCHEMA_VERSION, "events": {}, "updated_at": now()}
    hooks = {"schema_version": SCHEMA_VERSION, "hooks": {}, "updated_at": now()}
    write_json(manifest_path(root), manifest)
    write_json(state_dir(root) / "canon.json", canon)
    write_json(state_dir(root) / "timeline.json", timeline)
    write_json(state_dir(root) / "hooks.json", hooks)
    atomic_write(root / ".web-story/current-focus.md", "# 当前焦点\n\n待作者确认首批章节方向。\n")
    atomic_write(root / ".web-story/authorship-log.md", "# 创作决策记录\n\n- " + now() + "：创建项目。\n")
    atomic_write(root / "README.md", f"# {args.title}\n\n使用 `/web-story` 继续规划、写作、审稿或准备投稿。\n")
    atomic_write(root / "大纲/创作简报.md", "# 创作简报\n\n> 待作者确认：题材、主角/核心关系、主冲突、读者承诺与内容边界。\n")
    atomic_write(root / "大纲/总纲.md", "# 总纲\n\n> 待规划。\n")
    atomic_write(root / "设定集/人物.md", "# 人物\n\n> 待设定。\n")
    atomic_write(root / "设定集/世界观.md", "# 世界观\n\n> 待设定。\n")
    atomic_write(root / "设定集/文风契约.md", "# 文风契约\n\n> 待作者确认叙事视角、时态、语言密度与内容边界。\n")
    return emit({"ok": True, "action": "init", "project_root": str(root), "book_id": book_id})


def command_status(args: argparse.Namespace) -> int:
    root = project_root(args)
    manifest = require_project(root)
    chapters = chapter_files(root)
    staging = sorted(path.name for path in (state_dir(root) / "staging").iterdir() if path.is_dir())
    hooks = read_json(state_dir(root) / "hooks.json", "伏笔账本")
    open_hooks = [hook for hook in hooks.get("hooks", {}).values() if hook.get("status") != "resolved"]
    return emit({
        "ok": True,
        "action": "status",
        "title": manifest["title"],
        "mode": manifest["mode"],
        "status": manifest["status"],
        "accepted_chapters": manifest.get("accepted_chapters", []),
        "chapter_files": [number for number, _ in chapters],
        "open_hooks": len(open_hooks),
        "staging": staging,
    })


def command_preflight(args: argparse.Namespace) -> int:
    root = project_root(args)
    manifest = require_project(root)
    errors: list[str] = []
    warnings: list[str] = []
    for relative in ("正文", "大纲", "设定集", ".web-story/summaries", ".web-story/staging"):
        if not (root / relative).exists():
            errors.append(f"缺少目录: {relative}")
    staging = [path.name for path in (state_dir(root) / "staging").iterdir() if path.is_dir()]
    if staging:
        warnings.append("存在未结算章节工作区: " + ", ".join(staging))
    if manifest.get("status") == "planning":
        warnings.append("书籍仍处于 planning；写正文前应确认创作简报与首批计划")
    return emit({"ok": not errors, "action": "preflight", "errors": errors, "warnings": warnings}, 0 if not errors else 2)


def command_stage(args: argparse.Namespace) -> int:
    root = project_root(args)
    require_project(root)
    number = args.chapter
    if number < 1:
        raise StoryError("chapter 必须大于 0")
    target = state_dir(root) / "staging" / f"chapter-{number:04d}"
    if target.exists():
        raise StoryError(f"工作区已存在: {target}; 先完成、恢复或清理它")
    target.mkdir(parents=True)
    write_json(target / "chapter.json", {
        "chapter": number, "title": args.title, "phase": "intent-card-ready", "created_at": now(),
    })
    atomic_write(target / "intent-card.md", "# 章节意图卡\n\n- POV：\n- 时间地点：\n- 章节问题：\n- 人物目标与阻力：\n- 必须推进：\n- 禁止改变：\n- 伏笔：\n- 结尾拉力：\n- 目标字数：\n")
    atomic_write(target / "draft.md", "")
    atomic_write(target / "summary.md", "")
    write_json(target / "facts.json", [])
    write_json(target / "hooks.json", [])
    write_json(target / "review.json", {"status": "pending", "findings": []})
    return emit({"ok": True, "action": "stage", "workspace": str(target), "chapter": number})


def read_stage(root: Path, number: int) -> tuple[Path, dict[str, Any]]:
    workspace = state_dir(root) / "staging" / f"chapter-{number:04d}"
    if not workspace.is_dir():
        raise StoryError(f"未找到第 {number} 章工作区")
    data = read_json(workspace / "chapter.json", "工作区章节信息")
    if data.get("chapter") != number:
        raise StoryError("工作区章节号不匹配")
    return workspace, data


def stage_errors(workspace: Path, number: int) -> list[str]:
    errors: list[str] = []
    for name in REQUIRED_STAGE_FILES:
        if not (workspace / name).exists():
            errors.append(f"缺少工作区文件: {name}")
    if errors:
        return errors
    if not (workspace / "draft.md").read_text(encoding="utf-8").strip():
        errors.append("draft.md 为空")
    if not (workspace / "summary.md").read_text(encoding="utf-8").strip():
        errors.append("summary.md 为空")
    review = read_json(workspace / "review.json", "审稿结论")
    if review.get("status") != "pass":
        errors.append("审稿状态不是 pass")
    try:
        facts = read_json(workspace / "facts.json", "事实增量")
        if not isinstance(facts, list):
            errors.append("facts.json 必须是数组")
        else:
            for fact in facts:
                validate_fact(fact, number)
        hooks = read_json(workspace / "hooks.json", "伏笔增量")
        if not isinstance(hooks, list):
            errors.append("hooks.json 必须是数组")
        else:
            for hook in hooks:
                validate_hook(hook, number)
    except StoryError as exc:
        errors.append(str(exc))
    return errors


def command_validate(args: argparse.Namespace) -> int:
    root = project_root(args)
    manifest = require_project(root)
    errors: list[str] = []
    warnings: list[str] = []
    canonical = read_json(state_dir(root) / "canon.json", "正史")
    hooks = read_json(state_dir(root) / "hooks.json", "伏笔账本")
    if not isinstance(canonical.get("facts"), dict):
        errors.append("canon.json.facts 必须是对象")
    if not isinstance(hooks.get("hooks"), dict):
        errors.append("hooks.json.hooks 必须是对象")
    files = chapter_files(root)
    file_numbers = [number for number, _ in files]
    accepted = manifest.get("accepted_chapters", [])
    if accepted != sorted(set(accepted)):
        errors.append("manifest accepted_chapters 必须去重且排序")
    if accepted != file_numbers:
        errors.append(f"accepted_chapters 与正文文件不一致: manifest={accepted}, files={file_numbers}")
    for number, path in files:
        if not (state_dir(root) / "summaries" / f"chapter-{number:04d}.md").exists():
            errors.append(f"第 {number} 章缺少摘要")
        if word_count(path.read_text(encoding="utf-8")) < 100:
            warnings.append(f"第 {number} 章正文不足 100 字")
    return emit({"ok": not errors, "action": "validate", "errors": errors, "warnings": warnings}, 0 if not errors else 2)


def command_reconcile(args: argparse.Namespace) -> int:
    root = project_root(args)
    manifest = require_project(root)
    files = chapter_files(root)
    file_numbers = [number for number, _ in files]
    accepted = manifest.get("accepted_chapters", [])
    discrepancies: list[dict[str, Any]] = []
    if accepted != file_numbers:
        discrepancies.append({"type": "chapter-set", "manifest": accepted, "files": file_numbers})
    summaries = state_dir(root) / "summaries"
    for number, _ in files:
        if not (summaries / f"chapter-{number:04d}.md").exists():
            discrepancies.append({"type": "missing-summary", "chapter": number})
    canon = read_json(state_dir(root) / "canon.json", "正史")
    for fact_id, fact in canon.get("facts", {}).items():
        source = fact.get("source_chapter")
        if isinstance(source, int) and source not in file_numbers:
            discrepancies.append({"type": "orphan-fact", "fact_id": fact_id, "source_chapter": source})
    return emit({"ok": not discrepancies, "action": "reconcile", "discrepancies": discrepancies}, 0 if not discrepancies else 3)


def command_commit(args: argparse.Namespace) -> int:
    root = project_root(args)
    manifest = require_project(root)
    number = args.chapter
    workspace, chapter = read_stage(root, number)
    errors = stage_errors(workspace, number)
    if errors:
        return emit({"ok": False, "action": "commit", "errors": errors}, 2)
    accepted = manifest.get("accepted_chapters", [])
    if number in accepted:
        raise StoryError(f"第 {number} 章已经接受；拒绝重复提交")
    if accepted and number != max(accepted) + 1:
        raise StoryError(f"只能顺序提交下一章；当前最后一章为 {max(accepted)}")
    if not accepted and number != 1:
        raise StoryError("第一章必须从 chapter 1 开始")

    draft = workspace / "draft.md"
    summary = workspace / "summary.md"
    facts = [validate_fact(item, number) for item in read_json(workspace / "facts.json", "事实增量")]
    hook_changes = [validate_hook(item, number) for item in read_json(workspace / "hooks.json", "伏笔增量")]
    canon = read_json(state_dir(root) / "canon.json", "正史")
    ledger = read_json(state_dir(root) / "hooks.json", "伏笔账本")
    canon_facts = canon.setdefault("facts", {})
    hook_ledger = ledger.setdefault("hooks", {})

    for fact in facts:
        fact_id = fact.get("id") or next_id("FACT", canon_facts)
        fact["id"] = fact_id
        existing = canon_facts.get(fact_id)
        if existing and existing != fact and not args.allow_retcon:
            raise StoryError(f"事实 {fact_id} 已存在且内容不同；使用 --allow-retcon 并先取得作者确认")
        canon_facts[fact_id] = fact
    for hook in hook_changes:
        hook_id = hook.get("id") or next_id("HOOK", hook_ledger)
        hook["id"] = hook_id
        hook_ledger[hook_id] = hook

    title = str(chapter.get("title") or "未命名")
    prose_path = root / "正文" / chapter_name(number, title)
    summary_path = state_dir(root) / "summaries" / f"chapter-{number:04d}.md"
    review_path = state_dir(root) / "reviews" / f"chapter-{number:04d}.json"
    # All generated files are individually atomic. The run snapshot records enough
    # information for reconcile to reveal an interrupted multi-file commit.
    atomic_write(prose_path, draft.read_text(encoding="utf-8"))
    atomic_write(summary_path, summary.read_text(encoding="utf-8"))
    write_json(review_path, read_json(workspace / "review.json", "审稿结论"))
    canon["updated_at"] = now()
    ledger["updated_at"] = now()
    write_json(state_dir(root) / "canon.json", canon)
    write_json(state_dir(root) / "hooks.json", ledger)
    manifest["accepted_chapters"] = sorted(accepted + [number])
    manifest["status"] = "active"
    manifest["updated_at"] = now()
    write_json(manifest_path(root), manifest)
    run = {
        "chapter": number,
        "phase": "committed",
        "committed_at": now(),
        "artifacts": [str(prose_path.relative_to(root)), str(summary_path.relative_to(root)), str(review_path.relative_to(root))],
        "inputs_hash": hash_files([draft, summary, workspace / "facts.json", workspace / "hooks.json", workspace / "review.json"]),
    }
    write_json(state_dir(root) / "runs" / f"chapter-{number:04d}.json", run)
    archive = state_dir(root) / "runs" / f"chapter-{number:04d}-workspace"
    if archive.exists():
        shutil.rmtree(archive)
    shutil.move(str(workspace), str(archive))
    return emit({"ok": True, "action": "commit", "chapter": number, "prose": str(prose_path), "facts_added": len(facts), "hooks_updated": len(hook_changes)})


def command_build(args: argparse.Namespace) -> int:
    root = project_root(args)
    manifest = require_project(root)
    output = root / "投稿包"
    chapters = chapter_files(root)
    compiled = "\n\n".join(path.read_text(encoding="utf-8").rstrip() for _, path in chapters) + ("\n" if chapters else "")
    atomic_write(output / "全稿.md", compiled)
    checklist = "# 投稿前人工复核清单\n\n- [ ] 核对目标平台当前官方规则与合同\n- [ ] 核对作品原创性与引用/素材授权\n- [ ] 审阅内容边界和敏感项\n- [ ] 审阅标题、简介、标签与样章\n- [ ] 按平台要求决定 AI 协作披露方式\n"
    atomic_write(output / "人工复核清单.md", checklist)
    manifest_text = f"# 投稿包清单\n\n- 书名：{manifest['title']}\n- 模式：{manifest['mode']}\n- 平台画像：{args.platform}\n- 章节数：{len(chapters)}\n- 生成时间：{now()}\n\n本包仅用于投稿准备，不保证平台资格、审核、签约或收益。\n"
    atomic_write(output / "submission-manifest.md", manifest_text)
    return emit({"ok": True, "action": "build", "platform": args.platform, "output": str(output), "chapters": len(chapters)})


def parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project-root", default=".", help="书籍项目根目录（默认当前目录）")
    root = argparse.ArgumentParser(description="web-story deterministic project operations")
    commands = root.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", parents=[common])
    init.add_argument("--title", required=True)
    init.add_argument("--mode", choices=("short", "medium", "serial"), default="medium")
    init.set_defaults(handler=command_init)

    for name, handler in (("status", command_status), ("preflight", command_preflight), ("validate", command_validate), ("reconcile", command_reconcile)):
        sub = commands.add_parser(name, parents=[common])
        sub.set_defaults(handler=handler)

    stage = commands.add_parser("stage", parents=[common])
    stage.add_argument("--chapter", type=int, required=True)
    stage.add_argument("--title", required=True)
    stage.set_defaults(handler=command_stage)

    commit = commands.add_parser("commit", parents=[common])
    commit.add_argument("--chapter", type=int, required=True)
    commit.add_argument("--allow-retcon", action="store_true")
    commit.set_defaults(handler=command_commit)

    build = commands.add_parser("build", parents=[common])
    build.add_argument("--platform", default="通用中文商业网文")
    build.set_defaults(handler=command_build)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.handler(args)
    except StoryError as exc:
        return emit({"ok": False, "error": str(exc)}, 2)
    except Exception as exc:  # pragma: no cover - protects skill users from traceback noise
        return emit({"ok": False, "error": f"unexpected error: {exc}"}, 1)


if __name__ == "__main__":
    raise SystemExit(main())
