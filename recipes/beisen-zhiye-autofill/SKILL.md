---
name: beisen-zhiye-autofill
description: 北森招聘平台 zhiye.com 系（picc.zhiye.com、coamc.zhiye.com 等，自研 Phoenix 组件）系统层配方：编辑态与只读态判据、区块容器定位、真实键入写入与回读（该平台合成写入不落库）、常驻选择器与月份面板路径、弹层清场、保存后验证方式。Use when 填写北森 zhiye 系网申表单（先读框架层配方拿通用手法，本文件只写北森专属部分）。
---


> **通道状态（ego）**：页面层手法（页面内脚本）跨通道通用；依赖通道动作的步骤（真实点击／语义定位与 snapshot 索引／iframe 穿透）按「未在本通道跑过的只有三种动作」处理，按手册 §4.3 重验后就地回写。
# 北森 zhiye 网申填写配方（系统层）

> 适用：北森招聘平台 zhiye.com 系（picc.zhiye.com、coamc.zhiye.com 等），前端为北森自研 Phoenix 组件（`phoenix-*`）。只写北森专属实现；字段取值与口径见 `数据层（项目要求文件 §〇.1 点名的单文件）`，跨框架通用手法见框架层 skill。
> 来源：2026-09-13 东方资产、中国人民保险两次网申实测（台账已复核）。

## 0 页面态与入口
- URL `...form?fromPage=editMyResume` = 可编辑；`fromPage=myResume` = 只读视图（字段渲染为 `<p class="form-item__text">`，读为空属正常，**不是数据丢失**）
- 只读页回编辑态：点页面自带「编辑简历」按钮（`BUTTON.stylest__STFooterStandardButton…`）——按钮常在视口外，先 `scrollIntoView({block:'center'})` 再测坐标，**真实坐标点击**
- 每次保存/编辑后平台会自动跳回只读视图；动手前先看 URL 判断当前是编辑态还是只读态

## 1 结构定位
- 区块容器：`.twoLineFormStyleLong`，`id` 含 `Recruitment_extPerfect<区块名>`（PersonProfile／ApplicantEducation／ApplicantWorkExperience／ApplicantInternship／ApplicantProject／RelativesDeclaration…）；**每个条目一个容器**，条目增多容器也增多 → 按 DOM 顺序取第 n 个
- 字段：容器内 `.form-item`，标题 `.form-item__title`（必填另有 `.form-item__required` 或 `icon-cus-bitian`）；**一律按标题文本定位，禁用序号**
- 语言能力／兴趣爱好／奖励活动／家庭情况／自我评价不在 `.twoLineFormStyleLong` 内 → 用全页 `.form-item` 按标题匹配；「姓名」「政治面貌」等标签会重复，家庭情况取**最后一个**
- **重复区块（实习／校园经历／奖励／家庭情况）里同名字段会多次出现**：按标题文本匹配只会命中**第一个**同名字段——实测按标题填家庭情况「姓名」，值写进了表单顶部的「姓名」（如把表单顶部的「姓名」填成了家庭成员的姓名）。这类区块（以及任何标题会重复的场景）一律按 `.form-item` 的**全局索引**定位：先 dump 全字段清单拿索引，再按索引操作（2026-09-17 银河证券实测，事故背书）

## 2 区块入口与新增条目
- 工作经历／实习经历／项目经历 的首个控件是**「点击添加」下拉**，选项仅两个：`开始添加 ` / `无 `——有经历选「开始添加」展开字段；应届生无全职工作经历 → 工作经历选「无」
- 点 `添加XX` 后新增的条目**先渲染为折叠行**（也是「点击添加」下拉）→ 还要再选「开始添加」才出字段
- `添加XX` 按钮是 styled-components 的 DIV/SPAN（`..._addButton`）：先试 JS 合成点击，条目数没变就改**真实坐标点击**（测 `SPAN.sc-jeraig` 或外层 DIV 中心）
- **新增条目后必须逐条回读整个区块**：实测新增一条项目经历后，既有条目（JA中国）的字段被清空、且条目顺序变化 → 加完立刻按字段值（如「项目名称」）逐条核对，发现被清空立即补回；定位条目一律用字段值，不用索引
- **点「添加XX」按钮必须传完整合成事件对象**：其 `onClick` 内部读 `e.target.getBoundingClientRect()`，只给 `{type:'click',…}` 会抛 `Cannot read properties of undefined`，**且当前行输入被清空**。事件对象需含 `target`／`currentTarget`／`srcElement`／`nativeEvent`／`clientX,clientY` 与 `preventDefault`／`stopPropagation`／`persist`／`isDefaultPrevented`／`isPropagationStopped`（2026-09-17 银河实测：「添加家庭情况」简版 74→74 且清空姓名，完整版 74→78）
- **新增条目后要回读的是整页，不是只有新增块**：新增会让 React 重排，**已经填好的 select 值会串位**——实测加一条实习后，第二条校园经历的起止时间被写成新实习的日期。凡是本轮加过条目，收尾前必须整页回读一遍（2026-09-17 银河，事故背书）
- **「添加」式问答块没有删除入口**：多出来的空块（行内只有下箭头与 `phoenix-select__clearIcon`）无法删行，只能把它选「否」；这类空块不清掉会卡保存校验

