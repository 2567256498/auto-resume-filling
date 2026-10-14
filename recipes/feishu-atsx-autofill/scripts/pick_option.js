(() => {
  try {
    const want = '{{opt}}';
    const dds = Array.from(document.querySelectorAll('.ud__select__dropdown')).filter(e => e.getBoundingClientRect().height > 0);
    if (!dds.length) return 'NODD';
    let hit = null, seen = [];
    dds.forEach(d => {
      Array.from(d.querySelectorAll('[class*=list__item]')).forEach(o => {
        const t = (o.innerText || '').trim();
        if (t) seen.push(t.slice(0, 12));
        if (t === want) hit = o;
      });
    });
    if (!hit) return 'NOOPT:' + seen.join('/');
    hit.click();
    return 'CLICKED:' + want;
  } catch (e) { return 'err:' + e.message; }
})()
