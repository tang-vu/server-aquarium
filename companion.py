import datetime, json, math, re, subprocess
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from hardware import collect_hardware, memory_usage

ROOT = Path(__file__).resolve().parent
PS = ['docker','ps','--all','--filter','label=com.docker.compose.project=ods','--format','{{json .}}']
STATS = ['docker','stats','--no-stream','--format','{{json .}}']

def percent(value, limit=None):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?%',value):
        return None
    number = float(value[:-1])
    return number if math.isfinite(number) and (limit is None or number <= limit) else None

def collect(runner=None):
    runner = runner or subprocess.run
    def run(argv):
        result = runner(argv,shell=False,capture_output=True,text=True,timeout=8)
        if result.returncode != 0: raise RuntimeError('Docker is unavailable')
        rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        if any(not isinstance(row,dict) for row in rows): raise ValueError('Invalid Docker response')
        return rows
    rows = run(PS)
    services, seen_ids, seen_names = [], set(), set()
    for row in rows:
        name, identity = row.get('Names',''), row.get('ID','')
        if not isinstance(name,str) or not re.fullmatch(r'ods-[a-zA-Z0-9][a-zA-Z0-9_.-]*',name): continue
        if not isinstance(identity,str) or not re.fullmatch(r'[a-fA-F0-9]{12,64}',identity):
            raise ValueError('Invalid container identity')
        if identity in seen_ids or name in seen_names: raise ValueError('Duplicate container identity')
        seen_ids.add(identity); seen_names.add(name)
        status = row.get('Status','')
        if not isinstance(status,str): raise ValueError('Invalid container status')
        health = 'not-configured'
        for marker,label in [('(unhealthy)','unhealthy'),('(healthy)','healthy'),('(health: starting)','starting')]:
            if marker in status: health = label; break
        state = row.get('State','unknown')
        if not isinstance(state,str): state = 'unknown'
        services.append(dict(id=identity,name=name,state=state,health=health,cpu=None,mem=None))
    if len(services)>64: raise ValueError('More than 64 ODS services')
    running = {s['id']:s for s in services if s['state']=='running'}
    warning = None
    if running:
        try:
            samples = run(STATS + list(running))
            matched = set()
            values = {}
            for sample in samples:
                identity = sample.get('ID') or sample.get('Container')
                if identity not in running: continue
                if identity in matched: raise ValueError('Duplicate resource sample')
                matched.add(identity)
                values[identity] = (percent(sample.get('CPUPerc')),percent(sample.get('MemPerc'),100),*memory_usage(sample.get('MemUsage')))
            for identity,(cpu,mem,used,limit) in values.items():
                running[identity].update(cpu=cpu,mem=mem,memUsedBytes=used,memLimitBytes=limit)
            if len(matched)!=len(running): warning='Some resource samples are unavailable'
        except Exception:
            warning = 'Resource samples unavailable'
    return dict(source='docker',sampledAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                services=sorted(services,key=lambda s:s['name']),warning=warning)

def make_server(port=4317,collector=None,hardware_collector=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def allowed(self):
            port=self.server.server_port
            hosts={f'127.0.0.1:{port}',f'localhost:{port}'}
            origins={'http://'+host for host in hosts}
            return self.headers.get('Host') in hosts and (self.headers.get('Origin') is None or self.headers.get('Origin') in origins)
        def send(self,code,data,content_type='application/json; charset=utf-8'):
            if not isinstance(data,bytes): data=json.dumps(data,allow_nan=False).encode()
            self.send_response(code)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            try:
                self.end_headers()
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                return
        def do_GET(self):
            if not self.allowed(): return self.send(403,{'error':'Local same-origin requests only'})
            path=urlsplit(self.path).path
            if path=='/api/telemetry':
                try: return self.send(200,self.server.collector())
                except Exception: return self.send(503,{'error':'Docker telemetry unavailable. Check Docker Desktop and ODS containers.'})
            if path=='/api/hardware':
                try: return self.send(200,self.server.hardware_collector())
                except Exception: return self.send(503,{'error':'Hardware telemetry unavailable.'})
            files={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/telemetry.js':'telemetry.js','/styles.css':'styles.css','/aquarium-art.js':'aquarium-art.js','/aquarium-scene.js':'aquarium-scene.js','/recording.js':'recording.js','/hardware.js':'hardware.js','/demo.js':'demo.js'}
            name=files.get(path)
            if name is None: return self.send(404,{'error':'Not found'})
            file=ROOT/name
            if file.is_symlink() or not file.is_file(): return self.send(404,{'error':'Not found'})
            mime={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'application/javascript; charset=utf-8'}[file.suffix]
            return self.send(200,file.read_bytes(),mime)
        def refuse(self):
            return self.send(405 if self.allowed() else 403,{'error':'Read-only companion'})
        do_POST=do_PUT=do_DELETE=do_OPTIONS=refuse
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.collector=collector or collect
    server.hardware_collector=hardware_collector or collect_hardware
    server.daemon_threads=True
    return server

if __name__=='__main__':
    with make_server() as server:
        print('Server Aquarium: http://127.0.0.1:4317 (read-only Docker telemetry)',flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
