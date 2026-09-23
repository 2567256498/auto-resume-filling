(() => {
  try {
    const titles = Array.from(document.querySelectorAll('[class*=applyFormModuleWrapper-title]'));
    const out = [];
    titles.forEach(t => {
      const sec = (t.textContent || '').trim();
      if (!sec) return;
      let root = t;
      for (let i = 0; i < 4; i++) {
        if (!root.parentElement) break;
        root = root.parentElement;
        if (root.querySelector('[class*=applyFormModuleWrapper-right]')) break;
      }
      const right = root.querySelector('[class*=applyFormModuleWrapper-right]') || root;
      const cards = Array.from(right.querySelectorAll('div')).filter(e => /apply-form-array-card__/.test(e.className) && !/content/.test(e.className));
      const cb = right.querySelector('input[type=checkbox]');
      out.push(sec + ':cards=' + cards.length + (cb ? ' chk=' + (cb.checked ? 'Y' : 'N') : ''));
    });
    return JSON.stringify(out);
  } catch (e) { return 'err:' + e.message; }
})()
