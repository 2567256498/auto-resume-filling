# runtime/ — vendored 运行时本地改动记录

本目录来自 [CitroLabs/ego-lite](https://github.com/CitroLabs/ego-lite)（MIT，含 Linux 移植 PR #234
与本地代理补丁），在首次 vendoring 提交 `a77dee4` 时整体引入。**只读参照**为主。

> 排查/跟进上游前先看这里：如果一项改动只在下面列出，说明它相对上游是我们或本仓库维护引入的；
> 没列出的文件 = 与 vendored 时一致（它们可能本就是这个 Linux 移植自带的本地化）。

## 明确的本地改动（相对 vendored 基线）

| 文件 | 改动 | 原因 / 提交 |
|---|---|---|
| `runtime/ego-linux/src/cursor.mjs` | 光标覆盖层默认名 `Claude` → `DeepSeek`（4 处：默认值 + 注释） | 品牌统一，`dacbd47` |
| `runtime/ego-linux/src/chrome.mjs` | `resolveBinary()`: `candidate.includes("/")` → `isAbsolute(candidate)`；`which()`: Windows 用 `where` 替代 `which` | Windows 支持：POSIX `includes("/")` 不识别 `C:\\` 路径，`which` 在 Windows 不存在 |
| `runtime/ego-linux/src/chrome.mjs` | `LAUNCH_FLAGS` 加 `--no-startup-window`；`launch()` 删除 `"about:blank"` 位置参数 | 消除单次 `ego_space_open` 开两个窗口：原位置参数在默认 browser context 开残留 tab，space tab 走独立 context 又开一个窗口，Chrome 把不同 context 隔离到不同窗口 → 用户看到两窗。`useSpace+ensureRealTab` 路由下不再需要 launch 残留 tab |
| `runtime/ego-linux/src/chrome.mjs` | `launch()` 的 `args` 末尾 spread `filterChromeArgs(process.env.EGO_LINUX_EXTRA_ARGS ?? "")`；新增模块内 `CHROME_BLOCKED` 集合 + `tokenizeArgs`/`filterChromeArgs` 函数（与 `lib/config.js` 镜像，runtime 不 import lib/） | 用户自定义 Chrome 启动参数（设置字段 `chromeArgs`）：插件 `resolveEgoEnv` 把 `chromeArgs` 桥接到 `EGO_LINUX_EXTRA_ARGS`，runtime 切分 + 拉黑控制面标志（`--user-data-dir`/`--remote-debugging-port`/`--headless`/`--proxy-server` 等）后 spread 进 Chrome argv。仅浏览器下次冷启动生效 |
| `runtime/ego-linux/src/task-spaces.mjs`、`runtime/ego-linux/src/tabs.mjs` | 三处 `Target.createTarget` 加 `focus: false`，并删掉随后的 `Target.activateTarget` | **不抢前台**：CDP 默认（省略 `focus`）是「新建 target 会把整个浏览器窗口提到最前」，于是每个新任务空间、每个新标签页都把窗口顶到用户工作之上。`focus:false` 下标签页仍是其窗口的活动标签页（`background` 默认 false），只是不再前置窗口。Chrome 153 的 `Target.createTarget` 已支持该参数（`/json/protocol` 实测） |
| `runtime/ego-linux/src/task-spaces.mjs` | `IDLE_MINUTES` 默认 30 → 0；`readoptRestoredPages` 改 async，并在浏览器重启后按空间记忆的 url 重新打开页面 | **页面不再无声丢失**：空闲清扫会在 30 分钟后关掉未被点名的空间及其标签页；浏览器重启后 `reconcile` 会把「一个标签页都不剩」的空间整条删掉，而 Chrome 因 `--no-startup-window` 且 profile 无会话数据不会自己恢复页面 —— 两者都表现为「浏览器变白、页面没了」 |
| `runtime/ego-linux/src/paths.mjs` | Windows 用 `%LOCALAPPDATA%\\ego-lite-linux` 作为 DATA_DIR / STATE_DIR；`CHROME_CONFIG_CANDIDATES` 加 Windows 路径 | Windows 支持：XDG 变量在 Windows 不存在；`ego_doctor` 已预期 `%LOCALAPPDATA%` |
| `runtime/ego-linux/bin/ego-browser.mjs` | headless 判定加 `hasDisplay`：有可用 X display（如 Xvfb）时忽略继承的 `EGO_LINUX_HEADLESS=1`，跑 headed | watch 面板全帧率 + ffmpeg x11grab 后端能抓到画面：headless 走 swiftshader ~1fps 且不渲染到 X display（x11grab 抓黑屏）。PR #10 曾回退此逻辑（只认 env），已重新移植（2026-08-18） |
| `runtime/ego-linux/bin/ego-browser.mjs` | 显式 `EGO_LINUX_HEADLESS=1/true/yes/on` 现在优先于 `hasDisplay` 推断（含 win32）；未设置时维持原 hasDisplay 逻辑 | issue #35：此前 win32 硬编码 `hasDisplay=true` 导致显式设置的环境变量被静默忽略，与 CLI help / README 文档矛盾 |
| `runtime/ego-linux/src/task-spaces.mjs` | `createSeededContext()` 增加 `EGO_ISOLATE_SPACES` 环境变量开关支持；未开启（默认）时返回 `null` 复用磁盘 Profile，开启时保留原作者内存沙盒隔离 | 登录态持久化与沙盒隔离双模可配：用户在设置中选择是否开启空间隔离；默认关闭时所有登录态直接落盘，跨关机重启永久保留，开启时恢复独立内存沙盒 |
| `runtime/ego-browser/screenshot-clip.mjs` + `runtime/ego-browser/dist/out/index.js` `screenshot()` | viewport / locator 截图的 CDP clip 原点改为 `pageInfo().sx/sy`（`scrollX/scrollY`），不再固定 `{x:0,y:0}`；fullPage 仍从文档原点截整页 | CDP clip 是文档坐标且默认 `captureBeyondViewport:false`：滚动后 clip 落在未绘制区域会得到空白 PNG。与 `spaces-server.mjs` followClip 同一约定 |
| （其余 runtime 文件）| 与 vendoring 时一致 | 无后续本地改动 |

## 说明
- `chrome.mjs` 里的代理支持（`EGO_LINUX_PROXY`）在首次 vendoring 时已包含（本 Linux 移植特性），
  非后续本地改动；如需调整走它。
- **同步提醒**：`lib/index.js` 与 `bin/ego-cast-worker.mjs` 各有一份 humanCheck 探针（逻辑相似）——
  若改探针特征，两处都要同步。
- **同步提醒**：`lib/config.js` 的 `tokenizeArgs`/`filterArgs`/`CHROME_BLOCKED` 与 `runtime/ego-linux/src/chrome.mjs` 的 `tokenizeArgs`/`filterChromeArgs`/`CHROME_BLOCKED` 是镜像副本（runtime 不 import lib/）——改一处必须同步另一处。
- 若要跟进 ego-lite 上游，重点 diff 上表的 cursor.mjs；其余文件可直接与上游对齐。

## [local patch 2026-09-23b] 不抢窗口焦点（transport.mjs）

- 现象：ego 浏览器窗口在用户做别的事时反复弹到最前。
- 根因：`browser.switchTab`（harness 侧 `runtime/ego-browser/dist/out/index.js` 的 `switchTab`）每次都发
  `Target.activateTarget`；该调用经 `transport.mjs` 原样转给 Chrome，而 Chrome 激活后台窗口的标签页时会把整窗提到最前。
  另有 `focusSpace()`（`useTaskSpace`／`claimTaskSpace`／`takeOverTaskSpace`）走 shim 内部 `call()` 的同一调用。
- 处置：在 `transport.mjs` 的 `sendRaw()` 与 `call()` 中**吞掉** `Target.activateTarget`——仍记录 `activeTargetId`（
  `activeHint` 依赖它判断当前标签页），harness 侧则收到合成的成功响应，请求不会挂起。请求 id 不可解析时改为原样转发（不留悬挂请求）。
- 不改动：`bin/ego-browser.mjs` 的 show 路径（用户点启动器时**故意**前置窗口）、`window-fit.mjs` 的窗口尺寸适配。
- 备份：`.dsh/backups/ego-patch-2026-09-23/transport.mjs.orig`；重放：`.dsh/tmp/patch-ego-transport-2026-09-23.mjs`（幂等）。
