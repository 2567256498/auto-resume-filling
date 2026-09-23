---
name: chnenergy-autofill
description: 国家能源集团招聘系统（zhaopin.chnenergy.com.cn）在线简历填写配方：区块独立 URL 导航、各区块表单 ID 与保存函数、原生 select 与 zTree 词典弹窗手法、education order 强制格式、电子附件仅收图片。Use when 填写国家能源集团网申简历（先读框架层配方拿通用手法，本文件只写本系统专属部分）。
---

# 国家能源集团招聘系统填写配方（系统层）

> 适用：`zhaopin.chnenergy.com.cn` 在线简历（`/resume/editResume?type=1`）。
> 来源：某能源央企校招（服务端渲染 Bootstrap＋jQuery 站）在线简历各区块填写的系统层复现。
> **本通道已复现的动作**：页面内 JS（原型 setter 直写、原生 `select` 赋值、zTree 词典弹窗操作）、`browser_go_to_url` 真导航重载、整页回读**均已在本系统跑通**；**未在本通道跑过的只有三种动作**——真实点击、语义定位与 snapshot 索引、iframe 穿透，凡依赖它们的步骤都按【未复现】对待，能兜底的已写兜底；跑通后就地改写该处结论（手册 §5.3 第 5 条）。
> 字段取值与口径归使用者的数据层（字段映射文件），本配方只写操作手法。

## 0 页面态与入口

- 入口总览：`/resume/editResume?type=1`（**注意**：此页实际渲染的是**完整表单各区块纵向堆叠**，不是区块卡片列表）。
- **区块不是同页 Tab，而是各自独立的 URL 页面**，由左侧 `.menuList` 导航切换。动手前必须按目标区块导航到对应 URL，不要指望在总览页上直接写。

| 区块 | 列表页 | 新增/编辑页 |
|---|---|---|
| 个人信息 | `/resume/editBase` | 同左 |
| 教育经历 | `/resume/eduList` | `/resume/editEdu` |
| 资格证书 | `/resume/qualiList` | `/resume/editQuali?category=school` |
| 工作经历 | `/resume/workList` | `/resume/editWork` |
| 家庭成员 | `/resume/familyList` | `/resume/editFamily` |
| 取得成果 | `/resume/eidtAchiev` | 同左 |
| 奖惩情况 | `/resume/eidtReward` | 同左 |
| 爱好特长 | `/resume/eidtHobby` | 同左 |
| 自我评价 | `/resume/eidtSelfEvaluate` | 同左 |
| 电子附件 | `/resume/certList` | 同左 |
| 首选考试城市 | `/resume/editFacePlace` | 同左 |

> 站方把 `edit` 拼成了 `eidt`（取得成果/奖惩/爱好/自我评价四处），照抄不要改。

## 1 技术栈与识别判据

- 服务端渲染 Bootstrap 风格，`jQuery` 在、`window.Vue === false`、无 React fiber。
- 表单不靠前端框架托管：**元素都已渲染在 DOM 里，直接设值 + 派发事件即可落库**（无需 fiber 上溯）。
- 全站表单字段**大多数没有 id**（`name` 更可靠），时间类字段 `id` 与 `name` 不一致（`id="sdate"` ↔ `name="startTime"`）——定位一律走 `name`。

## 2 写入手法

### 2.1 文本 / 文本域（`input`、`textarea`）

```js
function setV(idOrSel, val){
  var e = document.querySelector(idOrSel);
  var d = Object.getOwnPropertyDescriptor(e.__proto__, 'value');
  d.set.call(e, val);
  e.dispatchEvent(new Event('input',  {bubbles:true}));
  e.dispatchEvent(new Event('change', {bubbles:true}));
}
```

- 本系统无框架重渲染，写入后**同一次 eval 内即可回读**（与 React 受控组件配方的「写入与回读分两次调用」口径不同）。
- 长文本字段上限见元素 `maxlength`：取得成果／奖惩／爱好特长／自我评价均为 **2000**。

