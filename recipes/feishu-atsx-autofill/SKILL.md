---
name: feishu-atsx-autofill
description: 飞书招聘 ATSx（飞书 hire / 字节招聘 SaaS 门户）简历表单自动填写。适用于 campus.duxiaoman.com 等使用飞书 ATSx 的校招投递页（React + Formily + UD 设计系统，类名前缀 ud__ / atsx-）。核心方法：data-form-field-id 精确定位、模块(title→right)反查卡片归属、UD Select 事件派发展开。
agent_created: true
---


> **通道状态（ego）**：页面层手法（页面内脚本）跨通道通用；依赖通道动作的步骤（真实点击／语义定位与 snapshot 索引／iframe 穿透）按「未在本通道跑过的只有三种动作」处理，按手册 §4.3 重验后就地回写。
# 飞书招聘 ATSx 简历表单填写

适用于使用**飞书招聘（ATSx / 飞书 hire）SaaS 校招门户**的投递与简历页，例如度小满 `campus.duxiaoman.com/<租户>/resume/<id>/apply`。

与字节自建招聘站（`jobs.bytedance.com`）同属 UD 设计系统，但**页面结构与交互细节不同**，勿直接套用——该站旧配方已于 2026-09-14 清理，其结论未经本通道复现。

## 一、识别判据（供 `CODEBUDDY.md` §五「表单操作配方与分层」使用）

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

统一通过 `ego_script`／`ego_js` 执行；脚本整体 try/catch。

### 命令行三个坑（2026-09-15 实测，都踩过）

1. **参数值含空格必须整体加引号**：命令清单按 `shlex` 解析，`--set:text=项目名称=某项目 一期 ` 会被拆成两个 token，后半个变成多余参数 → CLI 直接报错、**该次写入完全没发生**（不是写错值）。正确写法 `--set:text="项目名称=某项目 一期"`。凡是含空格的值（中英混合的奖项名、带分数的证书名）都要加引号。
2. **`@b64=` / `@tpl=` 的路径用正斜杠**：反斜杠被 shlex 当转义符吃掉，`<工作目录>/x.js` 变成 `D:workx.js` → `FileNotFoundError`。
3. **写入结果以脚本返回值为准**：`add_and_fill_card.js` 返回 `cards=N`、`fill_module_card.js` 返回 `字段=值 `；批量添加时看 `cards=` 是否逐次 +1，能立刻发现漏写（曾出现多条证书中有若干条因空格被静默跳过，就是靠这个发现的）。

### 回读的正确方式（别用 axtree 判断空满）

`ego_snapshot` 返回的 axtree **只覆盖视口内元素**：视口外的模块（如多张已填卡片）不出现，容易被误判成「模块是空的」。判断空满用 `read_module_cards.js`（逐卡列字段值）或全量扫描脚本（遍历 `document`），不要用 axtree。

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

- **展开**：向 `.ud__select__selector` 派发 `mousedown → mouseup → click`（`new MouseEvent(t,{bubbles:true,cancelable:true,view:window})`）即可展开，**本通道不需要真实鼠标点击**（与已清退的字节站旧配方所记结论不同，以本条实测为准）。
- **读选项**：展开后选项渲染在 `.ud__select__dropdown`（body 级 portal），选项元素类名含 `list__item`。
- **选中**：对目标选项 `el.click()`。
- **回读**：读该字段 `.ud__select` 的 `textContent`（`input.value` 恒空）。
- 选项是异步按 `data-form-field-id` 取回的；同一个 `.ud__select__dropdown` 里只会出现当前展开字段的选项，跨字段匹配文本时取最后一个匹配项即可。

### 起止时间（`start_end_time`）

容器内两个**原生 text input**（开始 / 结束），直接写入 `YYYY-MM`（精度到月）即可，无需 Enter 确认。

### 增删条目卡片