## 3 常驻选择器（民族／专业类别／地区类：实习地点、工作所在地…）
- 面板＝左侧列表（`.list-item-container`，行内 `.icon-container` 单选图标）＋右侧「已选 n/1」＋「取消/确定」
- 选中：**必须可信坐标点击行的 `.icon-container`**——JS 合成事件、点行容器、点行中心、搜索框回车全部无效
- 提交：JS 点击 `.phoenix-button__content`（文本「确定」）；判据是计数文本**以 1 开头**（形如 `1/`）
- 行多时先用面板搜索框（`input[placeholder="搜索"]`）过滤，再测过滤后首行图标的坐标
- 面板在视口外（y > innerHeight）时先让触发行滚到中部、**重测坐标**再点
- **（本通道实测首选）直调组件自身的选择回调**：合成鼠标事件点不中这类自绘列表项时，沿选项节点的 `__reactInternalInstance$` 向上找带 `onChangeCheck` 的组件层，调 `props.onChangeCheck(props.data, false)` 完成选中；展开下一级用 `props.onClickLabel(props.data)`；提交仍点 `.phoenix-button__content` 里的「确定」。民族／籍贯／生源地／现户口所在地四个字段由此全部写入成功（2026-09-17 银河实测）。同法扩展：**选项文本与数据结构**可在该层 `props.data` 上直接读到，不必靠猜

## 4 普通下拉（最高学历／学位／政治面貌／健康状况／学历／学习形式／类型…）
- JS 点击 `.phoenix-select` 开层 → 在**可见层**内按文本精确匹配选项并 JS 点击 → 回读 `.phoenix-select__input` / `placeHolder` 校验
- 未命中就把该层选项文本打出来，不猜
- 命名差异：本科＝**「大学」**
- 开层的点击必须打在 `.phoenix-select`（或 `.phoenix-select__wrapper`／`.phoenix-select__input`）上，且**要含原生 `click()`**——只 `dispatchEvent` mousedown/mouseup/click 三件套开不出来。**同一字段连续点击会 toggle 关层**，中间点开别的字段再关一下即可复位（2026-09-17 银河实测）；硕士＝「硕士研究生」；学习形式＝「全国普通高等院校全日制」；教育经历「学历」选项为 高中及以下／大专／大学／硕士研究生／博士研究生（**无单独「高中」项**，高中经历选「高中及以下」）；「学习形式」选项随学历联动（高中经历对应「高中全日制」）

## 5 日期控件
- **日级日历**（出生日期／毕业时间／获奖时间）：不要用 `.phoenix-calendar-input` 直填——会被解析成错月且不提交。四步走：
  1. 点触发器开层
  2. 点 `.phoenix-calendar-year-select` → 年面板选年
  3. 点 `.phoenix-calendar-month-select` → 月面板选月
  4. 点日格；同文本会在相邻月各出现一次且 class 相同 → 用**计算色值**排除灰格：`getComputedStyle(cell).color !== 'rgb(191, 191, 191)'`
