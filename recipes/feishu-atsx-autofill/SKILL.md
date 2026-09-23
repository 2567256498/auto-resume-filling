---
name: feishu-atsx-autofill
description: 飞书招聘 ATSx（飞书 hire / 字节招聘 SaaS 门户）简历表单自动填写。适用于使用飞书 ATSx 的校招投递页（React + Formily + UD 设计系统，类名前缀 ud__ / atsx-）。核心方法：data-form-field-id 精确定位、模块(title→right)反查卡片归属、UD Select 事件派发展开。
agent_created: true
---

# 飞书招聘 ATSx 简历表单填写

> **通道 = QQ 浏览器**（命令映射见手册 §三）。本配方多数内容不依赖通道能力——它们是在页面内执行的脚本（原型 setter／组件直调／事件派发／DOM 查询），**可直接用**；唯一风险是目标页面是否这套框架，动手前先判框架。
> **未在本通道跑过的只有三种动作**：真实点击、语义定位与 snapshot 索引、iframe 穿透——凡依赖它们的步骤都按【未复现】对待，能兜底的已写兜底；跑通后就地改写该处结论（手册 §5.3 第 5 条）。

适用于使用**飞书招聘（ATSx / 飞书 hire）SaaS 校招门户**的投递与简历页（URL 形如 `https://<门户域名>/<租户>/resume/<id>/apply`）。

与其他 UD 设计系统的自建招聘站**页面结构与交互细节不同**，勿直接套用。

## 一、识别判据（供本封装体手册 §4.7「系统判据对照与配方索引」使用）

- `document.body.className` 含 `saas-career`
- 资源域含 `feishucdn.com/obj/atsx-throne/.../portal/saas-career/`
- 字段容器类名：`.ud-formily-item`、`.ud-formily-item-label-content`、`.ud-formily-item-asterisk`（必填星号）
- 控件：`.ud__input`、`.ud__select`、`.atsx-upload`

## 二、字段定位（首选稳定键，不用坐标）

1. **首选** `[data-form-field-id="<key>"]`：每个字段容器都带 `data-form-field-id` / `data-form-field-name` / `data-form-field-i18n-name`。
   - 注意 `data-form-field-id` 会同时出现在外层容器与内层控件上，取值时用 `Array.find(e => e.querySelector('input,textarea'))` 选出含控件的那一层。
   - 常见 key：`name` 姓名、`email` 邮箱、`age` 年龄、`gender` 性别、`attachment_resume` 简历附件、`start_end_time` 起止时间、`degree` 学历、`school` 学校名称、`field_of_study` 专业；无意义数字串（如 `7673343694564673855`）对应学院/实验室/领域方向/导师等。
2. **按 label**：`.ud-formily-item` 内 `.ud-formily-item-label-content` 的文本（末尾带 `*` 需 strip）。
3. **禁用纵向坐标映射法**：页面为左右分栏，区块标题在 `applyFormModuleWrapper-left`、字段在 `applyFormModuleWrapper-right`，两者 y 坐标不对应，坐标法会把卡片判错区块。

## 三、区块与卡片归属（多条目模块）

每个区块由 6 个并列 wrapper 组成：`applyFormModuleWrapper-windowsappl / -left / -title / -textsofiaBo / -desc / -right`。带字段的是 `-windowsappl` 与 `-right`；`-title` 是区块名，但**与 `-windowsappl` 是兄弟节点而非父子**，所以不能用 `mod.querySelector(title)` 反查。

可靠反查（由内向外）：

```js
const cards = [...document.querySelectorAll('div')]
  .filter(e => /apply-form-array-card__/.test(e.className) && !/content/.test(e.className)); // 必须排除 -content，否则每张卡被计两次
const secOf = (card) => {
  const r = card.closest('[class*=applyFormModuleWrapper-right]');
  const root = r ? r.parentElement : null;
  const t = root ? root.querySelector('[class*=applyFormModuleWrapper-title]') : null;
  return t ? (t.textContent || '').trim() : '?';
};
const inSec = cards.filter(c => secOf(c) === '实习经历');
```

**用 `textContent` 而非 `innerText`**：`innerText` 对未进入视口的元素返回空串，会导致模块匹配全部失败。

## 四、写入通道（本通道实测有效）

