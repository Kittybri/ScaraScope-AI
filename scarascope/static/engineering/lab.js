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
  const qa=data.qa_retrieval;
  const comparison=clear('qa-comparison');
  const format=x=>`${(x*100).toFixed(1)}%`;
  const misses=clear('qa-misses');
  for(const [method,result] of Object.entries(qa.methods)){
   const m=result.metrics;const tr=document.createElement('tr');
   [method.toUpperCase(), format(m.recall_at_1),format(m.recall_at_3),format(m.recall_at_5),m.mrr_at_5.toFixed(3),`${m.correct_abstentions}/${m.unanswerable}`].forEach(v=>tr.append(node('td',v)));
   comparison.append(tr);
   const failures=result.cases.filter(c=>!c.passed);
   misses.append(node('div',`${method}: ${failures.length} cases missed · ${failures.map(f=>f.id).join(', ')||'none'}`));
  }
  el('qa-integrity').textContent=`${qa.question_count} held-out questions · ${qa.methods.lexical.metrics.answerable} answerable / ${qa.methods.lexical.metrics.unanswerable} unanswerable · ${qa.documents} reconstructed passages · dataset SHA-256 ${qa.dataset_sha256}. ${qa.limitations.join(' ')}`;
  const sources=clear('sources');for(const url of data.suites.financial.sources){try{const parsed=new URL(url);if(parsed.protocol!=='https:'||parsed.hostname!=='www.sec.gov')continue;const a=node('a',parsed.pathname.split('/').at(-1));a.href=parsed.href;a.target='_blank';a.rel='noopener noreferrer';a.className='source-link';sources.append(a);}catch{}}
  const limits=clear('limitations');for(const text of data.limitations)limits.append(node('li',text));
 }
 function renderCorpus(data){
  const parent=clear('corpus-status');
  parent.append(node('p',`${data.snapshots} validated filing snapshots · ${data.annotations.reviewed??0} reviewed questions · ${data.annotations.second_reviewed??0} with second review · ${data.annotations.unreviewed??0} awaiting review.`));
  parent.append(node('p',data.note,'muted'));
  if(data.validation_error)parent.append(node('p',`Integrity validation failed: ${data.validation_error}`,'fail'));
  for(const src of data.sources)parent.append(node('small',`${src.cik} · ${src.form} · accession ${src.accession} · SHA ${src.digest.slice(0,12)}`));
 }
 function renderRealCorpus(data){
  const parent=clear('real-corpus-evaluation');
  parent.append(node('p',`Real SEC corpus: ${data.status||'not_evaluated'} · ${data.review_policy||'one_reviewer'} review policy.`));
  if(data.status!=='evaluated'){
   parent.append(node('p',data.reason||'No complete reviewed answerable and unanswerable question set is available. No accuracy score can be reported.','muted'));
   return;
  }
  parent.append(node('p',`${data.reviewed_in_split} scored questions; ${data.excluded_unreviewed} unreviewed excluded; ${data.excluded_lacking_second_review||0} lacking required second review.`));
  parent.append(node('small',`Dataset SHA-256: ${data.dataset_sha256}`));
  const table=document.createElement('table');
  const h=document.createElement('tr');
  ['Retriever','Recall@3','MRR@5','Correct abstentions','Failures'].forEach(label=>h.append(node('th',label)));
  table.append(h);
  for(const [name,result] of Object.entries(data.methods||{})){
   const m=result.metrics,row=document.createElement('tr');
   [name,`${(100*m.recall_at_3).toFixed(1)}%`,m.mrr_at_5.toFixed(3),`${m.correct_abstentions}/${m.unanswerable}`,result.cases.filter(c=>!c.passed).map(c=>c.id).join(', ')||'none'].forEach(value=>row.append(node('td',value)));
   table.append(row);
  }
  parent.append(table);
  parent.append(node('p','Retrieved evidence ranking only, not independent AI answer correctness. Reviewer aliases do not prove independent review.','fine'));
 }
 function renderHistory(data){const parent=clear('history');if(!data.items.length){parent.append(node('p','No saved runs yet. Use the benchmark CLI to save one.','muted'));return;}for(const item of data.items){const div=node('div',`${item.generated_at}: ${item.status} (${item.file})`);parent.append(div);}}
 function renderRuntime(data){const parent=clear('runtime');const counters=Object.entries(data.counters);if(!counters.length)parent.append(node('div','No live provider calls recorded yet.'));for(const [event,count]of counters)parent.append(node('div',`${event}: ${count}`));}
 async function refresh(){el('run').disabled=true;el('error').hidden=true;el('status').textContent='Running offline benchmark…';try{const [report,history,runtime,corpus,realCorpus]=await Promise.all([request('/api/engineering/benchmark'),request('/api/engineering/history'),request('/api/engineering/runtime'),request('/api/engineering/corpus-status'),request('/api/engineering/corpus-evaluation?require_second_review='+String(el('require-second-review').checked))]);
   if(el('embed-eval').checked){report.qa_retrieval=await request('/api/engineering/retrieval-comparison?include_semantic=true');}
   renderReport(report);renderHistory(history);renderRuntime(runtime);renderCorpus(corpus);renderRealCorpus(realCorpus);}catch(e){el('status').textContent='Unable to run benchmark';el('error').textContent=e.message;el('error').hidden=false;}finally{el('run').disabled=false;}}
 el('run').addEventListener('click',refresh);el('suite').addEventListener('change',e=>renderCases(e.target.value));
})();