- **月份面板**（教育／实习／项目的开始-结束时间）：`.phoenix-calendar-month-panel` + `.phoenix-calendar-month-panel-month`；年份用 `.phoenix-calendar-month-panel-year-select` 或 `.phoenix-calendar-prev-year-btn` 逐年回退（≤10 次可行，约 0.2s/次）
- 年面板陷阱：**首次打开直接点年会关掉整个面板**（点到旧实例）→ 先点 `.phoenix-calendar-year-panel-prev-decade-btn` 翻十年代触发重渲染，再点目标年格
- 每步之前先清场（`document.body` 派发 mousedown/mouseup/click）：残留弹层会让「取最后一个可见层」取错
- **（本通道实测首选）年月控件直接写值，不要走弹出面板**：点开只把 React 外层 `visible` 置真，内层 popup 恒 `display:none`、`.phoenix-calendar` 不挂载，此后每次点击都变成「关闭」；调 `onVisibleChange(false)` 复位、甚至重载页面都开不出来。可靠办法＝沿该字段 input 的 `__reactInternalInstance$` 找**带 `format`（含 `YYYY`）且 `onChange` 是函数**的那层，调 `onChange('2025/09','2025/09')` 直接落值。**值在 props 层是字符串且为斜杠式**（年月 `YYYY/MM`、日级 `YYYY/MM/DD`；input 上显示才是连字符式），由同页已填字段的 props 反证。六个年月字段（教育起止、实习4段起止、校园2条起止）全部由此写入并重载留存（2026-09-17 银河实测）。写日期前先用**同页已填同类字段**确认值类型与格式，不要假设是 moment 对象；**格式还随站点／组件版本而异**——银河（2026-09-17）为斜杠式 `YYYY/MM`，中国人寿（2026-09-24）为连字符式 `YYYY-MM-DD` 且写在**带 `dateTimeType` 属性**的层上，错格式不报错、直接把值**清空**（见 §九）

## 6 文本与字数
- 输入框／文本域：**本平台实测合成写入不落库，交付一律走真实键入**（`ego_fill`／键盘事件；通道层做法见 `CHANNEL-ego.md`）。React 原型 setter ＋ `InputEvent('input',{inputType:'insertText',data})` ＋ `change` **只作侦察／临时草稿，不得作交付手段**。写完立即回读，并以**保存后整页回读**为判据（`CODEBUDDY.md` §一.4；2026-09-16 用户裁定）。
- 分点编号的描述类字段一律用**真实换行**分隔（各占一行），不用空格（`CODEBUDDY.md` §二.$1）。
- 上限读 `.phoenix-textarea__bottomBar`（形如 `204/200`）→ 超限**按整条精简**，不在句中截断
- 已实测上限：实习「工作内容描述」200
- **textarea（自我评价等带 `n/N` 计数器的字段）需失焦才提交**：真实键入后直接保存，重载回来是空的；补一次 `blur()` 并派发 `change`／`input` 再保存即留存（2026-09-17 银河实测，两次「暂存→重载」对照）。同类计数器控件收尾都要做这一步；项目「项目描述／项目中职责」200（区块提示写 100，**以计数器为准**）；兴趣爱好「描述」100；「自我评价」400

## 7 保存与校验
- 底部「保存」按钮；保存后自动跳只读视图（不是失败）
- 保存前扫必填：`.form-item__required`（或标题含 `icon-cus-bitian`）逐项判空，报「必填 N 项为空」
- **保存前做「库→表」覆盖清点**：拿库内条目清单（internships／campus／projects／awards／family／证书／语言）逐项确认「表里有没有落位」；表单无对应区块时按经历归类口径就近归位，或报给用户，**不得默认丢弃**（人保漏填领英俱乐部即因只做了「表→库」核对）
- 区块要求原文要读：教育经历「必填，自高中以上学习经历填起」（→ 高中条目必须填）；奖励/活动最多 5 条；兴趣爱好最多 3 条；项目经历最多 5 条
- 上传：`input[type=file]` 通常两个——`accept` 含 `image/*` 的是证件照；另一个是**上传简历解析入口**（文案「拖拽或点击上传简历，我们帮你快速解析」）——解析会覆盖已填字段，未获用户明确要求不要用

