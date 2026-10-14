(() => {
  try {
    const SEC = '{{sec}}';
    const norm = s => (s || '').replace(/\s+/g, '').replace(/[*＊]$/, '');
    const cards = Array.from(document.querySelectorAll('div')).filter(e => /apply-form-array-card__/.test(e.className) && !/content/.test(e.className));
    const secOf = (card) => {
      const r = card.closest('[class*=applyFormModuleWrapper-right]');
      const root = r ? r.parentElement : null;
      const t = root ? root.querySelector('[class*=applyFormModuleWrapper-title]') : null;
      return t ? (t.textContent || '').trim() : '?';
    };
    const list = cards.filter(c => secOf(c) === SEC);
    return JSON.stringify(list.map((c, i) => {
      const parts = [];
      c.querySelectorAll('.ud-formily-item').forEach(it => {
        const lab = norm((it.querySelector('.ud-formily-item-label-content') || {}).innerText);
        if (!lab || parts.some(p => p.indexOf(lab + '=') === 0)) return;
        const ins = Array.from(it.querySelectorAll('input:not([type=hidden]),textarea'));
        const sel = it.querySelector('.ud__select');
        const v = sel ? 'SEL:' + (sel.textContent || '').replace(/\s+/g, '').slice(0, 8)
          : ins.map(x => (x.value || '')).filter(x => x).join('/').slice(0, 20);
        parts.push(lab + '=' + v);
      });
      return i + ': ' + parts.join(' | ');
    }));
  } catch (e) { return 'err:' + e.message; }
})()
