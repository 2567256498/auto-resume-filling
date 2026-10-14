# 变更档案（ego-resume-fill）

## v1.0.0（2026-10-13）

- 建包：自 `qqbrowser-resume-fill`（QQ 浏览器通道，v3.1.0 封版）继承通用骨架，浏览器通道整体更换为 ego。
- 内置 ego 客户端与运行时（`runtime/`，自本机 `.workbuddy/ego-browser` 副本转入，约 1.5MB）；浏览器本体策略＝系统 Chrome/Edge 优先、没有才引导安装（§1.0 四条理由）。
- `drivers/` 三件套：silent-driver.mjs（后台静默写入）、ego-cdp-driver.mjs（任务空间外标签页 CDP 驱动）、patch-ego-silent.mjs（静默补丁，备份目录改相对定位＋环境变量可覆盖）。
- 新增 `scripts/probe-browser.py`：前置四段探测（Node ≥22 / ego 实例 / 系统浏览器 / profile），只读，退出码 0＝全过。
- 13 份配方随包（框架层 2＋系统层 11）；全部补 ego 通道状态声明；去个人化清洗（姓名／成绩／籍贯示例改占位，「此端」类双端术语改「本项目」）；feishu-atsx 运行器由 QQ 版 run_cli.py 改写为 ego 版 run_ego.py（CLI 探测链：EGO_BROWSER → 包内 runtime → PATH）。
- `scripts/init-workspace.py` ego 化：前置探测改调 probe-browser.py；启动器生成改「复制包内启动器＋注入包绝对路径」；包名改 ego-resume-fill。
- `templates/CODEBUDDY.md` 重写为 ego 单环境版（通道规范以手册 §三 为细则层）。
- `scripts/verify-package.py`：⑦⑧⑨ 扫描段排除 `runtime/`（内置第三方实现，不按本文档标准扫描）；第 5 段启动器判据分流——ego 直接可用形态（无占位符）判「引用包内客户端＋errorlevel」，QQ 模板形态（含 __CLI__）走原 NOCONFIG 护栏判据。
- `SKILL.md` 主手册约 75KB：六章＋附录 A/B/C（台账／变更档案／投递台账模板，init 就地抽取）。
- 校验：`verify-package.py --package` 九段＋运行态第十段全绿（FAIL 0 / WARN 0）。
