---
name: beisen-zhiye-autofill
description: 北森招聘平台 zhiye.com 系（`<租户>.zhiye.com`，自研 Phoenix 组件）系统层配方：编辑态与只读态判据、区块容器定位、真实键入写入与回读（该平台合成写入不落库）、常驻选择器与月份面板路径、弹层清场、保存后验证方式。Use when 填写北森 zhiye 系网申表单（先读框架层配方拿通用手法，本文件只写北森专属部分）。
---

# 北森 zhiye 网申填写配方（系统层）

> 适用：北森招聘平台 zhiye.com 系（`<租户>.zhiye.com`），前端为北森自研 Phoenix 组件（`phoenix-*`）。只写北森专属实现；字段取值与口径见使用者数据层，跨框架通用手法见框架层 skill。
> 来源：多次网申实测（台账已复核）。
> **通道 = QQ 浏览器**（命令映射见手册 §三）。本配方多数内容不依赖通道能力——它们是在页面内执行的脚本（原型 setter／组件直调／事件派发／DOM 查询），**可直接用**；唯一风险是目标页面是否这套框架，动手前先判框架。
> **本通道已复现的动作**：真实点击（开凤凰下拉面板、开日期面板）、语义定位（`--by text`／`--css`）、snapshot 索引（`--index`）三项**均已在本系统实测跑通**（结论见 §8）；唯一未复现的是 iframe 穿透，而本系统正式表单 iframe 数为 0，不影响本配方。正文 §2／§3／§5 里写的"真实坐标点击／测坐标"按手册 §3.3 换算为语义点击（本通道无坐标点击命令）。

## 0 页面态与入口
- URL `...form?fromPage=editMyResume` = 可编辑；`fromPage=myResume` = 只读视图（字段渲染为 `<p class="form-item__text">`，读为空属正常，**不是数据丢失**）
- 只读页回编辑态：点页面自带「编辑简历」按钮（`BUTTON.stylest__STFooterStandardButton…`）——按钮常在视口外，先 `scrollIntoView({block:'center'})` 再测坐标，**真实坐标点击**
- 每次保存/编辑后平台会自动跳回只读视图；动手前先看 URL 判断当前是编辑态还是只读态

## 1 结构定位
- 区块容器：`.twoLineFormStyleLong`，`id` 含 `Recruitment_extPerfect<区块名>`（PersonProfile／ApplicantEducation／ApplicantWorkExperience／ApplicantInternship／ApplicantProject／RelativesDeclaration…）；**每个条目一个容器**，条目增多容器也增多 → 按 DOM 顺序取第 n 个
- 字段：容器内 `.form-item`，标题 `.form-item__title`（必填另有 `.form-item__required` 或 `icon-cus-bitian`）；**一律按标题文本定位，禁用序号**
- 语言能力／兴趣爱好／奖励活动／家庭情况／自我评价不在 `.twoLineFormStyleLong` 内 → 用全页 `.form-item` 按标题匹配；「姓名」「政治面貌」等标签会重复，家庭情况取**最后一个**
- **重复区块（实习／校园经历／奖励／家庭情况）里同名字段会多次出现**：按标题文本匹配只会命中**第一个**同名字段——实测按标题填家庭情况「姓名」，值写进了表单顶部的「姓名」。这类区块（以及任何标题会重复的场景）一律按 `.form-item` 的**全局索引**定位：先 dump 全字段清单拿索引，再按索引操作（2026-09-17 实测，事故背书）

