'use strict';
const $ = id => document.getElementById(id);
const currency = value => value == null ? '—' : Math.abs(value) >= 1e9 ? `$${(value/1e9).toFixed(2)}B` : Math.abs(value) >= 1e6 ? `$${(value/1e6).toFixed(2)}M` : `$${Number(value).toLocaleString('en-US', {maximumFractionDigits:0})}`;
const pct = value => value == null ? '—' : `${value >= 0 ? '+' : ''}${Number(value).toFixed(2)}%`;
const node = (tag, cls, text) => { const n=document.createElement(tag); if(cls)n.className=cls;if(text!==undefined)n.textContent=text; return n; };

async function refreshHealth(){
 try{
  const res=await fetch('/api/health'); if(!res.ok)throw Error('API unavailable');
  const d=await res.json();
  $('health-label').textContent='API online'; $('api-state').textContent='Online';
  $('sec-state').textContent=d.sec_configured?'Configured':'Needs contact';
  $('ollama-state').textContent=d.ollama_enabled?'Enabled':'Disabled';
  $('groq-state').textContent=d.groq_configured?'Configured':'Not configured';
 }catch{ $('health-label').textContent='Offline';$('api-state').textContent='Unavailable'; }
}
function render(data){
 $('error-panel').hidden=true; $('result-panel').hidden=false;
 $('company-title').textContent=`${data.company} · ${data.ticker}`;
 $('result-meta').textContent=`${data.financials.length} annual period(s) · Generated ${new Date(data.generated_at).toLocaleString()}`;
 $('result-tag').textContent=data.data_kind==='synthetic_demo'?'FICTIONAL DEMO':'LIVE SEC DATA';
 const warnings=data.warnings||[]; $('warning-banner').hidden=warnings.length===0;$('warning-banner').textContent=warnings.join(' ');
 const latest=data.financials[0]||{};
 const items=[['Revenue',currency(latest.revenue),'USD, annual'],['Revenue growth',pct(latest.revenue_growth_pct),'Year over year'],['Operating margin',pct(latest.operating_margin_pct),'Operating profit / revenue'],['Net income',currency(latest.net_income),'USD, annual']];
 $('kpis').replaceChildren(...items.map(([label,value,hint])=>{let c=node('div','kpi');c.append(node('span','',label),node('strong','',value),node('small','',hint));return c;}));
 $('summary').textContent=data.summary;
 $('model-info').textContent=`Explanation: ${data.llm.provider} (${data.llm.model})${data.llm.fallback_used?' · fallback used':''}${data.llm.note?' · '+data.llm.note:''}`;
 const sorted=[...data.financials].reverse();const max=Math.max(...sorted.map(r=>r.revenue||0),1);
 $('chart').replaceChildren(...sorted.map(row=>{
   const c=node('div','chart-item'); const bar=node('div','bar');bar.style.height=`${Math.max(3,(Math.max(0,row.revenue||0)/max)*130)}px`;
   c.append(node('div','val',currency(row.revenue)),bar,node('div','period',row.period_end));return c;
 }));
 $('finance-body').replaceChildren(...data.financials.map(row=>{
  const tr=node('tr');[row.period_end,currency(row.revenue),currency(row.operating_income),currency(row.net_income),pct(row.revenue_growth_pct),pct(row.operating_margin_pct)].forEach(v=>tr.append(node('td','',v)));return tr;
 }));
 const sources=[];const seen=new Set();
 for(const year of data.financials)for(const s of year.sources||[]){const key=`${s.accession}:${s.metric}`;if(seen.has(key))continue;seen.add(key);
   try{const u=new URL(s.source_url);if(u.protocol!=='https:' || !(u.hostname==='sec.gov'||u.hostname.endsWith('.sec.gov')))continue;
     const link=node('a','source-link',`${s.period_end} · ${s.metric} ↗`);link.href=u.href;link.target='_blank';link.rel='noopener noreferrer';link.title=`${s.form} · ${s.accession}`;sources.push(link);
   }catch{} }
 $('sources').replaceChildren(...(sources.length?sources:[node('p','muted','No real SEC filings for synthetic demo.') ]));
 $('result-panel').scrollIntoView({behavior:'smooth',block:'start'});
}
async function submit(e){
 e.preventDefault();$('error-panel').hidden=true; const button=$('submit-btn');button.disabled=true;button.firstElementChild.textContent='Researching…';
 const req={ticker:$('ticker').value.trim().toUpperCase(),question:$('question').value.trim(),years:Number($('years').value),provider:$('provider').value,privacy:$('privacy').value};
 try{
  const headers={'Content-Type':'application/json'};if($('api-key').value)headers['X-API-Key']=$('api-key').value;
  const response=await fetch('/api/research',{method:'POST',headers,body:JSON.stringify(req)});
  const result=await response.json();
  if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'Check the ticker and settings.');
  render(result);
 }catch(err){$('error-panel').hidden=false;$('error-panel').textContent=`Research failed: ${err.message}`;}
 finally{button.disabled=false;button.firstElementChild.textContent='Run financial analysis';}
}
$('sample-btn').addEventListener('click',()=>{$('ticker').value='DEMO';$('provider').value='auto';});
$('research-form').addEventListener('submit',submit);
refreshHealth();
