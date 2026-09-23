---
name: antd-webform-autofill
description: antd（React）网申表单填写操作配方：普查先行、React 原型 setter 批量设值、antd Select 键盘开下拉、日期/月选择器键盘路径、坐标点击兜底与重复 DOM 树验证、字数/必填前置确认。Use when 填写任何 antd/React 系网申、招聘表单（如 `applyjob.chinahr.com` 等）；element-ui 系表单用 recipes/webform-autofill/SKILL.md。
---

# antd 网申表单填写配方

适用：antd（React 16/17）系网申表单，典型为 `applyjob.chinahr.com` 的 aply-form。行为红线（不编造、带星号必填、不擅自投递、回读核对、投递台账）以本封装体手册（`qqbrowser-resume-fill/SKILL.md`）为准（§2.1 行为红线、§2.2 内容填报口径），本文件只写操作层配方。

> **通道 = QQ 浏览器**（命令映射见手册 §三）。本配方多数内容不依赖通道能力——它们是在页面内执行的脚本（原型 setter／组件直调／事件派发／DOM 查询），**可直接用**；唯一风险是目标页面是否这套框架，动手前先判框架。
> **未在本通道跑过的只有三种动作**：真实点击、语义定位与 snapshot 索引、iframe 穿透——凡依赖它们的步骤都按【未复现】对待，能兜底的已写兜底；跑通后就地改写该处结论（手册 §5.3 第 5 条）。

## 固定节奏（效率核心）

普查 → 一区块一次调用批量设值 → 选择器/日期键盘优先 → 字数/必填前置确认 → 保存（只点一次）→ 一次批量回读。

- 一个区块的全部字段合并在**一次**页面内脚本（`browser_eval_content_js`）里设完并回读，不逐字段单发调用。
- **多条目区块逐条目即时保存**：页面丢失/异常时损失以单条为限。

## 普查模板（动手前一次页面内脚本）

1. 扫出每个字段：tag/class（Select / DatePicker / Input / TextArea / Cascader）、带 * 必填项、字数计数器上限、readOnly / filterable 属性。
2. **重复 DOM 树**：同一页常存在两棵相同 class 的树（可见 + 隐藏模板），定位前先确认目标在哪棵树里。
3. 记录哪些字段会随选择**动态增删**（如选完「学历」当场冒出研究方向/院系/专业）→ 一律按行 label 定位，禁用序号定位（一次重渲染即全部错位）。
4. 长文本先读字数计数器确认上限，不凭记忆。

## 文本/文本域设值（React）

- 按 tag 取原型 setter：input→`HTMLInputElement.prototype`，textarea→`HTMLTextAreaElement.prototype`（用错抛 Illegal invocation）；`setter.call(el, 值)` 后派发 `new Event('input',{bubbles:true})`。
- **口径：默认走真实输入**（本通道 `browser_input_text`），不先试合成写入。判据是**失败模式的可观测性**：真实输入失败**显性**（值进不去，回读即知）；合成写入失败**隐性**（DOM 与 fiber 回读都有值，保存后整页回读才归零）。**真实输入 ≠ 逐字符键入**，字段多不构成负担。
- **三类例外**（细则见手册 §3.7.5）：① 隐藏／组件托管控件（只读日期输入、隐藏字段）走**组件状态写入或键盘路径**，**不是"改用合成写入"**；② 远程联想字段（学校／公司／专业）走**下拉选择配方**——键入过滤仍是真实输入，文本值由点选动作写入；③ 本通道真实输入实测不可用（`--action type` 卡死属**工具缺陷**）时可降级合成写入做草稿，但**保存回读发现缺失一律改真实输入重写**。
- **落库判据统一是「保存后整页回读」**——真重载用 `browser_go_to_url`，**不要用 `browser_tab_reload`（本通道实测是空操作，返回 Success 但页面没重载）**。
- 例外 ③ 与侦察用的原型 setter：按 tag 取（input→`HTMLInputElement.prototype`，textarea→`HTMLTextAreaElement.prototype`，用错抛 Illegal invocation）；`setter.call(el, 值)` 后派发 `new Event('input',{bubbles:true})`。
- **合成写入并非普适失效**：另有站点实测合成写入与真实输入**等效**，经「暂存→真导航重载→全新标签」三重复证落库（2026-09-16 实测，Vue3 ＋ 自研 `md-` 组件库）。但适用面比「能写值」窄得多，故仍不作默认。
- 分点编号的描述类字段用**真实换行**分隔（各占一行），不用空格——空格分隔会被部分系统在保存回读时吞掉、造成两点粘连。
- 已保存条目变成只读卡片（DOM 无 input），设值前守卫 instanceof。

## antd Select 下拉（键盘优先）

- **JS 合成 mousedown 打不开下拉**。开法：`el.focus()` 后派发 ArrowDown 键（或真实键盘事件，通道做法见本封装体手册 §三）。
- 打开后高亮项=当前值（空值时为第一项），Enter 只会重选当前高亮项；从高亮项数 ArrowDown 到目标再 Enter。
- 整个走键过程合并在一次页面内脚本里；分次单独按键会触发重复调用拦截。
- 备选：JS 内 scrollIntoView + 测量坐标，紧接着一次真实点击开下拉，再对 li 派发 mousedown/mouseup/click 选项（本通道用法见本封装体手册 §三，【未复现】）。
- 下拉是否打开只看 className 是否含 hidden，别用 offsetParent（fixed 定位 portal 会误判）。

## antd 日期/月选择器（键盘优先）

- readOnly 的月输入框不接 fill——focus 面板后 ArrowLeft/Right ±月、Control+Arrow ±年、Enter 提交。
- 日输入框（`.ant-calendar-input`）可直接 fill YYYY-MM-DD + Enter + Escape。
- 面板只渲染出头部没有格子时，Escape 关掉重开再走键盘。
- 多步走月/走年合并在一次脚本调用里。
- 写完必须回读核对到「日」——auto-parse 补位可能把「日」写错（实测发生过）。

## 坐标点击（只作兜底）

- 测量（scrollIntoView＋等待＋取坐标＋elementFromPoint 验证命中目标树）与点击必须**紧挨着连续执行**——内层滚动容器在两次调用之间会漂移，视口 y≈560 以下内容可能被裁剪。
- 同一页两棵重复 DOM 树，点前必须验证命中的是目标树（topIsSelf）。

## 限制前置

- 必填缺失不逐个问——先填完能填的，保存一次让校验把缺失项一次暴露，再按本封装体手册 §2.1.8 批量问。
- 下拉枚举里没有的目标选项（证书类常见）用「其他」＋自由文本兜底。

## 站点特例速查：applyjob.chinahr.com（React16.8.6 + antd）

- 空态区块的添加入口是 `p.aply-form-empty`（"添加 xx"带图标），条目存在后头部 `em`「添加」才移除 hide 类。
- 保存成功 = 该区块表单收起、出现 `.aply-field-view` 卡片与编辑/删除；表单开着≠保存成功。
- **超长文本（如职责>200字）静默阻止保存，无任何报错**——按整条编号删除压字数后再存。
- 保存按钮必须在**目标区块容器内**找（`p.aply-form-top` 按 `.aply-form-tit` 文本定位后取 parentElement），容器里有隐藏模板按钮对（宽高 0），必须加 `offsetParent!==null` 过滤。
- 高考录取批次等字段会随学历选择动态显隐（选硕士时自动隐藏），无需手动清理。
