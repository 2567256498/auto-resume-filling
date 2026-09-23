---
name: 51job-autofill
description: 前程无忧／应届生校招（xyz.51job.com FillInResume.aspx，ASP.NET WebForms）系统层配方：单页向导回发机制、区块容器定位、图片按钮需页面内 JS 点击、左侧状态图标即落库判据、iframe 附件上传（未复现，处置见手册 §3.4）、半角长度单位校验与保存失败排查。Use when 填写 51job / 前程无忧 / 应届生校招系网申表单。
---

# 前程无忧 / 应届生校招简历录入（51job）系统层配方

> 适用：`xyz.51job.com/External/MyResume/FillInResume.aspx`（前程无忧校招、应届生求职网 `prd=campus.yingjiesheng.com`，ASP.NET WebForms）。
> 框架层无对应 skill（非 antd / 非 element-ui）；本文件只写该系统专属实现。字段取值与口径在使用者数据层。
> 证据与复核记录：使用者经验台账（配置项 6）。
> **通道 = QQ 浏览器**（命令映射见手册 §三）。本配方多数内容不依赖通道能力——它们是在页面内执行的脚本（原型 setter／组件直调／事件派发／DOM 查询），**可直接用**；唯一风险是目标页面是否这套框架，动手前先判框架。
> **未在本通道跑过的只有三种动作**：真实点击、语义定位与 snapshot 索引、iframe 穿透——凡依赖它们的步骤都按【未复现】对待，能兜底的已写兜底；跑通后就地改写该处结论（手册 §5.3 第 5 条）。　**本配方尤其留意**：附件上传一节（本通道写不了 file 控件，该节已给定论）。

## 0 页面态与导航

- 单页向导：`#container` 内只渲染 H1（区块名）+ `div.ci`（该区块内容），区块用回发切换，不做前端隐藏。
- 区块顺序：上传并解析附件简历 ｜ 基本信息 ｜ 教育经历 ｜ 语言能力 ｜ IT技能 ｜ 全职工作经历 ｜ 实习经历 ｜ 在校实践经验 ｜ 家庭关系 ｜ 其他。
- 左侧 LI 状态图标即落库判据：`cv2.gif`＝已填写完整、`cv1.gif`＝未填写完整、`cv0.gif`＝未填写（与"符号说明"图例一致）。
- 底部按钮：`imgbtnPrevious`、`imgbtnSave`、`imgbtnNext`；最后一页的"下一步"变成 `imgbtnSubmit`（提交/投递，禁点，除使用者明确指示）。
- **按钮一律用页面内 JS `el.click()` 触发**：`imgbtnPrevious`/`imgbtnSave` 是图片提交按钮（onclick 都是 `saveCheck()`），真实鼠标点击点它可能静默无回发（另一通道实测，本通道未复现）；保存与上一步各点一次，不要连点。

## 1 定位与读取

- 当前区块 = `#container h1` 文本；字段行 = `div.ci > dl`（标签 `dt` + 控件 `dd`）；必填 = `dt span.must`。
- **同名字段 id 在各区块重复**（如 `cc_CCF1_6_1` 同时出现在语言能力与其他区块）→ 只按当前区块内定位，不跨区块复用 id。
- 多条目区块（实习经历、在校实践经验、家庭关系、IT技能等）：一个 `div.ci` 就是一条记录；`DIV.tb` 内 `btnAppend`（`AppendControls`）新增、`btnDelete`（`DeleteControls`）删除整条。
- **新增/删除按钮认 class/id，不认文本**：`input.btnAppend` / `input.btnDelete` 的 `value` 为空，只有 `title="添加"`/`"删除"`——按可见文本或 value 扫描会漏判（本轮曾据此误判「IT技能只有一个技能槽」，实际可多条）。
- 条目内控件 id 形如 `cc_CCC1_3_4`（列名＋coltype＋序号），序号段前面还有 coltype 段 → 条目内定位用 `[id^="cc_CCC1_"]` 前缀匹配，别拼 `cc_CCC1_4`。

## 2 写入通道