## 8 三一集团 sany.zhiye.com 补充（2026-09-19 实测·**首见待验**，达门槛后并入上文各节）
- 作业页：`zhiye.com/form?fromPage=job&jobAdId=…&userId=…`（岗位投递表单），底部按钮为**「暂存」＋「预览并提交」**（与东方资产／人保／银河的「保存」不同）；保存接口 `POST /api/Submission/TempSave`，成功体 `{"Code":200,"Message":"operation success","Data":"<草稿id>"}`，重复暂存 `Data` 不变
- **地区类字段有多选形态**（「意向工作地点」可多选，与 §三 的单选面板不同）：面板内逐行 `onChangeCheck`／`onClickLabel` 与面板「确定」的 `onSubmit([data])` **都只改显示、不落库**；可行写法＝沿 `.phoenix-select` 的 `__reactInternalInstance$` 向上找到 `value` 为**数组**且带 `onChange` 的层，调 `onChange([{id:'1100',label:'北京市'}])`——此后暂存请求体出现 `WorkPlace={"text":"北京市","value":"1100"}`。**但该字段服务端不回填**：刷新后表单仍为空（两次复现），提交前须现场确认。**（2026-09-24 更正）「服务端不回填」是站点差异、不是平台事实**——中国人寿站同型字段（期望工作城市，同为 `phoenix-select--multi`）重载后仍有值，见 §九
- 页面带 `beforeunload` 拦截：重载／求值前先处理对话框（CDP `Page.handleJavaScriptDialog`，**本通道待验证**；见 手册 §3.5）
- 本站结构事实：获奖区块「奖项类型」**只有 奖学金／竞赛**，无荣誉称号类目（库内荣誉称号不录，硬填即错填）；「竞赛名称」带星必填，奖学金类按不适用填 `-`；教育经历**无高中层级**（页内说明「自大学以来的教育经历填起」）
- 已复现的既有手法（沿用，不重复记）：单选地区面板 `onChangeCheck`＋`onClickLabel`（户口所在地）、年月／日期写入（§五）、真实键入（§六）、新增条目后整页回读（§二）
## 9 中国人寿 chinalife.zhiye.com 补充（2026-09-24 实测·**首见待验**，达门槛后并入上文各节）
- 作业页与 §八 同形：`chinalife.zhiye.com/form?fromPage=job&jobAdId=…&userId=…`，底部按钮 `暂存`／`取消`／`预览并提交`；本站 164 个 `.form-item`
- **日期控件写法（本轮试错定论）**：点面板不可行（同 §五，内层 popup 不挂载）。沿该字段 input 的 `__reactInternalInstance$` **逐层**找**带 `dateTimeType` 属性**的组件层，调 `mp.onChange('YYYY-MM-DD')`。**格式随站点／组件版本而异**——本站连字符式 `2019-06-01` 命中，而 `2019/06/01`（银河的斜杠式）与对象式 `{value:'…'}` **都被静默清空**（不报错、回读才发现）。**别假设格式**：先按「层深 × 候选格式」扫一遍，命中的那组再批量用
- **普通下拉写法**：按键列出下拉选项的通道命令 在本通道恒返回 `No options found in any frame`，面板点选也不可靠。可靠办法＝沿 `.phoenix-select` 内 input 的 fiber 逐层找到 `memoizedProps.options` 为数组的那层（本站为**第 16 层**），在数组里按 `label` 命中后调 `mp.onChange(hit)`（`hit` 即该数组元素，形如 `{label:'<语种>',value:<id>}`）；写完回读该层 `value` 确认
- **条目顺序由服务端按起始时间倒序重排**：本站**没有排序控件**（每条只有「删除」），DOM 里新增的条目只追加在末尾；但**暂存后重载，服务端返回的是起始时间倒序**（实测：页内 亦庄／食品院／第四范式／民生 → 重载后 民生／亦庄／食品院／第四范式）。**页内顺序 ≠ 保存后顺序**，不必为「最新在前」另想绕法
- **保存按钮必须真实点击**：`ego_click` 对「暂存」走 `encodedId JS fallback` 时**返回成功、页面无任何报错，但服务端数据未变**（本次首存即由此静默失败）；改用按文本精确定位点击（`ego_click` + `page.getByText()`）后保存成功。**判据只能是服务端重载回读**
- **`beforeunload` 不是脏态判据**：本站表单**恒挂** `beforeunload`（另开一个从未编辑过的同 URL 标签页，导航时同样弹确认框）；反之真正未保存时也没有更强的提示。**不要用它推断「存上没有」**。由此，「保存后刷新回读」要**另开标签重载**（`browser.openOrReuseTab(<同一 URL>)`）——本标签内的导航会被拦下；新标签不一定是命令落点，用 `performance.timeOrigin` 分辨（`performance.now()` 数字大的是留在身后的旧标签，数据也是旧的）。机制见 手册 §3.5
- 本站结构（与 §八 三一不同）：获奖区块字段为 获奖时间／奖项名称／获奖级别／颁奖单位／其他补充／担当角色，**没有「奖项类型」字段**（§八 那句是站点差异，不是平台事实）；教育经历**要求填到高中**（页内说明「请从最高学历填写，填写至高中」）；工作经历描述上限 **2000**、自我评价 **32766**；语言能力为 外语语种＋语言等级＋得分 三件套（等级选项含 托福／雅思／全国大学英语六级…）
- **地区类多选字段本站正常回填**：期望工作城市（`phoenix-select--multi`）写入后暂存、重载，该栏仍有值，根 `.phoenix-select` 类名含 `phoenix-select--exsitMultiValue`——**回填与否按站点而异**，一律以重载回读为准（§八 那句仅对三一站成立）
- 已复现的既有手法（沿用，不重复记）：真实键入并在保存后整页回读（§六）、新增条目后整页回读（§二）、保存前扫必填（§七）

