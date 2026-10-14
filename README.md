# ego-resume-fill

简历网申填写工作流的**自包含封装体**：一个目录拷走，装上就能跑——ego 浏览器客户端与运行时在包内，13 份系统配方在包内，初始化与校验脚本在包内。浏览器本体走「系统 Chrome/Edge 优先，没有才引导安装」，登录态随 ego 专用 profile 走。

## 它解决什么问题、为什么长成现在这样

**要解决的问题**：把「驱动浏览器填招聘表单」这套流程从一台机器、一个会话里解放出来——换机器、换人、换客户端都不必从零攒。前提是流程所依赖的一切都随包走，除了刻意不随包的。

**四个刻意取舍**（都可以从原理推出来，不是偷懒）：

1. **浏览器本体不打包进包**。这套流程的前提是各招聘网站已登录，而登录态在 ego 的专用 profile 里（`%LOCALAPPDATA%\ego-lite-linux\profile`）——打包一个自带全新 profile 的 Chromium，等于作废全部登录态。且二进制月月过期、体积让 git 分发失效。换机器真正要迁移的是 profile 目录和数据层，不是浏览器。
2. **ego 客户端与运行时（约 1.5MB）反而必须内置**。它是流程与浏览器之间唯一的值钱依赖，且上游插件更新会还原本机补丁（静默补丁、驱动脚本）——内置即固化，不随任何外部安装更新而丢失。
3. **Node 用探测链、不打包**。ego 客户端只要 Node ≥22，探测链覆盖 PATH 与常见安装位；打包一个 50MB 的 Node 只换来「解压即跑」，代价是版本老化与体积。
4. **不携带任何个人数据**。包里只写「怎么做」，取值永远来自使用者的数据层；新环境由初始化脚本生成空骨架，内容由使用者填。

**克制之处（它不做什么）**：不自动启动浏览器（启动器由使用者双击，符合「浏览器由用户亲自打开并保持」）；不代点投递按钮；不猜任务空间名；不做「上传简历自动解析」的捷径（解析会清空已填字段，只作脚手架且必须整表回读）。

## 包结构

```
ego-resume-fill/
├── SKILL.md                  # 主手册：前置四段、部署配置、硬性要求、ego 通道规范、流程与配方分层、经验闭环、自检与失败模式、附录（台账/档案/投递台账模板）
├── README.md                 # 本文件
├── LICENSE                   # MIT
├── CHANGELOG.md              # 版本历史
├── launch-browser.bat        # （已迁至 scripts/）浏览器启动器
├── runtime/                  # 内置 ego 客户端与运行时（ego-browser.cmd + ego-linux，约1.5MB）
├── drivers/                  # silent-driver.mjs（后台静默写入）/ ego-cdp-driver.mjs（任务空间外标签页驱动）/ patch-ego-silent.mjs（静默补丁，幂等）
├── recipes/                  # 13 份系统配方（框架层2 + 系统层11）
├── scripts/
│   ├── probe-browser.py      # 前置四段探测（Node/实例/系统浏览器/profile），退出码0=全过
│   ├── init-workspace.py     # 首次部署初始化（--plan/--check/生成；--make-launcher；--clean-tmp）
│   ├── verify-package.py     # 包内机械校验（每轮档/--package 封装体档），退出码0才算完
│   └── launch-browser.bat    # 浏览器启动器（双击即用）
└── templates/
    └── CODEBUDDY.md          # 项目级要求文件模板（初始化时生成到项目根）
```

## 三分钟上手（新机器）

```bash
# 0. 前置：Node.js ≥ 22（没有就装 LTS）；系统有 Chrome 或 Edge（Windows 一般自带 Edge）

# 1. 整份拷贝到目标位置，然后为网申任务单开一个专用目录（项目根，空目录即可）

# 2. 前置四段探测（只读，不改任何东西）
python scripts/probe-browser.py            # 退出码 0 = 可以开工

# 3. 启动 ego 浏览器（双击 scripts/launch-browser.bat，窗口保持不关）
#    首次 profile 是空的：打开各招聘网站登录一次；
#    想继承日常 Chrome 的登录态：runtime\ego-browser.cmd --import-chrome-profile

# 4. 初始化项目（--plan 先看清单，都不改文件）
python scripts/init-workspace.py --plan  --project "<项目根>"
python scripts/init-workspace.py --check --project "<项目根>"
python scripts/init-workspace.py          --project "<项目根>"   # 生成项目级要求文件/台账/档案/数据层骨架/投递台账

# 5. 把简历事实与字段取值填进数据层（<项目根>/info/简历信息库.md）——只能使用者做

# 6. 跑一次封装体档校验，确认包自洽
python scripts/verify-package.py --package
```

**一轮任务怎么走**：前置探测 → 起手核对（问空间名、核对落点 URL、判框架）→ 侦察扫全表 → 分桶规划 → 按配方填写（文本字段真实输入、非文本控件走组件状态入口）→ 保存后整页回读双向核对 → 追加投递台账 → 十步收尾 → 跑每轮档校验。细则全在 `SKILL.md`。

**出问题看哪**：`SKILL.md` §6.2 失败模式对照（症状 → 先判什么 → 怎么处置）；前置不过看 §1.0 四段表；窗口总弹到前台看 §3.5（重跑 `drivers/patch-ego-silent.mjs`）。

## 与上游的关系

- ego 客户端与运行时来自 `dsh-ego-browser` 插件（Citro Labs，MIT），随包内置一份；本包的 `drivers/patch-ego-silent.mjs` 对其打静默补丁（不抬窗、不抢焦点），**插件或运行时更新后补丁会被还原，必须重跑**（幂等，自动备份）。
- 本包是 `qqbrowser-resume-fill`（QQ 浏览器通道封版）的继任者：通用骨架（硬性要求、流程、经验闭环、校验体系）一脉相承，浏览器通道整体更换为 ego。
- 协议：本包整体 MIT（`runtime/` 与 `drivers/` 内上游文件的许可见 `runtime/LICENSE` 与 `runtime/THIRD_PARTY_NOTICES.md`）。
