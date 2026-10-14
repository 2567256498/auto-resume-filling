---
name: webform-autofill
description: element-ui（Vue）网申表单填写操作配方（框架层）：普查先行、批量写入（文本默认真实输入；隐藏、联想类字段按例外分流）、el-select 下拉、日期组件注入、编辑器容器定位、回读时机与弹层红线。Use when 填写任何 element-ui 系网申、招聘、申报表单；智联（xiaoyuan.zhaopin.com）另加载系统层 skill zhaopin-autofill，antd 系表单改用 antd-webform-autofill/SKILL.md。
---


> **通道状态（ego）**：页面层手法（页面内脚本）跨通道通用；依赖通道动作的步骤（真实点击／语义定位与 snapshot 索引／iframe 穿透）按「未在本通道跑过的只有三种动作」处理，按手册 §4.3 重验后就地回写。
# element-ui 网申表单填写配方

适用：element-ui（Vue）系网申表单，典型为智联校招（xiaoyuan.zhaopin.com/scrd/resume2 等）。行为红线（不编造、带星号必填、不擅自投递、回读核对、投递台账）以 `CODEBUDDY.md` 为准（§二 行为硬规则、§三 内容填报硬规则），本文件只写操作层配方。

**本文件只收跨表单可复用的手法**；单个系统的取数入口、弹窗结构、下拉特殊项等专属细节记到该项目的字段映射文件（如 `简历信息库/表单字段映射.json` 的 `system_fields`），不写在这里以免换系统时误用。

## 固定节奏（效率核心）

普查 → 一区块一次调用批量设值 → 选择器/日期套配方 → 保存只点一次 → 隔次回读核对。

- 一个区块的全部字段合并在**一次**页面内脚本（`ego_js`）里设完并回读，不逐字段单发调用（速度差数倍）。
- **回读时机**：li 点击提交是异步的（Vue 异步队列），同一 promise 里立刻回读可能读到空值，会被误判失败而重复做功。选择后的核对放到**下一次**页面内脚本调用再核。
- **多条目区块逐条目即时保存**：页面丢失/异常时损失以单条为限。

## 普查模板（动手前一次页面内脚本）

1. 扫出每个 .el-form-item：label 文本、内部控件类型（input/textarea/el-select/el-date-editor/s-cascader）、required 星号、maxlength/计数器、readonly、是否 filterable。
2. 记录哪些字段会随选择**动态增删**（如「学历」选完当场冒出研究方向/院系/专业/专业课程）→ 这类表单一律按 label 定位，禁用序号定位（一次重渲染即全部错位）。
3. 长文本先读字数计数器确认上限，不凭记忆；写入前按上限截断判断，宁删整条也不让控件截断（控件截断会得到半句）。

## 文本/文本域设值（setNative）

```js
function setNative(el, val) {
  if (!(el instanceof HTMLInputElement) && !(el instanceof HTMLTextAreaElement)) throw new Error('not an input');
  const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
  setter.call(el, val);
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
}
```

- **口径：默认走真实输入**（`ego_fill`），`setNative` 降为「三类例外 + 侦察」用（`CODEBUDDY.md` §一.4；2026-09-16 用户裁定）。理由：真实输入失败**显性**（回读即知），合成写入失败**隐性**（DOM 与 Vue 状态回读都有值，保存后整页回读才归零，荣耀／北森 zhiye 两次事故即此）。**真实输入 ≠ 逐字符键入**（原子填充＝一次赋值＋单个 `input` 事件、按 locator 定位、与焦点无关），字段多不构成负担。
- **三类例外**：① 隐藏／组件托管控件（el-date-picker 的只读 input、el-radio 的原生 input、复选组隐藏字段）——键入进不去，走**组件状态写入或键盘路径**（本文件「日期」节、手册 §3.3）；**不要直接对组件托管的 DOM 写值**：鹏华 el-date-picker 直写 input 只改显示不落库、写 Vue 组件 `$data` 才生效；只有**无框架托管的隐藏字段**（51job 那类）setNative 直写才成立。② 远程联想字段（学校／公司／专业）——走下拉选择配方，键入过滤仍是真实输入、文本值由**点选动作**写入；直接合成写文本只写显示值、不写关联 ID、不触发搜索（智联 ApplyRemoteSelect、51job 联想控件双写是同一教训）。③ **本通道真实输入实测不可用时降级**（`--action type` 卡死 >250s 属通道工具缺陷，非真实输入本身）——可降级 setNative 做草稿，但**保存回读发现缺失一律改真实输入重写再复验**，并在汇报里点名。
- **落库判据统一是「保存后整页回读」**（`CODEBUDDY.md` §一.$1）。美的事实：`careers.midea.com`（Vue3 + `md-` 前缀，即本配方框架）合成写入与真实输入**等效**，均经「暂存→真导航重载→全新标签」三重复证——合成写入并非普适失效，但适用面比「能写值」窄得多，故不作默认。
- 已保存条目会变成只读卡片（DOM 里没有 input），setNative 前先守卫 instanceof，防 Illegal invocation。
- 分点编号的描述类字段一律用**真实换行**分隔（各占一行），不用空格（`CODEBUDDY.md` §二.$1）。
- 定位用 itemByLabel：label 文本匹配 + 确认该 form-item 内确有 input，再设值。
- 字段启用是有条件的（如选完「是否有证明人=是」才出现证明人输入）→ 先设触发字段，**下一次调用**再填被联动出的字段，别在同一次里硬写。