### 2.2 原生 `<select>`

```js
var s = document.querySelector('#familyForm select[name="relationship"]');
s.value = '51';                                    // 值取 option 的 value
s.dispatchEvent(new Event('change', {bubbles:true}));
```

### 2.3 省市联动

- 省级 select 带 `onchange="getCity('x')"`。设值后除派发 change 外，**还需显式调一次 `s.onchange()`** 才会加载下级选项；两级结构（省 → 市/区）。
- 控件名：籍贯 `nativPlace1`/`nativPlace2`；户口 `registPlace1`/`registPlace2`；生源 `studHometown1`/`studHometown2`，填直辖市时两级取同一个省级编码。

### 2.4 院校 / 专业：zTree 词典弹窗

- `choose('shool')` / `choose('major')` 打开 `#dictionformModal`；`#typeId` 是 **name 属性**（值 `shool`/`major`），不是 id。
- 流程：`#Kind` 过滤框输关键字 → `AutoMatchkind(k)` 检索 → `#treeKind` 里 zTree。
- **点父节点会弹 alert「只能选择子节点」**，弹窗阻塞后续 eval；要展开父节点就点 `span.switch`，选中只能点叶子 `a`。
- 选中后写进隐藏字段 `#kindName`（显示名）与 `#kingNode`（编码），再调 `subDicForm()` 提交回填。
- 实测：选中专业叶子后，该叶子的编码写进 `#kingNode`，提交回填 `extfield1=专业名`、`major=专业编码`；院校同理回填 `school=校编码`。**编码由站点词典随选项给出，按实际选中项读取，不要手填**（`school` 值长度 ≤5 会被拒，正是把编码误当校名填了的症状）。

## 3 各区块表单与保存函数

| 区块 | form id | 保存调用 | 备注 |
|---|---|---|---|
| 个人信息 | `#baseFrom` | `subForm()` | 校验极轻：手机号 11 位正则、备注 ≤2000、政治面貌为「中共党员」时才必填入党时间 |
| 教育经历 | `#eduFrom` | `saveEdu()` | 校验最硬，见 §4 |
| 资格证书 | `#qualiFrom` | `save()` | 5 字段全带星 |
| 工作经历 | `#workForm` | `save()` | 只校验 `jobContents` ≤2000 |
| 家庭成员 | `#familyForm` | `save()` | 6 字段全带星 |
| 取得成果 / 奖惩 / 爱好 / 自我评价 / 考试城市 | — | 按钮 `onclick="save();return false;"`（爱好为 `savehobby();`） | 单文本域或单组控件 |

> 新增入口统一是 `新增` 按钮，`onclick="addForm()"`（资格证书为 `addForm('school')`）；**点击后是页面跳转**，不是弹出层。

### 3.1 字段清单

- **个人信息**（`#baseFrom`）：`fullName` `sex` `birthday` `joinPartyTim` `nation` `politics` `nativPlace1/2` `marriage` `registPlace1/2` `studHometown1/2` `identType` `identNum` `foreigLang1` `foreigLang1Levl` `mobile` `email` `emergContact` `emergPhone` `health` `height` `weight` `isCaredCounty` `isRelativeAvoidance` `isEmployedIn2`；取值为空且合理的：`joinPartyTim`（非党员）、`foreigLang2/foreigLang2Levl`（无二外）、`otherSupplement`。
- **工作经历**（`#workForm`）：`jobNature`（实习）、`unit`、`position`、`startTime`/`endTime`、`jobContents`（≤2000）。
- **家庭成员**（`#familyForm`）：`fullName`(≤30) `birthday` `relationship`(select) `unit`(≤100) `position`(≤20) `isShStaff`(select，`X`=是／空=否)。
  - 本人视角关系下拉取值：父亲=`51`、母亲=`52`（其余 11 夫 / 12 妻 / 21 儿子 / 31 女儿 / 61 祖父 / 62 祖母 / 98 监护人 / 99 其他）。
