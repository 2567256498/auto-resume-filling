---
name: midea-autofill
description: 美的集团校园招聘官网（careers.midea.com/schoolOut/resume）校招简历填写配方：Vue 3 + 自研 md- 组件库；区块与行容器有稳定类名（ihr_recruit_resume-block-* 与 ..._multiple_form-<区块>-<序号>，按行定位优于序号）；ihr_base_picker 字典下拉须双击展开且选项异步加载；日期框须真实键入；div.action-add 单次点击语义与区块条数上限；div.action-delete 弹确认框；暂存＝存草稿、创建简历＝提交（禁点）。Use when 填写 美的 / midea 校招网申简历、careers.midea.com。
agent_created: true
---

# 美的集团校园招聘官网简历填写配方

> 适用：`https://careers.midea.com/schoolOut/resume`（美的集团校园招聘官网·创建/编辑简历页）。
> 框架层无对应 skill（非 antd／非 element-ui，是自研 `md-` 组件库）；本文件只写该系统专属实现。字段取值与口径见使用者数据层（配置项 4）。
> 证据与复核记录：台账与变更档案（配置项 6，不随包）。
> **通道 = QQ 浏览器**（命令映射见手册 §三）。⚠️ 本系统的下拉、弹窗、滚动三类交互**要求标签页在前台**（见 §7），标签页在后台时本配方多数步骤会静默失败。
> **本通道已复现的动作**：判框架、页面内 JS（原型 setter／完整事件序列派发／组件实例直调）、`browser_go_to_url` 真重载三项均已在本系统跑通；真实点击与语义定位**部分可用**（用于点「暂存」与开字典面板，但对 `div.action-add` 无效，须页内 `element.click()`）；**未复现**的是 iframe 穿透与附件上传（本通道无上传命令，见手册 §3.4），本配方不依赖二者。

## 1 识别判据

- URL 含 `careers.midea.com/schoolOut/resume`。
- 区块容器类名含 `ihr_recruit_resume-block`；行容器含 `ihr_recruit_resume-block-multiple_form`。
- 控件类名 `md-input__inner` / `md-textarea__inner` / `ihr_base_picker-search_input`；选择器面板 `ihr_dict_picker-panel ihr_base_picker-panel`。
- 页脚按钮：`暂存`（`md-button is-plain is-round`）、`创建简历`（`md-button--primary`）。

## 2 页面结构

固定区块顺序（**无** 证书、技能、家庭、校园职务/在校职务、自我评价 区块）：

| 区块 | 标题 | 区块类名 |
|---|---|---|
| 附件解析 | 简历附件 | —（上传区，`创建简历` 同页顶部） |
| 基本信息 | 基本信息 | —（平铺 `md-form-item`） |
| 教育经历 | 教育经历 | `ihr_recruit_resume-block-edu` |
| 实习经历 | 实习经历 | `ihr_recruit_resume-block-work` |
| 项目经验 | 项目经验 | `ihr_recruit_resume-block-project` |
| 获奖经历 | 获奖经历 | `ihr_recruit_resume-block-awards` |
| 发明专利 | 发明专利 | `ihr_recruit_resume-block-patent` |
| 论文 | 论文 | `ihr_recruit_resume-block-paper` |
| 语言能力 | 语言能力 | `ihr_recruit_resume-block-language` |
| 特长爱好 | 特长爱好 | `ihr_recruit_resume-block-specialty` |
| 备注 | 备注 | 仅标题 + `div.action-add`（无独立区块类名） |
| 附件 | 相关作品/附件 | —（`上传文件` 按钮） |

- **行容器带稳定类名**：`ihr_recruit_resume-block-multiple_form-<区块>-<序号>`，序号 0-based，如 `..._form-edu-0`、`..._form-work-3`、`..._form-awards-2`、`..._form-language-0`。**按行定位优先用这个**，比 snapshot 序号或 `.md-form-item` 全局序号稳（一次重渲染即全部错位）。
- 每个 `md-form-item` 由 `.md-form-item__label` 给标签；`is-warning` 类表示该校验未过（常见于必填未填）。
- 字段上限：工作描述／项目职责／项目成果／特长爱好 计数器为 `n / 1000`；工作描述实测按 1000 上限写。

## 3 写入通道

