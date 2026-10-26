import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),core=require('./replay-core.js');
function raw(at='2026-10-26T12:00:00Z'){
 return {at,source:'demo',servicesKnown:true,services:[{id:'portal',name:'Portal',cpu:0,mem:0,state:'running',health:'simulated',unknown:false,offline:false}],hardware:{source:'simulated',memory:{usedBytes:0,totalBytes:100},gpus:[{name:'Fixture GPU',utilization:0,memoryUsedBytes:0,memoryTotalBytes:100}]}};
}
test('measured zero remains zero; absent values remain unknown',()=>{
 const a=core.frame(raw());assert.equal(a.services[0].cpu,0);assert.equal(a.hardware.memory.usedBytes,0);assert.equal(core.stats(a).gpu,0);
 const b=raw();b.services[0].cpu=null;b.hardware.gpus[0].utilization=null;const f=core.frame(b);assert.equal(core.stats(f).maxCPU,null);assert.equal(core.stats(f).gpu,null);
});
test('stale readings are cleared, with no mutation of the input',()=>{
 const a=raw();a.services[0].unknown=true;a.services[0].cpu=94;a.services[0].memUsedBytes=100;
 const b=core.frame(a);assert.equal(b.services[0].cpu,null);assert.equal(b.services[0].memUsedBytes,null);assert.equal(a.services[0].cpu,94);assert.equal(core.stats(b).online,null);
});
test('missing service collection is not a genuine empty fleet',()=>{
 const a=raw();a.services=[];a.servicesKnown=false;assert.equal(core.stats(core.frame(a)).total,null);
 a.servicesKnown=true;assert.equal(core.stats(core.frame(a)).total,0);assert.equal(core.stats(core.frame(a)).online,0);
});
test('multicore CPU remains available as its actual value',()=>{
 const a=raw();a.services[0].cpu=250.5;assert.equal(core.stats(core.frame(a)).maxCPU,250.5);
});
test('nonfinite, negative, boolean and string measurements are refused',()=>{
 for(const value of [NaN,Infinity,-1,true,'10']){const a=raw();a.services[0].cpu=value;assert.throws(()=>core.frame(a));}
});
test('hardware provenance cannot be relabeled',()=>{
 const a=raw();a.source='live';assert.throws(()=>core.frame(a));a.hardware.source='system';assert.equal(core.frame(a).source,'live');
});
test('invalid dates, duplicate services, and control labels are refused',()=>{
 assert.throws(()=>core.frame(raw('not-a-date')));assert.throws(()=>core.frame(raw('2026-10-26T12:00:00')));
 const a=raw();a.services.push(a.services[0]);assert.throws(()=>core.frame(a));
 const b=raw();b.services[0].name='bad'+String.fromCharCode(10)+'label';assert.throws(()=>core.frame(b));
});
test('memory and GPU bounds are enforced',()=>{
 const a=raw();a.hardware.memory.usedBytes=101;assert.throws(()=>core.frame(a));
 const b=raw();b.hardware.gpus[0].memoryUsedBytes=101;assert.throws(()=>core.frame(b));
 const c=raw();c.hardware.gpus[0].utilization=101;assert.throws(()=>core.frame(c));
});
test('replay import is bounded, sorted and single-source',()=>{
 const first=raw(),last=raw('2026-10-26T12:00:10Z');
 assert.equal(core.load({version:1,frames:[last,first]})[0].at,first.at);
 assert.throws(()=>core.load({version:1,frames:[]}));assert.throws(()=>core.load({version:1,frames:[first,first]}));
 last.source='live';last.hardware.source='system';assert.throws(()=>core.load({version:1,frames:[first,last]}));
 assert.throws(()=>core.load('x'.repeat(1024*1024+1)));
});
test('rolling history retains at most 120 samples and ten minutes',()=>{
 const start=Date.parse('2026-10-26T12:00:00Z');let history=[];
 for(let i=0;i<140;i++){const now=start+i*1000;history=core.append(history,raw(new Date(now).toISOString()),now);}
 assert.equal(history.length,120);
 const now=start+20*60*1000;history=core.append(history,raw(new Date(now).toISOString()),now);assert.equal(history.length,1);
});
test('unknown extra fields are stripped from exported frame data',()=>{
 const a=raw();a.credential='fixture-private-value';a.services[0].privateKey='fixture-private-value';
 const output=JSON.stringify(core.wire(core.frame(a)));assert.equal(output.includes('fixture-private-value'),false);
});
