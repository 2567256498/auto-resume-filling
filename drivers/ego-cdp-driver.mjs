/**
 * ego-cdp-driver.mjs —— 直接驱动「不在任何任务空间里的标签页」的最小 CDP 驱动。
 *
 * 背景：ego 的结构化工具（ego_page_info / ego_snapshot / ego_fill / ego_click）
 * 只认「当前任务空间」内的标签页（tabs.mjs 的 listTabs 按 space 过滤），
 * 用户手动在 ego 窗口打开的标签页不属于任何 space，于是 page_info 返回 about:blank、
 * browser.switchTab 报 target not found。
 *
 * 本模块绕开空间过滤：Target.getTargets 全量列举 → 按 URL 找 targetId →
 * Target.attachToTarget(flatten) 拿独立 sessionId → 所有命令带 sessionId 发往该页。
 *
 * 用法（在 ego_script 内）：
 *   const { openPage } = await import('file:///<技能目录>/drivers/ego-cdp-driver.mjs');
 *   const p = await openPage(cdp, '/campus/position/22198/apply');
 */

export async function openPage(cdp, urlMatch) {
  const { targetInfos = [] } = await cdp('Target.getTargets', {});
  const pages = targetInfos.filter(
    (t) => t.type === 'page' && !String(t.url || '').startsWith('devtools://'),
  );
  const target = pages.find((t) => String(t.url || '').includes(urlMatch));
  if (!target) {
    throw new Error(
      'target not found for ' + urlMatch + ' | pages: ' + pages.map((p) => p.url).join(' ; '),
    );
  }
  const att = await cdp('Target.attachToTarget', { targetId: target.targetId, flatten: true });
  const sid = att && att.sessionId;
  if (!sid) throw new Error('attachToTarget returned no sessionId');
  return new Driver(cdp, target.targetId, sid, target.url);
}

export class Driver {
  constructor(cdp, targetId, sessionId, url) {
    this.cdp = cdp;
    this.targetId = targetId;
    this.sid = sessionId;
    this.url = url;
  }

  /** 原始求值：表达式内部自行 try/catch；返回 by-value 结果 */
  async ev(expression) {
    const r = await this.cdp(
      'Runtime.evaluate',
      { expression, returnByValue: true, awaitPromise: true },
      this.sid,
    );
    if (r && r.exceptionDetails) {
      const d = r.exceptionDetails;
      throw new Error(
        'eval error: ' + ((d.exception && d.exception.description) || d.text || 'unknown'),
      );
    }
    return r && r.result ? r.result.value : undefined;
  }

