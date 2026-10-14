(() => {
  try {
    const SEC = '{{sec}}', IDX = {{idx}};
    const norm = s => (s || '').replace(/\s+/g, '').replace(/[*＊]$/, '');
    const cards = Array.from(document.querySelectorAll('div')).filter(e => /apply-form-array-card__/.test(e.className) && !/content/.test(e.className));
    const secOf = (card) => {
      const r = card.closest('[class*=applyFormModuleWrapper-right]');
      const root = r ? r.parentElement : null;
      const t = root ? root.querySelector('[class*=applyFormModuleWrapper-title]') : null;
      return t ? (t.textContent || '').trim() : '?';
    };
    const map = cards.map((c, i) => i + ':' + secOf(c));
    if (!SEC || SEC === '-') return JSON.stringify({ map });
    const inSec = cards.filter(c => secOf(c) === SEC);
    const card = inSec[IDX];
    if (!card) return JSON.stringify({ map, err: 'NOCARD n=' + inSec.length });
    const out = [];
    card.querySelectorAll('.ud-formily-item').forEach(it => {
      const lab = norm((it.querySelector('.ud-formily-item-label-content') || {}).innerText);
      if (!lab) return;
      const ins = Array.from(it.querySelectorAll('input:not([type=hidden]),textarea'));
      const sel = it.querySelector('.ud__select');
      const v = sel ? 'SEL:' + (sel.textContent || '').replace(/\s+/g, '').slice(0, 8)
        : ins.map(x => x.tagName.toLowerCase() + '/' + (x.type || '') + (x.maxLength > 0 ? '/max' + x.maxLength : '') + '=' + x.value.slice(0, 18)).join(' ; ');
      const cnt = (it.textContent || '').match(/\d+\s*\/\s*\d+/);
      out.push(lab + ': ' + v + (cnt ? ' cnt=' + cnt[0] : ''));
    });
    return JSON.stringify({ map, card: out });
  } catch (e) { return 'err:' + e.message; }
})()
