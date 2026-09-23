---
name: wecruit-autofill
description: 北森 Wecruit（wecruit.hotjob.cn）在线简历填写配方：编辑态与预览态判据、保存接口与报文改写（含页内直发）、区块 set 键随站点模板变化、字段 ID 表与逐区块定位。Use when 填写 Wecruit 系在线简历（先读框架层配方拿通用手法，本文件只写 Wecruit 专属部分）。
---

# 北森 Wecruit 在线简历填写配方（系统层）

> 适用：北森 Wecruit 平台 `wecruit.hotjob.cn` 系（`resumeOperation.html` 在线简历编辑页）。前端 **React16 ＋ antd3**，与北森 zhiye 系（`phoenix-*` 自研组件）**不是同一套东西**，两套配方不可互换——动手前先按识别判据判归属。
> 来源：两个不同站点上 Wecruit 在线简历全量完成的系统层复现——先在站点一完成全量填写与工作经历重排，后在站点二复现，并补入「页内直发保存」「区块 set 键随站点模板变化」两条。
> **本通道已复现的动作**：页面内 JS（fiber 直读、组件实例直调、XHR 报文改写与直发）、`browser_go_to_url` 真重载**均已在本系统跑通**；**未在本通道跑过的**是真实点击、语义定位与 snapshot 索引、iframe 穿透三种动作——凡依赖它们的步骤都按【未复现】对待，能兜底的已写兜底；跑通后就地改写该处结论（手册 §5.3 第 5 条）。
> 字段取值与口径见**使用者数据层**（手册 §1.1 配置项 4）中本系统的条目。

## 0 页面态与入口

- 编辑页 URL：`resumeOperation.html?resumeId=<id>`；账号中心列表页：`account.html#/resume`、`account.html#/myDeliver`。
- **本页有「编辑态」与「预览态」两副面孔，且共用同一批 DOM**——这是本平台最容易踩的坑（见 §1）。

## 1 编辑态／预览态判据（首要判据）

- 容器 `.resume-content-wrap` 的 computed `display`：
  - `flex` ＝ **编辑态**（表单可写）
  - `none` ＝ **预览态**（表单被隐藏，DOM 仍在、但已重置）
- **点「保存」后页面自动跳回预览态**。此时所有字段写入（无论 DOM 直写还是 fiber 直调）都作用在**被隐藏且已重置的表单**上——回读可能仍有值，但从未进模型。（站点二复证：点「保存」后 `.ant-form-item` 数归零。）
- 表层症状：`browser_snapshot` 看不到填写项、`input.value` 读得到但保存后归零、表单项数量比预期少。
- 处置：每次操作前先判 display；发现是 `none` 就先回到编辑态（点页面自带的「编辑」入口），**不要在预览态下做任何写入**。

## 2 区块与字段定位

- 表单项统一为 `.ant-form-item`。
- 字段 ID 走 `data-fi`／`data-ml` 类标记，可由注入脚本按 fiber 回读刷新；**动态增删区块一律按行 label 定位，禁用序号**（手册 §2.1 第 4 条）。
- **区块 → `set_N` 映射随站点模板变化，不能跨站照搬**——同为 `resumeOperation.html`，站点一的工作经历在 `set_19`、站点二在 `set_123`。**每站先读页面主组件的 `state.resumeTpl` 建立本站映射再动手**；照抄别站实测出的 set 键，会把内容写进错误区块或整块丢失。
- 站点一（实测）：工作经历＝`set_19`（条目字段 `item_72` 开始／`item_73` 结束／`item_198` 企业／`item_76` 职位／`item_78` 职责／`item_75` 工作类型，工作类型「实习」取值 `0/461/580`）；教育＝`set_14`、校园实践＝`set_100101`、证书＝`set_44`、家庭＝`set_21`、语言＝`set_43`、开放问题＝`set_100006`。
- 站点二（实测）：个人信息＝`set_11`、教育＝`set_14`、工作经历（实习）＝`set_123`、学校工作＝`set_121`、奖励＝`set_120`、家庭＝`set_21`、开放问题＝`set_100001`／`set_101001`。
- **表单 item id ↔ 报文键**：`.ant-form-item` 的 React `id` 形如 `11_2_0`／`14_49_1`／`123_2129_0`，**中段**即报文里的 `item_<中段>`（例 `11_103301_0` → `item_103301`）。按字段名找报文键时先取该 form item 的 id 中段。
- 每条经历需要一个 `group_id`；重排时不改 `group_id`、只调整数组顺序。**新增条目的 `group_id` 由服务端在响应里回填**（响应的 `groupId` 列出该 set 全部条目 id，可据此确认新增是否被接受）。

## 3 保存接口与报文改写（本平台核心手法）

- 保存请求：`POST /wecruit/resume/info/edit/SU62f37858bef57c29ead8adab?iSaJAx=isAjax&request_locale=zh_CN`
- 请求体为**明文 JSON**：
  ```
  { resumeId, lang, recruitType, encryptType,
    resumeData: { resumeName, resumeDetail: { set_11, set_14, set_19, ... } } }
  ```
- **改写手法（XHR body-swap）**：给 `XMLHttpRequest.prototype.send` 挂钩，只重写 `body`、其余交回页面自己发（headers／鉴权原样保留）：
  ```js
  var OS = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function(b){
    if (typeof b === 'string' && b.indexOf('set_19') >= 0 && window.__FIX19) {
      var o = JSON.parse(b);
      if (o.resumeData && o.resumeData.resumeDetail) {
        o.resumeData.resumeDetail.set_19 = window.__FIX19;
        b = JSON.stringify(o);
      }
    }
    return OS.apply(this, arguments);
  };
  ```
