/**
 * 本机补丁：让 ego 运行时全程静默（不抢焦点、不抬窗口）
 * 用途：插件升级/重装后重跑一次即可恢复（幂等）。
 * 用法：node drivers/patch-ego-silent.mjs [runtimeRoot]
 *   runtimeRoot 默认 = %USERPROFILE%\.dsh\profiles\web\node_modules\dsh-ego-browser\ego-browser\runtime\ego-linux
 * 改动 4 个文件：
 *   src/tabs.mjs        Target.createTarget 加 focus:false
 *   src/task-spaces.mjs Target.createTarget 加 focus:false
 *   src/transport.mjs   吞掉 Target.activateTarget / Page.bringToFront（保留 activeHint 记录）
 *   src/window-fit.mjs  去掉 windowState:'normal'（不再取消最小化/抬窗）
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HOME = process.env.USERPROFILE || process.env.HOME;
const root = process.argv[2] || path.join(HOME, '.dsh', 'profiles', 'web', 'node_modules', 'dsh-ego-browser', 'runtime', 'ego-linux');
const src = path.join(root, 'src');
// 备份目录：默认 <包>/backups/ego-silent-patch（相对本脚本定位），可用 EGO_SILENT_BAK 覆盖。
const bak = process.env.EGO_SILENT_BAK
  || path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'backups', 'ego-silent-patch');
if (!fs.existsSync(src)) {
  console.log(JSON.stringify({ ok: false, err: 'runtime src not found: ' + src }));
  process.exit(2);
}
fs.mkdirSync(bak, { recursive: true });

const MARK = 'LOCAL PATCH (silent)';
const report = [];

function patch(file, edits) {
  const p = path.join(src, file);
  let text = fs.readFileSync(p, 'utf8');
  const before = text;
  const entry = { file, applied: [], already: [], missing: [] };
  for (const e of edits) {
    if (text.includes(e.mark)) {
      // Already patched. An entry may still carry an older patched form to upgrade.
      if (e.upgrade && text.includes(e.upgrade)) {
        text = text.replace(e.upgrade, e.upgradeReplace || e.replace);
        entry.applied.push(e.name + ':upgraded');
        continue;
      }
      entry.already.push(e.name);
      continue;
    }
    // altFinds: an older local-patch form may already cover this intent
    // (vendored runtime ships the 2026-09-23 patch shapes); report already, don't double-apply.
    if (e.altFinds && e.altFinds.some((f) => text.includes(f))) {
      entry.already.push(e.name + ':older-form');
      continue;
    }
    if (!text.includes(e.find)) { entry.missing.push(e.name); continue; }
    if (text.split(e.find).length - 1 !== 1) { entry.missing.push(e.name + '(multiple)'); continue; }
    text = text.replace(e.find, e.replace);
    entry.applied.push(e.name);
  }
  if (text !== before) {
    const dest = path.join(bak, file);
    if (!fs.existsSync(dest)) fs.copyFileSync(p, dest);
    fs.writeFileSync(p, text);
  }
  report.push(entry);
}

patch('tabs.mjs', [{
  name: 'createTarget:focus-false',
  altFinds: ['// [local patch 2026-09-23] focus:false', 'focus: false,'],
  mark: 'focus: false, // ' + MARK,
  find: 'const { targetId } = await cdp.call("Target.createTarget", {\n        url,\n        ...(browserContextId ? { browserContextId } : {}),\n      });',
  replace: 'const { targetId } = await cdp.call("Target.createTarget", {\n        url,\n        focus: false, // ' + MARK + ': never raise the OS window\n        ...(browserContextId ? { browserContextId } : {}),\n      });',
}]);

patch('task-spaces.mjs', [{
  name: 'createTarget:focus-false',
  altFinds: ['// [local patch 2026-09-23] Target.createTarget focuses', 'focus: false,'],
  mark: 'focus: false, // ' + MARK,
  find: '({ targetId } = await cdp.call("Target.createTarget", {\n          url: "about:blank",\n          ...(browserContextId ? { browserContextId } : {}),\n        }));',
  replace: '({ targetId } = await cdp.call("Target.createTarget", {\n          url: "about:blank",\n          focus: false, // ' + MARK + ': never raise the OS window\n          ...(browserContextId ? { browserContextId } : {}),\n        }));',
}]);

patch('transport.mjs', [
  {
    name: 'sendRaw:drop-raise',
    mark: 'drop window-raising commands authored by the harness',
    find: '    sendRaw(payload) {\n      assertOpen();\n      noteActivation(payload);',
    upgrade: '      // ' + MARK + ': drop window-raising commands authored by the harness.\n      if (payload.includes("Target.activateTarget") || payload.includes("Page.bringToFront")) {\n        return;\n      }',
    upgradeReplace: '      // ' + MARK + ': drop window-raising commands authored by the harness, but answer\n      // the request ourselves so the harness does not sit on a timeout.\n      if (payload.includes("Target.activateTarget") || payload.includes("Page.bringToFront")) {\n        try {\n          const m = JSON.parse(payload);\n          if (m && m.id !== undefined) {\n            runtime?.onCDPMessage?.(JSON.stringify({ id: m.id, result: {} }));\n          }\n        } catch {\n          // Unparseable payload: there is no request to answer.\n        }\n        return;\n      }',
    replace: '    sendRaw(payload) {\n      assertOpen();\n      noteActivation(payload);\n      // ' + MARK + ': drop window-raising commands authored by the harness, but answer\n      // the request ourselves so the harness does not sit on a timeout.\n      if (payload.includes("Target.activateTarget") || payload.includes("Page.bringToFront")) {\n        try {\n          const m = JSON.parse(payload);\n          if (m && m.id !== undefined) {\n            runtime?.onCDPMessage?.(JSON.stringify({ id: m.id, result: {} }));\n          }\n        } catch {\n          // Unparseable payload: there is no request to answer.\n        }\n        return;\n      }',
  },
  {
    name: 'call:drop-raise',
    altFinds: ['// [local patch 2026-09-23b] Same reason as sendRaw'],
    mark: 'the hint above is recorded, the raise is not sent',
    find: '      if (method === "Target.activateTarget" && params.targetId) {\n        activeTargetId = params.targetId;\n      }\n      const id = ++nextInternalId;',
    replace: '      if (method === "Target.activateTarget" && params.targetId) {\n        activeTargetId = params.targetId;\n      }\n      // ' + MARK + ': the hint above is recorded, the raise is not sent.\n      if (method === "Target.activateTarget" || method === "Page.bringToFront") {\n        return Promise.resolve({});\n      }\n      const id = ++nextInternalId;',
  },
]);

patch('transport.mjs', [
  {
    name: 'call:drop-bringToFront',
    mark: 'call() also drops Page.bringToFront',
    find: '      if (method === "Target.activateTarget" && params.targetId) {\n        activeTargetId = params.targetId;\n        // [local patch 2026-09-23b] Same reason as sendRaw — keep the hint, skip the window raise.\n        return Promise.resolve({});\n      }',
    replace: '      if (method === "Target.activateTarget" && params.targetId) {\n        activeTargetId = params.targetId;\n        // [local patch 2026-09-23b] Same reason as sendRaw — keep the hint, skip the window raise.\n        return Promise.resolve({});\n      }\n      // ' + MARK + ': call() also drops Page.bringToFront (the vendored 2026-09-23 form only dropped activateTarget).\n      if (method === "Page.bringToFront") {\n        return Promise.resolve({});\n      }',
  },
]);

patch('window-fit.mjs', [
  {
    name: 'restore:keep-minimized',
    mark: 'do not un-minimize / raise',
    find: '        bounds: { ...original, windowState: "normal" },',
    replace: '        bounds: { ...original }, // ' + MARK + ': do not un-minimize / raise',
  },
  {
    name: 'shrink:no-windowState',
    mark: 'no windowState -> a minimized window stays minimized',
    find: '            width: Math.round(width),\n            height: Math.round(height + CHROME_HEIGHT),\n            windowState: "normal",',
    replace: '            width: Math.round(width),\n            height: Math.round(height + CHROME_HEIGHT), // ' + MARK + ': no windowState -> a minimized window stays minimized',
  },
]);

const ok = report.every(r => r.missing.length === 0);
console.log(JSON.stringify({ ok, root, backup: bak, report }, null, 1));