> **口径归属**：可见 `input`／`textarea` 上的纯文本字段，按手册 §3.7.5 **默认走真实输入**（`browser_input_text`）；本节的**原型 setter 通道**用于三类例外——① 隐藏／组件托管控件、② 远程联想字段（文本值由点选动作写入）、③ 本通道真实输入不可用时的降级草稿。**保存回读发现缺失一律改真实输入重写**并在汇报里点名。本节其余内容（UD Select 展开、卡片增删、回读判据）不受此口径影响。

统一通过 `browser_eval_content_js --base64 --script <base64>` 执行；脚本整体 try/catch。

### 命令行三个坑（2026-09-15 实测，都踩过）

1. **参数值含空格必须整体加引号**：命令清单按 `shlex` 解析，`--set:text=项目名称=某项目 一期` 会被拆成两个 token，后半个变成多余参数 → CLI 直接报错、**该次写入完全没发生**（不是写错值）。正确写法 `--set:text="项目名称=某项目 一期"`。凡是含空格的值（中英混合的奖项名、带分数的证书名）都要加引号。
2. **`@b64=` / `@tpl=` 的路径用正斜杠**：反斜杠被 shlex 当转义符吃掉，`<目录>\x.js` 变成 `<目录>x.js` → `FileNotFoundError`。
3. **写入结果以脚本返回值为准**：`add_and_fill_card.js` 返回 `cards=N`、`fill_module_card.js` 返回 `字段=值`；批量添加时看 `cards=` 是否逐次 +1，能立刻发现漏写（曾出现多条证书中有若干条因空格被静默跳过，就是靠这个发现的）。

### 回读的正确方式（别用 axtree 判断空满）

`browser_tab_list` / `get_info` 返回的 axtree **只覆盖视口内元素**：视口外的模块（如多张已填卡片）不出现，容易被误判成「模块是空的」。判断空满用 `read_module_cards.js`（逐卡列字段值）或全量扫描脚本（遍历 `document`），不要用 axtree。

### 文本 input / textarea

```js
const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
el.focus(); setter.call(el, v);
el.dispatchEvent(new Event('input', { bubbles: true }));
el.dispatchEvent(new Event('change', { bubbles: true }));
el.blur();
```

- 对普通文本字段一次即落（写入后受控 input 的 `value` 属性即反映新值，说明 Formily state 已接收）。
- **学校名称 `school` 是 `ud__input`（不是 ud__select）**，用上面文本通道即可；不要误判为下拉而反复点开。

### UD Select 下拉（性别 / 获取校招信息渠道 / 学历 / 语言 / 精通程度）

- **展开**：向 `.ud__select__selector` 派发 `mousedown → mouseup → click`（`new MouseEvent(t,{bubbles:true,cancelable:true,view:window})`）即可展开，**本通道不需要真实鼠标点击**（与早前记录的结论相反，以本条实测为准）。
- **读选项**：展开后选项渲染在 `.ud__select__dropdown`（body 级 portal），选项元素类名含 `list__item`。
- **选中**：对目标选项 `el.click()`。
- **回读**：读该字段 `.ud__select` 的 `textContent`（`input.value` 恒空）。
- 选项是异步按 `data-form-field-id` 取回的；同一个 `.ud__select__dropdown` 里只会出现当前展开字段的选项，跨字段匹配文本时取最后一个匹配项即可。

### 起止时间（`start_end_time`）

容器内两个**原生 text input**（开始 / 结束），直接写入 `YYYY-MM`（精度到月）即可，无需 Enter 确认。

### 增删条目卡片

- 追加：在目标模块内找文本为「添加」的按钮 `el.click()`；React 同步 flush，**同一次 eval 内即可查询到新卡片**（取 `cards[cards.length-1]`）。
- 连续追加多张卡片时，在每次 add 之后加一条 `browser_wait --seconds 1` 再写值（多次连续追加 4–9 张卡片的实测均逐次命中新卡；不加 wait 是否同样可靠未验证）。
- 「工作经历」区块无「添加」按钮，只有一个「没有工作经历」复选框（应届生勾选）。

## 五、本系统字段清单（实测门户实例）

