'use strict';
// Separate dashboard adapter: never mix application logic or secrets into UI rendering.
(() => {
 const el=id=>document.getElementById(id);
 const line=(parent,label,detail='')=>{
   const div=document.createElement('div');div.className='lab-row';
   const strong=document.createElement('strong');strong.textContent=label;div.append(strong);
   if(detail){const p=document.createElement('div');p.textContent=detail;div.append(p);}
   parent.append(div);return div;
 };
 const clear=id=>{const parent=el(id);parent.replaceChildren();return parent;};
 const payload=()=>({ticker:el('ticker').value.trim().toUpperCase(),question:el('question').value.trim(),years:Number(el('years').value),privacy:el('privacy').value,provider:el('provider').value});
 const headers=()=>{const h={'Content-Type':'application/json'};const key=el('api-key').value;if(key)h['X-API-Key']=key;return h;};
 async function api(route,body){
   const response=await fetch(route,{method:body?'POST':'GET',headers:headers(),body:body?JSON.stringify(body):undefined});
   if(!response.ok){let message='Request failed';try{const d=await response.json();message=typeof d.detail==='string'?d.detail:JSON.stringify(d.detail);}catch{}throw Error(message);}
   return response.json();
 }
 async function run(id,callback){const parent=clear(id);line(parent,'Working…');try{await callback(clear(id));}catch(error){line(clear(id),'Could not complete',error.message);}}
 const link=(parent,url,label)=>{
   try {const parsed=new URL(url);if(parsed.protocol!=='https:'||!(['sec.gov','data.sec.gov','www.sec.gov'].includes(parsed.hostname)))return;
     const a=document.createElement('a');a.href=parsed.href;a.target='_blank';a.rel='noopener noreferrer';a.textContent=label;parent.append(a);
   }catch{}
 };
 el('agent-run').addEventListener('click',()=>run('agent-output',async parent=>{
   const data=await api('/api/agent/research',payload());
   line(parent,`Verification: ${data.verification.passed?'passed':'needs review'}`,`${data.verification.checks} arithmetic and source checks. Does not certify AI prose.`);
   for(const step of data.steps)line(parent,`${step.tool} · ${step.status}`,step.detail);
   if(data.filing.evidence.length){
     const details=document.createElement('details');const s=document.createElement('summary');s.textContent=`${data.filing.evidence.length} supporting filing excerpts`;details.append(s);
     for(const evidence of data.filing.evidence){const wrap=document.createElement('div');wrap.className='lab-row';line(wrap,evidence.locator,evidence.excerpt);link(wrap,evidence.filing_url,'View original SEC filing ↗');details.append(wrap);}
     parent.append(details);
   }
   line(parent,'Research summary',data.executive_summary);
   for(const warning of data.verification.issues)line(parent,'Verification issue',warning);
 }));
 el('compare-form').addEventListener('submit',event=>{event.preventDefault();run('compare-output',async parent=>{
   const data=await api('/api/compare',{left:el('peer-a').value.trim(),right:el('peer-b').value.trim(),years:Number(el('years').value)});
   line(parent,`${data.left.ticker} versus ${data.right.ticker}`,`${data.left.period_end} vs ${data.right.period_end}`);
   for(const metric of data.metrics){const v=x=>x==null?'Unavailable':metric.unit==='percent'?`${x.toFixed(2)}%`:Number(x).toLocaleString('en-US',{maximumFractionDigits:0});line(parent,metric.label,`${v(metric.left_value)} / ${v(metric.right_value)} · difference ${v(metric.difference)}`);}
   for(const warning of data.caveats)line(parent,'Caveat',warning);
 });});
 el('dcf-form').addEventListener('submit',event=>{event.preventDefault();run('dcf-output',async parent=>{
   const req={starting_unlevered_fcf:Number(el('fcf').value),fcf_growth_pct:Number(el('dcf-growth').value),discount_rate_pct:Number(el('dcf-discount').value),terminal_growth_pct:Number(el('dcf-terminal').value),forecast_years:5};
   const data=await api('/api/valuation/dcf',req);const result=data.result;
   line(parent,'Illustrative enterprise value',new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(result.implied_enterprise_value));
   line(parent,'Terminal component',`${result.terminal_share_pct}% of enterprise value`);
   line(parent,'Assumptions',`${req.fcf_growth_pct}% cash flow growth, ${req.discount_rate_pct}% discount rate, ${req.terminal_growth_pct}% terminal growth`);
   line(parent,'Important',result.disclaimer);
 });});
 async function exportFile(type){const parent=clear('export-output');line(parent,'Preparing download…');try{
   const response=await fetch(`/api/reports/research.${type}`,{method:'POST',headers:headers(),body:JSON.stringify(payload())});
   if(!response.ok){const d=await response.json();throw Error(typeof d.detail==='string'?d.detail:'Export failed');}
   const blob=await response.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`scarascope-${payload().ticker}.${type}`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),5000);
   line(clear('export-output'),'Download ready',`${type.toUpperCase()} report · ${blob.size.toLocaleString()} bytes`);
 }catch(err){line(clear('export-output'),'Download failed',err.message);}}
 el('export-pdf').addEventListener('click',()=>exportFile('pdf'));
 el('export-xlsx').addEventListener('click',()=>exportFile('xlsx'));
 el('eval-run').addEventListener('click',()=>run('export-output',async parent=>{
   const result=await api('/api/evaluation/deterministic');
   line(parent,`${result.passed}/${result.total} golden arithmetic cases passed`,result.limitation);
   for(const item of result.results)line(parent,`${item.passed?'✓':'✗'} ${item.label}`,`Expected ${item.expected??'missing'} · observed ${item.actual??'missing'}`);
 }));
 async function watches(){await run('watch-output',async parent=>{
   const data=await api('/api/watchlist');
   if(!data.items.length)line(parent,'No saved tickers yet');
   for(const item of data.items)line(parent,item.ticker,'Saved locally · no background alerts');
 });}
 el('watch-add').addEventListener('click',async()=>{try{await api('/api/watchlist',{ticker:el('ticker').value.trim()});await watches();}catch(err){line(clear('watch-output'),'Could not save ticker',err.message);}});
 el('watch-refresh').addEventListener('click',watches);
 el('watch-check').addEventListener('click',()=>run('watch-output',async parent=>{
   const result=await api('/api/watchlist/check',{});
   if(!result.items.length)line(parent,'Add a ticker before checking SEC filings.');
   for(const item of result.items)line(parent,`${item.ticker} · ${item.status}`,`${item.form||'—'} · ${item.accession||'—'} · ${item.filed||'—'}`);
   line(parent,'Scope',result.caveat);
 }));
})();
