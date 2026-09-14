# Historical pilot runner.
# Not an active launcher. The current snapshot is frozen; this file preserves the old pilot only.

import json, os, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
key = Path('/Users/guoshaoyang/Desktop/baiyu_autoresearch.ak').read_text().strip()
endpoint = os.environ.get('DEEPSEEK_ENDPOINT','https://api.deepseek.com/chat/completions')
model = os.environ.get('DEEPSEEK_MODEL','deepseek-flash')
prompts = json.loads(Path(__file__).with_name('prompts.json').read_text())
out = Path(__file__).parent/'runs'; out.mkdir(exist_ok=True)
def call(item):
    payload = json.dumps({'model': model, 'messages':[{'role':'user','content':item['prompt']}], 'temperature':0.2, 'max_tokens':7000, 'thinking':{'type':'disabled'}})
    try:
        cp = subprocess.run(['curl','-sS','--max-time','120',endpoint,'-H','Authorization: Bearer '+key,'-H','Content-Type: application/json','-d',payload],capture_output=True,text=True)
        data=json.loads(cp.stdout)
        rec={'id':item['id'],'role':item['role'],'model':model,'content':data.get('choices',[{}])[0].get('message',{}).get('content',''),'status':'ok'}
        if 'error' in data: rec={'id':item['id'],'role':item['role'],'model':model,'content':'','status':'error','error':str(data['error'])[:300]}
    except Exception as e:
        rec={'id':item['id'],'role':item['role'],'model':model,'content':'','status':'error','error':type(e).__name__+': '+str(e)[:300]}
    (out/(item['id']+'.json')).write_text(json.dumps(rec,ensure_ascii=False,indent=2))
    return rec
with ThreadPoolExecutor(max_workers=int(os.environ.get('WORKERS','5'))) as ex:
    for f in as_completed([ex.submit(call,p) for p in prompts]):
        r=f.result(); print(r['id'],r['status'],r.get('error',''))