| 区块 | 字段（data-form-field-id） |
|---|---|
| 申请信息 | `code_type` 推荐方式(radio：无/内推/大使推荐)、`application_preferred_city_list` 意向城市(只读) |
| 简历 | `attachment_resume` 简历附件（`atsx-upload` 拖拽区 + 隐藏 file input，**必填**） |
| 基本信息 | `name` 姓名\*、`mobile` 手机号码(只读展示账号手机)、`email` 邮箱\*、`age` 年龄、`gender` 性别、获取校招信息渠道\*(数字串 id) |
| 教育经历 | `start_end_time` 起止时间\*、`degree` 学历\*、`school` 学校名称\*、学院、`field_of_study` 专业\*、实验室、领域方向、导师 |
| 实习经历 | `company` 公司名称、`title` 职位名称、`start_end_time` 起止时间、`desc` 描述(ta) |
| 工作经历 | 「没有工作经历」复选框 |
| 项目经历 | 项目名称、项目角色、起止时间、项目链接、描述(ta) |
| 竞赛 | 竞赛名称、获得名次/奖项、描述(ta) |
| 证书 | 证书名称（`ud__input`，**自由文本**，卡片内**无时间字段**）、描述(ta) |
| 语言能力 | 语言(sel：英语/法语/日语…)、精通程度(sel：入门/日常会话/商务会话/无障碍沟通/母语) |
| 自我评价 | 自我评价(ta) |
| 社交账号 | 社交平台(sel：微信…)、URL / ID(input) |

**证书/竞赛/作品三个模块为空时**：DOM 里只有「添加」按钮，没有 `.ud-formily-item`、`cards=0`——这与「模块被隐藏」不同，可直接判定为空。

**带「时间」的字段只有三处**：教育经历 / 实习经历 / 项目经历的 `start_end_time`（均为容器内两个原生 text input，写 `YYYY-MM`）。证书、竞赛、语言能力、社交账号**没有时间字段**——若使用者的口径要求奖励/活动类填获得时间，这些模块无法落地，不要为此额外拼字符串进名称栏。

选项实测：学历 = 博士/MBA/硕士/本科/大专/高中/专职/初中/小学；获取渠道 = 本单位公众号·小红书账号/本单位校园招聘官网/学校就业网·公众号/牛客网/宣讲会·双选会/班级群·院系群·社团群/老…（随租户页面而变，现场 dump 为准）

## 六、页面机制与风险

1. **该页无「保存」按钮，只有「提交简历」**；实测填写过程中**无任何保存类 XHR**（`performance.getEntriesByType('resource')` 仅见选项加载的 `/v1/list`，2026-09-15 复测 120 条资源中 save/draft/submit/update 类命中 0 条）。即已填数据只存在于页面状态，刷新/关闭可能丢失，**提交即投递**。
2. **隔夜复检发现部分内容归零（2026-09-15 实测）**：同一标签、同一 URL 再接入时，部分模块的卡片值**全部保留**，而另一些模块（含证书、竞赛等）与部分字段**全部为空**（全页 `innerHTML` 检索这些模块的已知文本均为空，排除隐藏渲染）。丢失范围与保存触发点均未定论，**已列【待验】**。
   → 作业含义：**不要假设写入会留存**。收尾回读必须**全模块清点**（不能只看本次改的那几处），并当场告知使用者「未提交前随时可能清零、请尽快提交或自行截图留档」。
3. 「提交简历」属投递动作，非使用者明确指示不得点击（本封装体手册 §2.1.5）。
4. 简历附件为必填项，本通道 **CLI 未暴露上传命令**，file input 能否被程序化赋值未验证；实际执行时先按 `browser_find_and_act --by css --value "input[type=file]"` 试探，失败则请使用者手动点「选择文件」。**已上传成功的判据**：`.atsx-upload` 内出现「<文件名> 上次上传: <时间> 更新」文本——此状态不受 `input[type=file].files` 为空影响，按文本判 OK，不要按 `files.length` 判空（会误报必填缺失）。

## 七、随包脚本清单与调用约定

`scripts/` 共 9 个文件：8 个**页面脚本**（在目标页内执行，不用通道 API）＋ 1 个**本机运行器**。

### 7.1 运行器 `run_cli.py`（本机执行，不是页面脚本）

解决什么：脚本内容直写命令行会被空格、反斜杠、引号破坏（§四「命令行三个坑」第 1、2 条）。本运行器把脚本挪进文件、统一 base64 后交给 `--script`。

```bash
python scripts/run_cli.py browser_eval_content_js --sessionId <id> --base64 --script @tpl=<脚本目录>/list_modules.js
python scripts/run_cli.py browser_eval_content_js --sessionId <id> --base64 --script @tpl=<脚本目录>/add_and_fill_card.js --set:sec="证书" --set:text="证书名称=<证书名> <等级或分数>"
```

