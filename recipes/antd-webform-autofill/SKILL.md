---
name: antd-webform-autofill
description: antd（React）网申表单填写操作配方：普查先行、文本默认真实输入、例外按控件类型分流、antd Select 键盘开下拉、日期/月选择器键盘路径、坐标点击兜底与重复 DOM 树验证、字数/必填前置确认。Use when 填写任何 antd/React 系网申、招聘表单（中国银行 applyjob.chinahr.com、工商银行、邮储等）；element-ui 系表单用 webform-autofill。
---


> **通道状态（ego）**：页面层手法（页面内脚本）跨通道通用；依赖通道动作的步骤（真实点击／语义定位与 snapshot 索引／iframe 穿透）按「未在本通道跑过的只有三种动作」处理，按手册 §4.3 重验后就地回写。
# antd 网申表单填写配方

适用：antd（React 16/17）系网申表单，典型为中国银行（applyjob.chinahr.com aply-form）。行为红线（不编造、带星号必填、不擅自投递、回读核对、投递台账）以 `CODEBUDDY.md` 为准（§二 行为硬规则、§三 内容填报硬规则），本文件只写操作层配方。

## 固定节奏（效率核心）

普查 → 一区块一次调用批量设值 → 选择器/日期键盘优先 → 字数/必填前置确认 → 保存（只点一次）→ 一次批量回读。

- 一个区块的全部字段合并在**一次**页面内脚本（`ego_js`）里设完并回读，不逐字段单发调用。
- **多条目区块逐条目即时保存**：页面丢失/异常时损失以单条为限。

## 普查模板（动手前一次页面内脚本）

1. 扫出每个字段：tag/class（Select / DatePicker / Input / TextArea / Cascader）、带 * 必填项、字数计数器上限、readOnly / filterable 属性。
2. **重复 DOM 树**：同一页常存在两棵相同 class 的树（可见 + 隐藏模板），定位前先确认目标在哪棵树里。
3. 记录哪些字段会随选择**动态增删**（如选完「学历」当场冒出研究方向/院系/专业）→ 一律按行 label 定位，禁用序号定位（一次重渲染即全部错位）。
4. 长文本先读字数计数器确认上限，不凭记忆。

## 文本/文本域设值（React）

- **口径：默认走真实输入**（`ego_fill`），不先试合成写入（`CODEBUDDY.md` §一.4；2026-09-16 用户裁定）。理由：真实输入失败**显性**（值进不去，回读即知），合成写入失败**隐性**（DOM 与 fiber 回读都有值，保存后整页回读才归零，荣耀／北森 zhiye 两次事故即此），等发现时可能已保存甚至已投递。**真实输入 ≠ 逐字符键入**，其默认形态是原子填充（一次赋值＋单个 `input` 事件、locator 定位、与焦点无关），字段多不构成负担，「慢」不成立。
- **三类例外**（细则见 手册 §3.4）：① 隐藏／组件托管控件（只读日期输入、antd 单选的原生 input、隐藏字段）——键入进不去，走**组件状态写入或键盘路径**，不是泛泛的"改合成写入"；② 远程联想字段（学校／公司／专业）——走下拉选择配方，键入过滤仍是真实输入、文本值由**点选动作**写入，直接合成写文本只写显示值、不写关联 ID、不触发搜索；③ **本通道真实输入实测不可用时降级**（`--action type` 卡死 >250s 属通道工具缺陷）——可降级用原型 setter 做草稿，但**保存回读发现缺失一律改真实输入重写再复验**，并在汇报里点名。
- **落库判据统一是「保存后整页回读」**（`CODEBUDDY.md` §一.$1）。
- 例外 ③ 与侦察用的原型 setter：按 tag 取原型（input→`HTMLInputElement.prototype`，textarea→`HTMLTextAreaElement.prototype`，用错抛 Illegal invocation）；`setter.call(el, 值)` 后派发 `new Event('input',{bubbles:true})`。美的事实：`careers.midea.com`（Vue3 + `md-` 前缀）合成写入与真实输入**等效**、均经「暂存→真导航重载→全新标签」三重复证落库——合成写入并非普适失效，但适用面比「能写值」窄得多，故不作默认。
- 已保存条目变成只读卡片（DOM 无 input），设值前守卫 instanceof。
- 分点编号的描述类字段一律用**真实换行**分隔（各占一行），不用空格——空格分隔会被部分系统在保存回读时吞掉、造成两点粘连（`CODEBUDDY.md` §二.$1）。

## antd Select 下拉（键盘优先）

- **JS 合成 mousedown 打不开下拉**。开法：`el.focus()` 后派发 ArrowDown 键（或真实键盘事件，通道做法见 `CHANNEL-ego.md`）。
- 打开后高亮项=当前值（空值时为第一项），Enter 只会重选当前高亮项；从高亮项数 ArrowDown 到目标再 Enter。
- 整个走键过程合并在一次页面内脚本里；分次单独按键会触发重复调用拦截。
- 备选：JS 内 scrollIntoView + 测量坐标，紧接着一次真实点击开下拉，再对 li 派发 mousedown/mouseup/click 选项（本通道用法见 `CHANNEL-ego.md`，【未复现】）。
- 下拉是否打开只看 className 是否含 hidden，别用 offsetParent（fixed 定位 portal 会误判）。