## element-ui 下拉（el-select）

- **合成 click 打不开下拉**。开法：`el.focus()` + 合成 `new KeyboardEvent('keydown', { key: 'ArrowDown', keyCode: 40, bubbles: true })`。
- 选项：对目标 li 派发 `li.click()`。靠后选项（如「其他」）li.click 可能不提交模型 → 键盘兜底：focus → ArrowDown 开 → N×ArrowDown 高亮到目标 → Enter。
- **选项值按 label 现场匹配，不跨字段复用**：同类字段的 option value 不保证一致（同一表单里两处「是/否」可能就是 3/4 与 4/5）。每次取该字段自己的 `vm.options`，按 label 精确匹配后 `$emit('input'/'change', 选项原始 value)`。
- **直接 $emit 比点选可靠**：el-select 根组件 `$emit('input', v)` + `$emit('change', v)` 即可落值并刷新显示，不需要展开面板；面板路径只作兜底。（适用范围：element-ui 系；已在**智联、牛客**两处复现，其他 element-ui 系统未验证——某系统不生效时先怀疑它不是标准 el-select。）
- **下拉错绑**：多个 `.el-select-dropdown` popper 常驻 DOM，"第一个可见"可能绑到别的字段的旧下拉。每次打开后重新 dump 选项，并按矩形距离匹配：目标 input rect 与 dropdown rect 距离 <300px 才算本字段的。
- 打开状态判断看 className 是否含 hidden / aria-hidden，勿用 offsetParent（fixed 定位 portal 会误判）。

## filterable 学校类下拉（重点坑）

- 这类输入框 readonly，直到被**真实点击**聚焦才接受输入；合成点击、直接 fill 都无效（本通道做法见 `CHANNEL-ego.md`，【未复现】）。
- 优先找远程搜索的组件方法（多为 `vm.remoteMethod(关键词)`），可直接调用、无需点选；结果进 `vm.options` 后按 label 精确匹配再 $emit。
- **自由文本不能提交**：必须从列表选中项，否则校验报"请选择…院校"。
- 远程搜索有延迟：同一次调用内触发搜索后至少等 1.5 秒再取 `options`；更稳妥是"一次调用只触发搜索，下一次调用再读取并选中"。（1.5 秒是下限经验值，**未做对照测定**；首次遇到远程搜索时按"拆两次调用"执行，并把实测结论回写台账。）
- 目标项不在库里时**先找组件自带的手动添加入口**（远程下拉组件常带 footer action / 弹窗），不要直接判死为"问用户"；入口也没有才停下问用户。

## 真实鼠标点击（可信点击）

适用：element-ui popper、s- 自定义组件（s-cascader 等）、readonly 日期控件、filterable 聚焦。合成点击对这类控件无效，必须真实点击。

本通道对应做法：按 label 语义定位直接点（`ego_click` + `page.getByLabel()`）；语义定位不适用时先 `ego_snapshot` 取索引再 `ego_click`（索引每次 snapshot 重建，不可复用）。

通道无关的前置约束：测量（元素 rect 中心）与点击必须在同一次连续操作内完成——滚动容器会漂移；动手前先取 viewport 尺寸（用户可能调过窗口）。

【未复现】本通道真实点击能否打开 element-ui popper 与 readonly 日期控件；未复现前先用页面内脚本兜底。

## 日期（el-date-picker type=date）

1. 普通 input 日期优先程序化/直接输入；**el-date-picker 的 readonly input 直接 setNative 只改显示、不进 Vue 模型**（显示值≠模型，校验读模型会报日期为空）——readonly 日期必须走组件路径；点选只作兜底（坐标点选易点错控件）。
2. 自定义日期包装组件（element-ui 外层再包一层）优先向其 `$parent` 组件 `$emit('input', 'YYYY-MM-DD')` + `$emit('change', …)`，并回写其 model（`comp.model.value` / `comp.model.model[comp.model.key]`）；valueFormat 为日期串时**必须传字符串**，传 Date 对象不落值。
3. **同一容器内多个日期控件禁止按序号取**（`querySelectorAll('.el-date-editor')[i]` 会写错字段）：先按 label 定位 form-item，再取其中的日期控件，并沿 `__vue__.$parent` 上溯到包装组件写值；写完回读该 label 对应的日期串确认。
4. 兜底路径：点年份头部 label → `.el-year-table`（目标年不在本页用 prev/next 翻页，循环 guard<15）→ `.el-month-table` 点月 → `.el-date-table` 只点 `td.available` 且**排除含 prev-month/next-month 的格子**（前后月日期会混进面板）。
5. 写完必须回读核对到「日」——auto-parse 补位曾把 2001-07-30 解析成 2001-07-01，平台预填值也可能是错的；回读时对照证件等一手来源核验。
6. 面板"是否已打开"检测不可靠（visibility 过滤会误判）：用 elementFromPoint 探测面板实际位置；年表格子为数字、月表格子为中文数字（四月/六月/七月/八月）。面板卡死（反复 toggle 失效）＝点「取消」→ 重开编辑器 → 重填该条全部字段，不硬掰 toggle。

