import json,pathlib,html
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=pathlib.Path('/data3/guoshaoyang/workdir/ai4math-swarm'); STATE=ROOT/'runtime/state'
def page():
 try: rs=[json.loads(x) for x in (STATE/'overnight_watch.jsonl').read_text().splitlines()[-60:] if x.strip()]
 except: rs=[]
 c=rs[-1] if rs else {}
 rows='\n'.join(' '.join(str(r.get(k,'-')) for k in ['ts','controller','leads','workers','instances','artifacts','comms']) for r in rs)
 return '<meta charset=utf-8><meta http-equiv=refresh content=30><title>Astra panel</title><body style="font:15px system-ui;background:#101318;color:#e8edf5;margin:24px"><h1>Astra cosmic-censorship runtime</h1><p>localhost-only; isolated project ai4math-swarm; refresh 30s; '+html.escape(c.get('ts','-'))+'</p><h2>controller='+str(c.get('controller','-'))+' leads='+str(c.get('leads','-'))+' workers='+str(c.get('workers','-'))+' instances='+str(c.get('instances','-'))+' artifacts='+str(c.get('artifacts','-'))+' outbox='+str(c.get('comms','-'))+'</h2><p style="color:#ff8b8b">G-FORM/G-F0/G-AUDIT pending; N1 locked while full audit has hard findings.</p><pre>'+html.escape(rows)+'</pre></body>'
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  b=page().encode(); self.send_response(200); self.send_header('Content-Type','text/html'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
 def log_message(self,*a): pass
ThreadingHTTPServer(('127.0.0.1',8503),H).serve_forever()
