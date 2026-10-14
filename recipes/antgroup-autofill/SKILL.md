---
name: antgroup-autofill
description: 蚂蚁集团校招（talent.antgroup.com，React+antdForm）系统专属配方：保存接口、表单分表结构、education 与大赛等级等关键字段、写入通道。Use when 填写 talent.antgroup.com 简历/网申表单（先加载框架层 skill antd-webform-autofill 拿 antd 通用手法）。
---


> **通道状态（ego）**：页面层手法（页面内脚本）跨通道通用；依赖通道动作的步骤（真实点击／语义定位与 snapshot 索引／iframe 穿透）按「未在本通道跑过的只有三种动作」处理，按手册 §4.3 重验后就地回写。
# 蚂蚁集团（talent.antgroup.com）· 系统专属配方

定位：只写蚂蚁独有实现。框架通用手法（React 原型 setter、antd Select 键盘路径、日期选择器路径、坐标点击兜底等）见 `antd-webform-autofill`；字段取值与口径见 `简历信息库/表单字段映射.json`。

## 保存

- `POST /api/campus/resume/save?ctoken=...`（fetch），成功后自动切展示态。

## 表单分表结构

- `basicInfo` 表：`countryAreaCode` / `name` / `mobile` / `email` / `familyCity` / `schoolCity`
- 简历表：`educations` / `experiences` / `projects` / `reward` / `competitionsExp` / `competitionLevelCodes` / `paperPublications`
- 其他表：`informationSource` / `otherInformation` / `proficientDevelopmentLanguages` / `personalHomepages`

## 关键字段

- `educations[]{gpaTotalScore(满分), gpaScore(个人), professionalRanking, isRecommended, hasNationalScholarship, tutor, laboratory, description}`（`professionalRanking` 实测按 `"50%"` 这类百分档字符串提交，取值口径见 `表单字段映射.json` 成绩排名规则）
- 大赛等级 code：`international` / `national` / `provincial_municipal` / `college` / `others`

## 写入通道

- antd Form 实例（fiber `props.form`）`.setFieldsValue` 直写；保存按钮真实点击。
