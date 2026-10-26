const AquariumReplay = (()=>{
 const MAX_FRAMES=120, MAX_AGE=10*60*1000;
 function num(value, cap=2**60){
  if(value===null||value===undefined)return null;
  if(typeof value!=='number'||!Number.isFinite(value)||value<0||value>cap)throw Error('Invalid measurement');
  return value;
 }
 function text(value, max=120){
  if(typeof value!=='string'||value.length>max||/[\u0000-\u001f]/.test(value))throw Error('Invalid replay label');
  return value;
 }
 function memory(value){
  if(value===null||value===undefined)return null;
  if(typeof value!=='object'||Array.isArray(value))throw Error('Invalid memory reading');
  const used=num(value.usedBytes),total=num(value.totalBytes);
  if(used!==null&&total!==null&&(total<=0||used>total))throw Error('Invalid memory range');
  return {usedBytes:used,totalBytes:total};
 }
 function frame(raw){
  if(!raw||typeof raw!=='object'||!['demo','live'].includes(raw.source))throw Error('Invalid replay source');
  const at=text(raw.at,40);
  if(!Number.isFinite(Date.parse(at))||!/(Z|[+-][0-9]{2}:[0-9]{2})$/.test(at))throw Error('Invalid replay time');
  if(!Array.isArray(raw.services)||raw.services.length>64)throw Error('Too many services');
  const seen=new Set();
  const services=raw.services.map(s=>{
   if(!s||typeof s!=='object')throw Error('Invalid service');
   const id=text(s.id,80);if(seen.has(id))throw Error('Duplicate service');seen.add(id);
   const unknown=s.unknown===true;
   return {id,name:text(s.name),cpu:unknown?null:num(s.cpu,100000),mem:unknown?null:num(s.mem,100),memUsedBytes:unknown?null:num(s.memUsedBytes),memLimitBytes:unknown?null:num(s.memLimitBytes),offline:s.offline===true,unknown,state:text(s.state||'unknown',30),health:text(s.health||'unknown',30)};
  });
  let hardware=null;
  if(raw.hardware!==null&&raw.hardware!==undefined){
   const h=raw.hardware;
   if(h.source!==(raw.source==='demo'?'simulated':'system')||!Array.isArray(h.gpus)||h.gpus.length>16)throw Error('Hardware source mismatch');
   hardware={source:h.source,sampledAt:typeof h.sampledAt==='string'?text(h.sampledAt,40):null,memory:memory(h.memory),gpus:h.gpus.map(g=>{
    if(!g||typeof g!=='object')throw Error('Invalid GPU');
    const used=num(g.memoryUsedBytes),total=num(g.memoryTotalBytes);
    if(used!==null&&total!==null&&(total<=0||used>total))throw Error('Invalid VRAM range');
    return {name:text(g.name),utilization:num(g.utilization,100),memoryUsedBytes:used,memoryTotalBytes:total,temperatureC:num(g.temperatureC,200),powerW:num(g.powerW,10000)};
   })};
  }
  return {id:at+'|'+raw.source,at,source:raw.source,servicesKnown:raw.servicesKnown!==false,services,hardware};
 }
 function load(value){
  if(typeof value==='string'){
   if(value.length>1024*1024)throw Error('Replay is larger than 1 MiB');
   value=JSON.parse(value);
  }
  if(!value||value.version!==1||!Array.isArray(value.frames)||!value.frames.length||value.frames.length>MAX_FRAMES)throw Error('Expected a v1 Aquarium replay with 1–120 frames');
  const frames=value.frames.map(frame),seen=new Set();
  for(const f of frames){if(seen.has(f.id))throw Error('Duplicate replay time');seen.add(f.id);}
  if(new Set(frames.map(f=>f.source)).size!==1)throw Error('A replay must use a single source');
  frames.sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
  return frames;
 }
 function append(history, raw, now=Date.now()){
  const next=frame(raw);
  return history.filter(f=>f.source===next.source&&f.id!==next.id&&Date.parse(f.at)>=now-MAX_AGE&&Date.parse(f.at)<=now+60000).concat(next).slice(-MAX_FRAMES);
 }
 function wire(f){return {at:f.at,source:f.source,servicesKnown:f.servicesKnown,services:f.services,hardware:f.hardware};}
 function stats(f){
  const known=f.services.filter(s=>!s.unknown),loads=known.map(s=>s.cpu).filter(Number.isFinite);
  return {online:f.servicesKnown&&!f.services.some(s=>s.unknown)?known.filter(s=>!s.offline).length:null,total:f.servicesKnown?f.services.length:null,maxCPU:loads.length?Math.max(...loads):null,gpu:f.hardware?.gpus[0]?.utilization??null};
 }
 return {MAX_FRAMES,MAX_AGE,frame,load,append,wire,stats};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=AquariumReplay;
