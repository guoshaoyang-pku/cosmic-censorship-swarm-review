#!/usr/bin/env python3
import json,time,subprocess,datetime,pathlib
ROOT=pathlib.Path('/data3/guoshaoyang/workdir/ai4math-swarm')
OUT=ROOT/'runtime/state/overnight_watch.jsonl'
while True:
    try:
        names=[x.split(':',1)[0] for x in subprocess.check_output(['tmux','ls'],text=True,stderr=subprocess.DEVNULL).splitlines()]
    except Exception:
        names=[]
    def count(prefixes):
        return sum(any(x.startswith(p) for p in prefixes) for x in names)
    controller=count(('cosmic-controller-','astra-controller-cosmic-'))
    leads=count(('cosmic-lead-formulation-','cosmic-lead-literature-','cosmic-lead-numerics-','cosmic-lead-audit-'))
    workers=count(('cosmic-worker-',))
    checkpoints=sorted((ROOT/'runtime/state/checkpoints').glob('ckpt-*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    q=(ROOT/'runtime/state/quota_circuit_until').read_text().strip() if (ROOT/'runtime/state/quota_circuit_until').exists() else None
    record={'ts':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'project_tmux':controller+leads+workers,'controller':controller,'leads':leads,'workers':workers,'quota_until':q,'checkpoint':checkpoints[0].name if checkpoints else None}
    with OUT.open('a') as stream:
        stream.write(json.dumps(record,ensure_ascii=False)+'\n')
    time.sleep(300)