## 10 中金公司 cicc.zhiye.com 补充（2026-09-25 实测·**首见待验**，达门槛后并入上文各节）
- 作业页：`cicc.zhiye.com/form?fromPage=editMyResume`（编辑简历页，非岗位投递表单），底部按钮「取消」＋「保存」；区块 6 个：个人信息／教育经历／工作经历／证书／语言能力／简历附件，**无**项目经历、奖励荣誉、兴趣爱好、自我评价、家庭区块——奖项并入证书栏（§七 口径），无对应区块的内容如实缺位即可
- **「保存」是全页校验：任一区块必填缺失则整页不落库**。实测：个人信息写完先点保存，服务端无任何数据写入（另开标签重载为旧值），左侧导航「工作经历」出现「!」校验标记；全部必填齐后再点一次保存才落库。推论：这类全页保存表单必须把所有必填填完再保存，不能指望分块落库
- 保存成功后自动跳只读视图（§〇 口径）；只读视图的值渲染在 `.form-item__control p`，按 `input.value` 扫描会全部读空（§〇「不是数据丢失」的复现）
- 日期控件复现 §五：本站 props 层为**斜杠式** `YYYY/MM`（月）与 `YYYY/MM/DD`（日），写在带 `format` 的 `onChange` 层（实测 L17／L21）即命中；连字符式调了**不生效也不报错**（`props.value` 不变）——写后必须回读 `props.value` 确认真写入
- 地区面板复现 §三：现居住地／户口所在地／籍贯／工作地点全部为省市县单选面板，`onClickLabel` 逐级展开＋`onChangeCheck` 选中＋「确定」全部命中；**面板一次只开一个**——同一 eval 里连续 dispatch 两个字段的下拉会 toggle 掉前一个，必须一开一确认
- 普通下拉复现 §九 写法：`options` 数组层（本站 L16）`onChange(hit)` 全部命中（最高学历／最高学位／工作性质等）；日期与下拉写错层时静默不生效，回读是唯一判据
- 「学校名称」为本地 dataSource 自动完成（1.2 万条内置）：直接调 onSelect 层 `onSelect({label,value})` 即选中；「证书名称」为自由文本输入（非虚拟列表）
- 结构事实：教育经历无高中层级要求（页内无说明，未填高中）；教育条目顺序由服务端按学历倒序（页内先本科后硕士，保存后只读视图硕士在前）；工作经历区块实收实习（工作性质=实习），职责／离职原因 textarea 上限 2000；语言能力预填英语／精通（与档位口径一致）；textarea 换行经真实键入保留（保存回读 4 行完好）
- **岗位投递表单（`fromPage=job&jobAdId=…`，styled-components 版）与编辑简历页同站不同构（2026-09-25 实测）**：区块 8 个＝个人信息／教育经历／**其他学习经历**（高中槽位，学历下拉含小学～博士全档）／**实习经历**（独立区块，字段＝起止时间＋单位名称＋实习内容，无职位栏——部门岗位写进实习内容首行，`CODEBUDDY.md` §二.1 口径）／项目经历／工作经历／语言能力／简历附件；**实习一律填「实习经历」，工作经历留空**（应届生口径，用户明确纠正过一次）
- 本页日期控件为**连字符式** `YYYY-MM-DD`（日）与 `YYYY-MM`（月），与编辑简历页的斜杠式**相反**——同站两页面格式不同，写后必须回读 `input.value` 判格式，不能凭记忆
- 「学习形式」档位选「全国普通高等院校全日制」（档位名与常见「全日制」不同）；「学校名称」为高校字典联想（无中学），中学用手动场景（本页其他学习经历实测：联想不匹配即静默清空且会连带清空其他同名字段；最终用原生 setter＋input/change 事件写入可留存）
- 删除条目＝**phoenix-popover 确认弹层**「是否要删除该组信息？否／是」：合成事件与 `ego_click` 文本点击都不触发，须先 snapshot（给可见元素打 `data-hi` 标注）再 `ego_click` 点触发器、然后合成点击「是」；**单条目时删除按钮不渲染**（只能清空字段留空壳或先加一条再删）。**首见待验**，达门槛后并入 §三／§九

