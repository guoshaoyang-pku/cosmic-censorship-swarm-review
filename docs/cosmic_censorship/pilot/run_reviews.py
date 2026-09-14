import json, os, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
root=Path(__file__).parent
key=Path('/Users/guoshaoyang/Desktop/baiyu_autoresearch.ak').read_text().strip()
endpoint=os.environ.get('DEEPSEEK_ENDPOINT','https://api.deepseek.com/v1/chat/completions')
model=os.environ.get('DEEPSEEK_MODEL','deepseek-flash')
taxonomy=(root/'formulation_taxonomy.yaml').read_text()
draft=(root/'runs/F1.json').read_text()[:4500]
items=json.loads((root/'review_prompts.json').read_text())
out=root/'reviews'; out.mkdir(exist_ok=True)
def run(item):
    prompt=item['prompt']+'\n\nTAXONOMY:\n'+taxonomy+'\n\nDRAFT:\n'+draft
    body=json.dumps({'model':model,'messages':[{'role':'user','content':prompt}], 'temperature':0, 'max_tokens':6000, 'thinking':{'type':'disabled'}})
    p=subprocess.run(['curl','-sS','--max-time','120',endpoint,'-H','Authorization: Bearer '+key,'-H','Content-Type: application/json','-d',body],capture_output=True,text=True)
    try:
        x=json.loads(p.stdout); m=x.get('choices',[{}])[0].get('message',{}); rec={'id':item['id'],'role':item['role'],'content':m.get('content',''),'status':'ok' if m.get('content') else 'error'}
    except Exception as e:
        rec={'id':item['id'],'role':item['role'],'content':'','status':'error','error':str(e),'raw':p.stdout[:500],'stderr':p.stderr[:300]}
    (out/(item['id']+'.json')).write_text(json.dumps(rec,ensure_ascii=False,indent=2)); return rec
with ThreadPoolExecutor(max_workers=4) as ex:
    for f in as_completed([ex.submit(run,x) for x in items]):
        r=f.result(); print(r['id'],r['status'],len(r.get('content','')))
