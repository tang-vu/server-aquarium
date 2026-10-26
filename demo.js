let aquariumDemo=null;
function demoSimulationAction(action){aquariumDemo?.action(action);}
function drawDemoAtmosphere(ctx,w,h,t){
 if(state.source!=='demo')return;
 const hue=state.demoAccent||'#80dcc9',glow=ctx.createRadialGradient(w*.65,h*.2,0,w*.65,h*.2,w*.65);glow.addColorStop(0,hue+'1a');glow.addColorStop(1,hue+'00');ctx.fillStyle=glow;ctx.fillRect(0,0,w,h);
 ctx.save();ctx.strokeStyle=hue+'18';ctx.lineWidth=.8;for(let j=0;j<4;j++){ctx.beginPath();for(let i=0;i<=24;i++){const x=i*w/24,y=35+j*18+Math.sin(i*.6+t*.0004+j)*9;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);}ctx.stroke();}
 [.08,.48,.94].forEach((fraction,k)=>{const x=w*fraction,base=h-30,scale=w<600?.7:1;ctx.save();ctx.translate(x,base);ctx.scale(scale,scale);ctx.strokeStyle=['#c486ad','#72bdb3','#9e94cb'][k];ctx.globalAlpha=.62;ctx.lineWidth=3;ctx.lineCap='round';for(let j=-2;j<=2;j++){ctx.beginPath();ctx.moveTo(0,0);ctx.quadraticCurveTo(j*6,-28,j*13,-42-Math.abs(j)*7);ctx.stroke();for(let b=0;b<2;b++){const bx=j*7,by=-18-b*13;ctx.beginPath();ctx.moveTo(bx,by);ctx.lineTo(bx+(j<0?-1:1)*12,by-12);ctx.stroke();}}ctx.restore();});
 for(let i=0;i<16;i++){const x=(i*193.7+w*.1)%w,y=90+(i*71.3+t*.005)%(Math.max(50,h-160)),r=i%4===0?2:1;ctx.fillStyle=hue;ctx.globalAlpha=.16+.12*Math.sin(t*.001+i);ctx.shadowColor=hue;ctx.shadowBlur=7;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();}ctx.restore();
}
function drawDemoWake(ctx,f,t){
 if(state.source!=='demo'||f.offline||f.unknown)return;
 ctx.save();const dir=f.facing||1;ctx.fillStyle=f.color;for(let i=1;i<=4;i++){ctx.globalAlpha=(1-i/5)*.2;ctx.beginPath();ctx.arc(f.x-dir*(25+i*12),f.y+Math.sin(t*.003+i)*2,Math.max(.7,2-i*.3),0,Math.PI*2);ctx.fill();}
 if(f.id==='engine'&&state.demoMode==='inference'){ctx.strokeStyle='#b8a7ed';ctx.globalAlpha=.2;ctx.lineWidth=1;ctx.beginPath();ctx.ellipse(f.x,f.y,53+Math.sin(t*.002)*3,28,0,0,Math.PI*2);ctx.stroke();}ctx.restore();
}
document.addEventListener('DOMContentLoaded',()=>{
 const modes={
 balanced:{title:'Calm waters',subtitle:'Every service has room to breathe',story:'Small requests flow through Portal, Search and Database. Follow a fish to inspect its simulated resources.',phase:'Steady flow',cpu:[18,27,24,21,9,16],mem:[24,43,38,26,19,28],gpu:24,vram:5.6,ram:11.4,accent:'#80dcc9',select:'portal'},
 inference:{title:'AI inference',subtitle:'A model comes alive',story:'The Model Engine is serving an imagined AI request. GPU load and VRAM rise together while the rest of the stack stays responsive.',phase:'Generating a response',cpu:[32,48,25,18,13,30],mem:[31,68,39,27,24,34],gpu:86,vram:12.8,ram:19.2,accent:'#bba6ee',select:'engine'},
 traffic:{title:'Traffic surge',subtitle:'Follow the pressure through the stack',story:'A simulated burst reaches Portal, Database and Background Worker. Use Attention to find the services carrying the pressure.',phase:'Requests arriving',cpu:[91,45,78,64,38,83],mem:[63,52,77,46,56,65],gpu:39,vram:7.4,ram:22.6,accent:'#f0bd83',select:'portal'},
 recovery:{title:'Recovery drill',subtitle:'Observe, interrupt, reconnect, recover',story:'A 24-second scripted drill takes Database offline, then restores it. Watch its fish, the service state and the activity trail.',phase:'Observe',cpu:[28,25,32,22,18,29],mem:[30,42,41,29,25,35],gpu:22,vram:5.9,ram:13.2,accent:'#ef9eab',select:'database'}
 };
 const section=document.createElement('section');section.id='demo-studio';section.className='demo-studio';section.setAttribute('aria-label','Simulation studio');section.innerHTML='<div class="demo-intro"><div class="demo-eyebrow"><i></i> SIMULATION STUDIO <span>ALL DATA SIMULATED</span></div><div class="demo-heading"><h2>Small signals. A living ocean.</h2><button type="button" id="demo-pause" aria-pressed="false">Pause simulation</button></div><p>Choose a workload. See how the whole ecosystem responds.</p></div><div class="demo-scenes" role="group" aria-label="Demo scenarios">'+Object.entries(modes).map(([id,m],i)=>'<button type="button" data-demo-mode="'+id+'" aria-pressed="false"><span class="demo-scene-number">0'+(i+1)+'</span><span class="demo-scene-copy"><strong>'+m.title+'</strong><small>'+m.subtitle+'</small></span><span class="demo-scene-icon" aria-hidden="true">'+['≈','✧','↗','↻'][i]+'</span></button>').join('')+'</div><div class="demo-story"><div><strong id="demo-phase"></strong><p id="demo-description"></p></div><div class="demo-cycle"><div class="demo-progress" role="progressbar" aria-label="Simulated workload cycle" aria-valuemin="0" aria-valuemax="100"><i></i></div><small id="demo-clock"></small></div>';
 const restart=document.createElement('button');restart.type='button';restart.id='demo-restart';restart.textContent='Restart scene';section.querySelector('.demo-story').append(restart);
 document.querySelector('.summary-strip').after(section);
 let mode='balanced',seconds=0,paused=false,lastPhase='',overrides=new Map();const gib=1024**3,limits=[2,8,4,2,1,2];
 function update(){
  if(state.source!=='demo')return;const m=modes[mode],cycle=seconds%24;let phase=m.phase,offline=false;
  if(mode==='recovery'){phase=cycle<6?'01 · Observe':cycle<13?'02 · Database offline':cycle<18?'03 · Reconnected':'04 · Healthy again';offline=cycle>=6&&cycle<13;}
  state.demoMode=mode;state.demoAccent=m.accent;state.demoScenarioTitle=m.title;state.demoPaused=paused;if(paused&&!state.demoPausedAt)state.demoPausedAt=performance.now();if(!paused)state.demoPausedAt=null;
  const rows=demoResidents.map((r,i)=>{const manual=overrides.get(r[0]),down=manual==='outage'||(r[0]==='database'&&offline),wave=Math.sin(seconds*.65+i*.9)*3;let cpu=Math.max(0,Math.min(100,m.cpu[i]+wave)),mem=Math.max(0,Math.min(100,m.mem[i]+Math.sin(seconds*.3+i)*1.8));if(mode==='recovery'&&r[0]==='worker'&&offline)cpu=81+wave;if(manual==='spike')cpu=94;if(down){cpu=0;mem=0;}return {id:r[0],name:r[1],fullName:r[1],cpu,mem,memUsedBytes:Math.round(limits[i]*gib*mem/100),memLimitBytes:limits[i]*gib,color:palette[i],offline:down,unknown:false,health:'simulated',state:down?'exited':'running'};});
  const used=(m.ram+Math.sin(seconds*.22)*.3)*gib,gpu=Math.max(0,Math.min(100,m.gpu+Math.sin(seconds*.5)*5)),vram=(m.vram+Math.sin(seconds*.23)*.16)*gib;
  state.demoHardware={source:'simulated',sampledAt:new Date().toISOString(),memoryLabel:'Demo host RAM · simulated',memory:{label:'Demo host RAM · simulated',totalBytes:32*gib,usedBytes:used,availableBytes:32*gib-used,percent:used/(32*gib)*100},runtimeMemory:null,gpus:[{id:'demo-gpu',name:'Model accelerator · simulated',utilization:gpu,memoryUsedBytes:vram,memoryTotalBytes:16*gib,temperatureC:39+gpu*.31,powerW:25+gpu*1.55}],gpuStatus:'ok',warnings:[]};
  setServices(rows);state.fish.forEach(sampleFish);renderInspector();paintDemoHardware();
  section.style.setProperty('--demo-accent',m.accent);section.querySelectorAll('[data-demo-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.demoMode===mode)));$('demo-phase').textContent=m.title+' / '+phase;$('demo-description').textContent=m.story;$('demo-clock').textContent=(paused?'Paused':'Evolving')+' · '+Math.floor(cycle)+' / 24 s';const progress=section.querySelector('[role="progressbar"]');progress.setAttribute('aria-valuenow',String(Math.round(cycle/24*100)));progress.setAttribute('aria-valuetext',phase);progress.querySelector('i').style.width=(cycle/24*100)+'%';$('demo-pause').textContent=paused?'Resume simulation':'Pause simulation';$('demo-pause').setAttribute('aria-pressed',String(paused));$('tank-source').textContent='Simulated · '+m.title;document.querySelector('.tank-caption').textContent=m.title+' · simulated ecosystem';sourceMessage('Simulated workload · '+(paused?'paused':phase.toLowerCase()));
  if(phase!==lastPhase){lastPhase=phase;note('simulation','Demo: '+m.title+' / '+phase+'.');}
 }
 function choose(id){mode=id;seconds=0;lastPhase='';overrides.clear();state.attentionMode=false;state.selectedId=modes[id].select;update();}
 function sourceChanged(){const demo=$('data-source').value==='demo';document.body.classList.toggle('simulation-mode',demo);section.classList.toggle('hidden',!demo);if(demo){mode='balanced';seconds=0;paused=false;lastPhase='';overrides.clear();update();}else{state.demoHardware=null;document.querySelector('.tank-caption').textContent='Service ecosystem';}}
 aquariumDemo={action(action){if(state.source!=='demo')return;if(action==='recover'){mode='balanced';seconds=0;overrides.clear();lastPhase='';note('recovery','Demo: all services recovered to a balanced workload.');}else if(state.selectedId){overrides.set(state.selectedId,action==='outage'?'outage':'spike');note('incident','Demo: '+(state.fish.find(f=>f.id===state.selectedId)?.name||'Service')+(action==='outage'?' is offline.':' CPU is held at 94%.'));}update();}};
 section.querySelectorAll('[data-demo-mode]').forEach(b=>b.onclick=()=>choose(b.dataset.demoMode));$('demo-pause').onclick=()=>{paused=!paused;update();};$('demo-restart').onclick=()=>choose(mode);$('data-source').addEventListener('change',sourceChanged);sourceChanged();setInterval(()=>{if(state.source==='demo'&&!paused){seconds+=1.5;update();}},1500);

function paintDemoHardware(){
 if(state.source!=='demo'||!state.demoHardware)return;
 const h=state.demoHardware,r=h.memory,g=h.gpus[0];state.hardware=h;
 const area=document.getElementById('machine-resources');if(!area)return;
 const cards=area.querySelectorAll('.hw-card');if(cards.length<2)return;
 const ram=cards[0],gpu=cards[1],values=gpu.querySelectorAll('.hw-gpu-stats strong');
 ram.querySelector('h2').textContent=h.memoryLabel;
 ram.querySelector('.hw-value').textContent=hardwarePair(r.usedBytes,r.totalBytes);
 ram.querySelector('.hw-meter i').style.width=r.percent+'%';
 ram.querySelector('.hw-detail').textContent=metric(r.percent)+' used · '+hardwareBytes(r.availableBytes)+' available';
 gpu.querySelector('h2').textContent=g.name;
 if(values.length===2){values[0].textContent=metric(g.utilization);values[1].textContent=hardwarePair(g.memoryUsedBytes,g.memoryTotalBytes);}
 const meter=gpu.querySelector('.hw-meter i');if(meter)meter.style.width=(g.memoryUsedBytes*100/g.memoryTotalBytes)+'%';
 gpu.querySelector('.hw-detail').textContent='Temperature '+g.temperatureC.toFixed(0)+' °C · Power '+g.powerW.toFixed(1)+' W';
 gpu.querySelector('.hw-scope').textContent='Simulated device · follows the selected scene';
 area.querySelector('.hardware-heading small').textContent='Simulated · '+state.demoScenarioTitle+(state.demoPaused?' · paused':' · evolving');
}

},{once:true});