## [并入·DSH 侧 2026-10-05] 8 非 Phoenix 变体（老版 Portal 模板：`.bs_deliver` ＋ `form_container`）

> 已实测租户：zofund 中欧基金（2026-09-19）、itgholding 厦门国贸控股（2026-09-22）；本变体与 §一–§七 的 Phoenix 实现**完全不同**，先判形态再套手法。
> 尚有 5 条单租户观察（孤儿遮罩、同 id `#commonWrap` 多实例、「继续添加」落视口外、`offsetParent` 对 fixed 返回 null、`_txt`＋hidden code 成对）只在 itgholding 见过一次，按台账规则留在所在项目的经验台账 r21 行待验，复现后再并入本节。

- **形态判别**：URL 为 `/Portal/Resume/ResumeItem?stepId=…`；`body` 内含 `.bs_deliver`／`.form_container`／`li>label.label_required`；日期控件加载 `WdatePicker.js`；**完全没有 `phoenix-*` 选择器**。三步向导由顶部链接 `BSGlobal.navigate(stepId)` 切换（stepId=0 基本信息／1 个人履历／4 预览提交），全页只渲染当前 step 的区块
- **每条目一个独立 `<form>`，空白模板恒存在**（`id=emptyFrom_N`，`display:none`）：模板与实例控件同名（如 `RecruitmentPortalEducation_SchoolName`、`RecruitmentPortalExperience_CompanyName`），序号定位一定打到模板 → 动手前先给「可见且值为空的那一个 form」打标记（如 `data-ego`），后续全部按标记定位
- **Wdate 系日期控件必须键入 8 位纯数字**：出生日期输入框（`class="mul_input Wdate"`）点开后键入 `20010730` → 被其自动格式化为 `2001/07/30`；键入 `2001-07-30` 会被静默解析成错误月份（`2001/09/00`）。落库回读按控件显示格式核对
- **学校栏是只读联想控件 `school-select-v2`**：点输入框开面板 → `.sl_search_box input.ipt_df` 键入校名（可先 `fill()` 清掉其中的假占位文案）→ 点放大镜 `.btn_s` 检索 → **点结果行内 `input[type=radio]`**（点 `li`／`label` 不选中）→ 面板关闭且学校名写入只读输入框；省份靠 `.prov_list_item[itemid]` 切换；库内无校时用面板「手动添加」入口（`.manual_add` ＋ `.manual_add_ok`）
- **地区类只读控件（`Areas`）走 `.bas_select_wrap` 面板**：`li>div.lst_item>input[name=cateItems][value=code]` 是真正的选择点，**必须点行内 radio**，判据＝面板内「已选 n/10」计数变化；提交＝面板 `.bas_btn_save`（取消＝`.bas_btn_canc`）。直辖市该面板只到市级（北京市 value=1100）
- **字典弹层（行业 `hangye`／职业 `JobCategory`，`structured-data-select`）**：选项行为 `#data-list li>input.sel[name=dataSelect][id=code]+a[title=名称]`，**选中必须点 `input.sel` 本身**（点行内 `a` 走 `goNextGrade`，叶子项 `class=disabled` 直接 return，点了没反应）；确认＝该实例的 `#getAllValues`，取消＝`#cancelSelect`；判据＝`#selNum` 计数变化。写入结果是「可见 `_txt` input 显示名称 ＋ 同名隐藏 input 存 code」，提交流程以隐藏字段为准