- **资格证书**（`#qualiFrom`）：`name`(≤100) `lvl`(≤12) `getTime` `unit`(≤100) `field1`(≤100，即文号)。全部是自由文本，无下拉。
- **奖惩情况**：`reward`（textarea ≤2000）。
- **取得成果**：`profesAchiev`（textarea ≤2000）。
- **爱好特长**：`hobby`、`specialty`（**是 `specialty` 不是 `speciality`**，写错返回 MISSING）。

## 4 教育经历：`saveEdu()` 的硬校验

- `order`（班级或年级综合排名）**必填**，格式**必须为半角「数字/数字」**（前后均为整数，前 ≤ 后），否则保存被拦、表单不落库。
- `school` 值长度 ≤ 5 会被拒（说明把编码误当校名填了）。
- 全日制学习形式下按学历档位校验起止时间跨度。
- 字段：`sdate`(name=`startTime`) / `edate`(name=`endTime`) / `schoolName` / `school`(编码) / `extfield1`(专业名) / `major`(编码) / `learningForm` / `education` / `degree` / `oversea` / `order`。
- 档位实测：`learningForm=1`(全日制)、`education=23`(全日制硕士研究生及以上学历，本科用「大学本科」档)、`degree=367`(专业学位档之一；本科用**对应学士学位门类档**)、`oversea=0`(否)。
- 教育层级支持到**高级中学**（档位「高级中学」），本系统高中层级可填。

## 5 电子附件

- 区块路径 `/resume/certList`，11 个文件槽，表单控件是 **原生 `<input type="file" name="uploadCertImg">`**（无 id、无 accept）。
- **只收 2M 以内 JPG/JPEG/PNG/GIF 图片**——PDF 不被接受。带星必填：**证件、学生证（或其他学生身份证明）、成绩单**；就业推荐表／毕业证／学位证／学籍在线验证报告／留学认证／资质证书／户口／其他为选填。
- 本通道 CLI **无上传命令**，且浏览器禁止脚本给 `input[type=file]` 赋值 → **必须请使用者手动上传**，填写时留空并明确告知。

## 6 状态图标判据（判「这个区块填全了没有」）

左侧 `.menuList` 每个 `a` 的类名即区块状态，图例四档：

| 类名 | 状态 |
|---|---|
| `resumeIcon1 fill_in` | 已填写 |
| `resumeIcon2 incomplete` | 不完整 |
| `resumeIcon3 not_fill_in` | 未填写 |
| `resumeIcon4 optional` | 选填项 |

> 取类名时注意：`resumeIcon1` 是 `resumeIcon` 的子串匹配陷阱的**反面**——四档类名互不包含，直接精确匹配即可。

## 7 保存与回读判据

- 整页刷新后数据仍在才算保存成功（见包内手册 §4.4 回读判据）。列表页刷新后逐行核对条目数与内容。
- 单条目操作一气呵成，保存按钮只点一次。
- 个人信息页即便「不完整」也可能只是非党员无入党时间所致，逐字段核对后再判断，不要凭图标下结论。

## 8 未复现与兜底

| 动作 | 状态 | 兜底 |
|---|---|---|
| 文件上传（电子附件） | 【不可用】CLI 未暴露上传命令、浏览器禁止脚本赋值 file input | 请使用者手动上传 |
| 时间控件日历面板点选 | 【无需】时间字段为自由文本 input，直接写 `YYYY-MM-DD` | — |
| 教育经历 `order` 无数据时的绕行 | 【无】属必填且需真实数字 | 问使用者要「排名/总人数」，不得编造 |

## 9 落点与本轮遗留

- 本配方首见时的观察已在发现方的经验台账登记待验，达门槛后再上提进本文件正文。
- 待补：工作经历 `#workForm` 的完整字段名清单（首次记录时只确认 `jobNature`/`unit`/`position`/`startTime`/`endTime`/`jobContents`）。
