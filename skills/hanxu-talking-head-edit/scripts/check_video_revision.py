#!/usr/bin/env python3
"""Read-only revision fingerprints, editorial WAV clocks and scoped regressions.

Does not edit media/apps, infer semantic correctness or certify listening.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import wave


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def pairs(values):
    result = {}
    for value in values:
        role, separator, raw = value.partition('=')
        if not separator or not role.strip() or not raw or role in result:
            raise ValueError('Use unique role=path inputs')
        path = Path(raw).expanduser().resolve(strict=True)
        if not path.is_file():
            raise ValueError('Inputs must be readable files')
        result[role] = {'path': str(path), 'sha256': digest(path)}
    return result


def snapshot(revision, inputs, sources):
    if not revision.strip() or not sources or not inputs:
        raise ValueError('Revision, source files and inputs are required')
    if 'timeline_check' in inputs:
        check = read(inputs['timeline_check']['path'])
        if check.get('status') != 'timeline_checks_complete' or check.get('errors'):
            raise ValueError('Timeline numeric check has not passed')
        # Bind the actual inputs used by the existing geometry checker, rather
        # than trusting a green report saved before the timeline changed.
        for row in check.get('inputs', {}).values():
            if not isinstance(row, dict) or digest(row['path']) != row['sha256']:
                raise ValueError('Timeline check input is stale')
        if not check.get('inputs'):
            raise ValueError('Timeline check must retain its input hashes')
    return {'schemaVersion': 1, 'revision': revision, 'inputs': inputs, 'sources': sources,
            'status': 'fingerprints_recorded',
            'limits': 'File identity only; semantic decisions, word mapping and listening require separate evidence'}


def current(snapshot_data, input_roles=None):
    roles = list(snapshot_data['inputs']) if input_roles is None else input_roles
    for role in roles:
        if role not in snapshot_data['inputs']:
            raise ValueError('Missing bound input: ' + role)
    rows = list(snapshot_data['sources'].values()) + [snapshot_data['inputs'][k] for k in roles]
    for row in rows:
        if digest(row['path']) != row['sha256']:
            raise ValueError('Bound source/input changed: ' + row['path'])


def audio_check(binding, audio, timeline_check):
    current(binding)
    check_path = Path(timeline_check).resolve(strict=True)
    row = binding['inputs'].get('timeline_check')
    if row is None or digest(check_path) != row['sha256']:
        raise ValueError('Audio must use the bound timeline check')
    check = read(check_path)
    expected = check.get('seconds')
    if check.get('status') != 'timeline_checks_complete' or check.get('errors'):
        raise ValueError('Timeline numeric check has not passed')
    if isinstance(expected, bool) or not isinstance(expected, (int, float)) or not math.isfinite(expected) or expected <= 0:
        raise ValueError('Expected duration must be positive and finite')
    with wave.open(str(audio), 'rb') as stream:
        rate, frames = stream.getframerate(), stream.getnframes()
        channels, width = stream.getnchannels(), stream.getsampwidth()
        if stream.getcomptype() != 'NONE' or rate <= 0 or channels < 1 or width not in (1, 2, 3, 4):
            raise ValueError('A completed uncompressed PCM WAV is required')
        pcm = hashlib.sha256(); total = 0; non_silent = False
        while True:
            block = stream.readframes(65536)
            if not block:
                break
            total += len(block); pcm.update(block)
            # Unsigned PCM8 silence is128; wider PCM silence is all-zero.
            non_silent |= any(value != (128 if width == 1 else 0) for value in block)
    if total != frames * channels * width:
        raise ValueError('Truncated PCM data; keep partial output for recovery')
    actual = frames / rate
    # This is a clock allowance, never a permission to retain speech pauses.
    count = check.get('frames')
    if isinstance(count, bool) or not isinstance(count, (int, float)) or not math.isfinite(count) or count <= 0:
        raise ValueError('Expected frame count must be positive and finite')
    tolerance = expected / count + 1 / rate
    if abs(actual - expected) > tolerance or not non_silent:
        raise ValueError('WAV clock mismatch or fully silent audio')
    return {'status': 'audio_clock_checked', 'revision': binding['revision'],
            'audioSha256': digest(audio), 'pcmSha256': pcm.hexdigest(),
            'frames': frames, 'sampleRate': rate, 'channels': channels, 'pcmBits': width * 8,
            'expectedSeconds': expected, 'actualSeconds': actual, 'durationToleranceSeconds': tolerance,
            'nonSilentPCM': non_silent, 'actualListening': 'NOT_PERFORMED',
            'limits': 'Clock/file binding only; does not prove export origin, speech, seams, gain or final sound quality'}


def compare(before, after, unchanged):
    if not unchanged:
        raise ValueError('Explicit unchanged input roles required')
    # Both snapshots must remain available. Historic files may not be
    # overwritten in place, or they cannot support a regression claim.
    current(before, unchanged); current(after, unchanged)
    changes = []
    if {k: v['sha256'] for k, v in before['sources'].items()} != {k: v['sha256'] for k, v in after['sources'].items()}:
        changes.append('sources')
    for role in unchanged:
        if before['inputs'][role]['sha256'] != after['inputs'][role]['sha256']:
            changes.append(role)
    return {'status': 'unchanged_inputs_checked' if not changes else 'unexpected_changes',
            'expectedUnchanged': unchanged, 'unexpectedChanges': changes,
            'limits': 'Only supplied source/input identities checked; not unprovided tracks, pixels, speech or full effect parity'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    bind = sub.add_parser('snapshot'); bind.add_argument('--revision', required=True)
    bind.add_argument('--input', action='append', default=[]); bind.add_argument('--source', action='append', default=[])
    audio = sub.add_parser('audio'); audio.add_argument('--snapshot', required=True)
    audio.add_argument('--audio', required=True); audio.add_argument('--timeline-check', required=True)
    diff = sub.add_parser('compare'); diff.add_argument('--before', required=True); diff.add_argument('--after', required=True)
    diff.add_argument('--unchanged', action='append', required=True)
    for item in (bind, audio, diff):
        item.add_argument('--output', required=True)
    args = parser.parse_args(); output = Path(args.output)
    if output.exists():
        raise FileExistsError('Use a new evidence path; existing results are preserved')
    try:
        if args.command == 'snapshot':
            result = snapshot(args.revision, pairs(args.input), pairs(args.source))
        elif args.command == 'audio':
            result = audio_check(read(args.snapshot), Path(args.audio), args.timeline_check)
        else:
            result = compare(read(args.before), read(args.after), args.unchanged)
    except (ValueError, OSError, EOFError, KeyError, TypeError, wave.Error) as error:
        result = {'status': 'check_failed', 'error': str(error)}
    result['toolSha256'] = digest(__file__)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('inputs', 'sources')}, ensure_ascii=False))
    return 0 if result['status'] in ('fingerprints_recorded', 'audio_clock_checked', 'unchanged_inputs_checked') else 2


if __name__ == '__main__':
    raise SystemExit(main())
