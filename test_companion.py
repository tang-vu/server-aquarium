import http.client, json, subprocess, threading, unittest
import companion as c

A='abcdef123456'; B='123456abcdef'; C='aaaabbbbcccc'
PS=['docker','ps','--all','--filter','label=com.docker.compose.project=ods','--format','{{json .}}']
STATS=['docker','stats','--no-stream','--format','{{json .}}']
def row(identity=A,name='ods-test',state='running',status='Up 1 hour (healthy)'):
    return dict(ID=identity,Names=name,State=state,Status=status)
def sample(identity=A,**extra):
    return dict(ID=identity,**extra)
class Fake:
    def __init__(self,ps,stats=(),fail=None): self.ps=ps; self.stats=stats; self.fail=fail; self.calls=[]
    def __call__(self,argv,**kwargs):
        self.calls.append(argv)
        assert kwargs==dict(shell=False,capture_output=True,text=True,timeout=8),kwargs
        assert argv==PS or (argv[:len(STATS)]==STATS and len(argv)>len(STATS)),argv
        if argv[1]==self.fail: return subprocess.CompletedProcess(argv,1,'','private failure')
        items=self.ps if argv[1]=='ps' else self.stats
        return subprocess.CompletedProcess(argv,0,'\n'.join(json.dumps(x) for x in items),'')
class Collection(unittest.TestCase):
    def test_zero_missing_multicore(self):
        f=Fake([row(),row(B,'ods-other')],[sample(C,CPUPerc='99%',MemPerc='99%'),sample(A,CPUPerc='0.00%',MemPerc='0.00%'),sample(B,CPUPerc='250.5%')])
        result={s['id']:s for s in c.collect(f)['services']}
        self.assertEqual(result[A]['cpu'],0);self.assertEqual(result[A]['mem'],0)
        self.assertEqual(result[B]['cpu'],250.5);self.assertIsNone(result[B]['mem'])
        self.assertNotIn(C,result)
    def test_percent_invalid_and_limits(self):
        for value in [None,'','NaN%','inf%','-1%','40','junk4%']:
            self.assertIsNone(c.percent(value))
        self.assertEqual(c.percent('500%'),500);self.assertIsNone(c.percent('101%',100))
    def test_health_and_stopped(self):
        rows=[row(),row(B,'ods-no-check',status='Up 1 hour'),row(C,'ods-stopped',state='exited',status='Exited (0)')]
        f=Fake(rows,[sample(A,CPUPerc='1%',MemPerc='2%')])
        result={s['id']:s for s in c.collect(f)['services']}
        self.assertEqual(result[A]['health'],'healthy');self.assertEqual(result[B]['health'],'not-configured')
        self.assertEqual(result[C]['state'],'exited');self.assertIsNone(result[C]['cpu'])
        self.assertEqual(f.calls[1],STATS+[A,B])
    def test_unhealthy_and_starting(self):
        result=c.collect(Fake([row(status='Up (unhealthy)'),row(B,'ods-start',status='Up (health: starting)')]))
        self.assertEqual({s['health'] for s in result['services']},{'unhealthy','starting'})
    def test_empty_and_exited_avoid_stats(self):
        for rows in [[],[row(state='exited')],[row(name='other-project')]]:
            f=Fake(rows);result=c.collect(f);self.assertEqual(len(f.calls),1)
    def test_invalid_and_duplicate_identities(self):
        for rows in [[row(identity='--all')],[row(),row()],[row(),row(B)]]:
            with self.subTest(rows=rows),self.assertRaises(ValueError):c.collect(Fake(rows))
    def test_ps_failure(self):
        with self.assertRaises(RuntimeError):c.collect(Fake([row()],fail='ps'))
    def test_stats_failure_retains_state(self):
        result=c.collect(Fake([row()],fail='stats'));service=result['services'][0]
        self.assertEqual(service['state'],'running');self.assertEqual(service['health'],'healthy')
        self.assertIsNone(service['cpu']);self.assertIsNone(service['mem']);self.assertTrue(result['warning'])
    def test_malformed_stats_retains_state(self):
        result=c.collect(Fake([row()],stats=[[]]));self.assertEqual(result['services'][0]['state'],'running');self.assertTrue(result['warning'])
class HTTP(unittest.TestCase):
    def setUp(self):
        self.server=c.make_server(port=0,collector=lambda:dict(source='docker',services=[]))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(2)
    def get(self,path='/',headers=None,method='GET'):
        client=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        client.request(method,path,headers=headers or {});response=client.getresponse();body=response.read();code=response.status;client.close();return code,body
    def test_root_and_json(self):
        self.assertEqual(self.get('/')[0],200)
        code,data=self.get('/api/telemetry');self.assertEqual(code,200);self.assertEqual(json.loads(data)['source'],'docker')
    def test_host_and_origin(self):
        for headers in [{'Host':'foreign.invalid'},{'Host':'127.0.0.1:1'},{'Origin':'https://foreign.invalid'},{'Origin':'null'}]:
            self.assertEqual(self.get('/api/telemetry',headers)[0],403)
        origin=f'http://127.0.0.1:{self.server.server_port}'
        self.assertEqual(self.get('/api/telemetry',{'Origin':origin})[0],200)
    def test_traversal_and_read_only(self):
        for path in ['/../companion.py','/%2e%2e/companion.py','/companion.py','/unknown']:
            self.assertEqual(self.get(path)[0],404)
        for method in ['POST','PUT','DELETE']:self.assertEqual(self.get('/api/telemetry',method=method)[0],405)
    def test_collector_failure(self):
        def broken():raise RuntimeError('private secret error')
        self.server.collector=broken
        code,data=self.get('/api/telemetry');self.assertEqual(code,503);self.assertNotIn(b'private secret',data)
from unittest.mock import Mock
class DisconnectedClient(unittest.TestCase):
    def handler(self):
        server=c.make_server(port=0,collector=lambda:{})
        self.addCleanup(server.server_close)
        h=server.RequestHandlerClass.__new__(server.RequestHandlerClass)
        h.send_response=Mock();h.send_header=Mock();h.end_headers=Mock();h.wfile=Mock()
        return h
    def test_recognized_disconnect_is_terminal(self):
        for error in [BrokenPipeError,ConnectionResetError]:
            for stage in ['headers','body']:
                with self.subTest(error=error,stage=stage):
                    h=self.handler()
                    exc=error('client disconnected')
                    if stage=='headers':
                        h.end_headers.side_effect=exc
                    else:
                        h.wfile.write.side_effect=exc
                    h.send(200,{'ok':True})
                    h.send_response.assert_called_once_with(200)
    def test_unrelated_write_error_surfaces(self):
        h=self.handler();h.wfile.write.side_effect=OSError('unexpected write failure')
        with self.assertRaises(OSError):h.send(200,{'ok':True})

if __name__=='__main__':unittest.main()
