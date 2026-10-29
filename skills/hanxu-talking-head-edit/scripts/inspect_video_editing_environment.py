#!/usr/bin/env python3
"""Read-only capacity and process observations; never a GUI/quality health test.

Python standard library only. No app control, cleanup, authentication or media
access. A returned process PID does not establish that its window responds.
"""
import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

GIB = 1024 ** 3
STAGE_ROLES = {
    'source_read': {'source'},
    'native_handoff': {'source', 'project', 'cache'},
    'native_export': {'source', 'project', 'cache', 'export'},
    'local_review': {'source', 'cache', 'export'},
}
ROUTE_STAGES = {
    'formal_native': ('source_read', 'native_handoff', 'native_export'),
    'local_review': ('source_read', 'local_review'),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dependencies(plan, base, object_id, revision):
    """Observe declared actual dependencies without creating directories or files.

    A plan's basis is evidence of where paths came from, not a claim that this
    program discovered every asset or opened the native project.
    """
    if not object_id or not revision or (plan.get('objectId'), plan.get('revision')) != (object_id, revision):
        raise ValueError('Dependency plan must match current object and revision')
    route = plan.get('route')
    if route not in ROUTE_STAGES:
        raise ValueError('Explicit formal_native/local_review route required')
    basis = plan.get('basis')
    if not isinstance(basis, list) or not basis:
        raise ValueError('Actual project/configuration path-basis evidence required')
    for item in basis:
        p = Path(item['path']).expanduser()
        p = p if p.is_absolute() else base / p
        if not p.is_file() or digest(p) != item.get('sha256'):
            raise ValueError('Dependency path-basis evidence missing or changed')
    rows = plan.get('paths')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Dependency paths required')
    observations = []
    identifiers = set()
    for item in rows:
        ident = item.get('id')
        role, kind, access = item.get('role'), item.get('kind'), item.get('access')
        if not isinstance(ident, str) or not ident.strip() or ident in identifiers:
            raise ValueError('Unique dependency id required')
        identifiers.add(ident)
        if role not in {'source', 'project', 'cache', 'export'} or kind not in {'file', 'directory'} or access not in {'read', 'readwrite'}:
            raise ValueError('Invalid dependency role, kind or access')
        if role != 'source' and (kind != 'directory' or access != 'readwrite'):
            raise ValueError('Project/cache/export must be existing readwrite directories')
        if role == 'source' and kind != 'file':
            raise ValueError('List each actual source file; a directory is not a source asset')
        if not isinstance(item.get('path'), str) or not item['path'].strip():
            raise ValueError('Explicit dependency path required')
        logical = Path(item['path']).expanduser()
        logical = logical if logical.is_absolute() else base / logical
        row = {'id': ident, 'role': role, 'kind': kind, 'access': access,
               'logicalPath': str(logical), 'status': 'available'}
        try:
            target = logical.resolve(strict=True)
            row['resolvedPath'] = str(target)
            if not (target.is_file() if kind == 'file' else target.is_dir()):
                row['status'] = 'wrong_type'
            elif not os.access(target, os.R_OK | (os.W_OK if access == 'readwrite' else 0)
                               | (os.X_OK if kind == 'directory' else 0)):
                row['status'] = 'access_denied'
        except (OSError, RuntimeError) as exc:
            row['status'] = 'unresolvable'
            row['error'] = type(exc).__name__
        observations.append(row)
    stages = {}
    for stage, roles in STAGE_ROLES.items():
        if stage not in ROUTE_STAGES[route]:
            stages[stage] = {'status': 'not_checked', 'reason': 'Outside requested route'}
            continue
        missing = sorted(roles - {r['role'] for r in observations})
        blocked = [r['id'] for r in observations if r['role'] in roles and r['status'] != 'available']
        stages[stage] = {'status': 'blocked' if missing or blocked else 'paths_available',
                         'missingRoles': missing, 'blockedPaths': blocked}
    return {'objectId': object_id, 'revision': revision, 'route': route,
            'status': 'blocked' if any(v['status'] == 'blocked' for v in stages.values()) else 'paths_available',
            'stages': stages, 'paths': observations,
            'limits': 'Declared path coverage and access observations only; no write probe, native UI/project readiness, capacity guarantee or automatic repair'}


def require_dependency_report(path, object_id, revision, stage, project_path):
    """Recheck current inputs; local-only or stale evidence cannot bind native work."""
    report = json.loads(Path(path).read_text())
    if report.get('dependencyToolSha256') != digest(__file__):
        raise ValueError('Dependency checker changed; rerun preflight')
    ref = report['dependencyPlan']
    if digest(ref['path']) != ref['sha256']:
        raise ValueError('Dependency plan changed; rerun preflight')
    f = Path(ref['path'])
    current = dependencies(json.loads(f.read_text()), f.parent, object_id, revision)
    if current['stages'].get(stage, {}).get('status') != 'paths_available':
        raise ValueError('Current dependency stage is blocked or not checked: ' + stage)
    # A shortfall on a separate export volume must not block an otherwise
    # available handoff. Recheck only this stage's actual writable volumes.
    for row in current['paths']:
        if row['role'] not in STAGE_ROLES[stage] or row['kind'] != 'directory':continue
        groups=[v for v in report.get('volumes',[]) if row['resolvedPath'] in v['paths']]
        if not groups or any(shutil.disk_usage(row['resolvedPath']).free < v['requiredBytes'] for v in groups):
            raise ValueError('Current stage capacity unavailable or insufficient')
    projects = [r['resolvedPath'] for r in current['paths'] if r['role'] == 'project' and r['status'] == 'available']
    if str(Path(project_path).resolve(strict=True)) not in projects:
        raise ValueError('Native project is not covered by dependency plan')
    return current


def nonnegative(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("must be a finite nonnegative number")
    return number


def capacity(paths, min_free_gib, reserve_gib):
    """Check every actual target volume; do not sum space across volumes."""
    required = math.ceil((min_free_gib + reserve_gib) * GIB)
    volumes = {}
    for raw in paths:
        path = Path(raw).expanduser().resolve(strict=True)
        if not path.is_dir():
            raise ValueError(f"Expected existing directory: {path}")
        device = path.stat().st_dev
        if device not in volumes:
            usage = shutil.disk_usage(path)
            volumes[device] = {"device": device, "paths": [],
                               "freeBytes": usage.free, "requiredBytes": required,
                               "sufficient": usage.free >= required}
        volumes[device]["paths"].append(str(path))
    return list(volumes.values())


def observation(argv):
    try:
        result = subprocess.run(argv, capture_output=True, text=True,
                                timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "reason": type(exc).__name__}
    if result.returncode:
        return {"status": "unavailable", "returncode": result.returncode}
    return {"status": "observed", "value": result.stdout.strip()}


def app_observation():
    result = observation(["ps", "-axo", "pid=,rss=,comm="])
    if result["status"] != "observed":
        return result
    apps = []
    for line in result["value"].splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) != 3:
            continue
        name = Path(fields[2]).name
        if name not in {"JianyingPro", "VideoFusion-macOS", "CapCut", "ChatCut", "QuickTime Player"}:
            continue
        try:
            apps.append({"pid": int(fields[0]), "rssKiB": int(fields[1]),
                         "name": name})
        except ValueError:
            continue
    return {"status": "observed", "apps": apps,
            "windowResponsiveness": "not_tested"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", action="append", default=[],
                        help="Existing system/cache/export directory; repeat for volumes")
    parser.add_argument("--min-free-gb", type=nonnegative, default=5,
                        help="GiB floor, default 5; configurable capacity budget, not app guarantee")
    estimates = parser.add_mutually_exclusive_group()
    estimates.add_argument("--reserve-gb", type=nonnegative, default=0,
                        help="Additional estimated remaining output/cache GiB per volume")
    estimates.add_argument("--budget-plan", type=Path,
                          help="Explicit per-volume native/remux/retry/temp remaining-work JSON")
    parser.add_argument('--dependency-plan', type=Path,
                        help='Current object path roles and real configuration evidence')
    parser.add_argument('--object-id')
    parser.add_argument('--revision')
    args = parser.parse_args()
    if not args.path and not args.dependency_plan:
        parser.error('--path or --dependency-plan required')
    dependency_report = None
    dependency_ref = None
    try:
        if args.dependency_plan:
            dep_file = args.dependency_plan.resolve(strict=True)
            dependency_report = dependencies(json.loads(dep_file.read_text()), dep_file.parent,
                                             args.object_id, args.revision)
            dependency_ref = {'path': str(dep_file), 'sha256': digest(dep_file)}
        budget_report = None
        paths = list(args.path)
        if dependency_report:
            roles=set().union(*(STAGE_ROLES[s] for s in ROUTE_STAGES[dependency_report['route']]))
            paths += [r['logicalPath'] for r in dependency_report['paths']
                      if r['status'] == 'available' and r['kind'] == 'directory' and r['role'] in roles]
        if not paths:
            raise ValueError('No available directory for capacity observation')
        if args.budget_plan:
            from manage_video_editing_run import budget
            plan = args.budget_plan.resolve()
            budget_report = budget(json.loads(plan.read_text()), plan.parent,
                                   extra_paths=paths, minimum_gib=args.min_free_gb)
            volumes = budget_report['volumes']
        else:
            volumes = capacity(paths, args.min_free_gb, args.reserve_gb)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print(json.dumps({"capacityStatus": "unknown", "error": str(exc),
                          'dependencies': dependency_report, 'applicationHealth': 'not_tested'}))
        return 1
    sufficient = all(item["sufficient"] for item in volumes)
    report = {"observedAt": datetime.now(timezone.utc).isoformat(),
              "capacityStatus": "sufficient" if sufficient else "insufficient",
              "minFreeGiB": args.min_free_gb, "reserveGiB": None if budget_report else args.reserve_gb,
              "remainingWorkEstimateProvided": bool(budget_report) or args.reserve_gb > 0,
              "volumes": volumes, "processes": app_observation(),
              "applicationHealth": "not_tested"}
    report['dependencies'] = dependency_report or {'status': 'not_checked', 'reason': 'Capacity-only call'}
    if dependency_ref:
        report['dependencyPlan'] = dependency_ref
        report['dependencyToolSha256'] = digest(__file__)
    if budget_report:
        report['remainingWorkBudget'] = budget_report
    if platform.system() == "Darwin":
        report["swap"] = observation(["sysctl", "vm.swapusage"])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if sufficient and (not dependency_report or dependency_report['status'] != 'blocked') else 2


if __name__ == "__main__":
    raise SystemExit(main())
