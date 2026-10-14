// 静默驱动：直连 ego Chrome 的浏览器级 CDP，按 target 附加会话执行步骤。
// 关键点：全程不调用 Target.activateTarget / Page.bringToFront，因此不会把窗口/标签页顶到前台。
// 用法：node silent-driver.mjs <plan.json>
// plan.json = { urlMatch: "xxx", steps: [ {op:'eval'|'insert'|'click'|'wait'|'screenshot', ...} ] }
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const HOME = process.env.USERPROFILE || process.env.HOME;
const STATE = path.join(process.env.LOCALAPPDATA || path.join(HOME, 'AppData', 'Local'), 'ego-lite-linux', 'browser.json');

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let b = '';
      res.on('data', (d) => (b += d));
      res.on('end', () => { try { resolve(JSON.parse(b)); } catch (e) { reject(e); } });
    }).on('error', reject);
  });
}

const planFile = process.argv[2];
const plan = JSON.parse(fs.readFileSync(planFile, 'utf8'));
const st = JSON.parse(fs.readFileSync(STATE, 'utf8'));
const port = st.port;

const list = await getJson(`http://127.0.0.1:${port}/json/list`);
const match = plan.urlMatch || '';
const cands = list.filter((t) => t.type === 'page' && (!match || (t.url || '').includes(match)));
if (!cands.length) {
  console.log(JSON.stringify({ ok: false, err: 'no target matching ' + match, urls: list.filter(t => t.type === 'page').map(t => (t.url || '').slice(0, 80)) }));
  process.exit(2);
}
const target = cands[0];

const ws = new WebSocket(st.wsUrl);
let seq = 0;
const pending = new Map();
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
});
await new Promise((r) => ws.addEventListener('open', r, { once: true }));

function send(method, params = {}, sessionId) {
  return new Promise((resolve) => {
    const id = ++seq;
    pending.set(id, resolve);
    const msg = { id, method, params };
    if (sessionId) msg.sessionId = sessionId;
    ws.send(JSON.stringify(msg));
  });
}

const att = await send('Target.attachToTarget', { targetId: target.id, flatten: true });
const sessionId = att.result && att.result.sessionId;
if (!sessionId) {
  console.log(JSON.stringify({ ok: false, err: 'attach failed', att }));
  process.exit(3);
}

const out = [];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

for (const step of plan.steps) {
  try {
    if (step.op === 'eval') {
      const r = await send('Runtime.evaluate', { expression: step.expr, returnByValue: true, awaitPromise: true }, sessionId);
      const ex = r.result && r.result.exceptionDetails;
      out.push({ op: 'eval', label: step.label || null, value: ex ? { error: (ex.exception && ex.exception.description) || ex.text } : (r.result && r.result.result ? r.result.result.value : null) });
    } else if (step.op === 'insert') {
      const sel = JSON.stringify(step.selector);
      const f = await send('Runtime.evaluate', {
        expression: `(() => { const el = document.querySelector(${sel}); if (!el) return 'missing'; el.focus(); if (el.setSelectionRange) { try { el.setSelectionRange(0, el.value.length); } catch (e) {} } return 'ok'; })()`,
        returnByValue: true,
      }, sessionId);
      const st1 = f.result && f.result.result ? f.result.result.value : null;
      if (st1 !== 'ok') { out.push({ op: 'insert', label: step.label || null, value: 'focus failed: ' + st1 }); continue; }
      if (step.clear !== false) {
        await send('Input.dispatchKeyEvent', { type: 'keyDown', windowsVirtualKeyCode: 65, modifiers: 2, key: 'a', code: 'KeyA' }, sessionId);
        await send('Input.dispatchKeyEvent', { type: 'keyUp', windowsVirtualKeyCode: 65, modifiers: 2, key: 'a', code: 'KeyA' }, sessionId);
        await send('Input.dispatchKeyEvent', { type: 'keyDown', windowsVirtualKeyCode: 8, key: 'Backspace', code: 'Backspace' }, sessionId);
        await send('Input.dispatchKeyEvent', { type: 'keyUp', windowsVirtualKeyCode: 8, key: 'Backspace', code: 'Backspace' }, sessionId);
      }
      await send('Input.insertText', { text: step.text }, sessionId);
      const chk = await send('Runtime.evaluate', { expression: `(() => { const el = document.querySelector(${sel}); return el ? el.value.length : -1; })()`, returnByValue: true }, sessionId);
      out.push({ op: 'insert', label: step.label || null, value: 'len=' + (chk.result && chk.result.result ? chk.result.result.value : '?') });
    } else if (step.op === 'click') {
      const sel = JSON.stringify(step.selector);
      const r = await send('Runtime.evaluate', { expression: `(() => { const el = document.querySelector(${sel}); if (!el) return 'missing'; el.click(); return 'clicked'; })()`, returnByValue: true }, sessionId);
      out.push({ op: 'click', label: step.label || null, value: r.result && r.result.result ? r.result.result.value : null });
    } else if (step.op === 'key') {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', windowsVirtualKeyCode: step.vk, key: step.key, code: step.code }, sessionId);
      await send('Input.dispatchKeyEvent', { type: 'keyUp', windowsVirtualKeyCode: step.vk, key: step.key, code: step.code }, sessionId);
      out.push({ op: 'key', label: step.label || null, value: 'sent ' + step.key });
    } else if (step.op === 'wait') {
      await sleep(step.ms || 500);
      out.push({ op: 'wait', value: step.ms || 500 });
    } else {
      out.push({ op: step.op, value: 'unknown op' });
    }
  } catch (e) {
    out.push({ op: step.op, label: step.label || null, value: 'ERR ' + e.message });
  }
  if (step.settleMs) await sleep(step.settleMs);
}

const urlNow = await send('Runtime.evaluate', { expression: 'location.href', returnByValue: true }, sessionId);
console.log(JSON.stringify({ ok: true, targetId: target.id, url: urlNow.result && urlNow.result.result ? urlNow.result.result.value : null, steps: out }, null, 1));
ws.close();
process.exit(0);
