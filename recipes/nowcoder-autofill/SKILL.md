---
name: nowcoder-autofill
description: 牛客网申助手（nowcoder.com，Vue2+ElementUI）系统专属配方：保存接口、表单模型结构、关键字段名、写入通道。Use when 填写牛客网申助手 / nowcoder 系网申表单（先读框架层配方 recipes/webform-autofill/SKILL.md 拿 element-ui 通用手法）。
---

# 牛客网申助手 · 系统专属配方

定位：只写牛客独有实现。框架通用手法（setNative、el-select 与日期组件注入、编辑器容器定位、弹层红线等）见 `webform-autofill`；字段取值与口径见使用者数据层。

> **通道 = QQ 浏览器**（命令映射见手册 §三）。本配方多数内容不依赖通道能力——它们是在页面内执行的脚本（原型 setter／组件直调／事件派发／DOM 查询），**可直接用**；唯一风险是目标页面是否这套框架，动手前先判框架。
> **未在本通道跑过的只有三种动作**：真实点击、语义定位与 snapshot 索引、iframe 穿透——凡依赖它们的步骤都按【未复现】对待，能兜底的已写兜底；跑通后就地改写该处结论（手册 §5.3 第 5 条）。

## 保存

- 底部全局保存按钮 → `POST /api/sparta/resume-fill-plugin/save`。

## 表单模型结构

`basicInfo` / `jobIntentionInfo{availableDate, expectedCities, expectedSalary}` / `educationList` / `workList` / `projectList` / `campusExperienceList` / `awardList` / `languageAbilityList` / `computerSkillList` / `certificateList` / `familyMemberList` / `paperList` / `patentList` / `selfEvaluation` / `hobbies` / `portfolioList` / `competitionList`

## 关键字段名

- 工作证明人：`referenceName` / `referenceTitle` / `referenceContact`
- 证书时间：`validTime`
- 竞赛：`competitionName` / `participationTime` / `details`
- 家庭成员：`familyMemberList{name, relation, phone, company, position, politicalStatus}`
- 城市级联的显示值在 `.city-cascader-value`

## 写入通道

- el-select：`$emit`（el-select 根组件）
- el-date-picker：`$emit('yyyy-MM-dd')`
- 兜底：直接写 `formModel`
