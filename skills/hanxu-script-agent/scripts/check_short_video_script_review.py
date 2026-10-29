#!/usr/bin/env python3
"""Validate a source-bound AI/human body review, not literary quality itself.

The reviewer evaluates meaning. This tool verifies exact evidence, paragraph
coverage, revision and rejection handling; it never infers quality from keywords.
Python standard library only; no network, model calls or internal state access.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

STAGES = ('观点立意', '内容结构', '逐字稿')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def proof(path):
    p=Path(path).resolve(strict=True)
    if not p.is_file():raise ValueError('Expected an evidence file')
    return {'path':str(p),'sha256':digest(p)}


def checked_file(ref,base):
    p=Path(ref['path']).expanduser();p=p if p.is_absolute() else base/p
    p=p.resolve(strict=True)
    if not p.is_file() or digest(p)!=ref.get('sha256'):
        raise ValueError('Missing or stale source evidence: '+str(p))
    return p


def body_paragraphs(text):
    """Use the explicit spoken section when present; otherwise input is plain speech."""
    marker=re.search(r'(?m)^## 逐字稿[ \t]*$',text)
    body=text[marker.end():] if marker else text
    if marker:body=re.split(r'(?m)^## ',body,maxsplit=1)[0]
    body=body.strip()
    paragraphs=[p.strip() for p in re.split(r'\n\s*\n',body) if p.strip()]
    if not paragraphs:raise ValueError('Empty spoken body')
    return body,paragraphs


def required_text(value,label):
    if not isinstance(value,str) or not value.strip():raise ValueError('Missing actual review: '+label)
    return value


def quoted(value,text,label):
    value=required_text(value,label)
    if value not in text:raise ValueError('Quote is not in the current spoken body: '+label)


def check(review,base=Path('.')):
    if not isinstance(review,dict):raise ValueError('Review must be a JSON object')
    object_id=required_text(review.get('objectId'),'objectId')
    version=required_text(review.get('version'),'version')
    script=checked_file(review['script'],base)
    body,paragraphs=body_paragraphs(script.read_text(encoding='utf-8-sig'))
    task=review.get('taskType')
    if task not in {'method','explanation','correction','opinion','story'}:
        raise ValueError('Explicit task type required; not every video is a method tutorial')
    findings=[]
    def verdict(row,label):
        if not isinstance(row,dict):raise ValueError('Review item must be an object: '+label)
        state=row.get('verdict')
        if state not in {'pass','fail','unknown'}:raise ValueError('Explicit verdict required: '+label)
        required_text(row.get('reason'),label+'.reason')
        if state!='pass':
            stage=row.get('returnTo')
            if stage not in STAGES:raise ValueError('Return to actual owning stage required: '+label)
            findings.append({'check':label,'verdict':state,'returnTo':stage,'reason':row['reason'],
                             'quote':row.get('quote')})
    opening=review['opening']
    if not isinstance(opening,dict):raise ValueError('Opening review must be an object')
    quoted(opening.get('quote'),body,'opening')
    if not body.startswith(opening['quote']):raise ValueError('Opening evidence must begin at the spoken opening')
    required_text(opening.get('audienceRelation'),'opening.audienceRelation')
    verdict(opening,'opening')
    rows=review['paragraphs']
    if not isinstance(rows,list) or len(rows)!=len(paragraphs):
        raise ValueError('Every spoken paragraph must be reviewed exactly once')
    for i,(row,paragraph) in enumerate(zip(rows,paragraphs),1):
        if not isinstance(row,dict):raise ValueError('Paragraph review must be an object')
        if type(row.get('id')) is not int or row['id']!=i:raise ValueError('Paragraph order/coverage differs')
        quoted(row.get('quote'),paragraph,'paragraph '+str(i))
        required_text(row.get('adds'),'paragraph contribution or justified repetition')
        verdict(row,'paragraph '+str(i))
    gain=review['gain']
    if not isinstance(gain,dict):raise ValueError('Gain review must be an object')
    quoted(gain.get('quote'),body,'gain')
    verdict(gain,'gain')
    if gain['verdict']=='pass':
        if task in {'method','explanation','correction'}:
            for key in ('start','sequence','completion'):
                quoted(gain.get(key),body,'gain.'+key)
        else:
            for key in ('judgment','difference'):
                quoted(gain.get(key),body,'gain.'+key)
    feedback=[]
    for item in review.get('rejections',[]):
        path=checked_file(item['evidence'],base)
        quoted(item.get('quote'),path.read_text(),'rejection evidence')
        if item.get('scriptSha256')!=digest(script):
            raise ValueError('Rejection must identify this exact script; do not veto another revision')
        required_text(item.get('reason'),'rejection reason')
        if item.get('returnTo') not in STAGES:raise ValueError('Rejection owning stage missing')
        feedback.append({'evidence':proof(path),'quote':item['quote']})
        findings.append({'check':'known_author_rejection','verdict':'fail','returnTo':item['returnTo'],
                         'reason':item['reason'],'quote':item['quote']})
    status=('script_review_failed' if any(x['verdict']=='fail' for x in findings) else
            'script_review_unverified' if findings else 'script_review_passed')
    return {'objectId':object_id,'version':version,'script':proof(script),'status':status,
            'paragraphCount':len(paragraphs),'findings':findings,'feedback':feedback,
            'returnTo':min((x['returnTo'] for x in findings),key=STAGES.index) if findings else None,
            'limits':'Reviewer supplies semantic judgments; this tool validates evidence, coverage and current-version consistency. Not author adoption, independent/blind evaluation, audio or platform effectiveness.'}


def require_pass(report_path,script_path,object_id,version):
    report=json.loads(Path(report_path).read_text())
    if not isinstance(report,dict):raise ValueError('Review report must be an object')
    if report.get('toolSha256')!=digest(__file__):raise ValueError('Script reviewer checker changed; rerun check')
    ref=report['reviewInput'];p=checked_file(ref,Path(report_path).resolve().parent)
    result=check(json.loads(p.read_text()),p.parent)
    if (result['objectId']!=object_id or result['version']!=version or
            Path(result['script']['path'])!=Path(script_path).resolve(strict=True)):
        raise ValueError('Script review object/version/file mismatch')
    if result['status']!='script_review_passed':
        raise ValueError(result['status']+'; returnTo='+str(result['returnTo']))
    if report.get('status')!=result['status'] or report.get('script')!=result['script']:
        raise ValueError('Stored report is not the current script review result')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--review',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();result=None
    if a.output.resolve()==a.review.resolve():
        print(json.dumps({'status':'script_review_invalid','error':'Output cannot overwrite review input'}));return 2
    try:
        source=a.review.resolve(strict=True)
        review=json.loads(source.read_text())
        if not isinstance(review,dict):raise ValueError('Review must be a JSON object')
        script=Path(review.get('script',{}).get('path',''))
        script=script if script.is_absolute() else source.parent/script
        if a.output.resolve() in {source,script.resolve()}:
            print(json.dumps({'status':'script_review_invalid','error':'Output cannot overwrite review input or spoken script'}));return 2
        result=check(review,source.parent)
        result.update(reviewInput=proof(source),toolSha256=digest(__file__),checkedAt=datetime.now(timezone.utc).isoformat())
        code=0 if result['status']=='script_review_passed' else 1
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        result={'status':'script_review_invalid','error':str(exc),'toolSha256':digest(__file__)};code=2
    # Always replace an old green report on invalid input as well as failure.
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False));return code


if __name__=='__main__':raise SystemExit(main())
