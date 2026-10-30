"""Test published package bytes and checker CLI, without an AI app or model.

All author text is synthetic. This does not test Codex/WorkBuddy discovery,
writing quality, personal style, audio or adoption. No external API is used.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_package(repo, package):
    archive = repo / 'packages/hanxu-script-agent.zip'
    sums = dict(line.split(maxsplit=1)[::-1] for line in
                (repo / 'packages/SHA256SUMS.txt').read_text(encoding='utf-8').splitlines())
    assert digest(archive) == sums[archive.name], 'Downloaded package checksum'
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(x.casefold() for x in z.namelist()))
        for name in z.namelist():
            parts = name.split('/')
            assert parts[0] == 'hanxu-script-agent' and '..' not in parts
            assert z.read(name) == (package / Path(*parts[1:])).read_bytes()
    source = json.loads((package / 'SOURCE.json').read_text(encoding='utf-8'))
    for rel, sha in source['package_files'].items():
        assert digest(package / rel) == sha, rel
    for md in package.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', md.read_text(encoding='utf-8')):
            if not target.startswith(('http://', 'https://', '#')):
                rel = urllib.parse.unquote(target.split('#')[0].strip('<>'))
                assert (md.parent / rel).exists(), (md.name, rel)
    assert (package / 'SKILL.md').read_text(encoding='utf-8').startswith('---\nname: hanxu-script-agent\n')
    return source['version'], digest(archive)


def run_checks(package, root):
    # This is a filesystem layout check, not application discovery/install.
    install = root / '中文 项目/.agents/skills/hanxu-script-agent'
    import shutil
    shutil.copytree(package, install)
    tool = install / 'scripts/check_short_video_script_review.py'
    spec = importlib.util.spec_from_file_location('package_checker', tool)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    work = root / '作者 甲/口播试用'
    work.mkdir(parents=True)
    script, review, report = (work / n for n in ['口播稿.md', '正文复核.json', '结果.json'])
    first = '先确认这次包含什么，再安排日期。'
    last = '范围没定时，日期只是预估。'
    body = '# Synthetic fixture\n\n## 逐字稿\n\n' + first + '\n\n' + last + '\n\n## 非口播\n\n后台说明不能代替正文。\n'

    def fixture():
        return {'objectId': 'WINDOWS-PACKAGE', 'version': 'V1', 'taskType': 'opinion',
                'script': {'path': script.name, 'sha256': digest(script)},
                'opening': {'quote': first, 'audienceRelation': 'Synthetic fixture only',
                            'verdict': 'pass', 'reason': 'Tests evidence references only'},
                'paragraphs': [{'id': i, 'quote': p, 'adds': 'Synthetic contribution',
                                'verdict': 'pass', 'reason': 'Tests coverage only'}
                               for i, p in enumerate([first, last], 1)],
                'gain': {'quote': last, 'judgment': first, 'difference': last,
                         'verdict': 'pass', 'reason': 'Synthetic review, no semantic validation'}}

    def cli(expected, output=report):
        env = os.environ.copy()
        env.update(PYTHONUTF8='0', PYTHONIOENCODING='ascii')
        result = subprocess.run([sys.executable, str(tool), '--review', str(review),
                                 '--output', str(output)], cwd=root, env=env, capture_output=True)
        assert result.returncode == expected, (expected, result.returncode, result.stderr)
        printed = json.loads(result.stdout.decode('ascii'))
        if output == report:
            assert printed == json.loads(report.read_text(encoding='utf-8'))
        return printed

    count = 0
    for script_encoding in ['utf-8', 'utf-8-sig', 'utf-16']:
        for review_encoding in ['utf-8', 'utf-8-sig', 'utf-16']:
            script.write_bytes(body.replace('\n', '\r\n').encode(script_encoding))
            review.write_bytes(json.dumps(fixture(), ensure_ascii=False).encode(review_encoding))
            assert cli(0)['paragraphCount'] == 2
            checker.require_pass(report, script, 'WINDOWS-PACKAGE', 'V1')
            count += 1

    # Raw-byte changes must invalidate old evidence, including a BOM-only edit.
    script.write_bytes(body.encode('utf-8'))
    review.write_bytes(json.dumps(fixture(), ensure_ascii=False).encode('utf-8'))
    cli(0)
    script.write_bytes(body.encode('utf-8-sig'))
    try:
        checker.require_pass(report, script, 'WINDOWS-PACKAGE', 'V1')
    except ValueError:
        pass
    else:
        raise AssertionError('Stale report accepted')
    assert cli(2)['status'] == 'script_review_invalid'
    count += 1

    script.write_bytes(body.encode('utf-8'))
    data = fixture()
    feedback = work / '本人反馈.txt'
    feedback.write_bytes('这句不是我的意思。\r\n'.encode('utf-16'))
    data['rejections'] = [{'evidence': {'path': feedback.name, 'sha256': digest(feedback)},
                           'quote': '这句不是我的意思。', 'scriptSha256': digest(script),
                           'reason': 'Synthetic explicit rejection', 'returnTo': '观点立意'}]
    review.write_bytes(json.dumps(data, ensure_ascii=False).encode('utf-8-sig'))
    assert cli(1)['returnTo'] == '观点立意'
    count += 1

    before = script.read_bytes()
    cli(2, output=script)
    assert script.read_bytes() == before, 'Checker overwrote source script'
    count += 1

    profile = work / '作者表达记录.md'
    record = '# Synthetic author\n方法建议偏好：你可以先……\n来源：本次虚构反馈。\n'
    profile.write_bytes(record.encode('utf-8'))
    assert profile.read_text(encoding='utf-8') == record
    assert not profile.is_relative_to(install)
    # A fresh process must read the actual saved bytes; this is not LLM memory.
    code = 'from pathlib import Path; import hashlib,sys; print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())'
    got = subprocess.check_output([sys.executable, '-c', code, str(profile)], cwd=root)
    assert got.decode('ascii').strip() == digest(profile)
    count += 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--package-dir', required=True, type=Path)
    parser.add_argument('--require-windows', action='store_true')
    args = parser.parse_args()
    if args.require_windows:
        assert os.name == 'nt', 'This job must actually run on Windows'
    repo = Path.cwd()
    package = args.package_dir.resolve()
    version, sha = verify_package(repo, package)
    with tempfile.TemporaryDirectory(prefix='script-package-') as folder:
        checks = run_checks(package, Path(folder))
    print(json.dumps({'status': 'PASS', 'system': platform.platform(), 'python': platform.python_version(),
                      'packageVersion': version, 'zipSHA256': sha, 'runtimeChecks': checks,
                      'scope': 'Package/layout/encoding/checker/file persistence only; extraction method belongs to caller; no AI-client UI, generation or adoption'}, ensure_ascii=True))


if __name__ == '__main__':
    main()
