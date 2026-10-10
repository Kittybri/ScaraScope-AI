'use strict';
// Browser-only adapter. No financial logic, LLM prompts or secrets live here.
(() => {
  const $ = id => document.getElementById(id);
  const form = $('document-form');
  if (!form) return;
  const output = $('document-output');
  const add = (parent, tag, message, className = '') => {
    const node = document.createElement(tag);
    node.textContent = message;
    if (className) node.className = className;
    parent.append(node);
    return node;
  };
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const ticker = $('ticker').value.trim().toUpperCase();
    const question = $('document-question').value.trim();
    const body = {
      ticker, question, form: $('document-form-type').value,
      top_k: 5, retrieval_strategy: $('document-retrieval').value,
      provider: $('provider').value, privacy: $('privacy').value,
    };
    output.replaceChildren();
    add(output, 'p', 'Searching filing excerpts…');
    $('document-submit').disabled = true;
    try {
      const headers = {'Content-Type': 'application/json'};
      const key = $('api-key').value;
      if (key) headers['X-API-Key'] = key;
      const response = await fetch('/api/documents/ask', {method: 'POST', headers, body: JSON.stringify(body)});
      const data = await response.json();
      if (!response.ok) throw Error(typeof data.detail === 'string' ? data.detail : 'Document search failed.');
      output.replaceChildren();
      add(output, 'h4', `${data.ticker} · ${data.form} · ${data.status.replaceAll('_', ' ')}`);
      add(output, 'p', data.answer, 'document-answer');
      add(output, 'p', `Source: ${data.data_kind === 'synthetic_demo' ? 'Fictional demonstration' : 'SEC EDGAR'} · Explanation: ${data.provider}`, 'muted');
      if (data.evidence.length) {
        add(output, 'h4', `Retrieved passages (${data.evidence.length})`);
        for (const passage of data.evidence) {
          const card = add(output, 'div', '', 'lab-row');
          add(card, 'strong', `${passage.label} · ${passage.item} · ${passage.section_title}`);
          add(card, 'p', passage.excerpt);
          add(card, 'small', `${passage.locator} · offset ${passage.start_char} · accession ${passage.accession}`);
          try {
            const url = new URL(passage.filing_url);
            if (url.protocol === 'https:' && ['www.sec.gov','sec.gov'].includes(url.hostname)) {
              const link = document.createElement('a');
              link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
              link.textContent = 'Open original SEC filing ↗'; card.append(link);
            }
          } catch (_) { /* deliberately exclude invalid or demo URLs */ }
        }
      }
      for (const warning of data.warnings) add(output, 'p', warning, 'muted');
    } catch (error) {
      output.replaceChildren();
      add(output, 'p', `Unable to answer: ${error.message}`);
    } finally {
      $('document-submit').disabled = false;
    }
  });
})();
