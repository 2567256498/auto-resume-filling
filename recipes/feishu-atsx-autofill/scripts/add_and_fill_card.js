(() => {
  try {
    const SEC = '{{sec}}', spec = '{{text}}';
    const norm = s => (s || '').replace(/\s+/g, '').replace(/[*＊]$/, '');
    const titles = Array.from(document.querySelectorAll('[class*=applyFormModuleWrapper-title]'));
    const t = titles.find(e => (e.textContent || '').trim() === SEC);
    if (!t) return 'NOTITLE';
    let root = t;
    for (let i = 0; i < 4; i++) {
      if (!root.parentElement) break;
      root = root.parentElement;
      if (root.querySelector('[class*=applyFormModuleWrapper-right]')) break;
    }
    const right = root.querySelector('[class*=applyFormModuleWrapper-right]') || root;
    const btns = Array.from(right.querySelectorAll('button,[role=button]')).filter(b => (b.textContent || '').trim() === '添加');
    if (!btns.length) return 'NOBTN';
    btns[btns.length - 1].click();
    const cards = Array.from(right.querySelectorAll('div')).filter(e => /apply-form-array-card__/.test(e.className) && !/content/.test(e.className));
    const card = cards[cards.length - 1];
    if (!card) return 'NOCARD';
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
        out.push(lab + '=' + setV(ins[0], val).slice(0, 24));
      }
    });
    return 'cards=' + cards.length + ' ' + JSON.stringify(out);
  } catch (e) { return 'err:' + e.message; }
})()