- 普通 `input` / `select`：直接设 `value` / `selectedIndex` 并派发 `input`+`change`，服务端回发时按表单值读取，无需模拟键盘。
- 联想控件（`editstyle=18`，如毕业学校、专业）：`display:none` 的 `select`（真正提交）+ `span.custom-combobox > input.custom-combobox-input`（无 name，仅显示）。写入须**同时**设置 select 选中项与相邻 input 的文本。
- 级联 select：`onchange="DDL_OnChange(...)"` / `DDL_OnChange1(dict, value, 隐藏id)`；选一级后二级选项由 JS 生成，须触发一级 change 后**回读二级选项**再选（如英语水平→分数档、技能分类→具体技能、省→市）。
- 复选组（`editstyle=8`，如获得证书、招聘信息来源渠道）：checkbox 无 name/id，其后 `<span>` 是显示文本；真正提交的是隐藏 input（值以 `|` 连接）。勾选后须把所选文案写入隐藏 input，保存回发后服务端以 `|` 重渲染，可据此确认已落库。
- 日期 input：`readonly` + `onfocus="setday(this)"`（My97DatePicker），直接赋值 `YYYY-MM-DD` 即可，不会被解析改写，也不要点选。
- 长度上限读 `inputlen` / `maxlength` 属性（短栏位常见 50，长文本 textarea 为 4000）。**上限按"半角单位"计**：`ValidateLength` 用自定义 `length2()`（`this.replace(/[^\x00-\xff]/ig,"aa").length`），**一个汉字算 2**，所以 `inputlen=50` ≈ 25 个汉字；超限时页面上出现红色「XXX超出长度限制!」。各模板同名栏位上限可能不同，务必现读现算。

## 3 新增条目

- `AppendControls` 克隆 `sender.parentNode.parentNode`（即 `div.ci`）并追加到 `#container` 末尾，克隆体清空文本/复选/下拉，id 序号按最后一条的 `ResumeSubID` 递增重编号。
- 因此：新条目永远排在最后（DOM 顺序 = 提交顺序）；若平台/口径要求"最新在前"，须把最旧的一条放在首条位置填写，其余按时间倒序 append。
- `btnDelete` → `DeleteControls` 内有原生 `confirm("请确认删除")`：用 JS 删除时先临时 `window.confirm = () => true`，点完再还原（若直接点，confirm 会挂住页面内脚本执行直到超时）。（单次观察，未见第二次复现。）
- 新投递的简历会带过账号快照：公司、日期、长文本、照片等通常已预填，但**部门/岗位一类分列栏位常为空**，跨区块逐条回读时按 label 补齐。
- 新增后**必须逐条回读整个区块**（已有"新增条目清空既有条目"的数据丢失先例）；重复 id 出现后 `getElementById` 只取第一个。

## 4 附件与照片

- 上传位是 iframe：`/CommPage/Pages/UpLoad.aspx?fid=..&lang=..&cid=cc_XXX_n_n`，内含 `input[type=file]#txtUpLoad` + `input[type=submit]#btnUpload`（`onclick=return CheckAttachment()`）。
- **上传：本通道做不到**——file input 无法由脚本写值（任何手段写 `value`／`files` 均无效，`fill` 后 `value` 空、`files.length=0`；浏览器安全模型，见手册 §3.4「上传处置」）。上条的 iframe 结构保留作**页面结构知识**（认清上传位、读懂 `src` 里的 `attach=` 参数）；**实际附件一律请使用者在浏览器里手动上传**，不在页面内试探写 file、也不去点 `#btnUpload`。
- 手动上传完成后，父页隐藏字段会写入服务器路径（如 `cc_CCE8_5_1 = //xyz.51job.com/Static/.../xxx.PDF`），点保存才落库——**这条是回读判据**：字段有路径＝服务端已存，可据此确认使用者传成功了。
- 顶部"上传并解析附件简历"是解析器：按本封装体手册 §2.1.6 只当脚手架，未经使用者明确要求不使用。

## 5 保存、校验与覆盖清点

- 保存：`imgbtnSave`（`onclick=saveCheck()` → `ValidateAll` → 回发）。客户端校验失败时**不回发**（点击后没有任何网络请求、左侧图标不变、值看起来"填好了"），页面上出现红色提示；排查方式是直接在页面里调 `ValidateAll('','CN')`（返回布尔）并扫红色 `label` 文本，而不是反复点保存。
- 落库判据：回发后同区块重读仍为原值；跨区块来回切换（上一步/下一步）后重读，可验证服务端数据而非回显。左侧状态图标可交叉验证；附件类栏位可看上传 iframe 的 `src` 是否带回 `attach=<路径>`（带回＝服务端已存）。
- 「其他」区块的完整度图标需**上传简历附件**后才会变 `cv2`；反过来，图标停在 `cv0` 也可能是**保存被客户端校验拦住**（不是"平台认为没填"）——先跑 `ValidateAll` 再下结论。
- 教育经历按"最高学历组＋本科组＋硕士组＋博士组＋其他学历组"罗列，只有最高学历组与前一学历组带必填星号；其余为可选空行，按本封装体手册 §2.2 通用原则（只填条目明确要求的内容）不填重复信息。
- 本系统无自我评价、兴趣爱好、籍贯、高中层级、主修课程等栏位：库内对应内容无落位处时记入报告，不硬塞进相近栏位。
- **回读要剔除"来源残留行"**：本系统实习/实践区块没有"地点"字段，从简历文本块整段粘贴或解析导入时，简历里紧跟"岗位/部门"的那一行地点（如「北京」「成都」）会落进内容框首行，与正文无标点连接——回读时按内容结构判定并删掉，不作为内容保留。