- **文本字段（input / textarea）：原型 setter ＋ 派发 `input`/`change` 的合成写入即可落库**，无需真实键入。实测「暂存 → `go_to_url` 整页重载 → 回读」三重复证。**判据一律是保存后整页回读**，不以写入时的客户端回显为准。
- **日期框（`md-range-input` / 出生日期 / 学习时间 / 起止时间）：必须真实键入并回车**。先用真实击键全选（`focus` + `select`）再覆盖输入，否则会与旧值拼接（实测出现 `2026-042026-01`）。只到「月」精度的控件，落库记为当月，日按控件粒度（教育/实习填到月，获奖时间落成 `YYYY-MM-01`）。
- **分点描述用真实换行**（各分点各占一行，不用空格），与手册 §3.7.10 一致。
- 中文参数经 JSON 文件／base64 传递，避免 shell 编码破坏。

## 4 字典下拉（`ihr_base_picker`）

- 结构：`.ihr_base_picker`（含 `.ihr_base_picker-content` > `input.ihr_base_picker-search_input`，以及 `.ihr_base_picker-icon`）；面板为 `.ihr_dict_picker-panel.ihr_base_picker-panel`，选项 `.ihr_picker_menu-item`，文本在 `.ihr_picker_menu-item_label`。
- **字典是页面加载时一次性预取、缓存在 JS 内存里的**：点击展开**不发起任何新请求**（XHR/fetch 抓包实测 `cap=0`），选项也不因往搜索框键入而重新检索（键入只改输入框显示，不动选项）。
- **定位面板＝stale 标记法（2026-09-16 定论，替代旧的「按可见性找面板」）**：① 先给 DOM 里现存的所有 `.ihr_base_picker-panel` 打上 `data-stale="1"`；② 真实点击目标选择器（`find_and_act --by css <sel> click` 或 `browser_click_element --index`）——**点击会新建一个面板**（该选择器先前的面板仍留在 DOM 里）；③ 找**没有** `data-stale` 的那个面板，它就是这个选择器的面板；④ 读它的 item 文本，或对目标 item 的 `.ihr_picker_menu-item_label` 依次派发 `mousedown`＋`mouseup`＋`click` 完成选中。
- ⚠️ **不要用 `getClientRects().length>0`／`getBoundingClientRect()` 判断面板或选项是否可用**：隐藏文档下**所有**元素 rect 均为 0（见 §7），旧脚本因此把「已打开的面板」判成没打开、把「完整字典」判成只渲染了 2 项——本文件早期版本的「后台阻断下拉」结论即由此误判而来。
- **同一选择器重复点击是「开/关」切换**：已开时再点会关掉，不要靠连点两次「确保打开」；判据是第 ③ 步是否产生了新面板。
- **选中后 `input.value` 被清空是正常的**——值存在组件状态里、渲染成文本。**回读要读渲染文本**（`.ihr_base_picker-content` 的 `innerText`，已选值在 `span.ihr_base_picker-single_selected`）；控件根上的 `ihr_base_picker--selected` 类可直接判定「该项已有值」。
- ⚠️ **一个 `md-form-item` 里可能不止一个控件，回读必须遍历全部**：`证件号码`＝证件类型 picker ＋ 号码 `input`；`手机号码`＝区号 picker ＋ 号码 `input`；`外语类型`＝`.code_group-select` 内**两个** picker（语种「英语」＋考试类型「雅思 (IELTS)」）。只取「第一个 input」或「第一个 picker」会把已填好的手机号、身份证号读成空（实测踩过，一度误判为「必填有空缺」）。
- **外语只够一组槽位**：`外语类型`（语种＋考试类型两个 picker）＋ `外语等级`（成绩）。英语两项成绩在本表单**无独立落点**，按使用者数据层的「优先雅思」口径取值。
- **已验证字典规模（面板 item 数＝字典全量，不是「只渲染一屏」）**：语言名称 114 项、语言熟练程度 4 项（了解／掌握／熟练／精通）、**获奖「奖项类型」只有 2 项（竞赛／奖学金）**、获奖「奖项级别」6 项（国际级／国家级／省市级／校级／院系级／班级）。⇒ **获奖经历录不进「荣誉称号」类**（三好学生、优秀学生干部等无对应类型）。
- 教育「学校名称」「外语类型」「国籍/地区」、籍贯「省-市-区」树、获奖「奖项类型／奖项级别」等均为同类选择器（地区树用 `.ihr_tree-item`）。

