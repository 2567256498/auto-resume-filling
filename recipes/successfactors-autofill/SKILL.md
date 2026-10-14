---
name: successfactors-autofill
description: SAP SuccessFactors（career*.successfactors.eu）网申表单填写操作配方（系统层）：SFCascadingPicklist 点选、UI5 日期同步、注册+申请一体单页无暂存、附件组件与账号字段。Use when 填写 successfactors.eu 系招聘站点（汇丰控股 hsbcholdin 等）。
---


> **通道状态（ego）**：页面层手法（页面内脚本）跨通道通用；依赖通道动作的步骤（真实点击／语义定位与 snapshot 索引／iframe 穿透）按「未在本通道跑过的只有三种动作」处理，按手册 §4.3 重验后就地回写。
# SAP SuccessFactors 网申表单填写配方

适用：`career2.successfactors.eu/careers?company=hsbcholdin`（汇丰控股 graduate 申请页；2026-09-27 首见）。行为红线（不编造、带星必填、不擅自投递、回读核对、投递台账）以 `CODEBUDDY.md` §一／§三 为准，本文件只写操作层配方。

## 0. 框架识别

- URL：`career2.successfactors.eu`（亦见 career8 等编号子域），租户在 `company=` 参数。
- **服务端渲染 jQuery + SAP juic 组件**：控件内联 `onclick="juic.fire(...)"`；无 React fiber／Vue／Angular。`window.jQuery===true`。
- 下拉组件 **SFCascadingPicklist**：可见 combobox input `id=<N>:_input` ＋ 隐藏真值 `id=tor__fcust_<Field>_firstapp`（等，取自 `picklistConfig.valueFormElement`）；页面 script 内有 `picklistConfig = {fieldName, picklistId, parentPicklistId, valueFormElement, ...}`。
- 日期组件 **UI5 web component**：`ui5-date-picker-xweb-calendar-widget[data-testid=datePicker]`，`format-pattern="dd/MM/yyyy"`。
- 站点境外：浏览器侧须能解析并访问 `career2.successfactors.eu`（本机 2026-09-27 实测 DNS 被墙/无代理时 `ERR_NAME_NOT_RESOLVED`），动手前先确认可达。
- 文本字段无框架托管：原型 setter ＋ `input`/`change` 事件即可落值，**同一次 eval 内写入并立即回读**成立（与国家能源站同族，见 `webform-autofill/SKILL.md`）。

## 1. 字段命名与分组

- **账号注册字段前缀 `fbclc_`**：`userName`（邮箱）／`emailConf`（邮箱确认）／`pwd`／`pwdConf`（密码——凭据不代设，问用户）／`fName`／`lName`（Legal 名）／`country`（原生 `<select>`）／`searPref`（档案可见性 radio）／`emailEnabled`（通知 checkbox）。
- **申请字段前缀 `tor__fcust_`**：可见控件与隐藏真值成对（真值多带 `_firstapp` 后缀，如 `tor__fcust_Gender_firstapp`）；必填 hidden 带 class `appFieldRequired`——**必填空缺扫描判据：`input[type=hidden].appFieldRequired` 值为空即缺**。
- 问卷 radio `id=fbjq_question_<N>_<选项全文>`（选项全文在 id 里，含奇怪拼接，选择器按 id 精确取）。
- 附件组件：`93:_attach` 一类 attachWrapper，**无 `input[type=file]`**，点击弹系统文件选择框——本通道无上传命令，须用户手动上传（手册 §3.6）。

## 2. SFCascadingPicklist 点选手法