## antd 日期/月选择器（键盘优先）

- readOnly 的月输入框不接 fill——focus 面板后 ArrowLeft/Right ±月、Control+Arrow ±年、Enter 提交。
- 日输入框（`.ant-calendar-input`）可直接 fill YYYY-MM-DD + Enter + Escape。
- 面板只渲染出头部没有格子时，Escape 关掉重开再走键盘。
- 多步走月/走年合并在一次脚本调用里。
- 写完必须回读核对到「日」——auto-parse 补位曾把 2001-07-30 解析成 2001-07-01。

## 坐标点击（只作兜底）

- 测量（scrollIntoView＋等待＋取坐标＋elementFromPoint 验证命中目标树）与点击必须**紧挨着连续执行**——内层滚动容器在两次调用之间会漂移，视口 y≈560 以下内容可能被裁剪。
- 同一页两棵重复 DOM 树，点前必须验证命中的是目标树（topIsSelf）。

## 限制前置

- 必填缺失不逐个问——先填完能填的，保存一次让校验把缺失项一次暴露，再按 `CODEBUDDY.md` §一.$1 批量问。
- 下拉枚举里没有的目标选项（证书类常见）用「其他」＋自由文本兜底。

## 站点特例速查：中国银行 applyjob.chinahr.com（React16.8.6 + antd）

- 空态区块的添加入口是 `p.aply-form-empty`（"添加 xx"带图标），条目存在后头部 `em`「添加」才移除 hide 类。
- 保存成功 = 该区块表单收起、出现 `.aply-field-view` 卡片与编辑/删除；表单开着≠保存成功。
- **超长文本（如职责>200字）静默阻止保存，无任何报错**——按整条编号删除压字数后再存。
- 保存按钮必须在**目标区块容器内**找（`p.aply-form-top` 按 `.aply-form-tit` 文本定位后取 parentElement），容器里有隐藏模板按钮对（宽高 0），必须加 `offsetParent!==null` 过滤。
- 高考录取批次等字段会随学历选择动态显隐（选硕士时自动隐藏），无需手动清理。

## [并入·DSH 侧 2026-10-05] 保存成败的免刷新取证（框架通用）

- 不靠「刷新页面回读」判落库（会丢掉未保存内容，且部分站点 reload 即登出）：先注入 XHR/fetch 拦截，再触发一次保存，读响应体判定。
- 注入（页面内执行，幂等）：包 `XMLHttpRequest.prototype.open/send` 记录 `__m/__u` 与 `load` 后的 `status/responseText`；包 `window.fetch` 克隆响应体入库。之后 `window.__xhrlog` 即取证出口。
- 判据：响应体自带业务码时看它（如 `{"state":"200","type":"success"}` 为成功、`{"msg":"…","state":"50000","type":"error"}` 为被校验拦下，msg 常直接给出缺失字段原因）；无码时看底栏/页面 toast 文案＋时间戳。
- 落库范围也可读：返回体里的分包 groupId（如 `set_<区块id>:[…]`）能核对**哪些区块**被写、条目数是否与预期一致。
- 触发通道：区块自带「保存」按钮**可能不发请求**（变更已被周期自动保存覆盖）——请求数为 0 不等于保存失败，须结合自动保存时间戳判断。


## [并入·DSH 侧 2026-10-05] 站点特例速查：大易 wecruit 系（career.honor.com 荣耀 / wecruit.hotjob.cn 中化资本等）

- 结构：`div.form-cell[id=<区块id>]` 内 `div.form-cell-inner` 逐行 `div[id="<区块id>_<字段id>_<条目序号>"]`（条目序号从 0 起，新增条目即 `_1`/`_2`…），行尾一行是「保存/清空」按钮，区块底部 `div.add-more > .add-more-btn` 为「添加新的 X」。**按行 id 定位最稳**，一行 label 文本会随条目重复。
- **分包保存**：`POST /wecruit/resume/info/edit/<租户id>`，请求体 `resumeData.resumeDetail` 按 `set_<区块id>` 分包，响应回 `groupId.set_<区块id>` 列表（条目数可见）；此外有**周期自动保存**，底栏 `resumeFooterFixed` 显示「HH:MM:SS自动保存成功」。
- 区块「保存」按钮点击**有时不产生新请求**（变更已被自动保存推送）——判成功看响应/时间戳，别只看请求数（取证法见上节）。
- 「添加新的 X」用 Playwright 可信点击**有时不触发**，改页面内 DOM `click()` 有效；一律「加前查条目数 → 加后验数」。
- 日级日期控件 readOnly，首次点击**常不展开面板**，需重试 2–4 次；固定底栏会遮住区块底部字段致点击落空，先 `scrollIntoView({block:'center'})` 再点。
- 「添加条目」后同区块既有条目的**下拉值可能被还原**（实测「学习成绩排名 TOP25%」在新增条目后读回为「其他」）——保存前必须整区块回读一遍，别默认前一条还完好。