## 条目卡片编辑器（新增/编辑条目）

- 新增与编辑已有条目的确认按钮**文案可能不同**：动手前先看当前编辑器底部按钮文案（新增常见「添 加」/「新 增」，编辑常见「保 存」），用宽松正则容空白匹配；按「保存」找不到按钮时先怀疑是新增态。
- 「删除本条记录」类按钮一律不可点。
- **条目最终排序以页面自身规则为准**：先看已有条目的排列规律（按时间倒序？按添加顺序？）再决定添加顺序；同类系统既见过"新条目自动按时间倒序排"、也见过"新条目前插"，不要假设，展示顺序与写入顺序不一致时以页面实际渲染为准。
- **定位编辑器内字段**：已保存条目与打开中的编辑器常同时留在 DOM（编辑器关闭后旧节点不一定移除，同名 label 会出现多份）。先用当前激活的「保存 / 添 加」按钮向上找包含输入控件的祖先容器，再在容器内按 label 正则＋控件 tag 双重过滤；全页取第一个匹配会命中陈旧块，把值写进废弃节点上（表现为写入"成功"但读回为空或保存报缺项）。
- 同一个"提交容器"里可能存在多个主按钮（保存/添 加/立即投递），用文案精确区分，**投递类永远不点**。

## 弹层红线

- **绝不用内联 style（display:none / visibility:hidden）隐藏 element-ui popper**——v-show 恢复不了，全页下拉报废。
- 已犯修复法：`d.style.display=''; d.style.visibility='';` 清掉内联属性即可恢复。
- 关闭下拉用 body.click() 或 blur，不用隐藏。
- 模态弹窗（自绘 s-dialog 一类）可能有**多个同结构实例同时存在于 DOM**：必须按该字段所属组件实例（沿 `__vue__` 找到对应 key/绑定）定位它自己的弹窗，别用 `querySelector('.s-dialog')` 取第一个——会操作到隐藏实例上（点半天没反应）。操作后确认弹窗已关闭再继续。（**仅在智联实测**，其他自绘弹窗未验证。）

## 其他坑速查

- 保存按钮只点一次，双击触发重复提交弄掉会话。
- 保存成功判据 = 整页刷新后数据仍在，表单还开着不等于保存成功；`el-message` 的「保存成功」提示可作即时信号，但失败提示（如「请填写完整」）要立刻查 `.el-form-item__error` 定位缺项，别盲目重点保存。
- 同一页两次读取结果不一致（先有内容后全空）→ 按页面异常处理，先核状态/重载恢复，不在异常页上继续做功。
- 下拉枚举里没有的目标选项（证书类常见）用「其他」+ 自由文本兜底；学校类下拉不适用（见上）。
- 切换区块/离开模块时可能弹「当前模块还未保存」确认框，会挡住后续所有点击：先处理该弹窗再继续（模块已保存时选「不保存」）。

## 服务端渲染（jQuery）表单：同次写入回读

- **无框架托管的服务端渲染表单**（`window.Vue===false`、无 React fiber、无 juic 类组件壳，如国家能源集团 Bootstrap+jQuery、汇丰 SuccessFactors jQuery 页）：元素已渲染完毕，原型 setter ＋ `input`/`change` 事件即可落库，**同一次 `ego_js` 内写入并立即回读**成立，不必拆两次调用（2026-09-20 国家能源首证，2026-09-27 汇丰 SuccessFactors 复现达门槛）。
- 与 element-ui 的差异：这类页面没有「Vue 异步队列未 flush」问题，批量设值后同调用内回读即一致；保存判据仍以整页刷新回读为准（`CODEBUDDY.md` §一.$1）。

## [并入·DSH 侧 2026-10-05] CDP trusted click

适用：element-ui popper、s- 自定义组件（s-cascader 等）、readonly 日期控件、filterable 聚焦。测量（rect 中心）与三次 dispatch 必须同一次连续执行——滚动容器会漂移；动手前先取 viewport 尺寸（用户可能调过窗口）。

```
Input.dispatchMouseEvent  mouseMoved  { x, y }                          # 不带 button/clickCount
Input.dispatchMouseEvent  mousePressed { x, y, button:'left', clickCount:1 }
Input.dispatchMouseEvent  mouseReleased{ x, y, button:'left', clickCount:1 }
```

mouseMoved 带 button/clickCount 参数会报 Invalid parameters。
