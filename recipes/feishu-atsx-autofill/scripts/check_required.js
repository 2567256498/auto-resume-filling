(() => {
  try {
    const norm = s => (s || '').replace(/\s+/g, '').replace(/[*＊]$/, '');
    const out = [];
    document.querySelectorAll('.ud-formily-item').forEach(it => {
      const lab = norm((it.querySelector('.ud-formily-item-label-content') || {}).innerText);
      if (!it.querySelector('.ud-formily-item-asterisk')) return;
      const ins = Array.from(it.querySelectorAll('input:not([type=hidden]),textarea'));
      const sel = it.querySelector('.ud__select');
      const radio = it.querySelector('input[type=radio]:checked');
      const isUpload = !!it.querySelector('.atsx-upload') || ins.some(x => x.type === 'file');
      const fileOk = ins.some(x => x.type === 'file' && x.files && x.files.length);
      let has = false, how = '';
      if (sel && (sel.textContent || '').trim()) { has = true; how = 'sel'; }
      if (!has && ins.some(x => x.value)) { has = true; how = 'input'; }
      if (!has && radio) { has = true; how = 'radio'; }
      if (!has && !isUpload) {
        const c = it.querySelector('.ud-formily-item-control-content-component');
        if (c && (c.textContent || '').trim()) { has = true; how = 'readonly'; }
      }
      if (!has && fileOk) { has = true; how = 'file'; }
      out.push(lab + '=' + (has ? 'OK(' + how + ')' : 'EMPTY'));
    });
    return JSON.stringify(out);
  } catch (e) { return 'err:' + e.message; }
})()
