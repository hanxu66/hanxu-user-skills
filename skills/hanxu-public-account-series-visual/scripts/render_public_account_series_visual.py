#!/usr/bin/env python3
"""Render Hanxu's locked V0.7 public-account cover system without workflow scans."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTERNAL = (ROOT / "knowledge-base").is_dir()
TEMPLATE_DIR = (ROOT / "working-files/content-production/PA-2026-08-17-01-more-effort-less-human/series-visual-template-v0.1" if INTERNAL else ROOT / "assets/series-template")
RENDERER = TEMPLATE_DIR / "render-series-visuals.mjs"
NODE_BIN = Path(os.environ.get("HANXU_NODE") or shutil.which("node") or Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
NODE_MODULES = Path(os.environ.get("NODE_PATH") or (Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules" if INTERNAL else ROOT / "node_modules"))
EXPECTED_DIMENSIONS = {
    "UPLOAD-MASTER-1283x383": (1283, 383),
    "message-list-crop-900x383": (900, 383),
    "square-crop-383x383": (383, 383),
    "article-header-1080x120": (1080, 120),
}


def infer_issue(content_root: Path, object_id: str) -> tuple[int, str]:
    same_object: list[int] = []
    all_issues: list[int] = []
    for report_path in content_root.rglob("render-report.json"):
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            issue = int(report.get("issue", ""))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
        if not 1 <= issue <= 99:
            continue
        all_issues.append(issue)
        if report.get("objectId") == object_id:
            same_object.append(issue)
    if same_object:
        return max(same_object), "existing-current-object"
    if all_issues:
        next_issue = max(all_issues) + 1
        if next_issue > 99:
            raise ValueError("automatic issue inference exceeded 99")
        return next_issue, "max-existing-series-visual-plus-one"
    return 1, "first-series-visual"


def fail(message: str) -> int:
    print(f"PUBLIC_ACCOUNT_SERIES_VISUAL_RENDER_FAIL: {message}", file=sys.stderr)
    return 1


def auto_lines(title: str, max_chars: int = 8) -> list[str]:
    if len(title) <= max_chars:
        return [title]
    punctuation = {"，", "。", "？", "！", "：", "；", ","}
    near = round(len(title) / 2)
    split = -1
    for distance in range(5):
        for index in (near - distance, near + distance):
            if 0 < index < len(title) and title[index] in punctuation:
                split = index + 1
                break
        if split > 0:
            break
    if split < 0:
        split = min(max_chars, (len(title) + 1) // 2)
    first, rest = title[:split], title[split:]
    return [first, rest[:max_chars], rest[max_chars:]] if len(rest) > max_chars else [first, rest]


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


def cover_two_lines(title: str) -> list[str]:
    if len(title) <= 12:
        return [title]
    valid = [i for i in range(1, len(title)) if i <= 0.7 * (len(title) - i)
             and not (title[i - 1].isascii() and title[i - 1].isalnum()
                      and title[i].isascii() and title[i].isalnum())]
    punctuation = [i for i in valid if title[i - 1] in "，：；！？,;:"]
    choices = punctuation or valid
    if not choices:
        return [title]
    split = min(choices, key=lambda i: abs(i - len(title) / 3))
    return [title[:split], title[split:]]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--object-id")
    parser.add_argument("--object-dir", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--issue", default="auto")
    parser.add_argument("--visual-revision", default="V0.1")
    parser.add_argument("--article-version", default="current")
    parser.add_argument("--title-version", default="confirmed")
    parser.add_argument("--publish-date", default="unknown")
    parser.add_argument("--title-line", action="append", dest="title_lines")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--delivery-dir", type=Path)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--cover-style", choices=["1", "2"], default="1")
    parser.add_argument("--cover-only", action="store_true")
    parser.add_argument("--square-line", action="append", dest="square_lines")
    parser.add_argument("--brand-label", default="韩叙AI" if INTERNAL else "")
    parser.add_argument("--author", default="韩叙" if INTERNAL else "")
    parser.add_argument("--series-name", default="个人商业系统" if INTERNAL else "")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.cover_style == "2" and not args.cover_only:
        return fail("cover style 2 is cover-only; pass --cover-only")
    if args.cover_style == "2":
        if len(args.brand_label) > 8:
            return fail("brand label must be empty or at most eight characters")
    if not RENDERER.exists() or not NODE_BIN.exists() or not NODE_MODULES.exists():
        return fail("locked V0.7 renderer or bundled Node runtime is missing")
    title = args.title.strip()
    if not title or len(title) > 30:
        return fail("title must contain 1 to 30 characters")
    default_suffix = hashlib.sha256(title.encode("utf-8")).hexdigest()[:8]
    object_id = args.object_id or f"PA-{datetime.now().astimezone():%Y-%m-%d}-VISUAL-{default_suffix}"
    if not re.fullmatch(r"[A-Za-z0-9._-]+", object_id):
        return fail("object id contains unsupported characters")
    issue_source = "not-applicable-cover-two" if args.cover_style == "2" else "explicit"
    if args.cover_style == "2":
        issue = None
    elif str(args.issue).lower() == "auto":
        try:
            issue, issue_source = infer_issue((ROOT / "working-files/content-production" if INTERNAL else (args.output_dir or args.delivery_dir or Path.cwd() / "outputs")), object_id)
        except ValueError as exc:
            return fail(str(exc))
    else:
        try:
            issue = int(args.issue)
        except ValueError:
            return fail("issue must be auto or an integer between 1 and 99")
    if issue is not None and not 1 <= issue <= 99:
        return fail("issue must be between 1 and 99")
    if not re.fullmatch(r"V\d+\.\d+", args.visual_revision):
        return fail("visual revision must look like V0.4")
    automatic_lines = cover_two_lines(title) if args.cover_style == "2" else auto_lines(title)
    lines = [line.strip() for line in (args.title_lines or automatic_lines) if line.strip()]
    if args.cover_style == "1" and not args.title_lines and (len(lines) > 3 or any(len(line) > 10 for line in lines)):
        width = (len(title) + 2) // 3
        lines = [title[i:i + width] for i in range(0, len(title), width)]
    if "".join(lines) != title:
        return fail("title lines must reproduce the title exactly")
    if args.cover_style == "2" and (len(lines) > 2 or (len(lines) == 2 and len(lines[0]) > 0.7 * len(lines[1]))):
        return fail("cover two requires at most two lines; first line must be visibly shorter (at most 70% of second)")
    if args.cover_style == "1" and (len(lines) > 3 or any(len(line) > 10 for line in lines)):
        return fail("locked template supports at most three lines and ten characters per line")
    square_lines = []
    if args.cover_style == "2":
        square_lines = [line.strip() for line in (args.square_lines or ([title] if len(title) <= 8 else []))]
        if not 1 <= len(square_lines) <= 2 or any(not line or len(line) > 8 for line in square_lines):
            return fail("cover two needs one or two concise topic lines, each 1 to 8 characters; use --square-line")

    object_dir = (args.object_dir or (Path("working-files/content-production") if INTERNAL else Path.cwd() / "outputs") / object_id).expanduser()
    if not object_dir.is_absolute():
        object_dir = ROOT / object_dir
    object_dir = object_dir.resolve()
    object_dir.mkdir(parents=True, exist_ok=True)
    revision_slug = args.visual_revision.lower()
    output_dir = args.output_dir.expanduser() if args.output_dir else object_dir / f"series-visuals-{revision_slug}"
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir = output_dir.resolve()
    renders_dir = output_dir / "renders"
    if output_dir.exists() and any(output_dir.iterdir()) and not args.replace:
        return fail(f"output already exists; increment revision or pass --replace: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    renders_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "contentObjectId": object_id,
        "articleVersion": args.article_version,
        "titleVersion": args.title_version,
        "visualRevision": args.visual_revision,
        "seriesName": args.series_name if args.cover_style == "1" else None,
        "issueNumber": f"{issue:02d}" if issue is not None else None,
        "title": title,
        "titleLines": lines,
        "author": args.author if args.cover_style == "1" else None,
        "plannedPublishDate": args.publish_date,
        "coverStyle": args.cover_style,
        "coverOnly": args.cover_only,
        **({"squareLines": square_lines, "brandLabel": args.brand_label} if args.cover_style == "2" else {}),
    }
    config_path = output_dir / "config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    env = os.environ.copy()
    env["NODE_PATH"] = str(NODE_MODULES)
    env["PA_SERIES_OUTPUT_DIR"] = str(renders_dir)
    completed = subprocess.run(
        [str(NODE_BIN), str(RENDERER), str(config_path)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        return fail(f"renderer exit={completed.returncode}: {completed.stderr.strip() or completed.stdout.strip()}")

    stem = f"{object_id}-S{issue:02d}-{args.visual_revision}" if issue is not None else f"{object_id}-COVER2-{args.visual_revision}"
    outputs: list[dict[str, object]] = []
    expected = {k: v for k, v in EXPECTED_DIMENSIONS.items() if not args.cover_only or not k.startswith("article-header")}
    for role, dimensions in expected.items():
        png_path = renders_dir / f"{stem}-{role}.png"
        svg_path = renders_dir / f"{stem}-{role}.svg"
        if not png_path.exists() or not svg_path.exists():
            return fail(f"missing paired output for {role}")
        actual_dimensions = png_dimensions(png_path)
        if actual_dimensions != dimensions:
            return fail(f"dimension mismatch role={role} expected={dimensions} actual={actual_dimensions}")
        outputs.append(
            {
                "role": role,
                "png": relative_or_absolute(png_path),
                "svg": relative_or_absolute(svg_path),
                "width": dimensions[0],
                "height": dimensions[1],
                "sha256": sha256(png_path),
                "bytes": png_path.stat().st_size,
            }
        )

    cover_svg = (renders_dir / f"{stem}-message-list-crop-900x383.svg").read_text(encoding="utf-8")
    header_svg = "" if args.cover_only else (renders_dir / f"{stem}-article-header-1080x120.svg").read_text(encoding="utf-8")
    title_nodes = ET.fromstring(cover_svg).findall("{http://www.w3.org/2000/svg}text")
    rendered_lines = ["".join(node.itertext()) for node in title_nodes if node.get("class") == "title"]
    if rendered_lines != lines:
        return fail("rendered cover SVG does not contain every locked title line")
    if issue is not None:
        issue_label = f"第{issue:02d}篇"
        if issue_label not in cover_svg or (not args.cover_only and issue_label not in header_svg):
            return fail("rendered visual does not contain the locked issue number")
    else:
        square_svg = (renders_dir / f"{stem}-square-crop-383x383.svg").read_text(encoding="utf-8")
        square_tree = ET.fromstring(square_svg)
        caption_nodes = square_tree.findall(".//{http://www.w3.org/2000/svg}text")
        caption_text = ["".join(node.itertext()) for node in caption_nodes]
        left_labels = ["".join(node.itertext()) for node in title_nodes if node.get("class") == "brand-label"]
        if len(title_nodes) != len(lines) + bool(args.brand_label) or left_labels != ([args.brand_label] if args.brand_label else []):
            return fail("cover two left panel requires exact title and optional small brand label")
        if caption_text != square_lines or square_tree.findall(".//{http://www.w3.org/2000/svg}image"):
            return fail("cover two square panel requires exact topic lines and no portrait")

    report = {
        "status": "PRODUCTION_COMPLETE_PENDING_WORKFLOW_ACCEPTANCE",
        "profile": "LOCKED_TEMPLATE_RENDER",
        "template": relative_or_absolute(TEMPLATE_DIR),
        "templateVersion": "V0.7" if args.cover_style == "1" else "COVER2-V1.5",
        "coverName": "封面一" if args.cover_style == "1" else "封面二",
        "coverOnly": args.cover_only,
        "rendererSha256": sha256(RENDERER),
        "objectId": object_id,
        "title": title,
        "titleLines": lines,
        "issue": f"{issue:02d}" if issue is not None else None,
        "issueSource": issue_source,
        "visualRevision": args.visual_revision,
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "checks": {
            "titleExact": "PASS",
            "issueExact": "PASS" if issue is not None else "NOT_APPLICABLE",
            **({"titleAndSmallLeftBrand": "PASS", "squareTopicExact": "PASS", "squarePortraitAbsent": "PASS", "twoLineUpperShorter": "PASS"} if issue is None else {}),
            "pairedPngSvg": "PASS",
            "dimensions": "PASS",
            "filesReadable": "PASS",
        },
        "outputs": outputs,
        **({"squareLines": square_lines, "brandLabel": args.brand_label,
             "design": {"maxTitleFontPx": 46, "brandFontPx": 18, "brandPosition": "above-left-title", "squareTopicMaxFontPx": 62, "squareTextAlignment": "horizontal-and-vertical-center", "rightPanelWidthPx": 383},
             "cropRegions": {"messageList": {"x": 0, "y": 0, "width": 900, "height": 383, "ratio": "2.35:1"},
                             "shareAndHome": {"x": 900, "y": 0, "width": 383, "height": 383, "ratio": "1:1"}}} if issue is None else {}),
    }
    report_path = output_dir / "render-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readme_lines = [
        f"# {object_id}｜公众号系列视觉{args.visual_revision}",
        "",
        "- 生产模式：`LOCKED_TEMPLATE_RENDER`",
        f"- 固定母版：`{report['templateVersion']}`（{report['coverName']}）",
        "- 当前状态：`生产完成待工作流验收`",
        f"- 标题：`{title}`",
        f"- 系列编号：`{issue:02d}`（{issue_source}）" if issue is not None else "- 封面二无系列名、作者名或篇数，不分配期数。",
        f"- 配置：`{config_path.name}`",
        f"- 机器检查：`{report_path.name}`",
        "",
        "## 输出",
        "",
    ]
    for output in outputs:
        readme_lines.append(
            f"- `{Path(str(output['png'])).name}`｜{output['width']}×{output['height']}｜SHA-256 `{output['sha256']}`"
        )
    readme_lines.extend(
        [
            "",
            "本目录由锁定母版快速渲染工具一次生成。不得在本次任务中重新设计母版；最终成品仍须按公众号发布准备执行标准验收。",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")

    if args.delivery_dir:
        delivery_dir = args.delivery_dir.expanduser()
        if not delivery_dir.is_absolute():
            delivery_dir = ROOT / delivery_dir
        delivery_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            renders_dir / f"{stem}-UPLOAD-MASTER-1283x383.png",
            delivery_dir / (f"{report['coverName']}.png" if args.cover_only else "01-公众号封面图-1283x383.png"),
        )
        if not args.cover_only:
            shutil.copy2(
                renders_dir / f"{stem}-article-header-1080x120.png",
                delivery_dir / "02-正文头图-1080x120.png",
            )
        report["delivery"] = {
            "cover": relative_or_absolute(delivery_dir / (f"{report['coverName']}.png" if args.cover_only else "01-公众号封面图-1283x383.png")),
        }
        if not args.cover_only:
            report["delivery"]["articleHeader"] = relative_or_absolute(delivery_dir / "02-正文头图-1080x120.png")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("PUBLIC_ACCOUNT_SERIES_VISUAL_RENDER_PASS")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