## 2 区块入口与新增条目
- 工作经历／实习经历／项目经历 的首个控件是**「点击添加」下拉**，选项仅两个：`开始添加` / `无`——有经历选「开始添加」展开字段；应届生无全职工作经历 → 工作经历选「无」
- 点 `添加XX` 后新增的条目**先渲染为折叠行**（也是「点击添加」下拉）→ 还要再选「开始添加」才出字段
- `添加XX` 按钮是 styled-components 的 DIV/SPAN（`..._addButton`）：先试 JS 合成点击，条目数没变就改**真实坐标点击**（测 `SPAN.sc-jeraig` 或外层 DIV 中心）
- **新增条目后必须逐条回读整个区块**：实测新增一条项目经历后，既有条目的字段被清空、且条目顺序变化 → 加完立刻按字段值（如「项目名称」）逐条核对，发现被清空立即补回；定位条目一律用字段值，不用索引
- **点「添加XX」按钮必须传完整合成事件对象**：其 `onClick` 内部读 `e.target.getBoundingClientRect()`，只给 `{type:'click',…}` 会抛 `Cannot read properties of undefined`，**且当前行输入被清空**。事件对象需含 `target`／`currentTarget`／`srcElement`／`nativeEvent`／`clientX,clientY` 与 `preventDefault`／`stopPropagation`／`persist`／`isDefaultPrevented`／`isPropagationStopped`（2026-09-17 实测：「添加家庭情况」简版行数不变且清空姓名，完整版才真正加行）
- **新增条目后要回读的是整页，不是只有新增块**：新增会让 React 重排，**已经填好的下拉值会串位**——实测加一条实习后，另一条校园经历的起止时间被写成新实习的日期。凡是本轮加过条目，收尾前必须整页回读一遍（2026-09-17 实测，事故背书）
- **「添加」式问答块没有删除入口**：多出来的空块（行内只有下箭头与 `phoenix-select__clearIcon`）无法删行，只能把它选「否」；这类空块不清掉会卡保存校验

## 3 常驻选择器（民族／专业类别／地区类：实习地点、工作所在地…）
- 面板＝左侧列表（`.list-item-container`，行内 `.icon-container` 单选图标）＋右侧「已选 n/1」＋「取消/确定」
- 选中：**必须可信坐标点击行的 `.icon-container`**——JS 合成事件、点行容器、点行中心、搜索框回车全部无效
- 提交：JS 点击 `.phoenix-button__content`（文本「确定」）；判据是计数文本**以 1 开头**（形如 `1/`）
- 行多时先用面板搜索框（`input[placeholder="搜索"]`）过滤，再测过滤后首行图标的坐标
- 面板在视口外（y > innerHeight）时先让触发行滚到中部、**重测坐标**再点
- **（本通道实测首选）直调组件自身的选择回调**：合成鼠标事件点不中这类自绘列表项时，沿选项节点的 `__reactInternalInstance$` 向上找带 `onChangeCheck` 的组件层，调 `props.onChangeCheck(props.data, false)` 完成选中；展开下一级用 `props.onClickLabel(props.data)`；提交仍点 `.phoenix-button__content` 里的「确定」。民族／籍贯／生源地／现户口所在地四个字段由此全部写入成功（2026-09-17 实测，2026-09-19 复现）。同法扩展：**选项文本与数据结构**可在该层 `props.data` 上直接读到，不必靠猜

## 4 普通下拉（最高学历／学位／政治面貌／健康状况／学历／学习形式／类型…）
- JS 点击 `.phoenix-select` 开层 → 在**可见层**内按文本精确匹配选项并 JS 点击 → 回读 `.phoenix-select__input` / `placeHolder` 校验
- 未命中就把该层选项文本打出来，不猜
- 命名差异：本科＝**「大学」**；硕士＝「硕士研究生」；学习形式＝「全国普通高等院校全日制」；教育经历「学历」选项为 高中及以下／大专／大学／硕士研究生／博士研究生（**无单独「高中」项**，高中经历选「高中及以下」）；「学习形式」选项随学历联动（高中经历对应「高中全日制」）
- **开层的点击要打在 `.phoenix-select`（或 `.phoenix-select__wrapper`／`.phoenix-select__input`）上，且含原生 `click()`**——只派发 mousedown／mouseup／click 三件套开不出来。**同一字段连续点击是 toggle**，第二次会把已开的层关掉；点开别的字段再点回来即可复位（2026-09-17 实测）

## 5 日期控件
- **日级日历**（出生日期／毕业时间／获奖时间）：不要用 `.phoenix-calendar-input` 直填——会被解析成错月且不提交。四步走：
  1. 点触发器开层
  2. 点 `.phoenix-calendar-year-select` → 年面板选年
  3. 点 `.phoenix-calendar-month-select` → 月面板选月
  4. 点日格；同文本会在相邻月各出现一次且 class 相同 → 用**计算色值**排除灰格：`getComputedStyle(cell).color !== 'rgb(191, 191, 191)'`