| 写法 | 含义 |
|---|---|
| `--set:k=v` | 定义模板变量；**该 token 不传给通道 CLI**。`v` 含空格须整体加引号（写进命令清单文件时引号要写在文件里，清单按 `shlex` 切分） |
| `--set:k=<前缀>@file=<路径>` | 把该文件内容按 JS 单引号字符串转义（内含的真换行变 `\n`）后作为 `k` 的值——**多行描述走这条** |
| `@tpl=<路径>` | 读文件 → 把 `{{k}}` 替换成对应变量值 → base64 编码，作为该 token 的值 |
| `@b64=<路径>` | **与 `@tpl=` 行为完全相同**（一样替换 `{{k}}`、一样 base64）——名字只是可读性差别，不是「纯编码」 |
| `@cmdlist=<路径>` | 读命令清单（一行一条，`#` 开头为注释），`shlex` 切分后**顺序**执行 |

- CLI 路径：环境变量 `QQBROWSER_SKILL` ＞ PATH 里的 `qqbrowser-skill`；都没有则直接报错退出。
- 每条命令的 `>>> CMD`、`EXIT`、stdout／stderr 汇总写入 `%TEMP%\qqbrowser_cli_out.txt`——**结果读这个文件**，进程最后只打印 `done`。
- 路径一律用**正斜杠**。
- **占位符未替换即中止**：脚本里还剩 `{{k}}` 时直接报错退出、**不会把残稿发给通道**（提示缺哪个 `--set:`）。别指望浏览器侧报错——`const SEC='{{sec}}'` 是合法字符串，只会静默按字面量执行。

**随包形式**（与 §7.2 的页面脚本并列，便于核对清单与移交点数）：

| 文件 | 类别 | 取值方式 | 结果落点 |
|---|---|---|---|
| `run_cli.py` | 本机运行器（用 python 执行，不在页面内） | `--set:k=` 传值；脚本自身不含占位符 | `%TEMP%\qqbrowser_cli_out.txt`（进程只打印 `done`） |

### 7.2 页面脚本（8 个，经 `browser_eval_content_js` 执行）

| 脚本 | 作用 | 占位符 | 返回值 |
|---|---|---|---|
| `list_modules.js` | 列全部区块及各自的卡片数／复选框状态 | — | JSON 数组，元素形如 `区块名:cards=N chk=Y` |
| `read_module_cards.js` | 逐卡列出某区块的字段值（判空满用） | `{{sec}}` | JSON 数组，元素 `序号: 字段=值`，多字段以竖线连接 |
| `read_card_detail.js` | 单卡明细；`{{sec}}` 传 `-` 时只返回「卡片序号→区块」映射 | `{{sec}}` `{{idx}}` | JSON `{map, card}` |
| `check_required.js` | 扫全部必填项，列出仍为空者 | — | JSON 数组 |
| `open_select_in_module.js` | 展开某区块内某字段的 UD Select 下拉 | `{{sec}}` `{{field}}` | `DISPATCHED`／`NOTITLE`／`NF`／`NOSEL` |
| `pick_option.js` | 点选当前已展开的下拉选项 | `{{opt}}` | `CLICKED:<选项>`／`NOOPT:<可见项>`／`NODD` |
| `add_and_fill_card.js` | 区块内新增一张卡并填值 | `{{sec}}` `{{text}}` | `cards=N` ＋ 逐字段结果；失败 `NOTITLE`／`NOBTN`／`NOCARD` |
| `fill_module_card.js` | 填区块内第 N 张卡（不改卡片数） | `{{sec}}` `{{idx}}` `{{text}}` | JSON 数组（逐字段结果）；越界 `NOCARD n=…` |

**`{{text}}` 的格式**（`add_and_fill_card.js` 与 `fill_module_card.js` 共用）：

- 多条 `字段=值`，以 **`||` 分隔**（不是换行——换行会被命令行拆掉）；字段名须与该行 label 一致（脚本先抹掉空白与末尾星号再比对）。
- 起止时间单独写：字段名用 `起止时间`，值用 `YYYY-MM~~YYYY-MM`（**`~~` 分隔起止**），两个原生 input 依次写入。
- 逐字段结果的编码：命中则回写写入后的值（截前 24／26 字符）；`=NF` 表示该字段没找到、`=NOIN` 表示该字段内没有可写 input。
- `{{idx}}` 是**该区块内卡片的 0-based 序号**（脚本先按区块过滤再取下标）。

**通用约定**：全部脚本整体 `try/catch`，异常返回 `err:<message>`；**返回值就是判据**——不要另外用 axtree 判空满（§四「回读的正确方式」）。