  /** 读：把表达式结果 JSON 化，页面异常变成 {__err}，绝不逃逸成进程崩溃 */
  async read(expr) {
    const raw = await this.ev(
      `(()=>{try{return JSON.stringify(${expr})}catch(e){return JSON.stringify({__err:String((e&&e.message)||e)})}})()`,
    );
    if (raw === undefined || raw === null) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return { __raw: raw };
    }
  }

  async info() {
    return this.read(
      `({url:location.href,title:document.title,ready:document.readyState,w:innerWidth,h:innerHeight,sy:scrollY,sh:document.documentElement.scrollHeight})`,
    );
  }

  /** 视口塌缩守卫：点击前必须为真 */
  async assertViewport() {
    const i = await this.info();
    if (!i || !(i.h > 600)) throw new Error('viewport collapsed: ' + JSON.stringify(i));
    return i;
  }

  /** 元素屏幕坐标（先 scrollIntoView 再取 rect；不可见返回 null） */
  async rect(selector, nth = 0) {
    const r = await this.read(
      `(()=>{const els=[...document.querySelectorAll(${JSON.stringify(selector)})];const el=els[${nth}];if(!el)return null;el.scrollIntoView({block:'center'});const b=el.getBoundingClientRect();return {x:b.left+b.width/2,y:b.top+b.height/2,w:b.width,h:b.height,top:b.top,left:b.left,vis:b.width>0&&b.height>0};})()`,
    );
    if (!r || r.__err || !r.vis) return null;
    return r;
  }

  /** 可信鼠标点击（坐标来自 rect()，非有限值直接拒绝派发） */
  async clickXY(x, y) {
    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      throw new Error('refuse to dispatch mouse event with non-finite coords');
    }
    const px = Math.round(x);
    const py = Math.round(y);
    await this.cdp(
      'Input.dispatchMouseEvent',
      { type: 'mouseMoved', x: px, y: py, button: 'none', buttons: 0 },
      this.sid,
    );
    await this.cdp(
      'Input.dispatchMouseEvent',
      { type: 'mousePressed', x: px, y: py, button: 'left', buttons: 1, clickCount: 1 },
      this.sid,
    );
    await this.cdp(
      'Input.dispatchMouseEvent',
      { type: 'mouseReleased', x: px, y: py, button: 'left', buttons: 0, clickCount: 1 },
      this.sid,
    );
    return { x: px, y: py };
  }

  async click(selector, nth = 0) {
    const r = await this.rect(selector, nth);
    if (!r) throw new Error('element not clickable: ' + selector + ' [' + nth + ']');
    return this.clickXY(r.x, r.y);
  }

  /** 第 i 个 .ant-form-item 内的元素坐标（先滚动到视口中心再取 rect） */
  async rectIn(i, inner) {
    const r = await this.read(
      `(()=>{const it=[...document.querySelectorAll('.ant-form-item')][${i}];if(!it)return null;const el=it.querySelector(${JSON.stringify(inner)});if(!el)return null;el.scrollIntoView({block:'center'});const b=el.getBoundingClientRect();return {x:b.left+b.width/2,y:b.top+b.height/2,w:b.width,h:b.height,vis:b.width>0&&b.height>0};})()`,
    );
    if (!r || r.__err || !r.vis) return null;
    return r;
  }

  async clickIn(i, inner) {
    const r = await this.rectIn(i, inner);
    if (!r) throw new Error('not clickable: item[' + i + '] ' + inner);
    return this.clickXY(r.x, r.y);
  }

  async fillIn(i, inner, text) {
    const r = await this.rectIn(i, inner);
    if (!r) throw new Error('not fillable: item[' + i + '] ' + inner);
    await this.clickXY(r.x, r.y);
    await this.clearAndType(text);
  }

  /** 当前展开的 antd 下拉里的可见选项文本 */
  async dropdownOptions() {
    return this.read(
      `(()=>[...document.querySelectorAll('.ant-select-dropdown')].filter(x=>!x.classList.contains('ant-select-dropdown-hidden')).map(x=>[...x.querySelectorAll('.ant-select-item-option')].map(o=>o.innerText.replace(/\\s+/g,' ').trim())))()`,
    );
  }

  async pressEscape() {
    await this.key('Escape');
  }

  /** 按 id 定位（同 id 多输入框用 nth 区分，如 RangePicker 起/止） */
  async rectById(id, nth = 0) {
    const r = await this.read(
      `(()=>{const els=[...document.querySelectorAll('[id='+${JSON.stringify(JSON.stringify(id))}+']')];const el=els[${nth}];if(!el)return null;el.scrollIntoView({block:'center'});const b=el.getBoundingClientRect();return {x:b.left+b.width/2,y:b.top+b.height/2,w:b.width,h:b.height,vis:b.width>0&&b.height>0};})()`,
    );
    if (!r || r.__err || !r.vis) return null;
    return r;
  }

  async clickById(id, nth = 0) {
    const r = await this.rectById(id, nth);
    if (!r) throw new Error('not clickable by id: ' + id + ' [' + nth + ']');
    return this.clickXY(r.x, r.y);
  }

  async fillById(id, text, nth = 0) {
    const r = await this.rectById(id, nth);
    if (!r) throw new Error('not fillable by id: ' + id + ' [' + nth + ']');
    await this.clickXY(r.x, r.y);
    await this.clearAndType(text);
  }

  async valueById(id, nth = 0) {
    return this.read(
      `(()=>{const els=[...document.querySelectorAll('[id='+${JSON.stringify(JSON.stringify(id))}+']')];const el=els[${nth}];return el?el.value:null;})()`,
    );
  }

  /** 在当前展开的下拉里按文本点选项（先取最后打开、可见的那个下拉） */
  async pickOption(optionText, exact = true) {
    const r = await this.read(
      `(()=>{const t=${JSON.stringify(String(optionText))};const dds=[...document.querySelectorAll('.ant-select-dropdown')].filter(d=>!d.classList.contains('ant-select-dropdown-hidden'));for(const dd of dds.reverse()){const opts=[...dd.querySelectorAll('.ant-select-item-option')];const o=opts.find(x=>{const s=x.innerText.replace(/\\s+/g,' ').trim();return ${exact ? 's===t' : 's.includes(t)'};});if(o){o.scrollIntoView({block:'nearest'});const b=o.getBoundingClientRect();if(b.width>0)return {x:b.left+b.width/2,y:b.top+b.height/2,text:o.innerText.replace(/\\s+/g,' ').trim()};}}return null;})()`,
    );
    if (!r || r.__err) throw new Error('option not found: ' + optionText);
    return this.clickXY(r.x, r.y);
  }

  /** 单选/多选下拉：点开 → 选文本 → 关闭 */
  async selectByText(openSelectorOrId, optionText, opts = {}) {
    if (opts.byId) await this.clickById(openSelectorOrId, opts.nth || 0);
    else await this.click(openSelectorOrId, opts.nth || 0);
    await new Promise((r) => setTimeout(r, Number(opts.wait || 700)));
    await this.pickOption(optionText, opts.exact !== false);
    await new Promise((r) => setTimeout(r, Number(opts.after || 400)));
  }

  async sleep(ms) {
    await new Promise((r) => setTimeout(r, Number(ms) || 0));
  }

  /** 可信文本写入：聚焦后 Input.insertText（isTrusted=true） */
  async insertText(text) {
    await this.cdp('Input.insertText', { text: String(text) }, this.sid);
  }

  async key(key, opts = {}) {
    const table = {
      Enter: { code: 'Enter', keyCode: 13, text: '\r' },
      Tab: { code: 'Tab', keyCode: 9, text: '\t' },
      ArrowDown: { code: 'ArrowDown', keyCode: 40, text: '' },
      ArrowUp: { code: 'ArrowUp', keyCode: 38, text: '' },
      Escape: { code: 'Escape', keyCode: 27, text: '' },
      Backspace: { code: 'Backspace', keyCode: 8, text: '' },
      a: { code: 'KeyA', keyCode: 65, text: 'a' },
    };
    const t = table[key];
    if (!t) throw new Error('unsupported key ' + key);
    const modifiers = opts.ctrl ? 2 : 0;
    const base = {
      key: opts.ctrl ? 'Control' : key,
      code: t.code,
      windowsVirtualKeyCode: t.keyCode,
      nativeVirtualKeyCode: t.keyCode,
      modifiers,
    };
    await this.cdp(
      'Input.dispatchKeyEvent',
      { type: t.text && !opts.ctrl ? 'keyDown' : 'rawKeyDown', ...base, ...(t.text && !opts.ctrl ? { text: t.text } : {}) },
      this.sid,
    );
    await this.cdp('Input.dispatchKeyEvent', { type: 'keyUp', ...base }, this.sid);
  }

  /** 清空并写入：Ctrl+A → Backspace → insertText（全部可信通道） */
  async clearAndType(text) {
    await this.key('a', { ctrl: true });
    await this.key('Backspace');
    if (text !== undefined && text !== null && String(text) !== '') await this.insertText(String(text));
  }

  /** 聚焦元素（点击优先，退化为 DOM focus） */
  async focus(selector, nth = 0) {
    const r = await this.rect(selector, nth);
    if (r) {
      await this.clickXY(r.x, r.y);
      return true;
    }
    const ok = await this.read(
      `(()=>{const els=[...document.querySelectorAll(${JSON.stringify(selector)})];const el=els[${nth}];if(!el)return false;el.focus();return true;})()`,
    );
    return !!ok;
  }

  /** 在输入框内写入（先点击聚焦，再全选覆盖） */
  async fill(selector, text, nth = 0) {
    await this.focus(selector, nth);
    await this.clearAndType(text);
  }

  async snapshot() {
    return this.ev('document.documentElement.outerHTML.length');
  }
}
