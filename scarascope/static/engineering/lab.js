'use strict';
(() => {
 const el = id => document.getElementById(id);
 const node = (tag, text, className) => { const e=document.createElement(tag);e.textContent=String(text??'');if(className)e.className=className;return e; };
 const headers = () => {const h={};const key=el('key').value.trim();if(key)h['X-API-Key']=key;return h;};
 const request = async path => {const r=await fetch(path,{headers:headers(),cache:'no-store'});if(!r.ok)throw Error(`Request failed (HTTP ${r.status})`);return r.json();};
 const clear=id=>{el(id).replaceChildren();return el(id);};
 let suites={};
 function renderCases(name){const parent=clear('cases');const suite=suites[name];if(!suite)return;
  for(const c of suite.results||suite.cases||[]){const tr=document.createElement('tr');let expected=c.expected??c.expected_section??c.expected_provider??'—';let actual=c.observed??c.actual??c.retrieved_section??c.observed_provider??'—';
   const cells=[c.id??c.label??c.question,c.passed?'PASS':'FAIL',expected,actual];cells.forEach((v,i)=>tr.append(node('td',v,i===1?(c.passed?'pass':'fail'):'')));parent.append(tr);
  }
 }
 function renderReport(data){const status=el('status');status.textContent=`${data.status.toUpperCase()} · ${new Date(data.generated_at).toLocaleString()}`;
  suites=data.suites;const grid=clear('metric-grid');const labels={financial:'Historical financial figures',arithmetic:'Arithmetic smoke tests',retrieval:'Lexical retrieval fixtures',reliability:'Simulated outages / privacy'};
  for(const [name,score] of Object.entries(suites)){const box=node('div','','metric');box.append(node('strong',`${score.passed}/${score.total}`));box.append(node('small',labels[name]??name));box.append(node('span',`${score.total?Math.round(score.passed/score.total*100):0}% fixture pass rate`,'detail'));grid.append(box);}
  el('integrity').textContent=`Dataset SHA-256: ${data.suites.financial.dataset_sha256} · Python ${data.runtime.python} · ${data.suites.financial.companies.join(', ')} · offline results only.`;
  const selector=el('suite');selector.replaceChildren();Object.keys(suites).forEach(name=>{const option=node('option',name);option.value=name;selector.append(option);});selector.disabled=false;selector.value='financial';renderCases('financial');
  const sources=clear('sources');for(const url of data.suites.financial.sources){try{const parsed=new URL(url);if(parsed.protocol!=='https:'||parsed.hostname!=='www.sec.gov')continue;const a=node('a',parsed.pathname.split('/').at(-1));a.href=parsed.href;a.target='_blank';a.rel='noopener noreferrer';a.className='source-link';sources.append(a);}catch{}}
  const limits=clear('limitations');for(const text of data.limitations)limits.append(node('li',text));
 }
 function renderHistory(data){const parent=clear('history');if(!data.items.length){parent.append(node('p','No saved runs yet. Use the benchmark CLI to save one.','muted'));return;}for(const item of data.items){const div=node('div',`${item.generated_at}: ${item.status} (${item.file})`);parent.append(div);}}
 function renderRuntime(data){const parent=clear('runtime');const counters=Object.entries(data.counters);if(!counters.length)parent.append(node('div','No live provider calls recorded yet.'));for(const [event,count]of counters)parent.append(node('div',`${event}: ${count}`));}
 async function refresh(){el('run').disabled=true;el('error').hidden=true;el('status').textContent='Running offline benchmark…';try{const [report,history,runtime]=await Promise.all([request('/api/engineering/benchmark'),request('/api/engineering/history'),request('/api/engineering/runtime')]);renderReport(report);renderHistory(history);renderRuntime(runtime);}catch(e){el('status').textContent='Unable to run benchmark';el('error').textContent=e.message;el('error').hidden=false;}finally{el('run').disabled=false;}}
 el('run').addEventListener('click',refresh);el('suite').addEventListener('change',e=>renderCases(e.target.value));
})();
