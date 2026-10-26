import http.client,json,subprocess,threading,unittest
import hardware as h
import companion as c
from test_companion import Fake,row,sample
GiB=1024**3
GPU='0, NVIDIA GeForce RTX 3060, 0, 0, 12288, N/A, [Not Supported]\n'
class Readers:
    def __init__(self,fail_gpu=False,fail_host=False):self.fail_gpu=fail_gpu;self.fail_host=fail_host;self.calls=[]
    def __call__(self,args,**kwargs):
        self.calls.append(args)
        assert kwargs==dict(shell=False,capture_output=True,text=True,timeout=5)
        if args[0]=='nvidia-smi':
            assert args==['nvidia-smi','--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw','--format=csv,noheader,nounits']
            return subprocess.CompletedProcess(args,1 if self.fail_gpu else 0,GPU,'')
        assert len(args)==6 and args[:5]==['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command']
        assert 'Get-CimInstance Win32_OperatingSystem' in args[5]
        return subprocess.CompletedProcess(args,1 if self.fail_host else 0,json.dumps(dict(totalBytes=80*GiB,availableBytes=40*GiB)),'')
class Hardware(unittest.TestCase):
    def test_zero_and_unavailable_gpu_fields(self):
        g=h.parse_gpus(GPU)[0]
        self.assertEqual(g['utilization'],0);self.assertEqual(g['memoryUsedBytes'],0)
        self.assertEqual(g['memoryTotalBytes'],12*GiB);self.assertIsNone(g['temperatureC']);self.assertIsNone(g['powerW'])
    def test_multiple_gpus_and_duplicate_refusal(self):
        text=GPU+'1, Second GPU, 99, 2048, 8192, 65, 150.5\n'
        self.assertEqual(len(h.parse_gpus(text)),2)
        self.assertEqual(h.parse_gpus(text)[1]['memoryUsedBytes'],2*GiB)
        for bad in [GPU+GPU,'broken row\n']:
            with self.assertRaises(ValueError):h.parse_gpus(bad)
    def test_memory_units(self):
        self.assertEqual(h.memory_usage('1.5GiB / 12GiB'),(int(1.5*GiB),12*GiB))
        self.assertEqual(h.memory_usage('0B / 512MiB'),(0,512*1024**2))
        self.assertEqual(h.memory_amount('1 MB'),1000000)
    def test_invalid_memory_is_unknown(self):
        for value in [None,'N/A','-1MiB','NaNMiB','12']:
            self.assertIsNone(h.memory_amount(value))
        self.assertIsNone(h.memory_record(0,0,'RAM'));self.assertIsNone(h.memory_record(10,11,'RAM'))
        self.assertEqual(h.memory_record(10,10,'RAM')['percent'],0)
    def test_wsl_host_and_runtime_are_distinct(self):
        data=h.collect_hardware(runner=Readers(),system='Linux',release='microsoft-WSL2',linux_reader=lambda:(40*GiB,30*GiB))
        self.assertEqual(data['memory']['totalBytes'],80*GiB)
        self.assertEqual(data['memory']['usedBytes'],40*GiB)
        self.assertEqual(data['runtimeMemory']['totalBytes'],40*GiB)
        self.assertEqual(data['runtimeMemory']['usedBytes'],10*GiB)
        self.assertEqual(data['memoryLabel'],'Windows host RAM');self.assertEqual(data['gpuStatus'],'ok')
    def test_wsl_host_failure_never_relabels_runtime(self):
        data=h.collect_hardware(runner=Readers(fail_host=True),system='Linux',release='microsoft',linux_reader=lambda:(40*GiB,30*GiB))
        self.assertIsNone(data['memory']);self.assertEqual(data['runtimeMemory']['totalBytes'],40*GiB)
        self.assertEqual(data['memoryLabel'],'Windows host RAM');self.assertEqual(data['gpuStatus'],'ok');self.assertTrue(data['warnings'])
    def test_gpu_failure_keeps_host_ram(self):
        data=h.collect_hardware(runner=Readers(fail_gpu=True),system='Windows',release='',windows_reader=lambda:(80*GiB,40*GiB))
        self.assertEqual(data['memory']['usedBytes'],40*GiB);self.assertEqual(data['gpus'],[])
        self.assertEqual(data['gpuStatus'],'unavailable')
    def test_windows_memory_source(self):
        reader=Readers();data=h.collect_hardware(runner=reader,system='Windows',release='',windows_reader=lambda:(80*GiB,20*GiB))
        self.assertEqual(data['memory']['usedBytes'],60*GiB);self.assertIsNone(data['runtimeMemory'])
        self.assertEqual(data['gpuStatus'],'ok');self.assertEqual(len(reader.calls),1)
    def test_linux_memory_unknown(self):
        data=h.collect_hardware(runner=Readers(),system='Linux',release='6.8',linux_reader=lambda:(None,None))
        self.assertIsNone(data['memory']);self.assertTrue(data['warnings']);self.assertEqual(data['gpuStatus'],'ok')
    def test_container_ram_bytes(self):
        data=c.collect(Fake([row()],[sample(CPUPerc='0%',MemPerc='12.5%',MemUsage='1.5GiB / 12GiB')]))
        service=data['services'][0]
        self.assertEqual(service['memUsedBytes'],int(1.5*GiB));self.assertEqual(service['memLimitBytes'],12*GiB)
        self.assertEqual(service['mem'],12.5)
class HardwareHTTP(unittest.TestCase):
    def setUp(self):
        def failed_docker():raise RuntimeError('unavailable')
        self.server=c.make_server(port=0,collector=failed_docker,hardware_collector=lambda:dict(source='system',gpus=[],memory=None))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join(2)
    def get(self,path,headers=None,method='GET'):
        client=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        client.request(method,path,headers=headers or {});r=client.getresponse();data=r.read();code=r.status;client.close();return code,data
    def test_endpoint_independent_of_docker(self):
        code,data=self.get('/api/hardware');self.assertEqual(code,200);self.assertEqual(json.loads(data)['source'],'system')
        self.assertEqual(self.get('/api/telemetry')[0],503)
    def test_hardware_host_origin_and_readonly(self):
        for headers in [{'Host':'evil.invalid'},{'Origin':'https://evil.invalid'}]:
            self.assertEqual(self.get('/api/hardware',headers)[0],403)
        self.assertEqual(self.get('/api/hardware',method='POST')[0],405)
if __name__=='__main__':unittest.main()
