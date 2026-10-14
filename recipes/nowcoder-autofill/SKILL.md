---
name: nowcoder-autofill
description: 牛客网申助手（nowcoder.com，Vue2+ElementUI）系统专属配方：保存接口、表单模型结构、关键字段名、写入通道。Use when 填写牛客网申助手 / nowcoder 系网申表单（先加载框架层 skill webform-autofill 拿 element-ui 通用手法）。
---


> **通道状态（ego）**：页面层手法（页面内脚本）跨通道通用；依赖通道动作的步骤（真实点击／语义定位与 snapshot 索引／iframe 穿透）按「未在本通道跑过的只有三种动作」处理，按手册 §4.3 重验后就地回写。
# 牛客网申助手 · 系统专属配方

定位：只写牛客独有实现。框架通用手法（setNative、el-select 与日期组件注入、编辑器容器定位、弹层红线等）见 `webform-autofill`；字段取值与口径见 `简历信息库/表单字段映射.json`。

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
