let AquariumRecorder=null;
document.addEventListener('DOMContentLoaded',()=>{
 const core=AquariumReplay,storeKey='aquarium.replay.v1';
 const observatory=document.createElement('section');observatory.id='observatory';observatory.className='observatory';observatory.innerHTML='<header class="obs-heading"><div><small>ODS OBSERVATORY</small><h2>Observe. Replay. Understand.</h2></div><span>Recorded measurements stay in this browser</span></header><div id="obs-panels" class="obs-panels"></div>';
 document.querySelector('.panels-container').after(observatory);
 const pane=document.createElement('article');pane.className='obs-panel';pane.id='replay-panel';
 pane.innerHTML=[
 '<div class="obs-title"><h3>Flight recorder</h3><span id="replay-badge" class="obs-chip">Recording</span></div>',
 '<p class="obs-description">Scrub up to ten minutes of captured readings. The aquarium above keeps its current view.</p>',
 '<div class="obs-toolbar"><button type="button" id="replay-sample">Open sample replay</button><button type="button" id="replay-import">Import replay</button><button type="button" id="replay-export">Save replay</button><input id="replay-file" type="file" accept=".json,application/json" hidden></div>',
 '<p id="replay-status" class="obs-status" role="status"></p>',
 '<svg id="replay-chart" viewBox="0 0 440 68" role="img" aria-label="Recorded GPU load and highest service CPU, displayed up to 100 percent"></svg>',
 '<div class="replay-legend"><span>GPU · whole device</span><span>Highest service CPU · display capped at 100%</span></div>',
 '<label class="obs-label" for="replay-slider">Selected moment <strong id="replay-time">Waiting for a sample</strong></label>',
 '<input id="replay-slider" type="range" min="0" max="0" value="0" step="1" disabled>',
 '<div id="replay-facts" class="replay-facts"></div>',
 '<div id="replay-services" class="replay-services"></div>',
 '<div class="obs-toolbar"><button type="button" id="replay-baseline">Use as baseline</button><button type="button" id="replay-explain" class="primary">Explain this moment</button><button type="button" id="replay-back">Follow recorder</button></div>',
 '<small id="replay-baseline-note" class="obs-footnote"></small>'
 ].join('');
 document.getElementById('obs-panels').append(pane);
 const el=id=>document.getElementById(id),streams={demo:[],live:[]};let imported=null,builtin=null,selectedId=null,baselineId=null,follow=true,storageNote='';
 try{
  const saved=JSON.parse(localStorage.getItem(storeKey)||'null');
  if(saved?.version===1)for(const source of ['demo','live']){
   const rows=saved.streams?.[source];
   if(Array.isArray(rows)&&rows.length)streams[source]=core.load({version:1,frames:rows}).filter(f=>Date.parse(f.at)>=Date.now()-core.MAX_AGE);
  }
 }catch(error){storageNote='Previous browser history could not be restored.';}
 function rows(){return imported||streams[state.source]||[];}
 function selected(){const list=rows();return list.find(f=>f.id===selectedId)||list[list.length-1]||null;}
 function baseline(){const f=selected();if(!f)return null;return rows().find(x=>x.id===baselineId&&Date.parse(x.at)<=Date.parse(f.at))||rows().find(x=>Date.parse(x.at)<Date.parse(f.at))||null;}
 function persist(){
  try{
   let saved=JSON.stringify({version:1,streams});
   if(saved.length>1024*1024){storageNote='History is held in memory because the storage budget was reached.';return;}
   localStorage.setItem(storeKey,saved);
  }catch(error){storageNote='Browser storage unavailable; history remains in memory.';}
 }
 function render(){
  const list=rows(),f=selected(),base=baseline();
  el('replay-badge').textContent=imported?(builtin?'Recorded sample':'Imported replay'):(follow?'Following recorder':'Historical moment');
  el('replay-status').textContent=list.length+' / 120 samples · '+(f?(f.source==='demo'?'simulated':'observed'):'waiting')+(storageNote?' · '+storageNote:'');
  const slider=el('replay-slider');slider.disabled=!list.length;slider.max=String(Math.max(0,list.length-1));slider.value=String(Math.max(0,list.indexOf(f)));
  el('replay-time').textContent=f?new Date(f.at).toLocaleString():'Waiting for a sample';
  const facts=el('replay-facts'),services=el('replay-services');facts.replaceChildren();services.replaceChildren();
  if(f){
   const s=core.stats(f),memory=f.hardware?.memory,gpu=f.hardware?.gpus[0];
   for(const [title,value] of [['Running / recorded',s.online===null?'—':s.online+' / '+s.total],['Host RAM',memory?hardwarePair(memory.usedBytes,memory.totalBytes):'—'],['GPU load',metric(gpu?.utilization)],['VRAM',gpu?hardwarePair(gpu.memoryUsedBytes,gpu.memoryTotalBytes):'—']]){
    const cell=document.createElement('div'),small=document.createElement('small'),strong=document.createElement('strong');small.textContent=title;strong.textContent=value;cell.append(small,strong);facts.append(cell);
   }
   f.services.slice(0,12).forEach(s=>{const row=document.createElement('div');row.className='replay-service';const name=document.createElement('span'),detail=document.createElement('small');name.textContent=s.name;detail.textContent=(s.unknown?'Unknown':s.offline?'Offline':s.state)+' · CPU '+metric(s.cpu)+' · RAM '+metric(s.mem);row.append(name,detail);services.append(row);});
   if(!f.servicesKnown){const p=document.createElement('p');p.textContent='Service observations unavailable at this moment.';services.append(p);}
  }
  const svg=el('replay-chart');svg.replaceChildren();
  for(const [field,color] of [['gpu','#b5a6e8'],['maxCPU','#8ed4bb']]){
   let points=[];const flush=()=>{if(points.length){const line=document.createElementNS('http://www.w3.org/2000/svg','polyline');line.setAttribute('points',points.join(' '));line.setAttribute('fill','none');line.setAttribute('stroke',color);line.setAttribute('stroke-width','2');svg.append(line);points=[];}};
   list.forEach((sample,i)=>{const value=core.stats(sample)[field];if(value===null){flush();return;}points.push((4+i*432/Math.max(1,list.length-1)).toFixed(1)+','+(62-Math.min(100,value)*.54).toFixed(1));});flush();
  }
  if(f&&list.length>1){const marker=document.createElementNS('http://www.w3.org/2000/svg','line'),x=4+list.indexOf(f)*432/(list.length-1);marker.setAttribute('x1',x);marker.setAttribute('x2',x);marker.setAttribute('y1','2');marker.setAttribute('y2','66');marker.setAttribute('stroke','#c8d9d0');marker.setAttribute('stroke-dasharray','2 3');svg.append(marker);}
  el('replay-baseline-note').textContent=base?'Baseline: '+new Date(base.at).toLocaleString()+' · same source':'Select an earlier moment to compare a baseline.';
  for(const id of ['replay-explain','replay-baseline','replay-export'])el(id).disabled=!f;
 }
 function capture(){
  try{
   const raw={at:new Date().toISOString(),source:state.source,servicesKnown:state.source==='demo'||state.hasLiveData===true,services:state.fish.map(f=>({id:f.id,name:f.fullName,cpu:f.cpu,mem:f.mem,memUsedBytes:f.memUsedBytes,memLimitBytes:f.memLimitBytes,offline:f.offline,unknown:f.unknown,state:f.state,health:f.health})),hardware:state.hardware||null};
   for(const kind of ['demo','live'])streams[kind]=streams[kind].filter(item=>Date.parse(item.at)>=Date.now()-core.MAX_AGE);const f=core.frame(raw);streams[f.source]=core.append(streams[f.source],f);persist();
   if(!imported&&follow)selectedId=f.id;
   render();
  }catch(error){el('replay-status').textContent='Snapshot unavailable; waiting for valid observations.';}
 }
 function openFrames(value, sample=false){
  imported=core.load(value);builtin=sample?value:null;follow=false;baselineId=null;
  const index=Number.isInteger(value.defaultIndex)?Math.max(0,Math.min(imported.length-1,value.defaultIndex)):imported.length-1;
  selectedId=imported[index].id;render();
 }
 AquariumRecorder={
  selection(){const f=selected(),base=baseline();return f?[...(base&&base.id!==f.id?[core.wire(base)]:[]),core.wire(f)]:[];},
  viewFrames(frames,index=frames.length-1){openFrames({version:1,frames,defaultIndex:index});},
  recorded(){const f=selected(),base=baseline(),record=builtin?.recordedExplanation;const expected=record&&Array.isArray(record.frames)?record.frames.map(item=>core.wire(core.frame(item))):null;return record&&f?.at===record.forAt&&base?.at===record.baselineAt&&JSON.stringify(expected)===JSON.stringify(AquariumRecorder.selection())?record:null;}
 };
 el('replay-slider').oninput=event=>{follow=false;selectedId=rows()[Number(event.target.value)]?.id;render();};
 el('replay-baseline').onclick=()=>{baselineId=selected()?.id||null;render();};
 el('replay-back').onclick=()=>{imported=null;builtin=null;follow=true;baselineId=null;selectedId=null;render();};
 el('replay-explain').onclick=()=>document.dispatchEvent(new CustomEvent('aquarium-explain',{detail:{frames:AquariumRecorder.selection(),recorded:AquariumRecorder.recorded()}}));
 el('replay-export').onclick=()=>{const f=selected();if(!f)return;const data={version:1,app:'Server Aquarium',frames:rows()},url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='aquarium-replay-'+f.source+'-'+Date.now()+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);};
 el('replay-import').onclick=()=>el('replay-file').click();
 el('replay-file').onchange=async event=>{const file=event.target.files[0];if(!file)return;try{if(file.size>1024*1024)throw Error('Replay exceeds 1 MiB');openFrames(JSON.parse(await file.text()));}catch(error){el('replay-status').textContent='Import refused: '+error.message;}event.target.value='';};
 el('replay-sample').onclick=async()=>{try{const response=await fetch(new URL('sample-replay.json',location.href),{cache:'no-store'});if(!response.ok)throw Error('Sample unavailable');openFrames(await response.json(),true);}catch(error){el('replay-status').textContent='Sample replay unavailable.';}};
 document.getElementById('data-source').addEventListener('change',()=>{if(!imported){selectedId=null;baselineId=null;follow=true;}setTimeout(capture,50);});
 capture();setInterval(capture,5000);
},{once:true});