## 5 新增与删除条目

- **新增：`div.action-add`（不是原生 button，`find_and_act --action click` 无效）。页内 `element.click()` 一次＝新增 1 行**；该 `@click` 会被合成事件触发。⚠️ 若脚本既调 `.click()` 又补派发一次 `click` 事件，会**一次新增 2 行**——加行脚本必须只触发一次。
- **删除：`div.action-delete`（每行一个，同一区块内按顺序排列）。点击后弹 `md-message-box` 确认框**「确定要删除你的<区块名>吗？」，须再点「确定」才真删除（只点删除＝只弹框，行数不变）。
- 新增的行默认插在该区块**末尾**，不按时间排序；若表单未做排序，条目顺序＝填写顺序（跨时间倒序需要自己按序填）。
- ⚠️ **【待验·1 次观测】客户端新增的行，其选择器是空字典**：新增行的「奖项类型／奖项级别」打开后显示**「暂无数据」**（面板 DOM 内是 .md-empty、.ihr_picker_menu-item 数为 0），且**不发起任何请求**（字典已在内存，开面板不重拉）。补填行内其它字段（获奖时间、奖项名称）后仍为空。⇒ 新增的获奖行**无法设置必填的类型／级别**，即本表单当前无法再新增获奖条目。

## 6 保存与回读

- **保存草稿 = 页脚 `暂存` 按钮**（文本「暂存」，只点一次）；成功提示「暂存成功」。
- **`创建简历` = 提交/投递动作，除用户明确指示外禁点。**
- 保存判据：整页重载（`go_to_url` 同一 URL；`tab_reload` 是空操作）后数据仍在。**重载后页面与字典要等约 20 秒再操作**，否则读到空白或空选项。
- 顶部「简历附件」上传区会把整页渲染成上传引导态，**首屏刚加载时字段会短暂显示为空**，须等加载完成再判读，别误判为「数据没了」。
- 只到月的值（`YYYY-MM`，如获奖时间）落库读回为 `YYYY-MM-01`。

## 7 通道边界（未在本通道复现的写法／已知失败）

- ⚠️ **后台标签页（`visibilityState=hidden`）的真实影响（2026-09-16 更正）**：隐藏文档里**所有**元素的 `getBoundingClientRect()`／`getClientRects()` 都返回 0，所以「用可见性判面板是否打开」必然误判——**旧结论「后台时下拉拉不开、`.ihr_picker_menu-item` 恒为 0」是判据错误，已证伪并撤销**。实测后台状态下：真实点击选择器**会**创建面板、选项**全量渲染**（级别 6 项、类型 2 项、语言 114 项全在 DOM 内）、对 `.ihr_picker_menu-item_label` 派发 `mousedown`＋`mouseup`＋`click` **能正常写入并落库**（两次独立复现：级别由国际级→省市级→国际级）。后台真正会失效的是：页面与容器滚动（`pageYOffset` 恒 0）、偶发的按屏幕坐标真实点击（坐标全为 0，落点随机）、`md-message-box` 的 enter/leave 过渡（弹层卡住不消解）。⇒ **不必强求前台，改用 §4 的 stale 标记法。**
- 弹层会**堆叠**：合成点击若把确认框点出来而没关掉，再点同一条删除会再叠一个框。误堆叠后**不要盲点「确定」**（每点一次就真删一条）；整页重载可清空。
- 上传：本通道 CLI **无上传命令**，个人照片与「相关作品/附件」需使用者手工上传（或在页面内自行构造上传），不要承诺自动上传。
- 未探明：备注区点「新增备注」后的字段构成与上限（备注区仅标题 ＋ `div.action-add`，无独立区块类名、无 `md-form-item`）；教育／实习／项目／语言各区块的条数上限。
- **获奖经历上限【待验，仅 1 次观测】4 条**——曾观察到 3→4 行可加、到 4 行后再点 `action-add` 行数不增且不报错；但后台下点击本身偶发不生效，故该上限尚未复现、阈值未定。**判定口径**：点击新增后必须回读行数确认，不能凭点击返回值。
