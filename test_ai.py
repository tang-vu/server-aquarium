import copy
import http.client
import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ai_bridge import AIEngine, RequestError, loopback_base
from evidence import frames_from, evidence_for, validated_analysis
import companion

def replay():
    return dict(at='2026-10-26T12:00:00Z', source='demo', servicesKnown=True, services=[dict(id='portal', name='Portal', cpu=0, mem=0, state='running', health='simulated', unknown=False, offline=False)], hardware=dict(source='simulated', memory=dict(usedBytes=0, totalBytes=100), gpus=[dict(name='Simulated GPU', utilization=0, memoryUsedBytes=0, memoryTotalBytes=100)]))

def analysis():
    row=dict(text='The supplied moment contains simulated observations.', evidenceIds=['E1'])
    return dict(summary=row, observations=[row], nextChecks=[row])

class EvidenceTests(unittest.TestCase):
    def test_zero_and_unknown_are_distinct(self):
        frame=frames_from([replay()])[0]
        self.assertEqual(frame['services'][0]['cpu'],0)
        self.assertEqual(frame['hardware']['memory']['usedBytes'],0)
        self.assertIn('CPU 0%', '\n'.join(f['text'] for f in evidence_for([frame])))
    def test_nonfinite_boolean_negative_rejected(self):
        for value in [float('nan'),float('inf'),True,-1]:
            raw=replay();raw['services'][0]['cpu']=value
            with self.subTest(value=value),self.assertRaises(ValueError):frames_from([raw])
    def test_source_mismatch_and_mixed_sources_rejected(self):
        raw=replay();raw['source']='live'
        with self.assertRaises(ValueError):frames_from([raw])
        raw['hardware']['source']='system'
        with self.assertRaises(ValueError):frames_from([replay(),raw])
    def test_duplicate_and_excessive_services_rejected(self):
        for rows in [[replay()['services'][0]]*2,[dict(replay()['services'][0],id=str(i)) for i in range(65)]]:
            raw=replay();raw['services']=rows
            with self.assertRaises(ValueError):frames_from([raw])
    def test_memory_ranges_and_dates_rejected(self):
        raw=replay();raw['hardware']['memory']['usedBytes']=101
        with self.assertRaises(ValueError):frames_from([raw])
        raw=replay();raw['at']='2026-10-26T12:00:00'
        with self.assertRaises(ValueError):frames_from([raw])
        later=replay();later['at']='2026-10-26T12:01:00Z'
        with self.assertRaises(ValueError):frames_from([later,replay()])
    def test_unknown_values_are_not_current_measurements(self):
        raw=replay();raw['services'][0].update(unknown=True,cpu=94,mem=80)
        clean=frames_from([raw])[0]
        self.assertIsNone(clean['services'][0]['cpu']);self.assertIsNone(clean['services'][0]['mem'])
    def test_unavailable_service_counts_are_not_zero(self):
        raw=replay();raw['servicesKnown']=False;raw['services']=[]
        facts=evidence_for(frames_from([raw]));self.assertIn('unavailable',facts[0]['text'].lower());self.assertNotIn('0 services',facts[0]['text'])
    def test_extra_fields_are_not_forwarded(self):
        raw=replay();raw['credential']='fixture-private-value'
        clean=frames_from([raw]);self.assertNotIn('credential',json.dumps(clean));self.assertNotIn('fixture-private-value',json.dumps(evidence_for(clean)))
    def test_valid_citations_and_unknown_reference_refusal(self):
        facts=evidence_for(frames_from([replay()]));self.assertEqual(validated_analysis(json.dumps(analysis()),facts)['summary']['evidenceIds'],['E1'])
        bad=analysis();bad['summary']=dict(text='Unsupported claim',evidenceIds=['E999'])
        with self.assertRaises(ValueError):validated_analysis(json.dumps(bad),facts)
    def test_uncited_or_unstructured_model_output_refused(self):
        facts=evidence_for(frames_from([replay()]))
        for value in ['Plain text',json.dumps(dict(summary='No evidence',observations=[],nextChecks=[]))]:
            with self.assertRaises(ValueError):validated_analysis(value,facts)
    def test_gpu_scope_and_no_input_mutation(self):
        raw=replay();before=copy.deepcopy(raw);facts=evidence_for(frames_from([raw]));self.assertEqual(raw,before)
        self.assertTrue(any('Whole-device' in f['text'] and 'no per-service attribution' in f['text'] for f in facts))

    def test_computed_deltas_preserve_unchanged_container_ram(self):
        before=replay();after=replay();after['at']='2026-10-26T12:00:20Z';after['services'][0]['cpu']=94;after['hardware']['memory']['usedBytes']=50
        facts=evidence_for(frames_from([before,after]));changes=[f['text'] for f in facts if f['text'].startswith('COMPUTED CHANGE:')]
        self.assertTrue(any('CPU +94' in text and 'container RAM +0' in text for text in changes))
        self.assertTrue(any('host RAM used bytes +50' in text for text in changes))
    def log_message(self,*args):pass
    def do_POST(self):
        self.server.calls+=1
        self.server.received=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        mode=self.server.mode
        if mode=='auth':self.send_error(401);return
        if mode=='redirect':
            self.send_response(302);self.send_header('Location','https://example.invalid/should-not-be-called');self.end_headers();return
        self.send_response(200);self.send_header('Content-Type','application/json' if mode=='wrong-type' else 'text/event-stream');self.end_headers()
        try:
            if mode=='slow':self.server.gate.wait(2)
            if mode=='oversize':self.wfile.write(b'data: '+b'x'*70000+b'\n');self.wfile.flush();return
            if mode=='malformed':self.wfile.write(b'data: {broken}\n\n');self.wfile.flush();return
            role={'choices':[{'delta':{'role':'assistant'}}]}
            body=json.dumps(analysis()) if mode=='explain' else 'A real streamed fixture response.'
            events=[role,{'choices':[{'delta':{'content':body}}]}]
            if mode!='no-usage':events.append({'choices':[],'usage':{'completion_tokens':5}})
            for event in events:self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode());self.wfile.flush()
            if mode!='truncated':self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
        except OSError:pass

class ModelHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        self.server.calls+=1
        self.server.received=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        mode=self.server.mode
        if mode=='auth':self.send_error(401);return
        if mode=='redirect':
            self.send_response(302);self.send_header('Location','https://example.invalid/should-not-be-called');self.end_headers();return
        self.send_response(200);self.send_header('Content-Type','application/json' if mode=='wrong-type' else 'text/event-stream');self.end_headers()
        try:
            if mode=='slow':self.server.gate.wait(2)
            if mode=='oversize':self.wfile.write(b'data: '+b'x'*70000+b'\n');self.wfile.flush();return
            if mode=='malformed':self.wfile.write(b'data: {broken}\n\n');self.wfile.flush();return
            role={'choices':[{'delta':{'role':'assistant'}}]}
            body=json.dumps(analysis()) if mode=='explain' else 'A real streamed fixture response.'
            events=[role,{'choices':[{'delta':{'content':body}}]}]
            if mode!='no-usage':events.append({'choices':[],'usage':{'completion_tokens':5}})
            for event in events:self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode());self.wfile.flush()
            if mode!='truncated':self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
        except OSError:pass

class ModelFixture(unittest.TestCase):
    def setUp(self):
        self.upstream=ThreadingHTTPServer(('127.0.0.1',0),ModelHandler);self.upstream.daemon_threads=True
        self.upstream.mode='normal';self.upstream.calls=0;self.upstream.received=None;self.upstream.gate=threading.Event()
        self.thread=threading.Thread(target=lambda:self.upstream.serve_forever(poll_interval=.01),daemon=True);self.thread.start()
        self.engine=AIEngine(base='http://127.0.0.1:'+str(self.upstream.server_port)+'/v1',token='test-fixture-key',model='fixture-model')
    def tearDown(self):
        self.upstream.gate.set();self.upstream.shutdown();self.upstream.server_close();self.thread.join(2)
    def terminal(self,identity):
        until=time.monotonic()+4
        while time.monotonic()<until:
            job=self.engine.snapshot(identity)
            if job['status'] not in ('running','cancelling'):return job
            time.sleep(.01)
        self.fail('Fixture job did not finish')
    def run_job(self,mode='normal'):
        self.upstream.mode=mode;return self.terminal(self.engine.start('run',{'prompt':'Test the bounded inference path'})['id'])

