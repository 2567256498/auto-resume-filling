(() => {
  try {
    const SEC = '{{sec}}', FIELD = '{{field}}';
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
    const fld = Array.from(right.querySelectorAll('.ud-formily-item')).find(it => norm((it.querySelector('.ud-formily-item-label-content') || {}).innerText) === FIELD);
    if (!fld) return 'NF';
    const sel = fld.querySelector('.ud__select__selector') || fld.querySelector('.ud__select');
    if (!sel) return 'NOSEL';
    ['mousedown', 'mouseup', 'click'].forEach(x => sel.dispatchEvent(new MouseEvent(x, { bubbles: true, cancelable: true, view: window })));
    return 'DISPATCHED';
  } catch (e) { return 'err:' + e.message; }
})()
