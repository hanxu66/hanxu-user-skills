#!/usr/bin/env python3
"""Read-only ChatCut A-roll geometry gate; never edits or controls an editor.

Capture the chosen source ranges BEFORE changing speed. Check the fresh timeline
AND every item's fresh readback afterwards. No language or audible seam verdict.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value, positive=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('Finite numeric field required')
    if positive and value<=0:raise ValueError('Positive value required')
    return value


def entries(snapshot,track):
    rows=[x for x in snapshot['entries'] if x.get('itemType')=='video' and x.get('trackAlias')==track]
    if not rows:raise ValueError('Selected video track is empty')
    ids=[x['id'] for x in rows]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate timeline item IDs')
    return sorted(rows,key=lambda x:number(x['timelineRange']['fromFrame']))


def capture(snapshot,track,fps):
    number(fps,True)
    rows=[]
    for x in entries(snapshot,track):
        start=number(x['sourceRange']['start']);end=number(x['sourceRange']['end'])
        if start<0 or end<=start:raise ValueError('Invalid locked source range')
        rows.append({'id':x['id'],'assetId':x['asset']['id'],'sourceStartUs':start,'sourceEndUs':end})
    return {'status':'source_plan_captured','schemaVersion':1,'track':track,'fps':fps,'items':rows,
            'scope':'Chosen source ranges before speed mutation; capture is not a validation pass'}


def check(snapshot,readbacks,plan,sources,rate):
    number(rate,True);fps=number(plan['fps'],True);rows=entries(snapshot,plan['track'])
    expected={x['id']:x for x in plan['items']}
    if len(expected)!=len(plan['items']):raise ValueError('Duplicate locked plan IDs')
    actual={x['id']:x['data'] for x in readbacks}
    if len(actual)!=len(readbacks):raise ValueError('Duplicate item readback IDs')
    errors=[];reviews=[];checks=[];cursor=0;previous=None
    if set(expected)!={x['id'] for x in rows}:errors.append({'kind':'locked_item_set_changed'})
    for x in rows:
        ident=x['id'];src=x['sourceRange'];t=x['timelineRange'];a=number(src['start']);b=number(src['end'])
        first=number(t['fromFrame']);last=number(t['toFrame']);count=last-first
        item_errors=[]
        if first!=int(first) or last!=int(last) or count<=0:item_errors.append('invalid_frame_range')
        if first!=cursor:item_errors.append('timeline_gap_or_overlap')
        cursor=last
        asset=x['asset']['id'];duration=sources.get(asset)
        if isinstance(duration,dict):duration=duration.get('durationUs')
        if duration is None:item_errors.append('missing_source_duration')
        elif a<0 or b<=a or b>number(duration,True)+1:item_errors.append('source_out_of_bounds')
        rb=actual.get(ident)
        if rb is None:item_errors.append('missing_item_readback')
        else:
            if abs(number(rb['playbackRate'],True)-rate)>1e-8:item_errors.append('playback_rate')
            if rb['startFrame']!=first or rb['durationFrames']!=count:item_errors.append('item_timeline_disagrees')
            if abs(number(rb['sourceIn'])-a)>1:item_errors.append('item_source_start_disagrees')
            if not asset.replace('-','').startswith(str(rb['assetId']).replace('-','')):item_errors.append('item_asset_disagrees')
        if abs((b-a)-count/fps*rate*1e6)>2:item_errors.append('source_span_vs_duration_rate')
        locked=expected.get(ident)
        if locked:
            if locked['assetId']!=asset:item_errors.append('locked_asset_changed')
            if abs(a-locked['sourceStartUs'])>1:item_errors.append('locked_source_start_changed')
            chosen=number(locked['sourceEndUs'])-number(locked['sourceStartUs'])
            if count!=int(math.floor(chosen/1e6/rate*fps+0.5)):item_errors.append('duration_not_retimed')
            drift=b-locked['sourceEndUs']
            if abs(drift)>rate/fps*1e6+2:item_errors.append('locked_source_end_changed')
            elif abs(drift)>2:reviews.append({'id':ident,'kind':'frame_quantized_source_end','deltaUs':drift})
        if count<=3:reviews.append({'id':ident,'kind':'short_fragment','frames':count})
        if previous and previous['asset']['id']==asset:
            overlap=previous['sourceRange']['end']-a
            if overlap>1:reviews.append({'id':ident,'kind':'source_overlap','overlapUs':overlap})
        if item_errors:errors.append({'id':ident,'kinds':item_errors})
        checks.append({'id':ident,'frames':count,'sourceStartUs':a,'sourceEndUs':b,'errors':item_errors})
        previous=x
    return {'status':'timeline_checks_failed' if errors else 'timeline_checks_complete',
            'count':len(rows),'frames':cursor,'seconds':cursor/fps,'targetRate':rate,
            'errors':errors,'boundaryReviewRequired':reviews,'items':checks,
            'limits':'Numeric geometry only; short fragments, quantized edges and overlaps need actual semantic/waveform review. No audible word or seam pass.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('capture','check'):
        q=sub.add_parser(name);q.add_argument('--timeline',required=True);q.add_argument('--output',required=True)
        if name=='capture':q.add_argument('--track',required=True);q.add_argument('--fps',type=float,required=True)
        else:
            for key in ('readbacks','plan','sources'):q.add_argument('--'+key,required=True)
            q.add_argument('--target-rate',required=True,type=float)
    a=p.parse_args()
    try:
        snap=json.loads(Path(a.timeline).read_text())
        if a.command=='capture':
            result=capture(snap,a.track,a.fps);result['timelineSha256']=digest(a.timeline)
        else:
            result=check(snap,*(json.loads(Path(getattr(a,k)).read_text()) for k in ('readbacks','plan','sources')),a.target_rate)
            result['inputs']={k:{'path':str(Path(getattr(a,k)).resolve()),'sha256':digest(getattr(a,k))}
                              for k in ('timeline','readbacks','plan','sources')}
    except (ValueError,OSError,KeyError,TypeError) as e:result={'status':'check_failed','error':str(e)}
    result['toolSha256']=digest(__file__)
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('items','inputs','boundaryReviewRequired')},ensure_ascii=False))
    return 0 if result['status'] in ('timeline_checks_complete','source_plan_captured') else 2


if __name__=='__main__':raise SystemExit(main())