- **月份面板**（教育／实习／项目的开始-结束时间）：`.phoenix-calendar-month-panel` + `.phoenix-calendar-month-panel-month`；年份用 `.phoenix-calendar-month-panel-year-select` 或 `.phoenix-calendar-prev-year-btn` 逐年回退（≤10 次可行，约 0.2s/次）
- 年面板陷阱：**首次打开直接点年会关掉整个面板**（点到旧实例）→ 先点 `.phoenix-calendar-year-panel-prev-decade-btn` 翻十年代触发重渲染，再点目标年格
- 每步之前先清场（`document.body` 派发 mousedown/mouseup/click）：残留弹层会让「取最后一个可见层」取错
- **（本通道实测首选）年月控件直接写值，不要走弹出面板**：点开只把 React 外层 `visible` 置真，内层 popup 恒 `display:none`、`.phoenix-calendar` 不挂载，此后每次点击都变成「关闭」；调 `onVisibleChange(false)` 复位、甚至重载页面都开不出来。可靠办法＝沿该字段 input 的 `__reactInternalInstance$` 找**带 `format`（含 `YYYY`）且 `onChange` 是函数**的那层，调 `onChange('2025/09','2025/09')` 直接落值。**值在 props 层是字符串且为斜杠式**（年月 `YYYY/MM`、日级 `YYYY/MM/DD`；input 上显示的才是连字符式），由同页已填字段的 props 反证。六个年月字段（教育起止、实习 4 段起止、校园 2 条起止）全部由此写入并重载留存（2026-09-17 实测）。写日期前先用**同页已填同类字段**确认值类型与格式，不要假设是 moment 对象

## 6 文本与字数
- 输入框／文本域：**交付一律走真实键入**（`browser_input_text`，秒回、中文无损）——本平台实测合成写入不落库。React 原型 setter ＋ `InputEvent('input',{inputType:'insertText',data})` ＋ `change` **只作侦察／临时草稿，不得作交付手段**。写完立即回读，判据是**保存后整页回读**（真重载用 `browser_go_to_url`；`browser_tab_reload` 实测是空操作）。本平台属手册 §3.7.5 的「默认走真实输入」，例外三类参见该条。
- 分点编号的描述类字段（工作内容、项目描述等）用**真实换行**分隔（`1.` `2.` `3.` 各占一行），**不用空格**——空格分隔会被部分系统在保存回读时吞掉、造成两点粘连。
- 上限读 `.phoenix-textarea__bottomBar`（形如 `204/200`）→ 超限**按整条精简**，不在句中截断
- 已实测上限：实习「工作内容描述」200；项目「项目描述／项目中职责」200（区块提示写 100，**以计数器为准**）；兴趣爱好「描述」100；「自我评价」400。**带 `n/N` 计数器的 textarea（自我评价等）需失焦才提交**——真实键入后直接保存，重载回来是空的；补一次 `blur()` 并派发 `change`／`input` 再保存即留存（2026-09-17 实测，两次「暂存→重载」对照）。同类计数器控件收尾都要做这一步

## 7 保存与校验
- 底部「保存」按钮；保存后自动跳只读视图（不是失败）
- 保存前扫必填：`.form-item__required`（或标题含 `icon-cus-bitian`）逐项判空，报「必填 N 项为空」
- **保存前做「库→表」覆盖清点**：拿库内条目清单（internships／campus／projects／awards／family／证书／语言）逐项确认「表里有没有落位」；表单无对应区块时按经历归类口径就近归位，或报给使用者，**不得默认丢弃**（曾因只做了「表→库」核对而漏填同类条目）
- 区块要求原文要读：教育经历「必填，自高中以上学习经历填起」（→ 高中条目必须填）；奖励/活动最多 5 条；兴趣爱好最多 3 条；项目经历最多 5 条
- 上传：`input[type=file]` 通常两个——`accept` 含 `image/*` 的是证件照；另一个是**上传简历解析入口**（文案「拖拽或点击上传简历，我们帮你快速解析」）——解析会覆盖已填字段，未获使用者明确要求不要用

## 8 本通道（QQ 浏览器）实测补充（2026-09-17，`<租户>.zhiye.com` 正式表单）

