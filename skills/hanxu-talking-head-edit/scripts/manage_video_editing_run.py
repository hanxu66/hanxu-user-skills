#!/usr/bin/env python3
"""Evidence checklist, exclusive phase timers and per-volume remaining-work budgets.

Updates only the supplied run record. Never controls apps, deletes files or proves
that an evidence screenshot truthfully represents a native parameter.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

GIB=1024**3
CATEGORIES={'active','wait','rework'}
CHECKS={'speed','voice','beauty','body','grade','subtitles','identity','animation','cover'}


def now():
    return datetime.now(timezone.utc).isoformat()


def positive(value, allow_zero=False):
    n=float(value)
    if isinstance(value,bool) or not math.isfinite(n) or n < 0 or (n==0 and not allow_zero):
        raise ValueError('Invalid estimated quantity')
    return n


def budget(plan, base=Path('.'), extra_paths=(), minimum_gib=5):
    required={'native_export','container_copy','retry_export','temporary'}
    decisions={x['kind'] for x in plan['items']}
    omitted=plan.get('excluded',{})
    if (not required.issubset(decisions|set(omitted)) or decisions&set(omitted)
            or any(not str(v).strip() for v in omitted.values())):
        raise ValueError('Explicit native/container-copy/retry/temporary decisions required')
    groups={};labels=set()
    def directory(raw):
        p=Path(raw).expanduser();p=p if p.is_absolute() else base/p
        p=p.resolve(strict=True)
        if not p.is_dir():raise ValueError('Budget directory must already exist')
        dev=p.stat().st_dev
        if dev not in groups:
            groups[dev]={'device':dev,'paths':[],'freeBytes':shutil.disk_usage(p).free,'estimatedAdditionalBytes':0,'items':[]}
        if str(p) not in groups[dev]['paths']:groups[dev]['paths'].append(str(p))
        return groups[dev]
    for x in plan['items']:
        if not x.get('label') or x['label'] in labels:raise ValueError('Unique budget labels required')
        labels.add(x['label']);g=directory(x['directory'])
        copies=x.get('copies',1)
        if isinstance(copies,bool) or not isinstance(copies,int) or copies<1:raise ValueError('Positive integer copies required')
        if 'bytes' in x:estimate=math.ceil(positive(x['bytes'],True))*copies
        else:estimate=math.ceil(positive(x['duration_seconds'])*(positive(x['video_mbps'])*1e6+positive(x.get('audio_kbps',0),True)*1000)/8)*copies
        if x.get('already_present'):
            p=Path(x['existing_path']);p=p if p.is_absolute() else base/p
            if not p.is_file():raise ValueError('Already-present budget item requires an existing file')
            estimate=0
        g['estimatedAdditionalBytes']+=estimate
        g['items'].append({'label':x['label'],'kind':x['kind'],'bytes':estimate,'alreadyPresent':bool(x.get('already_present'))})
    for path in extra_paths:directory(path)
    floor=math.ceil(positive(minimum_gib,True)*GIB)
    for g in groups.values():
        g['requiredBytes']=floor+g['estimatedAdditionalBytes'];g['shortfallBytes']=max(0,g['requiredBytes']-g['freeBytes']);g['sufficient']=not g['shortfallBytes']
    return {'status':'sufficient' if groups and all(g['sufficient'] for g in groups.values()) else 'insufficient',
            'volumes':list(groups.values()),'excluded':omitted,
            'scope':'remaining physical allocations, separate per volume; no purgeable/clone savings assumed; no cleanup performed'}


def init(record, revision, requirements):
    if set(requirements)!=CHECKS:raise ValueError('Requirements must explicitly cover all nine packaging checks')
    if record.get('revision',revision)!=revision:raise ValueError('Record revision differs')
    existing=record.get('editingExecution')
    if existing and (existing.get('requirements') is not None or existing['revision']!=revision):
        raise ValueError('Checklist exists; invalidate affected keys instead of resetting')
    for key,row in requirements.items():
        if not isinstance(row.get('required'),bool):raise ValueError('required must be boolean')
        if row['required'] and row.get('target') is None:raise ValueError('Required target missing')
        if not row['required'] and not row.get('reason'):raise ValueError('Not-applicable reason missing')
    if not existing:record['editingExecution']=execution(revision)
    record['editingExecution']['requirements']=requirements


def execution(revision):
    return {'revision':revision,'createdAt':now(),'requirements':None,
            'checks':{},'intervals':[],'openTimer':None,'history':[]}


def begin(record,revision,phase,category):
    if record.get('revision',revision)!=revision:raise ValueError('Record revision differs')
    if 'editingExecution' not in record:record['editingExecution']=execution(revision)
    if record['editingExecution']['revision']!=revision:raise ValueError('Execution revision differs')
    timer_start(record,phase,category)


def verify(record,key,actual,evidence,scope):
    e=record['editingExecution'];target=e['requirements'][key]
    if not target['required']:raise ValueError('Cannot verify a not-applicable check')
    if not scope.strip() or not evidence:raise ValueError('Native coverage description and evidence required')
    files=[]
    for path in evidence:
        p=Path(path).resolve(strict=True)
        if not p.is_file():raise ValueError('Evidence must be an existing file')
        files.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    match=actual==target['target']
    e['checks'][key]={'actual':actual,'matchesTarget':match,'scope':scope,'evidence':files,'verifiedAt':now()}
    return match


def checklist(record):
    e=record['editingExecution'];pending=[]
    if e.get('requirements') is None:
        return {'status':'packaging_incomplete','pending':sorted(CHECKS),'reason':'Targets not configured yet; timing may already run'}
    for key,req in e['requirements'].items():
        if not req['required']:continue
        check=e['checks'].get(key,{})
        evidence=check.get('evidence',[])
        valid=check.get('matchesTarget') and check.get('actual')==req['target'] and evidence
        for file in evidence:
            p=Path(file['path'])
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=file['sha256']:valid=False
        if not valid:pending.append(key)
    return {'status':'packaging_record_complete' if not pending else 'packaging_incomplete','pending':pending,
            'limits':'Record completeness only; native UI and visual truth, current capacity, exported file and playback still need their own checks'}


def boot_id():
    """Best-effort reboot boundary; never persist a process-local clock as elapsed time."""
    try:
        if sys.platform=='linux':return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        if sys.platform=='darwin':
            return subprocess.check_output(['/usr/sbin/sysctl','-n','kern.bootsessionuuid'],
                                           stderr=subprocess.DEVNULL,timeout=2).decode().strip() or None
    except (OSError,subprocess.SubprocessError):pass
    return None


def timer_start(record,phase,category):
    e=record['editingExecution']
    if e['openTimer']:raise ValueError('Stop the current interval before starting another; no overlapping totals')
    if category not in CATEGORIES or not phase.strip():raise ValueError('Invalid phase/category')
    e['openTimer']={'phase':phase,'category':category,'startedAt':now(),
                    'clockSource':'utc-wall','pid':os.getpid(),'bootId':boot_id(),
                    'monotonicStart':time.monotonic()}


def timer_stop(record):
    e=record['editingExecution'];opened=e['openTimer']
    if not opened:raise ValueError('No open timer; historical time cannot be reconstructed')
    if opened.get('clockSource')!='utc-wall':
        raise ValueError('Legacy timer is unverified; timer-abandon preserves it without reconstructing history')
    end=now();seconds=(datetime.fromisoformat(end)-datetime.fromisoformat(opened['startedAt'])).total_seconds()
    current_boot=boot_id()
    if seconds<0 or (opened.get('bootId') and current_boot and opened['bootId']!=current_boot):
        raise ValueError('Clock/reboot mismatch; interval remains unverified')
    # Some executors give each child process its own monotonic origin. Compare
    # monotonic only inside the SAME process, never across persisted CLI calls.
    if opened.get('pid')==os.getpid() and abs(time.monotonic()-opened['monotonicStart']-seconds)>5:
        raise ValueError('Clock mismatch within process; interval remains unverified')
    e['intervals'].append({**{k:v for k,v in opened.items() if k!='monotonicStart'},
                          'endedAt':end,'seconds':seconds,
                          'clockVerification':'boot-id-matched' if current_boot and opened.get('bootId') else 'boot-id-unavailable'})
    e['openTimer']=None


def timer_abandon(record,reason):
    e=record['editingExecution']
    if not e['openTimer'] or not reason.strip():raise ValueError('Open interval and explicit reason required')
    e.setdefault('unverifiedIntervals',[]).append({**e['openTimer'],'endedAt':now(),
                                                  'reason':reason,'duration':None})
    e['openTimer']=None


def summary(record):
    e=record['editingExecution'];totals={k:None for k in CATEGORIES};phases={}
    for row in e['intervals']:
        cat=row['category'];totals[cat]=(totals[cat] or 0)+row['seconds']
        phases[row['phase']]=phases.get(row['phase'],0)+row['seconds']
    return {'coverageSince':e['createdAt'],'measuredSecondsByCategory':totals,'measuredSecondsByPhase':phases,
            'openInterval':e['openTimer'],'unrecordedHistoricalTime':'unknown, not zero',
            'unverifiedIntervals':e.get('unverifiedIntervals',[]),
            'scope':'exclusive UTC wall intervals; boot boundaries checked when available; cross-process forward wall-clock changes cannot always be detected; machine durations separate, no historical backfill'}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('budget');b.add_argument('--plan',required=True);b.add_argument('--output',required=True);b.add_argument('--min-free-gib',type=float,default=5)
    for name in ['begin','init','verify','invalidate','checklist','timer-start','timer-switch','timer-stop','timer-abandon','summary']:
        q=sub.add_parser(name);q.add_argument('--record',required=True)
        if name=='init':q.add_argument('--revision',required=True);q.add_argument('--requirements',required=True)
        if name=='begin':q.add_argument('--revision',required=True)
        if name=='verify':
            q.add_argument('--key',choices=sorted(CHECKS),required=True);q.add_argument('--actual',required=True);q.add_argument('--evidence',action='append',required=True);q.add_argument('--scope',required=True)
        if name=='invalidate':q.add_argument('--key',choices=sorted(CHECKS),required=True);q.add_argument('--reason',required=True)
        if name in {'begin','timer-start','timer-switch'}:q.add_argument('--phase',required=True);q.add_argument('--category',choices=sorted(CATEGORIES),required=True)
        if name=='timer-abandon':q.add_argument('--reason',required=True)
    a=p.parse_args()
    try:
        if a.command=='budget':
            f=Path(a.plan).resolve();result=budget(json.loads(f.read_text()),f.parent,minimum_gib=a.min_free_gib);Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False));return 0 if result['status']=='sufficient' else 2
        path=Path(a.record);record=json.loads(path.read_text()) if path.exists() else {}
        if a.command=='begin':begin(record,a.revision,a.phase,a.category)
        elif a.command=='init':init(record,a.revision,json.loads(Path(a.requirements).read_text()))
        elif a.command=='verify':verify(record,a.key,json.loads(Path(a.actual).read_text()),a.evidence,a.scope)
        elif a.command=='invalidate':
            e=record['editingExecution'];e['checks'].pop(a.key,None);e['history'].append({'at':now(),'invalidated':a.key,'reason':a.reason})
        elif a.command=='timer-start':timer_start(record,a.phase,a.category)
        elif a.command=='timer-switch':
            timer_stop(record);timer_start(record,a.phase,a.category)
        elif a.command=='timer-stop':timer_stop(record)
        elif a.command=='timer-abandon':timer_abandon(record,a.reason)
        if a.command not in {'checklist','summary'}:
            tmp=path.with_name(path.name+'.tmp');tmp.write_text(json.dumps(record,ensure_ascii=False,indent=2));tmp.replace(path)
        result=summary(record) if a.command in {'summary','begin','timer-start','timer-switch','timer-stop','timer-abandon'} else checklist(record)
        print(json.dumps(result,ensure_ascii=False))
        return 1 if ((a.command=='checklist' and result.get('pending')) or
                     (a.command=='verify' and not record['editingExecution']['checks'][a.key]['matchesTarget'])) else 0
    except (ValueError,OSError,KeyError,TypeError) as error:
        print(json.dumps({'status':'invalid','error':str(error)}));return 2


if __name__=='__main__':raise SystemExit(main())
