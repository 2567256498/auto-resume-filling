---
name: zhaopin-autofill
description: 智联校招（xiaoyuan.zhaopin.com/scrd/resume2 等）系统专属配方：区块切换取数入口、ApplyFormDate 日期组件、ApplyRemoteSelect 远程下拉与「手动添加」入口、SRegion 地区弹窗、附件上传位选择器、条目编辑器按钮文案与排序、平台预填值的核对要点。Use when 填写智联系网申表单（先读框架层配方 recipes/webform-autofill/SKILL.md 拿 element-ui 通用手法，本文件只写智联专属部分）。
---

# 智联校招 · 系统专属配方

定位：只写**智联独有**的实现细节。框架通用手法（setNative、el-select $emit、编辑器容器定位、日期按 label 上溯、弹层红线等）见 `webform-autofill`；字段取值与口径见使用者数据层。

> **通道 = QQ 浏览器**（命令映射见手册 §三）。本配方多数内容不依赖通道能力——它们是在页面内执行的脚本（原型 setter／组件直调／事件派发／DOM 查询），**可直接用**；唯一风险是目标页面是否这套框架，动手前先判框架。
> **未在本通道跑过的只有三种动作**：真实点击、语义定位与 snapshot 索引、iframe 穿透——凡依赖它们的步骤都按【未复现】对待，能兜底的已写兜底；跑通后就地改写该处结论（手册 §5.3 第 5 条）。

## 表单结构

- 网申表地址形如 `xiaoyuan.zhaopin.com/scrd/resume2?cid=&pid=&projectId=`。13 个区块：个人信息、家庭关系、教育经历、校园经历、实习/工作经历、奖励活动、技能/爱好、培训经历、附件、自我评价、亲属在本单位体系任职情况、亲属在同业体系（不含本单位）任职情况、本人承诺。
- 两类编辑器：**整区块编辑器**（个人信息、家庭关系、校园经历、奖励活动、技能/爱好、自我评价、亲属、本人承诺——一个「编辑」打开该区块全部字段）；**条目式**（教育经历、实习/工作经历——「添加」逐条，已保存条目是卡片各带「编辑」）。
- **区块切换**：取 `ul.apply-resume-menu` 的 `__vue__.resumeList[N]`（模块对象在菜单组件自身，不在 `$parent` 上），再调 `其.$parent.listChange(模块对象, N)`。合成点击无效。

## 日期组件 ApplyFormDate

- 字段 key：`birth`（出生日期）、`FIELD1003`（最高学历预计毕业时间）、`edu_date_start` / `edu_date_end`（教育经历）、`job_date_start` / `job_date_end`（实习经历）。
- 写法：沿 `.el-date-editor` 的 `__vue__.$parent` 找到 `ApplyFormDate`，`$emit('input','YYYY-MM-DD')` + `$emit('change',…)`，并回写 `model.value` 与 `model.model[model.key]`。
- 同一区块有多个日期控件时按 label 定位 form-item 再取其控件；按序号取会把值写到相邻字段（实测把入职时间写成了离职区间）。

## 远程下拉 ApplyRemoteSelect（学校 / 公司类）

- 调 `vm.remoteMethod(关键词)` 触发搜索，结果进 `vm.options`；按 label 精确匹配后 `$emit('input'/'change', 原始 value)`。
- 搜索有延迟：触发后至少等 1.5 秒再读 `options`；稳妥做法是拆成两次调用（一次触发、一次读取并选中）。
- **库内没有目标项时走组件自带入口**：调 `vm.emitFooterAction()`（footer 文案见 `vm.$props.footerActionText`，实测为「手动添加」）→ 弹出「手动添加」对话框 → 写入全称 → 点「确定」→ 对应 model 字段（如 `school_name`）落值。高中等中学在库里普遍没有，这是唯一通路。

## 地区选择 SRegion（籍贯 / 现居住城市 / 生源地）

- 三个独立实例，按 `vm.$parent.model.key` 区分：`nowlocated_city`（现居住城市）、`FIELD1000_city`（籍贯）、`hukou_city`（生源地）。
- 弹窗为 `.s-dialog`，**三个实例同结构同时存在于 DOM**：必须按所属实例定位它自己的弹窗；用 `querySelector('.s-dialog')` 会拿到隐藏实例，点了没反应。
- 路径：省份 → 市（城市项是 `li.s-checkbutton__item`，点中后该 li 带 `--selected`）。选中后输入框显示形如 `<省>-<市>`，并写 model 的 `FIELD1000_city_id` / `nowlocated_district_id` / `hukou_city_id`。
- 无「确定」按钮，点遮罩即关闭（关闭后值保留）。

## 附件上传位

- 证件照：`input[name="files"]`（图片 ≤4M）
- 生活照：`.FIELD1039_wrap input[type=file]`
- 简历附件：`.attach_path_wrap input[type=file]`（pdf/word/zip ≤4M）
- 三个上传位都支持「重新上传」，上传成功后以图片/文件名回显核对。

## 条目编辑器

- 新增态确认按钮是 `添 加`，编辑态是 `保 存`（同页可能并存，按文案区分后只点一次）。
- 教育经历与实习/工作经历**显示按时间倒序**，与添加先后无关（不要为排序倒推添加顺序）。

## 平台预填值必须逐项核对

- 登录后平台档案会带入部分数据，且**预填值可能是错的**：实测出生日期的「日」被写错（与证件不符）、离职时间偏移、职责为空等；这类字段必须逐项比对权威库。

## 选项值现状（仍须每次现场 dump）

- 同类字段 option value 不统一：亲属任职两处实测为 `3=是/4=否` 与 `4=是/5=否`；承诺条款为 `3=同意接受/4=不同意接受`；「其他语言证书」为 `10=GRE/11=GMAT/5=其他/8=无`。
- 因此本文件不提供可复制的"值→含义"对照表作为操作依据，只作现象记录；操作时一律按 label 现场匹配。
