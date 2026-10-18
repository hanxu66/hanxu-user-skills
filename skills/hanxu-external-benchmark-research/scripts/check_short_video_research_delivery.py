#!/usr/bin/env python3
"""Check visible research-card coverage; does not verify source truth or delivery."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import re
import sys
from pathlib import Path
DEFAULT_SOURCE = None  # imported only for an explicit internal library check

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'working-files/system-optimization/short-video-workflow-v3/skills/外部对标研究.md'
if not SKILL.exists():
    SKILL = ROOT / 'SKILL.md'
FIELD = re.compile(r'^\*\*(\d+)\. ([^\n]+)\*\*\s*$', re.M)
CARD = re.compile(r'^### (?:对标题面|对标拆解)｜([^｜\n]+)｜([^\n]+)$', re.M)

def check_conclusion(text: str, items: list[dict]) -> list[str]:
    """Check only the frozen visible recommendations, not all background cards."""
    visible = visible_text(text)
    errors = []
    if not items:
        return [] if '没有符合标准的正式候选' in visible else ['缺少0候选结论']
    headings = list(re.finditer(r'^### \d+\. (.+)$', visible, re.M))
    titles = [h.group(1).strip() for h in headings]
    expected = [item['title'] for item in items]
    if titles != expected:
        errors.append('可见推荐题目与本次拟展示清单不符')
    for h, item in zip(headings, items):
        tail = visible[h.end():]
        boundary = re.search(r'^#{1,3}\s', tail, re.M)
        block = tail[:boundary.start()] if boundary else tail
        for label in ['为什么值得写', '准备写什么', '参考']:
            if not re.search(r'\*\*' + label + r'：\*\*\s*\S+', block):
                errors.append(item['title'] + '：缺少' + label)
        for ref in item.get('source_refs', []):
            if ref not in block:
                errors.append(item['title'] + '：缺少实际原作来源')
    return errors

def required_fields(skill_text: str) -> list[tuple[str, str]]:
    start = '<!-- delivery-card-template:start -->'
    end = '<!-- delivery-card-template:end -->'
    if skill_text.count(start) != 1 or skill_text.count(end) != 1:
        raise ValueError('Skill必须包含一份交付模板')
    template = skill_text.split(start, 1)[1].split(end, 1)[0]
    fields = FIELD.findall(template)
    if not fields or len(set(fields)) != len(fields):
        raise ValueError('Skill模板字段为空或重复')
    return fields

def visible_text(text: str) -> str:
    # A pasted template/code example cannot masquerade as delivered cards.
    result, fence = [], None
    for line in text.splitlines():
        stripped = line.lstrip()
        opening = re.match(r'(`{3,}|~{3,})', stripped)
        if fence:
            if re.fullmatch(re.escape(fence[0]) + '{' + str(fence[1]) + r',}\s*', stripped):
                fence = None
            result.append('')
        elif opening:
            run = opening.group(1); fence = (run[0], len(run)); result.append('')
        else:
            result.append(line)
    return '\n'.join(result)

def check(text: str, expected: list[str], fields: list[tuple[str, str]]) -> list[str]:
    errors = []
    if not expected or len(set(expected)) != len(expected):
        errors.append('预期交付清单为空或对象ID重复')
    visible = visible_text(text)
    matches = list(CARD.finditer(visible))
    found = [m.group(1).strip() for m in matches]
    if len(set(found)) != len(found): errors.append('实际回复存在重复对象ID')
    for oid in sorted(set(expected) - set(found)): errors.append(f'缺少整张拆解卡：{oid}')
    for oid in sorted(set(found) - set(expected)): errors.append(f'卡片未列入交付清单：{oid}')
    for m in matches:
        oid = m.group(1).strip()
        tail = visible[m.end():]
        boundary = re.search(r'^#{1,3}\s', tail, re.M)
        block = tail[:boundary.start()] if boundary else tail
        sections = list(FIELD.finditer(block))
        actual = [(x.group(1), x.group(2)) for x in sections]
        if actual != fields:
            errors.append(f'{oid}：字段缺失、重复、顺序或名称不符；实际={actual}')
        for i, sec in enumerate(sections):
            body = block[sec.end():sections[i+1].start() if i+1<len(sections) else len(block)].strip()
            if not body or body in {'待填','待填写','TODO','TBD','未验证','未知','—','-'} or re.fullmatch(r'\{[^{}\n]+\}',body):
                errors.append(f'{oid}：{sec.group(2)}为空或只有占位符')
    return errors

def check_library_rows(text: str, expected_ids: list[str], source: Path = DEFAULT_SOURCE) -> list[str]:
    visible = visible_text(text)
    found = re.findall(r'^\|\s*`(SVLIB-[^`|]+)`\s*\|', visible, re.M)
    # Historical deliveries retain their original ID-based receipt. New visible
    # tables omit IDs, so compare their titles against the internal source map.
    if not found:
        if source is None:
            return [f'回复正文缺少选题库行：{oid}' for oid in expected_ids]
        def plain(value):
            value = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', value)
            return re.sub(r'\s+', ' ', value.replace('`', '')).strip()
        titles = {}
        for line in source.read_text(encoding='utf-8').splitlines():
            if not re.match(r'^\|\s*`SVLIB-', line):
                continue
            cells = [c.strip() for c in re.split(r'(?<!\\)\|', line)[1:-1]]
            if len(cells) == 9:
                titles[cells[0].strip('`')] = plain(cells[3])
        expected = Counter(titles[oid] for oid in expected_ids if oid in titles)
        actual = Counter()
        in_library = False
        for line in visible.splitlines():
            if not line.startswith('|'):
                in_library = False
                continue
            cells = [c.strip() for c in re.split(r'(?<!\\)\|', line)[1:-1]]
            if len(cells) == 6 and cells[0] == '题目':
                in_library = True
                continue
            if in_library and len(cells) == 6 and not all(re.fullmatch(r':?-+:?', c) for c in cells):
                actual[plain(cells[0])] += 1
        errors = [f'内部清单缺少主库映射：{oid}' for oid in expected_ids if oid not in titles]
        errors += [f'回复正文缺少选题库题目：{title}' for title, n in (expected - actual).items() for _ in range(n)]
        errors += [f'回复正文出现重复或非主库题目：{title}' for title, n in (actual - expected).items() for _ in range(n)]
        return errors
    errors = [f'回复正文缺少选题库行：{oid}' for oid in expected_ids if oid not in found]
    errors += [f'回复正文重复选题库行：{oid}' for oid in sorted(set(found)) if found.count(oid) > 1]
    errors += [f'回复正文出现非主库选题行：{oid}' for oid in sorted(set(found) - set(expected_ids))]
    return errors

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--file', type=Path, help='兼容旧运行记录中的草稿文件')
    source.add_argument('--stdin', action='store_true', help='从标准输入检查准备发送的完整回复')
    parser.add_argument('--expect', nargs='+', help='详细卡片模式的实际对象ID')
    parser.add_argument('--library-source', type=Path, help='完整找题时提供唯一选题主库，检查回复正文是否列出每一条')
    parser.add_argument('--conclusion-items', type=Path, help='简洁结论的拟展示清单JSON；不检查历史全库的可见覆盖')
    args = parser.parse_args()
    if not args.conclusion_items and not args.expect:
        parser.error('详细卡片模式需要--expect；简洁结论提供--conclusion-items')
    try:
        raw=(sys.stdin.buffer.read() if args.stdin else args.file.read_bytes())
        fields=required_fields(SKILL.read_text(encoding='utf-8'))
        errors=(check_conclusion(raw.decode('utf-8'), json.loads(args.conclusion_items.read_text()))
                if args.conclusion_items else check(raw.decode('utf-8'),args.expect,fields))
        if args.library_source and not args.conclusion_items:
            if SKILL == ROOT / 'SKILL.md':
                library_ids = re.findall(r'^\|\s*`(SVLIB-[^`|]+)`\s*\|', args.library_source.read_text(encoding='utf-8'), re.M)
                if not library_ids:
                    raise ValueError('用户选题库需有实际SVLIB行ID；未提供时只核验题面卡')
            else:
                from render_short_video_topic_library import render
                _, library_ids = render(args.library_source)
            errors += check_library_rows(raw.decode('utf-8'), library_ids, args.library_source)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'FORMAT_ERROR: {exc}\n')
    if errors:
        print('FORMAT_FAIL\n'+'\n'.join('- '+x for x in errors)); return 1
    print('FORMAT_PASS')
    print('sha256='+hashlib.sha256(raw).hexdigest())
    print('仅核验实际草稿的题面卡片与字段；来源真实性、候选质量和消息送达另行核验。')
    return 0

if __name__=='__main__': raise SystemExit(main())
