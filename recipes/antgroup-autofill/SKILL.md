---
name: antgroup-autofill
description: antd 系校招门户（talent.antgroup.com，React + antd Form）系统专属配方：保存接口、表单分表结构、education 与大赛等级等关键字段、写入通道。Use when 填写 talent.antgroup.com 简历/网申表单（先读框架层配方 recipes/antd-webform-autofill/SKILL.md 拿 antd 通用手法）。
---

# talent.antgroup.com · 系统专属配方

定位：只写该门户独有实现。框架通用手法（React 原型 setter、antd Select 键盘路径、日期选择器路径、坐标点击兜底等）见 `antd-webform-autofill`；字段取值与口径见使用者数据层。

> **通道 = QQ 浏览器**（命令映射见手册 §三）。本配方多数内容不依赖通道能力——它们是在页面内执行的脚本（原型 setter／组件直调／事件派发／DOM 查询），**可直接用**；唯一风险是目标页面是否这套框架，动手前先判框架。
> **未在本通道跑过的只有三种动作**：真实点击、语义定位与 snapshot 索引、iframe 穿透——凡依赖它们的步骤都按【未复现】对待，能兜底的已写兜底；跑通后就地改写该处结论（手册 §5.3 第 5 条）。

## 保存

- `POST /api/campus/resume/save?ctoken=...`（fetch），成功后自动切展示态。

## 表单分表结构

- `basicInfo` 表：`countryAreaCode` / `name` / `mobile` / `email` / `familyCity` / `schoolCity`
- 简历表：`educations` / `experiences` / `projects` / `reward` / `competitionsExp` / `competitionLevelCodes` / `paperPublications`
- 其他表：`informationSource` / `otherInformation` / `proficientDevelopmentLanguages` / `personalHomepages`

## 关键字段

- `educations[]{gpaTotalScore(满分), gpaScore(个人), professionalRanking, isRecommended, hasNationalScholarship, tutor, laboratory, description}`（`professionalRanking` 实测按 `"50%"` 这类百分档字符串提交，取值口径见数据层的成绩排名规则）
- 大赛等级 code：`international` / `national` / `provincial_municipal` / `college` / `others`

## 写入通道

- antd Form 实例（fiber `props.form`）`.setFieldsValue` 直写；保存按钮真实点击。