- 追加：在目标模块内找文本为「添加」的按钮 `el.click()`；React 同步 flush，**同一次 eval 内即可查询到新卡片**（取 `cards[cards.length-1]`）。
- 连续追加多张卡片时，在每次 add 之后加一条 脚本内 `await` 延时 1 秒 再写值（本轮证书 4 连加 + 项目 1 张共 5 次，回读全部命中新卡；不加 wait 是否同样可靠未验证）。
- 「工作经历」区块无「添加」按钮，只有一个「没有工作经历」复选框（应届生勾选）。

## 五、本系统字段清单（度小满投递页实例）

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

**带「时间」的字段只有三处**：教育经历 / 实习经历 / 项目经历的 `start_end_time`（均为容器内两个原生 text input，写 `YYYY-MM`）。证书、竞赛、语言能力、社交账号**没有时间字段**——若用户的口径要求奖励/活动类填获得时间，这些模块无法落地，不要为此额外拼字符串进名称栏。

选项实测：学历 = 博士/MBA/硕士/本科/大专/高中/专职/初中/小学；获取渠道 = 本单位公众号·小红书账号/本单位校园招聘官网/学校就业网·公众号/牛客网/宣讲会·双选会/班级群·院系群·社团群/老…（随租户页面而变，现场 dump 为准）

## 六、页面机制与风险

1. **该页无「保存」按钮，只有「提交简历」**；实测填写过程中**无任何保存类 XHR**（`performance.getEntriesByType('resource')` 仅见选项加载的 `/v1/list`，2026-09-15 复测 120 条资源中 save/draft/submit/update 类命中 0 条）。即已填数据只存在于页面状态，刷新/关闭可能丢失，**提交即投递**。
2. **隔夜复检发现部分内容归零（2026-09-15 实测）**：同一标签、同一 URL 再接入时，部分模块的卡片值**全部保留**，而另一些模块（含证书、竞赛等）与部分字段**全部为空**（全页 `innerHTML` 检索这些模块的已知文本均为空，排除隐藏渲染）。丢失范围与保存触发点均未定论，**已列【待验】**。
   → 作业含义：**不要假设写入会留存**。收尾回读必须**全模块清点**（不能只看本次改的那几处），并当场告知用户「未提交前随时可能清零、请尽快提交或自行截图留档」。
3. 「提交简历」属投递动作，非用户明确指示不得点击（`CODEBUDDY.md` §一.$1）。
4. 简历附件为必填项，本通道 **CLI 未暴露上传命令**，file input 能否被程序化赋值未验证；实际执行时先按 CSS 定位（`ego_click` + `page.locator()`）试探，失败则请用户手动点「选择文件」。**已上传成功的判据**：`.atsx-upload` 内出现「<文件名> 上次上传: <时间> 更新」文本——此状态不受 `input[type=file].files` 为空影响，按文本判 OK，不要按 `files.length` 判空（会误报必填缺失）。


## 七、随包脚本（scripts/，经 run_ego.py 驱动）

`run_ego.py`＝本配方的 ego 通道运行器（接口：`python scripts/run_ego.py <JS 参数>` 或 `@cmdlist=<命令清单文件>`；CLI 探测链＝环境变量 `EGO_BROWSER` → 包内 `runtime/ego-browser.cmd` → PATH）。页面脚本都是纯页面内 IIFE，经 `page.evaluate()` 执行，占位符 `{{...}}` 由运行器替换：

| 脚本 | 占位符 | 用途 |
|---|---|---|
| `list_modules.js` | — | 列出全部模块标题与卡片数 |
| `check_required.js` | — | 扫必填项缺口 |
| `read_module_cards.js` | `{{sec}}` | 读指定模块全部卡片摘要 |
| `read_card_detail.js` | `{{sec}}`、`{{idx}}` | 读指定卡片全部字段 |
| `add_and_fill_card.js` | `{{sec}}`、`{{text}}` | 加卡片并填文本 |
| `fill_module_card.js` | `{{sec}}`、`{{idx}}`、`{{text}}` | 填指定卡片 |
| `open_select_in_module.js` | `{{sec}}`、`{{field}}` | 展开指定下拉 |
| `pick_option.js` | `{{opt}}` | 点选下拉选项 |
| `run_ego.py` | — | 本机运行器（非页面脚本） |