- **两道纪律**：
  1. **注入脚本必须包 IIFE**——`window.X = {...}; return ...` 在顶层非法，会**静默失败**（不报错、不生效）。
  2. **保存后立即整页重载**——页面会每隔数十秒自动保存一次，覆盖你改过的报文并把挂钩卸载。用 `browser_go_to_url` 回同一 URL 真重载（`browser_tab_reload` 在本通道为空操作，见手册 §3.4）。挂钩与待写报文都要在重载后重新注入。

**更稳的提交方式：页内直发**（不点页面「保存」按钮）——在 `browser_eval_content_js` 里用同步 XHR 直接提交：

```js
var x = new XMLHttpRequest();
x.open('POST', '<保存接口路径>?iSaJAx=isAjax&request_locale=zh_CN', false);
x.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
x.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
x.send(window.__PBODY);   // 返回 status 200 即被服务端接受
```

- 好处：不依赖保存按钮的编码索引（页面重载后索引会变），也不依赖「点保存」这个动作不被页面态切换吃掉。
- **报文必须先抓真实模板再改写，不可从零构造**：`item_2`（姓名）／`item_29`（身份证）／`item_36`（电话）／`item_37`（邮箱）在报文里是 **hash 串**。做法＝先让页面自己发一次（挂钩只记录、不改写），把真实 body 存下来当模板，再在模板上改目标字段。
- **改写后的报文送进页面**：本地改好的 JSON 以 base64 传入，页面内解码后挂到全局变量（如 `window.__PBODY`）。中文长 JSON 不要直接拼进 JS 源码——经 shell→Python→JS 多层转义必失败（手册 §3.4）。
- **值是否真进去，以报文为准、不看 DOM**：本平台受控控件（复选框／单选）用 JS 回退点击**只改显示、不进表单模型**——实测两处点完 DOM 已变、报文里仍是旧值，最终靠改报文落库。

## 4 工作经历区块：顺序钉死与绕行

- **界面无法重排**：区块第一条经历被平台钉死（不显示删除按钮、无排序控件、无拖拽把手）。
- 因此**顺序只能改报文**：按**本站工作经历 set**（§2 映射，如站点一为 `set_19`）的正确顺序重建整个数组（每条保留原 `group_id`），经 §3 的直发或挂钩提交。
- 日期不经 UI 写：直接写进工作经历 set 的条目字段（站点一为 `set_19` 的 `item_72`／`item_73`）。**UI 里改不动的结束日期（如某段实习的 end）在报文里能正常落库**——UI 写不进不必然是服务端限制，先怀疑编辑态／控件托管问题，再怀疑服务端。
- 重排风险：重建数组时容易漏条。**动手前先整份备份工作经历 set 及相邻 set，重排后逐条回读比对条目数**。

## 5 保存与回读判据

- 整页重载后数据仍在才算保存成功（手册 §2.1 第 7 条）。
- 单项操作一气呵成，保存按钮只点一次（双击触发重复提交会弄掉会话）。
- 回读项数会随条目数变化：实测由一个站点在线简历的 105 项增至 166 项 `.ant-form-item`（新增 4 条工作经历＋录入证书等）。
- **优先回读表单数据模型**：页面主组件的 `state.resumeData.resumeDetail` 就是当前表单数据（与将要提交的报文同源），比逐项读 DOM 直接。取法＝从任一 `.ant-form-item` 沿 `__reactFiber$` 上溯到首个带 `setFieldValue` 的实例（实测第 34 层）。
- 计数器类（文本框右下「n/上限」）与复选框类字段，**回读要读模型而不是读显示**：DOM 已点选、模型仍是旧值，是本平台最常见的假填。

## 6 本平台结构事实

- 地区类字段（现居住地／户口所在地／高考所在地）为**城市级下拉，只到直辖市本级、无区县层级**——直辖市填到本级即可，不下沉到区县。
- 教育经历**要求填到高中层级**（与招商银行站一致，与中欧基金站「从大学起填」相反）。
- 证书区块可承载奖项证书类条目（实测一站录入 11 条，含奖学金与荣誉称号）。
- 开放问题区沿用页面现值，不主动改写。
- 文件上传项在报文里是**对象**而非字符串：`item_41` = `{"fileName","fileUrl","fileId"}`（编辑态 fiber 读值只看到 fileId）。照片／附件类项照此结构写。
- **「上传简历自动解析」会按解析结果覆盖已填字段**（手册 §2.1 第 6 条）：进本页时若已有解析回填内容，一律按数据层逐项核对改写，不当它已完成。

## 7 未复现与兜底

| 动作 | 状态 | 兜底 |
|---|---|---|
| 区块「添加」按钮的真实点击 | 【未复现】本通道无坐标点击命令（手册 §3.5） | 用页面内脚本触发组件回调，或按行 label 精确定位后派发事件 |
| 上传（证件照／简历附件） | 【未复现】本通道 CLI 未暴露 `upload_file`（手册 §3.4） | 请使用者手动上传，填写时留空并明确告知 |
| 预览态 → 编辑态的入口按钮定位 | 【未复现】两次都靠 URL 重载回到编辑态 | 优先用 URL 重载；确需点击时先 `scrollIntoView` 再定位 |

## 8 落点与遗留

- 本文件的观察来自两个站点的实测；后续新观察先登记进**使用者台账**（手册 §1.1 配置项 6）的【待验】表，达门槛后再上提进本文件正文。
- 待补：条目级字段 ID 表——两次实测都只提取到工作经历一处，教育／校园实践／证书／家庭／语言的条目字段 ID 下次填本平台时顺手补齐。