class InferenceTests(ModelFixture):
    def test_success_metrics_use_reported_usage(self):
        job=self.run_job();self.assertEqual(job['status'],'done');self.assertEqual(job['outputTokens'],5);self.assertGreaterEqual(job['ttftMs'],0);self.assertGreater(job['tokensPerSecond'],0)
        self.assertEqual(self.upstream.received['model'],'fixture-model');self.assertTrue(self.upstream.received['stream_options']['include_usage']);self.assertEqual(self.upstream.calls,1)
        self.assertNotIn('test-fixture-key',json.dumps(job));self.assertNotIn('test-fixture-key',json.dumps(self.engine.info()))
    def test_missing_usage_stays_unknown(self):
        job=self.run_job('no-usage');self.assertEqual(job['status'],'done');self.assertIsNone(job['outputTokens']);self.assertIsNone(job['tokensPerSecond'])
    def test_truncation_and_malformed_responses_fail(self):
        for mode in ['truncated','malformed','wrong-type','oversize']:
            with self.subTest(mode=mode):self.assertEqual(self.run_job(mode)['status'],'failed')
    def test_authentication_error_and_redirect_are_not_retried(self):
        for mode in ['auth','redirect']:
            before=self.upstream.calls;job=self.run_job(mode);self.assertEqual(job['status'],'failed');self.assertEqual(self.upstream.calls,before+1)
    def test_single_flight_and_confirmed_cancel(self):
        self.upstream.mode='slow';job=self.engine.start('run',{'prompt':'Hold this request'})
        with self.assertRaises(RequestError) as caught:self.engine.start('run',{'prompt':'Second request'})
        self.assertEqual(caught.exception.status,409);self.assertEqual(self.engine.cancel(job['id'])['status'],'cancelling');self.upstream.gate.set()
        self.assertEqual(self.terminal(job['id'])['status'],'cancelled')
    def test_prompt_and_unconfigured_route_refused(self):
        for payload in [{},{'prompt':''},{'prompt':True},{'prompt':'x'*2001},{'prompt':'ok','url':'external'}]:
            with self.assertRaises(RequestError):self.engine.start('run',payload)
        missing=AIEngine(token='');self.assertFalse(missing.info()['configured'])
        with self.assertRaises(RequestError) as caught:missing.start('run',{'prompt':'hello'})
        self.assertEqual(caught.exception.status,503)
    def test_only_loopback_configuration_allowed(self):
        for url in ['https://example.invalid/v1','http://0.0.0.0/v1','http://127.0.0.1@remote.invalid/v1','http://127.0.0.1/v1?redirect=1']:
            with self.assertRaises(ValueError):loopback_base(url)
        self.assertEqual(loopback_base('http://localhost:4000/v1'),'http://127.0.0.1:4000/v1')
    def test_explain_has_valid_citations(self):
        self.upstream.mode='explain';job=self.terminal(self.engine.start('explain',{'frames':[replay()]})['id'])
        self.assertEqual(job['status'],'done');self.assertEqual(job['analysis']['summary']['evidenceIds'],['E1']);self.assertTrue(job['evidence']);self.assertEqual(self.upstream.received['response_format'],{'type':'json_object'})
    def test_explain_with_none_evidence_raises_503(self):
        with unittest.mock.patch('ai_bridge.evidence_for', return_value=None):
            with self.assertRaises(RequestError) as caught:
                self.engine.start('explain', {'frames': [replay()]})
            self.assertEqual(caught.exception.status, 503)
        self.assertEqual(self.upstream.calls, 0)
    def test_bounded_job_retention_and_unknown_receipt(self):
        first=self.run_job()['id']
        for _ in range(8):self.run_job()
        self.assertEqual(len(self.engine.jobs),8)
        with self.assertRaises(RequestError):self.engine.snapshot(first)
    def test_failed_validation_preserves_reported_usage(self):
        self.upstream.mode='normal'
        job=self.terminal(self.engine.start('explain',{'frames':[replay()]})['id'])
        self.assertEqual(job['status'],'failed')
        self.assertEqual(job['outputTokens'],5)
        self.assertGreater(job['tokensPerSecond'],0)

class AIHTTPTests(ModelFixture):
    def setUp(self):
        super().setUp();self.server=companion.make_server(port=0,collector=lambda:{},ai_engine=self.engine)
        self.http_thread=threading.Thread(target=lambda:self.server.serve_forever(poll_interval=.01),daemon=True);self.http_thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.http_thread.join(2);super().tearDown()
    def request(self,path,method='GET',data=None,headers=None):
        client=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        body=None if data is None else json.dumps(data);h={'Content-Type':'application/json'} if data is not None else {};h.update(headers or {})
        client.request(method,path,body=body,headers=h);response=client.getresponse();raw=response.read();client.close();return response.status,json.loads(raw)
    def test_job_route_and_service_mutation_refusal(self):
        code,data=self.request('/api/ai/run','POST',{'prompt':'Hello'});self.assertEqual(code,202);self.assertEqual(self.request('/api/ai/jobs/'+data['id'])[0],200)
        self.assertEqual(self.request('/api/telemetry','POST',{})[0],405)
        self.assertEqual(self.request('/api/ai/status')[0],200)
    def test_foreign_origin_host_and_wrong_content_type(self):
        for h in [{'Origin':'https://foreign.invalid'},{'Origin':'null'},{'Host':'foreign.invalid'}]:self.assertEqual(self.request('/api/ai/run','POST',{'prompt':'Hello'},h)[0],403)
        self.assertEqual(self.request('/api/ai/run','POST',{'prompt':'Hello'},{'Content-Type':'text/plain'})[0],415)
    def test_oversized_and_chunked_bodies_refused(self):
        self.assertEqual(self.request('/api/ai/run','POST',{}, {'Content-Length':'65537'})[0],413)
        self.assertEqual(self.request('/api/ai/run','POST',{}, {'Transfer-Encoding':'chunked'})[0],400)
    def test_opaque_job_ids_and_cancel_unknown(self):
        self.assertEqual(self.request('/api/ai/jobs/not-an-id')[0],404)
        self.assertEqual(self.request('/api/ai/jobs/'+'a'*32+'/cancel','POST',{})[0],404)

if __name__=='__main__':unittest.main()