- **React 版本＝16**：fiber 键名是 `__reactInternalInstance$<rand>`（fiber）与 `__reactEventHandlers$<rand>`（props），**不是** `__reactFiber$`／`__reactProps$`。按 `__react*` 前缀判 React 仍成立，但取 props 必须用前者；顶层 fiber 上溯 `memoizedProps`／`stateNode.state` 的写法不变。
- **凤凰下拉开层只有一条路**：用**真实点击**打触发器——`find_and_act --by text --value "请选择" [--nth N] --action click`（`--nth` 为 1-based DOM 序）。已实测**无效**的手段：JS 合成 mousedown/mouseup/click（点容器／ul／箭头／placeholder／input 全试过）、`browser_click_element` 点 input 或容器、focus 后 Enter／Space／双击、直接调用 fiber 上的 `onClick`／`onPopupVisibleChange`。
- **选项选中**：面板打开后选项类名 `.phoenix-selectList__listItem`，用 `find_and_act --by text --value "<选项文本>" --action click` 选中；回读 `.phoenix-select__placeHolder` 文本。
- **`browser_get_dropdown_options`／`browser_select_dropdown_option` 在本系统不可用**——只认原生 `<select>`，对凤凰下拉返回 `No options found in any frame for dropdown`。
- **文本写入三条路，只有两条能交付**：① `find_and_act --action focus`（按 CSS/文本定位）＋ `browser_keyboard_op --action inserttext`＝原子真实输入，**落库**，且不必取 snapshot 索引（推荐）；② `browser_input_text --index`＝逐字符真实键入，**落库**；③ `find_and_act --action fill`＝DOM setter＋合成事件，DOM 与 React props 都变但**保存后归零**，**禁止用于交付**。
- **日期控件**：`browser_click_element`（真实点击）能打开 `.phoenix-calendar`（基线 0 → 点击后 1/1）；开层后仍按 §5 的年／月／日三步走。
- **上传做不到**：本通道无法写 `input[type=file]`（`fill` 后 `value` 空、`files.length=0`），附件一律请使用者手动上传。
- **保存与重载**：JS 点「暂存」按钮可行；验证务必用 `browser_go_to_url` 重新导航。导航会触发 `beforeunload` 对话框挡住后续命令，先用 `browser_dialog --action accept` 放行。（2026-09-19 补：对话框不处理时，**其后任何命令都整体失效**，不只是求值——见手册 §3.4）

## 9 岗位投递表单（`zhiye.com/form?fromPage=job&jobAdId=…`）补充（2026-09-19 实测·**首见待验**，达门槛后并入上文各节）

- 作业页是**岗位投递表单**，底部按钮为**「暂存」＋「预览并提交」**（与简历编辑页的「保存」不同）；保存接口 `POST /api/Submission/TempSave`，成功体 `{"Code":200,"Message":"operation success","Data":"<草稿id>"}`，重复暂存 `Data` 不变——可作草稿同一性判据
- **地区类字段有多选形态**（「意向工作地点」可多选，与 §3 的单选面板不同）：面板内逐行 `onChangeCheck`／`onClickLabel` 与面板「确定」的 `onSubmit([data])` **都只改显示、不落库**；可行写法＝沿 `.phoenix-select` 的 `__reactInternalInstance$` 向上找到 `value` 为**数组**且带 `onChange` 的层，调 `onChange([{id:'1100',label:'北京市'}])`——此后暂存请求体出现 `WorkPlace={"text":"北京市","value":"1100"}`。**但该字段服务端不回填**：刷新后表单仍为空（两次复现），提交前须现场确认
- 页面带 `beforeunload` 拦截：重载／求值前先 `browser_dialog --action accept`（手册 §3.4、§6.2）
- 本站结构事实：获奖区块「奖项类型」**只有 奖学金／竞赛**，无荣誉称号类目（荣誉称号类硬填即错填）；「竞赛名称」带星标必填，奖学金类按不适用填 `-`；教育经历**无高中层级**（页内说明「自大学以来的教育经历填起」）
- 已复现的既有手法（沿用，不重复记）：单选地区面板 `onChangeCheck` ＋ `onClickLabel`（户口所在地）、年月／日期写入（§5）、真实键入（§6）、新增条目后整页回读（§2）
