document.addEventListener('DOMContentLoaded',()=>{
 let lastReport=null;
 const pane=document.createElement('article');pane.id='lab-panel';pane.className='obs-panel';
 pane.innerHTML=[
 '<div class="obs-title"><h3>AI lab</h3><span id="ai-route" class="obs-chip">Checking companion</span></div>',
 '<p class="obs-description">Run a real request through your ODS gateway, or explain a selected replay moment with linked measurements.</p>',
 '<label class="obs-label" for="ai-prompt">Your prompt</label>',
 '<textarea id="ai-prompt" rows="3" maxlength="2000">Explain how a local AI request uses the model, GPU and memory in five short bullet points.</textarea>',
 '<div class="obs-toolbar"><button type="button" id="ai-run" class="primary" disabled>Run through ODS</button><button type="button" id="ai-cancel" disabled>Cancel request</button><button type="button" id="ai-refresh">Check connection</button><button type="button" id="ai-save" disabled>Save AI report</button></div>',
 '<p id="ai-status" class="obs-status" role="status">Checking the local companion…</p>',
 '<div class="ai-metrics"><div><small>First content</small><strong id="ai-ttft">—</strong></div><div><small>Output tokens</small><strong id="ai-tokens">—</strong></div><div><small>Tokens / total second</small><strong id="ai-rate">—</strong></div><div><small>Elapsed</small><strong id="ai-elapsed">—</strong></div></div>',
 '<p class="obs-footnote">Explanation sends selected replay readings to your configured ODS model route. Usage is reported by the gateway. The rate includes waiting for first content. GPU readings describe the whole device.</p>',
 '<div id="ai-output" class="ai-output" aria-live="polite"></div>',
 '<p id="ai-setup" class="obs-footnote">For real inference, run companion.py with your ODS gateway environment configured. <a href="https://github.com/tang-vu/server-aquarium#run" target="_blank" rel="noopener">Setup guide</a></p>'
 ].join('');
 document.getElementById('obs-panels').append(pane);
 const el=id=>document.getElementById(id),receiptKey='aquarium.ai.active';let configured=false,active=false,jobId=null,context=[],currentKind='run';
 const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 const seconds=n=>Number.isFinite(n)?(n/1000).toFixed(2)+' s':'—';
 function busy(value){active=value;state.aiRunning=value;document.body.classList.toggle('ai-active',value);el('ai-run').disabled=value||!configured;el('ai-cancel').disabled=!value||!jobId;}
 async function api(path,method='GET',data){
  const control=new AbortController(),timer=setTimeout(()=>control.abort(),10000);
  try{
   const response=await fetch(new URL(path,location.href),{method,cache:'no-store',signal:control.signal,headers:method==='POST'?{'Content-Type':'application/json'}:{},body:data===undefined?undefined:JSON.stringify(data)});
   const result=await response.json();if(!response.ok){const error=Error(result.error||'Companion request refused');error.refused=response.status>=400&&response.status<500;throw error;}return result;
  }finally{clearTimeout(timer);}
 }
 function metrics(job){el('ai-ttft').textContent=seconds(job.ttftMs);el('ai-tokens').textContent=Number.isInteger(job.outputTokens)?String(job.outputTokens):'—';el('ai-rate').textContent=Number.isFinite(job.tokensPerSecond)?job.tokensPerSecond.toFixed(2):'—';el('ai-elapsed').textContent=seconds(job.elapsedMs);}
 function showAnalysis(analysis,facts,frames,recorded=false){
  const output=el('ai-output'),known=new Map(facts.map(f=>[f.id,f]));
  const rows=[analysis?.summary,...(analysis?.observations||[]),...(analysis?.nextChecks||[])];
  if(!analysis||!rows.length||rows.some(row=>!row||typeof row.text!=='string'||!Array.isArray(row.evidenceIds)||!row.evidenceIds.length||row.evidenceIds.some(id=>!known.has(id))))throw Error('Explanation references could not be validated');
  output.replaceChildren();const label=document.createElement('p');label.className='obs-footnote';label.textContent=(recorded?'Recorded ODS response':'ODS model interpretation')+' · check the linked measurements; proposed checks have not been executed.';output.append(label);
  const cite=(id)=>{const fact=known.get(id),button=document.createElement('button');button.type='button';button.className='evidence-link';button.textContent=id;button.title='Show the captured moment for '+id;button.onclick=()=>{AquariumRecorder.viewFrames(frames,fact.frameIndex);document.getElementById('replay-panel').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'nearest'});};return button;}
  for(const [title,group] of [['Summary',[analysis.summary]],['Observations',analysis.observations],['Suggested checks',analysis.nextChecks]]){
   const heading=document.createElement('h4');heading.textContent=title;output.append(heading);
   for(const row of group){const p=document.createElement('p'),span=document.createElement('span');span.textContent=row.text;p.append(span);for(const id of row.evidenceIds)p.append(' ',cite(id));output.append(p);}
  }
  const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Supporting measurements ('+facts.length+')';details.append(summary);
  facts.forEach(fact=>{const p=document.createElement('p'),span=document.createElement('span');span.textContent=new Date(fact.at).toLocaleTimeString()+' · '+fact.text;p.append(cite(fact.id),' ',span);details.append(p);});output.append(details);
 }
 async function poll(identity,kind,frames){
  jobId=identity;context=frames;currentKind=kind;busy(true);let misses=0;const started=Date.now();
  try{
   while(Date.now()-started<125000){
    let job;
    try{job=await api('api/ai/jobs/'+identity);misses=0;}catch(error){misses++;el('ai-status').textContent='Connection interrupted; checking the existing request…';if(misses>=4)throw error;await wait(1000);continue;}
    metrics(job);el('ai-status').textContent=job.status==='cancelling'?'Cancellation requested; waiting for the upstream read to finish.':job.status==='running'?(kind==='run'?'ODS is generating…':'ODS is interpreting the selected replay evidence…'):job.error||('Request '+job.status+'.');
    if(kind==='run'){el('ai-output').textContent=job.text||(['running','cancelling'].includes(job.status)?'Waiting for first content…':'No content was generated.');}
    if(['done','failed','cancelled'].includes(job.status)){
     lastReport={...job,frames};
     el('ai-save').disabled=false;

     if(kind==='explain'&&job.status==='done')showAnalysis(job.analysis,job.evidence,frames);
     if(kind==='explain'&&job.status!=='done')el('ai-output').textContent='The captured replay is still available. No validated model explanation was produced.';
     try{sessionStorage.removeItem(receiptKey);}catch(error){}
     note('ai','ODS '+kind+' request '+job.status+'.');return;
    }
    await wait(700);
   }
   throw Error('Monitoring deadline reached');
  }catch(error){el('ai-status').textContent='Status unavailable. The request may still be running; Check connection resumes its existing receipt.';}
  finally{busy(false);}
 }
 async function start(kind,payload,frames=[]){
  if(active){el('ai-status').textContent='Wait for the current ODS request or cancel it.';return;}
  if(!configured){el('ai-status').textContent='Real inference requires the configured local companion. Open sample replay to inspect the recorded example.';return;}
  lastReport=null;el('ai-save').disabled=true;jobId=null;busy(true);metrics({});el('ai-output').replaceChildren();el('ai-status').textContent='Submitting one bounded ODS request…';
  if(kind==='run'&&el('data-source').value!=='live'){el('data-source').value='live';el('data-source').dispatchEvent(new Event('change'));}
  try{
   const job=await api('api/ai/'+kind,'POST',payload);jobId=job.id;
   try{sessionStorage.setItem(receiptKey,JSON.stringify({id:job.id,kind,frames}));}catch(error){}
   await poll(job.id,kind,frames);
  }catch(error){el('ai-status').textContent=(error.refused?'Request refused: ':'No request receipt was obtained: ')+error.message;busy(false);}
 }
 async function connect(){
  if(active)return;
  configured=false;el('ai-run').disabled=true;
  if(!['127.0.0.1','localhost','[::1]'].includes(location.hostname)){
   el('ai-route').textContent='Public demo';el('ai-status').textContent='Explore the sample replay here. Run the companion locally for real ODS requests.';return;
  }
  try{
   const status=await api('api/ai/status');configured=status.configured===true;el('ai-route').textContent=configured?'ODS · '+status.model:'Companion needs setup';el('ai-status').textContent=configured?'Ready. One request at a time through your configured ODS route.':status.message||'Configure the companion environment.';el('ai-run').disabled=!configured;
   const receipt=JSON.parse(sessionStorage.getItem(receiptKey)||'null');
   if(configured&&receipt&&/^[a-f0-9]{32}$/.test(receipt.id)&&['run','explain'].includes(receipt.kind)){const frames=Array.isArray(receipt.frames)?receipt.frames.map(AquariumReplay.frame):[];await poll(receipt.id,receipt.kind,frames);}
  }catch(error){el('ai-route').textContent='Companion unavailable';el('ai-status').textContent='Start the local companion to run AI. Recorded replay remains available.';}
 }
 el('ai-run').onclick=()=>start('run',{prompt:el('ai-prompt').value});
 el('ai-refresh').onclick=connect;
 el('ai-save').onclick=()=>{
  if(!lastReport)return;
  const data={version:1,app:'Server Aquarium',report:lastReport};
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const a=document.createElement('a');
  a.href=url;
  a.download='aquarium-ai-'+lastReport.kind+'-'+Date.now()+'.json';
  a.click();
  setTimeout(()=>URL.revokeObjectURL(url),30000);
 };
 el('ai-cancel').onclick=async()=>{if(!jobId)return;try{await api('api/ai/jobs/'+jobId+'/cancel','POST',{});el('ai-status').textContent='Cancellation requested; waiting for confirmation.';}catch(error){el('ai-status').textContent='Cancellation could not be confirmed. Check the existing request status.';}};
 document.addEventListener('aquarium-explain',event=>{
  if(active){el('ai-status').textContent='Wait for the current ODS request or cancel it.';return;}
  const detail=event.detail,frames=detail.frames;
  if(!configured&&detail.recorded){try{lastReport={...detail.recorded,frames,kind:'explain',status:'recorded'};el('ai-save').disabled=false;metrics(detail.recorded);showAnalysis(detail.recorded.analysis,detail.recorded.evidence,frames,true);el('ai-status').textContent='Recorded ODS explanation for this exact sample comparison.';}catch(error){el('ai-status').textContent='The recorded explanation could not be validated.';}return;}
  start('explain',{frames},frames);
 });
 connect();
},{once:true});
