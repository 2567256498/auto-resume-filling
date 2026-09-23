(() => {
  try {
    const SEC = '{{sec}}', IDX = {{idx}}, spec = '{{text}}';
    const norm = s => (s || '').replace(/\s+/g, '').replace(/[*＊]$/, '');
    const cards = Array.from(document.querySelectorAll('div')).filter(e => /apply-form-array-card__/.test(e.className) && !/content/.test(e.className));
    const secOf = (card) => {
      const r = card.closest('[class*=applyFormModuleWrapper-right]');
      const root = r ? r.parentElement : null;
      const t = root ? root.querySelector('[class*=applyFormModuleWrapper-title]') : null;
      return t ? (t.textContent || '').trim() : '?';
    };
    const inSec = cards.filter(c => secOf(c) === SEC);
    const card = inSec[IDX];
    if (!card) return 'NOCARD n=' + inSec.length + ' all=' + cards.map(secOf).join(',');
    const setV = (el, v) => {
      const proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
      el.focus();
      setter.call(el, v);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      el.blur();
      return el.value;
    };
    const out = [];
    spec.split('||').forEach(p => {
      const i = p.indexOf('=');
      if (i < 0) return;
      const lab = p.slice(0, i), val = p.slice(i + 1);
      const fld = Array.from(card.querySelectorAll('.ud-formily-item')).find(e => norm((e.querySelector('.ud-formily-item-label-content') || {}).innerText) === lab);
      if (!fld) { out.push(lab + '=NF'); return; }
      const ins = Array.from(fld.querySelectorAll('input:not([type=hidden]),textarea'));
      if (lab === '起止时间') {
        const vs = val.split('~~'), r = [];
        ins.forEach((el, k) => { if (vs[k] !== undefined && vs[k] !== '') r.push(setV(el, vs[k])); });
        out.push('起止时间=' + r.join('/'));
      } else {
        if (!ins.length) { out.push(lab + '=NOIN'); return; }
        out.push(lab + '=' + setV(ins[0], val).slice(0, 26));
      }
    });
    return JSON.stringify(out);
  } catch (e) { return 'err:' + e.message; }
})()
