#!/usr/bin/env python3
"""Evidence-backed SRT import/reopen journal in the existing run JSON.

This tool returns a next action; it never controls an app, imports, restarts,
reapplies packaging, edits a draft or certifies that an observation is truthful.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from inspect_video_editing_environment import require_dependency_report


def now():return datetime.now(timezone.utc).isoformat()
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def proof(path):
    p=Path(path).resolve(strict=True)
    if not p.is_file():raise ValueError('Evidence must be a file')
    return {'path':str(p),'sha256':digest(p)}
def integer(x):
    if isinstance(x,bool) or not isinstance(x,int) or x<0:raise ValueError('Nonnegative integer required')
    return x


def bind(record,config):
    if 'nativeHandoff' in record:raise ValueError('Binding already exists; reuse it or start a genuine new revision record')
    project=Path(config['projectPath']).resolve(strict=True)
    if not project.is_dir():raise ValueError('Actual saved native project directory required')
    dependency_report=config['dependencyReport']
    require_dependency_report(dependency_report,record.get('objectId'),record['revision'],
                              'native_handoff',project)
    report=json.loads(Path(config['timelineReport']).read_text())
    if report['status']!='timeline_checks_complete':raise ValueError('Passing timeline geometry report required')
    if report.get('toolSha256')!=digest(Path(__file__).with_name('check_video_timeline.py')):
        raise ValueError('Timeline checker version changed; rerun current check')
    if integer(config['expectedFrames'])!=report['frames']:raise ValueError('Duration differs from checked timeline')
    srt=Path(config['srt']).resolve(strict=True);body=srt.read_text(encoding='utf-8-sig')
    stamps=re.findall(r'(?m)^\d+\s*\n(\d\d:\d\d:\d\d,\d{3}) --> (\d\d:\d\d:\d\d,\d{3})',body)
    count=len(stamps)
    if count!=integer(config['expectedCaptionCount']) or count==0:raise ValueError('Expected SRT card count differs')
    inputs=[proof(config['timelineReport']),proof(srt),proof(Path(__file__).with_name('check_video_timeline.py')),
            proof(dependency_report)]
    def milliseconds(stamp):
        h,m,s,ms=map(int,re.split('[:,]',stamp));return ((h*60+m)*60+s)*1000+ms
    previous=0
    for start,end in stamps:
        a,b=milliseconds(start),milliseconds(end)
        if a<previous or b<=a or b>report['seconds']*1000+1:raise ValueError('SRT timing outside checked timeline or overlapping')
        previous=b
    warnings=report.get('boundaryReviewRequired',[])
    if warnings:
        review=json.loads(Path(config['boundaryReview']).read_text())
        if (review['timelineSha256']!=report['inputs']['timeline']['sha256'] or
                not {x['id'] for x in warnings}.issubset(set(review['reviewedItemIds'])) or
                not review.get('note') or not review.get('evidence')):
            raise ValueError('Current short-fragment/overlap boundary review missing')
        inputs.append(proof(config['boundaryReview']))
        inputs.extend(proof(x) for x in review['evidence'])
    for row in report['inputs'].values():
        if digest(row['path'])!=row['sha256']:raise ValueError('Stale timeline input')
        inputs.append(proof(row['path']))
    record['nativeHandoff']={'revision':record['revision'],'projectPath':str(project),
        'expectedFrames':config['expectedFrames'],'expectedCaptionCount':count,
        'dependencyReport':str(Path(dependency_report).resolve(strict=True)),
        'boundAt':now(),'inputs':inputs,'sequence':0,'requests':[],'observations':[]}


def observe(record,value,evidence):
    h=record['nativeHandoff'];value=dict(value)
    if not isinstance(value.get('windowReadable'),bool):raise ValueError('Explicit window readability required')
    if value['windowReadable']:
        if value.get('projectPath') is not None:value['projectPath']=str(Path(value['projectPath']).resolve(strict=True))
        for key in ('durationFrames','captionCount'):
            if value.get(key) is not None:integer(value[key])
        for key in ('captionResourceReady','captionsOnTimeline','saved','resourcesSufficient'):
            if value.get(key) is not None and not isinstance(value[key],bool):raise ValueError('Boolean or explicit unknown required: '+key)
    h['sequence']+=1
    h['observations'].append({'sequence':h['sequence'],'at':now(),'value':value,'evidence':proof(evidence)})


def update_dependencies(record,report):
    """Refresh only dependency evidence on the same saved project, including legacy runs."""
    h=record['nativeHandoff']
    if record['revision']!=h['revision']:raise ValueError('Cannot refresh dependencies across revisions')
    require_dependency_report(report,record.get('objectId'),record['revision'],
                              'native_handoff',h['projectPath'])
    ref=proof(report);previous=h.get('dependencyReport')
    h.setdefault('dependencyHistory',[]).append({'at':now(),'previousReport':previous,'current':ref})
    h['inputs']=[p for p in h['inputs'] if p['path']!=previous]+[ref]
    h['dependencyReport']=ref['path']


def next_action(record):
    h=record['nativeHandoff']
    result={'projectPath':h['projectPath'],'revision':h['revision'],
            'limits':'Journal guidance only; actual UI observation required, no app action performed'}
    def answer(action,reason):return {**result,'action':action,'reason':reason}
    if record['revision']!=h['revision']:return answer('blocked_revision_mismatch','Do not inherit across changed revisions')
    if not Path(h['projectPath']).is_dir():return answer('blocked_missing_project','Bound saved project directory is missing')
    try:
        require_dependency_report(h['dependencyReport'],record.get('objectId'),record['revision'],
                                  'native_handoff',h['projectPath'])
    except (OSError,ValueError,KeyError,TypeError):
        return answer('blocked_dependencies','Run current object dependency preflight; preserve the saved project')
    try:
        if any(digest(x['path'])!=x['sha256'] for x in h['inputs']):
            return answer('blocked_stale_binding','Timeline/SRT changed; do not repeat an old operation')
    except OSError:return answer('blocked_missing_input','Saved checked input is no longer available')
    if not h['observations']:return answer('observe','Read the correct native project before mutations')
    last=h['observations'][-1]
    try:
        if digest(last['evidence']['path'])!=last['evidence']['sha256']:
            return answer('blocked_stale_observation','Observation evidence changed')
    except OSError:return answer('blocked_missing_evidence','Observation evidence missing')
    if h['requests'] and h['requests'][-1]['sequence']>last['sequence']:
        return answer('observe_pending_outcome','An action is already requested; never resend before reading its outcome')
    v=last['value']
    if not v['windowReadable']:return answer('blocked_unreadable_window','Use the existing controlled recovery branch; process existence is insufficient')
    if any(v.get(k) is None for k in ('projectPath','durationFrames','captionCount','captionResourceReady','captionsOnTimeline','saved','resourcesSufficient')):
        return answer('blocked_unknown_state','An actual field is unknown; observe it, never replace unknown with a planned count or zero')
    if v['projectPath']!=h['projectPath']:return answer('blocked_project_mismatch','Wrong native project; do not import or change parameters')
    if v['durationFrames']!=h['expectedFrames']:return answer('blocked_timeline_mismatch','Read/save the correct timeline; unchanged packaging must not be reset')
    if v['captionCount']==h['expectedCaptionCount'] and v['captionsOnTimeline']:
        return answer('reuse_captions','Existing caption checkpoint is present; continue unfinished packaging only')
    if v['captionCount'] or v['captionsOnTimeline']:
        return answer('blocked_partial_captions','Inspect the partial/different track; do not add a second full SRT')
    if not v['resourcesSufficient']:return answer('blocked_resources','Keep checkpoint; no import/restart until the remaining allocation budget passes')
    requested=[x['action'] for x in h['requests']]
    if not v['captionResourceReady']:
        return answer('blocked_resource_import','SRT resource import already attempted; inspect its result') if 'import-resource' in requested else answer('import-resource','Import this exact bound SRT resource once')
    additions=[x for x in h['requests'] if x['action']=='add-captions']
    reopens=[x for x in h['requests'] if x['action']=='reopen']
    if not additions:return answer('add-captions','Resource is ready and actual timeline is empty; add once')
    if not reopens:
        if not v['saved']:return answer('save_checkpoint','Confirm native save before any recovery request')
        return answer('reopen','Known add failure and saved correct project; reopen this same project once')
    if additions[-1]['sequence']<reopens[-1]['sequence']:
        return answer('add-captions','Same saved project is readable after one recovery; one new add is allowed')
    return answer('blocked_after_one_recovery','Second add still absent; preserve checkpoint and stop this import branch')


def request(record,action):
    decision=next_action(record)
    if decision['action']!=action:raise ValueError('Action refused; next='+decision['action'])
    h=record['nativeHandoff'];h['sequence']+=1
    h['requests'].append({'sequence':h['sequence'],'action':action,'at':now(),
                          'observationSequence':h['observations'][-1]['sequence']})


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('bind','dependencies','observe','next','request'):
        q=sub.add_parser(name);q.add_argument('--record',required=True)
        if name=='bind':q.add_argument('--config',required=True)
        if name=='dependencies':q.add_argument('--report',required=True)
        if name=='observe':q.add_argument('--observation',required=True);q.add_argument('--evidence',required=True)
        if name=='request':q.add_argument('--action',choices=('import-resource','add-captions','reopen'),required=True)
    a=p.parse_args()
    try:
        path=Path(a.record);record=json.loads(path.read_text())
        if a.command=='bind':bind(record,json.loads(Path(a.config).read_text()))
        elif a.command=='dependencies':update_dependencies(record,a.report)
        elif a.command=='observe':observe(record,json.loads(Path(a.observation).read_text()),a.evidence)
        elif a.command=='request':request(record,a.action)
        if a.command!='next':
            tmp=path.with_name(path.name+'.tmp');tmp.write_text(json.dumps(record,ensure_ascii=False,indent=2));tmp.replace(path)
        result=next_action(record);print(json.dumps(result,ensure_ascii=False))
        return 1 if result['action'].startswith('blocked_') else 0
    except (ValueError,OSError,KeyError,TypeError) as e:
        print(json.dumps({'status':'invalid','error':str(e)}));return 2


if __name__=='__main__':raise SystemExit(main())