1. **展开**：`document.getElementById("<N>:_input").click()`（内联 onclick 触发 juic `_click`）；立即 focus。
2. **选项容器**：input 的 `aria-owns` 指向 `<N+1>:_listSelect`；选项为 `li`，点 `li` 内 `a/div/span`（本次实测 a 命中）。
3. **真值落位**：选中后组件写 `valueFormElement`（hidden）为**内部码值**（如 3749198），显示值写 `_input`。**判据：hidden 值非空才算成**（只看 `_input` 显示不够）。
4. **分页型**（电话区号、大学名等 100+ 项）：**键入过滤只在已载条目内生效**（首屏仅 100 条、按省块非严格字母序——大学名首屏无 Renmin，过滤 0 命中）。翻页：把**列表侧** globalMenu 容器（input 为 `M:_input`、列表 `(M+1):_listSelect` 时，滚动容器 id＝`(M+1):`——即**列表编号前缀**，不是输入框的 `M:`；overflow:auto）`scrollTop` 置底并派发 `scroll` 事件，触发 `fetch-page-in-order` 逐页加载（每页 100）。**目标 li 须在 globalMenu 全容器（`querySelectorAll("li")`，含 `(M+1):1`／`(M+1):2`… 各分页块）内搜**——`_listSelect` 只含首屏 100 条（r15 二次复现：只搜 `_listSelect` 空转 12 轮）。判据＝目标 li 在全容器出现。区号组件的 `.rcmpaginatedselectbutton` 不通用。
5. **联动依赖**：`cust_UniversityName` 的 `picklistConfig.parentPicklistId='ISOCountryList'`——先选 University Location 再选大学名。
6. 个别下拉展开偶发 `NO_LIST`（本轮 1/15 次）：单独重试一次（click → sleep 2s → 抓列表）即成。

## 3. UI5 日期（Graduation date）

- **同步 hidden 首选＝`_change` 伪事件（界面语言无关，不依赖可见 input）**：r15 英文界面实证——该页可见日期 input 无 Graduation 字样可定位（id/aria 均无），CustomEvent 无挂点；`dp._change(伪事件)` 直接落值。取全局实例调 `_change`：

```js
var dp = dateConfigMap['cust_GraduationDate'];
var params = {value:'2027-06-30', newValue:'2027-06-30', valid:true, statusCode:200, dateValue:new Date(2027,5,30)};
var ev = {getParameter:function(n){return params[n];}, getParameters:function(){return params;},
          getSource:function(){return dp;}, oSource:dp, target:dp};
dp._change(ev);  // hidden 落 YYYY-MM-DD；伪事件缺 getParameter 会报 a.getParameter is not a function
```
- 备选（须有可定位的可见 input 挂点）：`el.value="DD/MM/YYYY"`（按 `format-pattern`）＋ `CustomEvent("change",{bubbles:true,composed:true,detail:{value,valid:true}})`（标准 `Event("change")` 无效；中文界面此路 hidden 不落）。
- 判据：hidden（`tor__fcust_GraduationDate`）值非空（`2027-06-30` 形态）。

## 4. 页面结构风险

- **注册＋申请一体单页，无暂存／保存接口**：数据只存页面内存，**刷新或关闭即全丢**（2026-09-27 实际发生一次页面重载丢失、整轮重填）。填写期间严禁刷新／导航；`CODEBUDDY.md` §一.$1「保存后整页刷新回读」在此**不适用**，改用「整表 eval 回读 ＋ `appFieldRequired` 空缺扫描」作为核对判据。
- **界面语言影响**：中文界面下选项文案中文化（「是／否」「男性」「不適用」等），大学名词库仍为英文——点选匹配须同时兼容两种文案；切换语言不改变 hidden 码值。
- 提交按钮 **Apply**：非用户明确指示不点。
- Cookie Consent 弹窗（`cookiemanageriframe`）先处理再操作表单。
- `beforeunload` 本轮未出现；页面弹对话框时按 手册 §3.5 处理。

## 5. 字段清单与档位（hsbcholdin Graduate 56295 实测）

- 教育 8 项：Highest education level（Diploma／Post-university education／Pre-university education (16-18)／University education——**硕士→University education**）；University name（联想点选，库内「<学校全称>」→ <对应英文名>）；Degree type（Bachelor／Diploma／High School／Intermediate／Master／PhD）；Subject（自由文本，填 Accounting）；Area of study（42 项词表，Accounting 在列）；Graduation date（UI5 日期）；Grade/GPA（21 档：First/Upper Second/Lower Second/…/GPA 3.0–3.9 单档/GPA 4.0 or above/GPA below 3.0/To be notified——**<绩点>/4.0 → 就近档**）；最低学历未达标说明（Not Applicable）。
- 问卷 6 题（radio）：2027 年 7 月起全职／GPA≥3.0(5.0)／英语+普通话流利／中国大陆全程工作资格／应届<2 年／渠道。渠道映射：库内「招聘渠道 学校就业网」→ **University career center / job board**。
- 合规：Diversity and Inclusion Consent＝Yes；「Consent Form for Personal Information Processing」＝Yes（唯一选项）。
- 账号区 Country/Territory 为原生 select（China 在列）；电话区号 picklist 选 +86。
