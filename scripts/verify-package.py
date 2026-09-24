#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""封装体机械校验（交付前 / 手册改动后必跑）。

用法（两档，2026-09-23 起）：
  python scripts/verify-package.py                      # 【每轮档·默认】运行态第十段 ＋ 模板自证
  python scripts/verify-package.py --ledger <台账.md>   # 同上；指定台账（不指定则自动探测）
  python scripts/verify-package.py --package            # 【封装体档】九段全跑；改过封装体才需要
  python scripts/verify-package.py --apply <投递.xlsx>  # 第十段里对账轮锚（可省，自动找）
退出码：0 = 全绿；1 = 有 FAIL（先修结构再收工）。
为什么分两档：九段里有 7 段查的是「封装体自身是否自洽」（维护者项），对「这次填报对不对」
零贡献。每轮收尾只跑运行态（第十段）＋ 模板自证（生成物质量），改过封装体时再加跑九段。
第十段按台账声明的**档位**（§5.1：轻量／完整，未声明＝完整）决定检查面：轻量档不要求待验表
存在、不判到期与池量；完整档下若连续 3 个已复核轮事件流无新增行，另给一条「机制是否过重」WARN。

包自洽九段：①手册一级章节齐全 ②frontmatter 完整且版本号唯一
③配方索引 ↔ 磁盘双向一致 ＋ 配方内点名的随包脚本 ↔ 磁盘 ＋ 占位符声明 ↔ 脚本实际
④各配方 frontmatter 与目录名一致 ⑤启动器护栏在位（条件跳转＋标签＋exit /b 1 三者齐备） ⑥交叉引用不悬空（手册正文 ＋ 配方内 ＋ **包根文档内**的 § 引用，2026-09-22 补）
⑦个人数据黑名单扫描（含**成绩／证书类具体值**：三位数成绩、考试名后直接跟分数——示例须用占位符，2026-09-22 补）
   ＋**双端术语**扫描（假设存在第二处部署环境的措辞；本包面向单环境接收方，2026-09-22 补）
⑧本机绝对路径扫描 ⑨配方通道状态声明齐备 ＋ 编码健康 ＋ Markdown 表格列数与分隔行格数一致
   ＋ **游离表格行**（以 | 开头却无表头分隔行的块，渲染成普通段落＝表格静默断裂，2026-09-23 补）
   ＋ ⑨附「初始化能力自证」：init-workspace.py 在位且只读封装体、templates/ 占位符与脚本替换表双向闭合、
     templates/ 引用的包内脚本可解析（2026-09-22 补——生成的要求文件不得指向空气）
   （2026-09-20 补：只验证封装体自洽时，「照 §1.5 建的新环境是不是绿的」无人验——与模板事故同类）
运行态第十段（只在找到台账时启用）：轮次基准可解析且轮号连续、待验表七列
（条目|域|登记轮|关联次数|固化|待验原因|触发条件）与计数不变量、
「不计入范围」两形态（无／序号 a-b）、台账内任意表格的列数与分隔行格数、
到期（**域阈值分档** 流程域 4／框架域 6／系统域 10，固化＝已达门槛者豁免；第二支「反复不复现」型）、
池量（上限 20）、投递记录对账与「未复核轮」自动判定、
留档区三项（待验表 ↔ 休眠／已删除区互斥、留档区各表列数一致、休眠区唤醒提示）。

只读脚本，不修改任何文件；黑名单可用 --deny 追加（逗号分隔），或自建 scripts/verify-deny.txt。
台账路径：--ledger 参数 > 环境变量 VERIFY_LEDGER > 常见位置自动探测（找不到即跳过第十段）。
第十段的「到期」分两半（2026-09-22 同步源环境）：**有没有到期行未处置**是机械判据（空转 ≥ 域阈值
且 未固化，或第二支「反复不复现」）→ **改退出码**，机制判定该条已失效、留着即闭环停摆；
**「降级休眠还是清出（已入册）」**取决于该条是否已写进正文，属语义判断 → 脚本只给对账提示。
第十段还查变更档案「条目登记簿 ↔ 事件流」一致性（未登记 ID／悬空 ID／事件数守恒）并复算
漂移／固化率（2026-09-19 补，抖动判据按条目 ID 计，见 SKILL.md §5.1 与 §6.3），
分母只计登记簿「类＝条目」的在册 ID——「类＝部件」的机制类 ID（校验器／模板／
轮次基准／休眠归档／说明文档…）其变动属部件被正常使用与改进，两个判据都不触发
（2026-09-21 用户裁定），见 §6.3 判据对照表。
第九段另挂「模板机制数值 ↔ 校验判据一致」（2026-09-22 补）：机制数值集中在 MECH 一处，
模板与校验判据不一致即 FAIL——原判据「模板写 20、校验器判 30」两侧都不报，全绿而实分叉。
"""
import io
import os
import re
import sys
import zipfile
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "SKILL.md"
RECIPES = ROOT / "recipes"
BAT = ROOT / "scripts" / "launch-browser.bat"

CHECKS = 10
# 经验机制数值的**单一实现处**（2026-09-22 补）。判据出处：本手册 §5.1（模板与计数口径）
# 与项目级要求的「经验固化与复核」节。第九段据它核对模板文本与校验判据是否一致——
# 原先两处各写一份（模板写「上限 20」、第十段判「>30」），分叉时两侧都不报、全绿。
MECH = {
    "pool_cap": 20,                                    # 待验池上限：超过则降级入休眠区（非删除）
    "th": {"流程域": 4, "框架域": 6, "系统域": 10},      # 到期阈值按域分档（一律按空转）
    "pend_cols": 7,
    "pend_head": ["条目", "域", "登记轮", "关联次数", "固化", "待验原因", "触发条件"],
}
# 黑名单**不写进包**（写进去就违反了「不携带个人数据」这条自身声明）。
# 部署者自建本机名单：scripts/verify-deny.txt（一行一词，不随包），或用 --deny 追加。
DENY_FILE = ROOT / "scripts" / "verify-deny.txt"
SELF = Path(__file__).resolve()
# 档位（2026-09-23 补）：默认只跑「每轮档」= 运行态第十段 ＋ 模板自证；--package 才跑九段全量。
FULL_MODE = "--package" in sys.argv

fails, warns = [], []


def fail(sec, msg):
    fails.append("[%d] %s" % (sec, msg))


def warn(sec, msg):
    warns.append("[%d] %s" % (sec, msg))


def read_utf8(p):
    return io.open(str(p), encoding="utf-8").read()


def read_text(p):
    """读取时容错：优先 UTF-8，退而 GBK（**仅指解码时不炸**）。

    注意：这不等于「.bat 可以写非 ASCII」——判据见 scan_bat_non_ascii()。
    """
    raw = p.read_bytes()
    for enc in ("utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


def scan_bat_non_ascii():
    """返回包内含**非 ASCII 字节**的 .bat：[相对路径, [行号…]]。

    为什么单列这段（2026-09-24）：本包模板 `scripts/launch-browser.bat` 曾用中文写 REM 注释、
    文件按 UTF-8 存盘；`cmd.exe` 按本地 ANSI 代码页（中文 Windows＝GBK）解析批处理，
    注释行被撕成碎片并当命令执行（实测报错 `'紙--display-invisible-extension' 不是内部或外部命令`）。
    **当时九段全绿**——原判据只判「能否用 UTF-8 或 GBK 解开」＋护栏／参数是否齐，**不看编码本身**。
    故补此段：包内任何 .bat 含非 ASCII 即判 FAIL（对应手册 §3.0.1 的硬规矩）。
    """
    out = []
    for dp, dn, fn in os.walk(str(ROOT)):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git", ".svn", ".hg")]
        for f in fn:
            if not f.lower().endswith(".bat"):
                continue
            p = Path(dp) / f
            try:
                raw = p.read_bytes()
            except OSError:
                continue
            if not any(b > 0x7F for b in raw):
                continue
            ln = [str(i + 1) for i, l in
                  enumerate(raw.decode("utf-8", "replace").splitlines())
                  if any(ord(c) > 0x7F for c in l)]
            out.append([str(p.relative_to(ROOT)), ln])
    return out


def _split_row(line):
    """按竖线切单元格；\\| 是转义写法，不算分隔符。"""
    t = line.replace("\\|", "\x00")
    cells = [c.replace("\x00", "|") for c in t.split("|")]
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return cells


SEP_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def check_md_tables(text, rel, seg=9):
    """表格列数一致：单元格里的裸竖线会被当分隔符（整行错列），分隔行格数与表头不符则整块不成表。

    另查「游离表格行」（2026-09-23 补，v3.0.3 实例）：以 `|` 开头、整块却没有表头分隔行的连续块——
    渲染器把整块当普通段落（排版里显出带竖线的怪句子），表格静默断裂。
    原判据只校「已被认出是表的块」，碎掉的那部分不进视野，于是全绿而实坏。
    判据收窄以防误报：只在块首报一次；块内每行 `|` 数须 ≥2；块内确无分隔行。
    """
    ls = text.split("\n")
    in_code = False
    i = 0
    while i < len(ls):
        s = ls[i].rstrip()
        if s.strip().startswith("```"):
            in_code = not in_code
            i += 1
            continue
        if not in_code and s.strip().startswith("|"):
            # A. 已成表：表头 + 分隔行 + 后续 | 行，校列数
            if i + 1 < len(ls) and SEP_RE.match(ls[i + 1]):
                n = len(_split_row(s.strip()))
                ns = len(_split_row(ls[i + 1].strip()))
                if ns != n:
                    fail(seg, "%s 第 %d 行分隔行 %d 格 ≠ 表头 %d 格（不符时多数渲染器整块不成表）"
                         % (rel, i + 2, ns, n))
                j = i + 2
                while j < len(ls) and ls[j].strip().startswith("|"):
                    c = len(_split_row(ls[j].strip()))
                    if c != n:
                        fail(seg, "%s 第 %d 行表格 %d 列 ≠ 表头 %d 列（单元格内的裸竖线要写成 \\|）"
                             % (rel, j + 1, c, n))
                    j += 1
                i = j
                continue
            # B. 未成表：整块以 | 开头却无分隔行 → 渲染成普通段落，表格静默断裂
            if not (i > 0 and ls[i - 1].strip().startswith("|")):      # 只在块首判一次
                j = i
                while j < len(ls) and ls[j].strip().startswith("|"):
                    j += 1
                blk = [x.strip() for x in ls[i:j]]
                like_row = all(x.count("|") >= 2 for x in blk)
                if like_row and not any(SEP_RE.match(x) for x in blk):
                    fail(seg, "%s 第 %d 行起 %d 行以 | 开头却无表头分隔行（渲染成普通段落、表格静默断裂；"
                              "补一行 |---| 或去掉竖线）" % (rel, i + 1, len(blk)))
            i += 1
            continue
        i += 1


def recipe_dirs():
    if not RECIPES.is_dir():
        return []
    return sorted(d.name for d in RECIPES.iterdir() if d.is_dir())


def doc_heads(text):
    """文档里的节号：返回 (全部, 纯数字)。配方用带点号指手册的节、用单数字指自己的节。"""
    allnum, plain = set(), set()
    for m in re.finditer(r"^#{2,4}\s+(\d+(?:\.\d+)*)[^\n]*$", text, re.M):
        allnum.add(m.group(1))
        if "." not in m.group(1):
            plain.add(m.group(1))
    return allnum, plain


def find_ledger():
    """台账路径：--ledger > 环境变量 VERIFY_LEDGER > 常见位置探测。"""
    cands = []
    if "--ledger" in sys.argv:
        cands.append(Path(sys.argv[sys.argv.index("--ledger") + 1]))
    env = os.environ.get("VERIFY_LEDGER")
    if env:
        cands.append(Path(env))
    for base in [Path.cwd(), ROOT] + list(ROOT.parents)[:3]:
        cands += [base / "EXPERIENCE-LEDGER.md",
                  base / ".workbuddy" / "skills" / "EXPERIENCE-LEDGER.md"]
    for c in cands:
        if c.is_file():
            return c
    return None


def find_apply(ledger):
    """投递记录：--apply > 台账附近按名找（限深 3 层，跳过隐藏目录与备份件）。

    备份件必须排除：否则 `.workbuddy/tmp/投递台账.bak-<ts>.xlsx` 会先被命中，
    拿旧副本对账（曾把 30 行的正本读成 29 行，害得新锚点的序号被判为不存在）。
    正本名（投递台账.xlsx）优先于其他同模式命中。
    """
    if "--apply" in sys.argv:
        return Path(sys.argv[sys.argv.index("--apply") + 1])
    BAK = ("bak", "backup", "副本", "copy", "存档")
    exact, other = None, None
    for r in [ledger.parent] + list(ledger.parents)[:3]:
        for p in sorted(r.glob("*/投递*.xlsx")) + sorted(r.glob("*投递*.xlsx")) \
                + sorted(r.glob("*/*/*投递*.xlsx")) + sorted(r.glob("*/台账*.xlsx")) \
                + sorted(r.glob("*台账*.xlsx")):
            rel = p.relative_to(r)
            if any(part.startswith(".") or part in ("node_modules", "__pycache__")
                   for part in rel.parts):
                continue
            if not p.is_file() or p.name.startswith("~$"):
                continue
            if any(k in p.name.lower() for k in BAK):
                continue
            if p.name == "投递台账.xlsx":
                exact = exact or p
            else:
                other = other or p
    return exact or other


def _find_md_apply(ledger):
    """探测 v3.0.1 短暂采用过的 Markdown 形态投递台账（只用于迁移提示，不参与对账）。"""
    BAK = ("bak", "backup", "副本", "copy", "存档")
    for r in [ledger.parent] + list(ledger.parents)[:3]:
        for p in sorted(r.glob("*/投递*.md")) + sorted(r.glob("*投递*.md")):
            if not p.is_file() or p.name.startswith("~$") or p.name.startswith("EXPERIENCE"):
                continue
            if any(k in p.name.lower() for k in BAK):
                continue
            return p
    return None


def xlsx_first_col_int(path):
    """直读 xlsx 的 A 列整数（不依赖 Excel／openpyxl）。

    返回 (序号列表, 非数字行数)。共享字符串会解析后再判——序号列里「21」可能是文本型
    （`t="s"`），按数值处理；表头「序号」等非数字串跳过并计数。
    """
    out, strange = [], 0
    with zipfile.ZipFile(str(path)) as z:
        names = z.namelist()
        sheet = next((n for n in names if n.startswith("xl/worksheets/sheet")), None)
        if not sheet:
            return None, 0
        xml = z.read(sheet).decode("utf-8", "replace")
        shared = []
        if "xl/sharedStrings.xml" in names:
            ss = z.read("xl/sharedStrings.xml").decode("utf-8", "replace")
            for si in re.findall(r"<si>(.*?)</si>", ss, re.S):
                shared.append("".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S)))
    for idx, row in enumerate(re.finditer(r"<row[^>]*>(.*?)</row>", xml, re.S), 1):
        if idx == 1:
            continue                      # 首行＝表头，不计入「非数字」"
        mc = re.search(r'<c r="A\d+"([^>]*?)(?:/>|>(.*?)</c>)', row.group(1), re.S)
        if not mc:
            continue
        attrs, cell = mc.group(1) or "", mc.group(2) or ""
        mv = re.search(r"<v>([^<]*)</v>", cell)
        if mv:
            val = mv.group(1).strip()
            if 't="s"' in attrs:
                try:
                    val = shared[int(val)]
                except (ValueError, IndexError):
                    continue
        else:
            # 内联字符串（t="inlineStr"）的值在 <is><t> 里，没有 <v>；
            # 漏掉这一支会把这类行整个丢弃（曾把 30 行读成 29 行）
            mi = re.search(r"<is>.*?<t[^>]*>(.*?)</t>", cell, re.S)
            if not mi:
                continue
            val = mi.group(1).strip()
        val = (val or "").strip()
        if re.fullmatch(r"\d+", val):
            out.append(int(val))
        else:
            strange += 1
    return out, strange


# 停用词：这些词在正文里必然出现，拿来当「已收录」的证据只会误报（首版实测假阳性）。
_RECON_STOP = {
    "react", "vue", "vue2", "vue3", "eval", "input", "textarea", "value", "change",
    "click", "form", "body", "data", "file", "dom", "css", "html", "json", "api",
    "text", "type", "fill", "set", "get", "true", "false", "null", "none", "item",
    "list", "page", "node", "test", "main", "code", "name", "url", "http", "https",
    "add", "del", "new", "old", "top", "end", "size", "mode", "user", "base",
}


def _recon_bases(led):
    """对账时用来解析「拟入层级」相对路径的候选根目录。"""
    out, seen = [], set()
    try:
        rp = led.resolve()
        out += [rp.parent, rp.parent.parent, rp.parent.parent.parent]
    except Exception:
        pass
    out += [Path.cwd(), ROOT.parent, ROOT]
    return [b for b in out if not (b in seen or seen.add(b))]


def _recon_target(row_text, led):
    """从待验行取〔拟入层级→`路径`〕里的路径，解析成磁盘文件；返回 (原始路径, Path 或 None)。"""
    m = re.search(r"拟入层级[^`]*`([^`]+)`", row_text)
    if not m:
        return None, None
    raw = m.group(1).strip()
    if not re.search(r"[\\/]|\.(md|py|ps1|json|js|bat)$", raw):
        return raw, None
    for b in _recon_bases(led):
        p = b / raw
        if p.is_file():
            return raw, p
    return raw, None


def _recon_tokens(row_text):
    """取检索词：优先反引号内的标识符，其次拉丁词，最后 4-10 字中文串。"""
    out = []
    for t in re.findall(r"`([^`\n]{2,50})`", row_text):
        t = t.strip()
        if len(t) < 3 or not re.search(r"[A-Za-z0-9_$]", t):
            continue
        if re.search(r"[\\/]|\.(md|py|ps1|json|js|bat)$", t):
            continue
        if t.lower() in _RECON_STOP:
            continue
        if t not in out:
            out.append(t)
    if not out:
        # 先把含斜杠／反斜杠的路径片段整段抹掉，否则 `.workbuddy/skills/x.md` 会喂出
        # 「workbuddy」「skills」这类词，报出一串与判定无关的"试过"。
        clean = re.sub(r"\S*[\\/]\S*", " ", row_text)
        # 拉丁词须 ≥5 字符且不在停用词表内，否则「React」「eval」这类通用词会误报
        for t in re.findall(r"[A-Za-z][A-Za-z0-9_.\-]{4,}", clean):
            if t.lower() in _RECON_STOP:
                continue
            if re.search(r"\.(md|py|ps1|json|js|bat)$", t, re.I):
                continue
            if t.lower() not in [x.lower() for x in out]:
                out.append(t)
    if not out:
        out = re.findall(r"[\u4e00-\u9fa5]{4,10}", row_text)
    return out[:3]


def _recon_hit(tok, body):
    """该检索词是否出现在正文里（含中文的按原样比，纯拉丁／符号的忽略大小写）。"""
    if re.search(r"[\u4e00-\u9fa5]", tok):
        return tok in body
    return tok.lower() in body.lower()


def reconcile_hint(row_text, led):
    """到期条目的正文对账提示。只出文字，不做 pass/fail、不改退出码。"""
    raw, p = _recon_target(row_text, led)
    if raw is None:
        return "拟入层级未指向文件 → 处置前须人工对账正文"
    if p is None:
        return "目标不在磁盘（%s）→ 处置前须人工对账正文" % raw
    toks = _recon_tokens(row_text)
    if not toks:
        return "无可用检索词 → 处置前须人工对账 %s" % raw
    try:
        body = read_utf8(p)
    except Exception:
        return "目标读不到（%s）→ 处置前须人工对账正文" % raw
    hit = [t for t in toks if _recon_hit(t, body)]
    if len(hit) == len(toks):
        return "疑似已收录于 %s（命中 %s）→ 核实后记「清出（已入册）」，不得记删除" % (raw, "、".join(hit))
    if hit:
        return ("部分命中 %s（未命中 %s）→ 无法据此判定，请人工核对正文"
                % ("、".join(hit), "／".join([t for t in toks if t not in hit])))
    return "正文未见（试过 %s）→ 若确为到期才可删除，请人工确认" % "／".join(toks)


def check_registry(led):
    """第十段附：变更档案「落点登记簿 ↔ 事件流」一致性 ＋ 漂移/固化率复算（2026-09-19 补）。
    判据：每条经验一个不变 ID（<域>#<主题键>，不含落点路径），登记簿做分母。
      ①未登记 ID＝事件流有、登记簿没有；②悬空 ID＝在册却没有任何事件行（待验条目不判）；
      ③登记簿「事件数」必须等于事件流＋留档区已折叠行的实际行数（折叠只移不删）；
      ④按登记簿状态与窗口日期复算漂移／固化率，与档案两节所填数字比对。"""
    info = []
    chg = led.parent / "EXPERIENCE-CHANGELOG.md"
    if not chg.is_file():
        return ["登记簿对账：跳过（台账旁未找到 EXPERIENCE-CHANGELOG.md）"]
    s = read_utf8(chg)
    lines = s.split("\n")
    hi = next((i for i, l in enumerate(lines)
               if re.match(r"^\|\s*条目 ID\s*\|\s*(类\s*\|\s*)?当前落点\s*\|", l)), None)
    if hi is None:
        fail(10, "变更档案找不到「落点登记簿」表头（应为「| 条目 ID | 类 | 当前落点 | 状态 | …」）")
        return info
    # 2026-09-21 用户裁定：登记簿新增「类」列（条目／部件）。漂移与固化率的分母
    # 都只统计「条目」类 ID——机制类部件（校验器／模板／轮次基准／休眠归档／说明文档…）
    # 其变动属部件被正常使用与改进，不代表定义不清。判据是语义（描述部件还是判断点），
    # 表里写死结论、不硬编码名单。旧格式（无「类」列）按全部记作「条目」，向后兼容。
    has_cls = bool(re.match(r"^\|\s*条目 ID\s*\|\s*类\s*\|", lines[hi]))
    reg = {}
    for l in lines[hi + 1:]:
        if not l.startswith("|"):
            break
        if re.match(r"^\|[\s\-:|]+\|?\s*$", l):
            continue
        f = [x.strip() for x in l.strip("|").split("|")]
        if has_cls:
            if len(f) >= 7 and f[0]:
                reg[f[0]] = {"cls": f[1] or "条目", "st": f[3],
                             "n": int(f[5]) if re.fullmatch(r"\d+", f[5]) else -1}
        else:
            if len(f) >= 6 and f[0]:
                reg[f[0]] = {"cls": "条目", "st": f[2],
                             "n": int(f[4]) if re.fullmatch(r"\d+", f[4]) else -1}
    if not reg:
        return ["登记簿：初态（空）——跳过登记簿对账与抖动复算"]
    flow, folded, sec = [], [], ""
    for l in lines:
        if re.match(r"^#{2,3} ", l):
            sec = l.strip()
            continue
        if not re.match(r"^\| \d{4}-\d{2}-\d{2}", l) or "（折叠）" in l:
            continue
        f = [x.strip() for x in l.strip("|").split("|")]
        if len(f) < 2:
            continue
        if sec == "## 事件流":
            flow.append(f[1])
        elif sec == "### 已折叠事件（按 ID）":
            folded.append(f[1])
    cnt = {}
    for x in flow + folded:
        cnt[x] = cnt.get(x, 0) + 1
    unreg = sorted({x for x in flow if x not in reg})
    dangling = sorted(k for k, v in reg.items() if v["st"] == "在册" and k not in cnt)
    mism = sorted(k for k, v in reg.items() if k in cnt and v["n"] != cnt[k])
    live = [k for k, v in reg.items() if v["st"] == "在册"]
    info.append("登记簿：%d 条（在册 %d）｜事件流 %d 行＋已折叠 %d 行"
                % (len(reg), len(live), len(flow), len(folded)))
    if unreg:
        fail(10, "未登记 ID（事件流有、登记簿无）→ %s" % ", ".join(unreg[:8]))
    if dangling:
        fail(10, "悬空 ID（在册却无任何事件行）→ %s" % ", ".join(dangling[:8]))
    if mism:
        fail(10, "登记簿「事件数」与明细不符 → %s" % ", ".join(
            "%s（簿%d／实%d）" % (k, reg[k]["n"], cnt[k]) for k in mism[:8]))
    if not (unreg or dangling or mism):
        info.append("未登记 0／悬空 0／各 ID 事件数与明细一致")
    mw = re.search(r"窗口＝[^（]*（r\d+–r\d+，(\d{4}-\d{2}-\d{2})～(\d{4}-\d{2}-\d{2}|\d{2}-\d{2})）", s)
    if not mw:
        warn(10, "抖动命中节缺窗口声明（rA–rB，日期～日期），跳过漂移／固化率复算")
        return info
    w0 = mw.group(1)
    w1 = mw.group(2) if len(mw.group(2)) == 10 else w0[:5] + mw.group(2)
    wc = {}
    for l in lines:
        if not re.match(r"^\| \d{4}-\d{2}-\d{2} ", l) or "（折叠）" in l:
            continue
        d = l[2:12]
        if not (w0 <= d <= w1):
            continue
        f = [x.strip() for x in l.strip("|").split("|")]
        if len(f) >= 2:
            wc[f[1]] = wc.get(f[1], 0) + 1
    # 分母＝「条目」类在册 ID；漂移与固化率同用此集合（部件类只列不计）。
    ent = [k for k, v in reg.items() if v["st"] == "在册" and v.get("cls") != "部件"]
    part_n = len([k for k, v in reg.items() if v["st"] == "在册" and v.get("cls") == "部件"])
    drift = sorted(k for k in ent if wc.get(k, 0) >= 3)
    touched = sum(1 for k in ent if k in wc)
    frozen = len(ent) - touched
    rate = round(100.0 * frozen / len(ent), 1) if ent else 0.0
    info.append("复算：窗口 %s～%s；漂移 %d 条%s；固化率 %d/%d＝%s%%（分母＝条目类在册 ID；另有部件类 %d 条不计）" % (
        w0, w1, len(drift), ("（%s）" % "，".join(drift)) if drift else "",
        frozen, len(ent), rate, part_n))
    # 「抖动命中」正文表只数到「已排除（部件类）」子标题之前——那之后的排除表
    # 行同样以「| 漂移 |」开头，但它列的是被排除的部件类，不该计入真漂移行数。
    excl_at = s.find("### 已排除（部件类")
    sect = s[:excl_at] if excl_at != -1 else s
    n_drift_rows = len(re.findall(r"(?m)^\| 漂移 \| [^|]+ \|", sect))
    m_dr = re.search(r"\| 漂移条目 \| (\d+) \|", s)
    m_rate = re.search(r"\| \*\*固化率\*\* \| (\d+)/(\d+)", s)
    bad2 = 0
    if n_drift_rows != len(drift):
        fail(10, "「抖动命中」漂移行 %d ≠ 复算 %d" % (n_drift_rows, len(drift))); bad2 += 1
    if m_dr and int(m_dr.group(1)) != len(drift):
        fail(10, "「本轮指标·漂移条目」%s ≠ 复算 %d" % (m_dr.group(1), len(drift))); bad2 += 1
    if m_rate and (int(m_rate.group(1)) != frozen or int(m_rate.group(2)) != len(ent)):
        fail(10, "「本轮指标·固化率」%s/%s ≠ 复算 %d/%d" % (
            m_rate.group(1), m_rate.group(2), frozen, len(ent))); bad2 += 1
    if not bad2:
        info.append("档案两节所填漂移／固化率与复算一致")

    # ---- 留档区：互斥 ＋ 各表列数 ＋ 休眠区唤醒提示（2026-09-22 补）----
    # 判据出处：§5.1 节首「休眠区不得只进不出」——同一条不得既挂待验又在休眠／已删除区；
    #   休眠区里属于「本轮出现的域」的条目应被唤醒回表（标「反复不复现」者除外）。
    # 实现要点：① 只扫「## 留档区」这一节（到下一个 ## 为止），否则抖动计数表也会被当留档区；
    #          ② 表的「条目」列**按表头里名为「条目」的单元格定位**，不假定在第 1 格——
    #             「已删除／清出条目」表第 1 格是「日期」，按第 1 格取键会让互斥检查静默失效；
    #          ③ 行格数须与本表表头一致（多写一格会整行错位、后面取值全偏）。
    pend = []
    lt = read_utf8(led).split("\n")
    lh = next((i for i, l in enumerate(lt)
               if re.match(r"^\|\s*条目\s*\|\s*域\s*\|\s*登记轮", l)), None)
    if lh is not None:
        for l in lt[lh + 1:]:
            if not l.startswith("|"):
                break
            if re.match(r"^\|[\s\-:|]+\|?\s*$", l):
                continue
            pend.append(_pend_key(l.strip("|").split("|")[0]))
    ai = next((i for i, l in enumerate(lines) if re.match(r"^## 留档区", l)), None)
    if ai is None:
        info.append("留档区：跳过（档案中找不到「## 留档区」）")
    else:
        zones, tbl_bad, zone, expect_hdr, hdr_n, kc, dc = {}, 0, "", True, 0, -1, -1
        for i2 in range(ai, len(lines)):
            l = lines[i2]
            if i2 > ai and re.match(r"^##\s", l):
                break
            m3 = re.match(r"^###\s*(.+)$", l)
            if m3:
                zone, expect_hdr = m3.group(1).strip(), True
                continue
            if not l.startswith("|"):
                expect_hdr = True
                continue
            if re.match(r"^\|[\s\-:|]+\|?\s*$", l):
                continue
            c = [x.strip() for x in l.strip("|").split("|")]
            if expect_hdr:
                expect_hdr, hdr_n, kc, dc = False, len(c), -1, -1
                for j2, v in enumerate(c):
                    if v == "条目":
                        kc = j2
                    if v == "域":
                        dc = j2
                if kc < 0:
                    hdr_n = 0                      # 本表无「条目」列（如历史结论表）→ 整表跳过
                    continue
                if i2 + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|?\s*$", lines[i2 + 1]):
                    ns = len(lines[i2 + 1].strip("|").split("|"))
                    if ns != hdr_n:
                        fail(10, "留档区「%s」表头 %d 格 ≠ 分隔行 %d 格" % (zone, hdr_n, ns))
                        tbl_bad += 1
                continue
            if hdr_n == 0:
                continue
            if len(c) != hdr_n:
                fail(10, "留档区「%s」第 %d 行 %d 格（本表表头 %d 格）" % (zone, i2 + 1, len(c), hdr_n))
                tbl_bad += 1
                continue
            if kc >= len(c):
                continue
            k = _pend_key(c[kc])
            if not k:
                continue
            zones.setdefault(zone, []).append(
                {"k": k, "dom": c[dc] if 0 <= dc < len(c) else "",
                 "txt": l, "dorm": zone.startswith("休眠")})
        dup = []
        for z, rs in zones.items():
            if not (z.startswith("休眠") or z.startswith("已删除")):
                continue
            for r in rs:
                if r["k"] in pend:
                    dup.append("「%s…」同时在待验表与「%s」" % (r["k"], z))
        info.append("留档区：%d 行；与待验表 %d 行%s；表列数异常 %d" % (
            sum(len(v) for v in zones.values()), len(pend),
            ("有 %d 处重复" % len(dup)) if dup else "无重复", tbl_bad))
        for d in dup:
            fail(10, "互斥性：%s（同一条不得既挂待验又在休眠／已删除区）" % d)
        dorm = [r for z, rs in zones.items() if z.startswith("休眠") for r in rs]
        if not dorm:
            info.append("休眠区：无条目或本轮身份解析不出，唤醒检查跳过")
        else:
            # 本轮身份＝「本轮复核结论」节下第一个 ### 标题；取不到就退回轮次基准里当前轮的名字。
            cur_name = ""
            ri = next((i for i, l in enumerate(lines) if re.match(r"^## 本轮复核结论", l)), None)
            if ri is not None:
                for l in lines[ri:]:
                    m4 = re.match(r"^### (.+)$", l)
                    if m4:
                        cur_name = m4.group(1)
                        break
            if not cur_name:
                m5 = re.search(r"r(\d+)\s+\d{2}-\d{2}\s+([^（]+)（", "\n".join(lt))
                if m5:
                    cur_name = m5.group(2).strip()
            wk, rep_skip = [], 0
            for r in dorm:
                if "反复不复现" in r["txt"]:
                    rep_skip += 1                      # 第二支判据休眠，明确不再被唤醒
                    continue
                m6 = re.search(r"（(.+)）", r["dom"])
                if not m6:
                    continue
                for w in re.split(r"[／，,\s]+", m6.group(1)):
                    if len(w) >= 2 and cur_name and (w in cur_name or cur_name in w):
                        wk.append(r["k"])
                        break
            zones_note = ("；休眠区 %d 条属本轮出现的域，按「唤醒在到期之后」应唤醒回表并关联 +1 → %s"
                          % (len(wk), "；".join(wk))) if wk else "；休眠区无本轮出现的域，无需唤醒"
            if not cur_name:
                zones_note = "；休眠区唤醒检查跳过（本轮身份解析不出）"
            zones_note += ("（另 %d 条标「反复不复现」，按第二支判据不唤醒）" % rep_skip) if rep_skip else ""
            info.append("休眠区：%d 条%s" % (len(dorm), zones_note))
    return info

def _pend_key(cell):
    """待验／留档条目的比对键：取前 24 字（与 PS 版 `$key` 同口径）。"""
    t = (cell or "").strip()
    return t[:24]


def ledger_tier(text):
    """台账档位（§5.1 档位段，2026-09-23）：读「计数与口径」段首的 `**档位**：轻量|完整`。
    未声明即按**完整档**——向后兼容 2026-09-23 之前生成的台账。"""
    m = re.search(r"\*\*档位\*\*\s*[:：]\s*(轻量|完整)", text)
    return m.group(1) if m else "完整"


def _mech_weight_hint(s, rounds):
    """运行证据门槛（§5.1，T2-3）：完整档下连续 ≥3 个已复核轮内事件流无新增行 →
    提示复核机制是否过重。**只提示（WARN），降档与否由使用者定。**"""
    if len(rounds) < 3:
        return []
    dates = {}
    for m in re.finditer(r"\br(\d+)\b[^\n]{0,8}?(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s):
        dates[int(m.group(1))] = "%04d-%02d-%02d" % (
            int(m.group(2)), int(m.group(3)), int(m.group(4)))
    anchor = dates.get(sorted(rounds)[-3])
    if not anchor:
        return []
    ev = []
    es = re.search(r"^#{2,4}\s*事件流[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)", s, re.M | re.S)
    if es:
        for l in es.group(1).split("\n"):
            m = re.match(r"^\|\s*(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", l)
            if m:
                ev.append("%04d-%02d-%02d" % (int(m.group(1)), int(m.group(2)), int(m.group(3))))
    if ev and max(ev) >= anchor:
        return []
    warn(10, "完整档已连续 ≥3 轮（r%s 起）事件流无新增行——按 §5.1 运行证据门槛复核机制是否过重："
             "降为轻量档，或在该轮结论里写明为何仍需保留" % sorted(rounds)[-3])
    return ["机制运行证据：连续 ≥3 轮无事件（触发一次「是否过重」复核，提示非阻断）"]


def _check_trace(led):
    """第十段附：开工体检留痕（v3.1.2 补）。§〇.7 要求每次开工先跑
    ``--check --record-trace``，留痕追加在 <项目根>/.workbuddy/evidence/deploy-check.log；
    本判据把「体检跑没跑靠人记」升级为「有痕迹可查」。台账不在标准布局
    （<根>/.workbuddy/skills/）时跳过——定位不了项目根，宁可不判也不误报。"""
    out = []
    p = Path(led).resolve()
    if not (p.parent.name == "skills" and p.parent.parent.name == ".workbuddy"):
        out.append("开工体检留痕：跳过（台账不在标准布局，定位不了项目根）")
        return out
    t = p.parent.parent / "evidence" / "deploy-check.log"
    if not t.is_file():
        fail(10, "开工体检留痕缺失——每个任务开工第 0 步应先跑 "
                 "init-workspace.py --check --record-trace --project \"<项目根>\"，"
                 "留痕会追加到 .workbuddy/evidence/deploy-check.log；跑一次即生成（§4.1／§6.1）")
        out.append("开工体检留痕：缺失")
        return out
    lns = [l for l in read_utf8(t).splitlines() if l.strip()]
    last = lns[-1].strip() if lns else ""
    m = re.match(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})", last)
    if not m:
        fail(10, "开工体检留痕末行不可解析（应为「<ISO时刻> | <包版本> | miss=x/5 | channel=…」，"
                 "由 --check --record-trace 写入）→ %r" % last[:80])
        out.append("开工体检留痕：末行不可解析")
        return out
    out.append("开工体检留痕：末次 %s %s（共 %d 行）" % (m.group(1), m.group(2), len(lns)))
    try:
        d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        if (date.today() - d).days > 7:
            warn(10, "开工体检留痕末次 %s（>7 天）——环境久未复检或留痕停记；"
                     "开工前补跑一次 --check --record-trace" % m.group(1))
    except ValueError:
        pass
    return out


def check_ledger(led, apply_xlsx):
    """第十段：运行态台账校验。返回打印用信息行。"""
    s = read_utf8(led)
    info = ["台账：%s" % led]
    tier = ledger_tier(s)
    light = (tier == "轻量")
    info.append("档位：%s%s" % (tier, "（轻量档：待验池／到期／池量／休眠／折叠不强制）"
                              if light else "（完整档：全机制）"))
    # 台账是运行态文件、不在包里，第 9 段的扫描扫不到它；这里补一次表格结构检查
    # （2026-09-17 事故：账本待验表 6 列表头配 4 格分隔行，渲染器整块不成表，两套脚本都没拦住）。
    check_md_tables(s, os.path.basename(led), 10)

    # 轮次基准
    rounds, anchor_seqs, body = [], set(), ""
    mb = re.search(r"^#{2,4}\s*轮次基准[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)", s, re.M | re.S)
    if not mb:
        fail(10, "找不到「轮次基准」节")
    else:
        body = mb.group(1)
        # 只认基准条目行（bullet），排除「不计入范围」说明行与正文括注，免得把正文里的 rN 当轮号
        entry = "\n".join(l for l in body.split("\n")
                          if l.strip().startswith("-") and "不计入范围" not in l)
        rounds = sorted({int(x) for x in re.findall(r"\br(\d+)\b", entry)})
        if not rounds:
            warn(10, "轮次基准为空（首个计入轮尚未登记）")
        elif rounds != list(range(1, max(rounds) + 1)):
            fail(10, "轮次号不连续或有重复：%s" % rounds)
        for grp in re.findall(r"（序号\s*([^）]*)）", entry):
            for tok in re.split(r"[、,，]", grp):
                tok = tok.strip()
                if re.fullmatch(r"\d+", tok):
                    anchor_seqs.add(int(tok))
                else:
                    rng = re.fullmatch(r"(\d+)\s*[-–~]\s*(\d+)", tok)
                    if rng:
                        anchor_seqs |= set(range(int(rng.group(1)), int(rng.group(2)) + 1))
        info.append("轮次基准：%d 轮（r%s）｜锚定序号 %d 个" % (
            len(rounds), rounds[-1] if rounds else "-", len(anchor_seqs)))

    # 不计入范围
    excluded = set()
    nc = re.search(r"不计入范围[^\n]*", s)
    nc_none = False
    if not nc:
        warn(10, "缺「不计入范围」声明（无法区分未复核轮与历史轮）")
    else:
        # 只认两种形态：「无」＝空区间（新建环境照 §5.1 模板建完即此形态），或「序号 a-b」。
        if re.search(r"不计入范围[：:]\s*\**无\b", nc.group(0)):
            nc_none = True
        rng = re.search(r"(\d+)\s*[-–~]\s*(\d+)", nc.group(0))
        if rng and not nc_none:
            excluded = set(range(int(rng.group(1)), int(rng.group(2)) + 1))
        info.append("不计入范围：%s" % (("序号 %d-%d" % (min(excluded), max(excluded)))
                                    if excluded else ("无" if nc_none else "未声明区间")))

    # 待验表结构（7 列：条目|域|登记轮|关联次数|固化|待验原因|触发条件）
    lines = s.split("\n")
    hi = next((i for i, l in enumerate(lines)
               if re.match(r"^\|\s*条目\s*\|\s*域\s*\|\s*登记轮", l)), None)
    due, rep = [], []
    if hi is None:
        if light:
            # 轻量档（§5.1 默认）不维护待验池：可整节留空或不建，不报错
            info.append("待验表：轻量档未启用（可整节留空／不建）——跳过结构、到期与池量检查")
            rows = 0
        else:
            fail(10, "找不到待验表头（应为「| %s |」）" % " | ".join(MECH["pend_head"]))
            rows = 0
    else:
        rows, bad = 0, 0
        cur = max(rounds) if rounds else 0
        # 表头与分隔行格数必须一致：不符时多数渲染器把整块当普通段落（不成表），比"错列"严重
        if hi + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|?\s*$", lines[hi + 1]):
            nh = len(lines[hi].strip().strip("|").split("|"))
            ns = len(lines[hi + 1].strip().strip("|").split("|"))
            if nh != ns:
                fail(10, "待验表头 %d 列、分隔行 %d 列不一致——多数渲染器会把整块当普通段落，不成表" % (nh, ns))
            if nh != MECH["pend_cols"]:
                fail(10, "待验表头 %d 列（应 %d：%s）"
                     % (nh, MECH["pend_cols"], " | ".join(MECH["pend_head"])))
        for l in lines[hi + 1:]:
            if not l.startswith("|"):
                break
            if re.match(r"^\|[\s\-|]+\|?\s*$", l):
                continue
            f = [x.strip() for x in l.strip("|").split("|")]
            if len(f) != MECH["pend_cols"]:
                fail(10, "待验表列数 %d（应 %d；单元格禁写竖线）→ %s"
                     % (len(f), MECH["pend_cols"], f[0][:24]))
                continue
            rows += 1
            label, dom, reg, rel, fix = f[0][:28], f[1], f[2], f[3], f[4]
            # 域校验分两步：先校形状（有无括号）、再校成员。若写成一体化正则
            # `^(流程域|框架域（.+）|系统域（.+）)$`，「域不在三档内」永远不可达
            # （能过该正则的必在三档内）——该分支成为死代码，2026-09-22 与源环境同批修正。
            if not re.match(r"^(流程域|[^（]+（.+）)$", dom):
                fail(10, "待验表域格式异常 → %s（%s）（应为「流程域」或「X域（系统名）」）" % (dom, label))
                bad += 1
                continue
            dkey = dom.split("（")[0]
            if dkey not in MECH["th"]:
                fail(10, "域不在三档内（流程域／框架域／系统域）→ %s（%s）" % (dom, label))
                bad += 1
                continue
            if not re.match(r"^r\d+$", reg):
                fail(10, "登记轮格式异常 → %s（%s）" % (reg, label)); bad += 1; continue
            rn = int(reg[1:])
            if rn not in rounds:
                fail(10, "登记轮 %s 不在轮次基准内（%s）" % (reg, label)); bad += 1; continue
            if not re.fullmatch(r"\d+", rel):
                fail(10, "关联次数非数字 → %s（%s）" % (rel, label)); bad += 1; continue
            # 固化三态：未固化／已达门槛（待并入 X）／已并入（X）。「已并入」＝已并进正文，
            # 不该再留在待验表（该清出未清出）；「已达门槛」受固化豁免保护、永不到期。
            if not re.match(r"^(未固化|已达门槛（待并入 .+）|已并入（.+）)$", fix):
                fail(10, "固化格式异常 → %s（%s）" % (fix, label)); bad += 1; continue
            if fix.startswith("已并入"):
                fail(10, "固化＝已并入却仍在待验表（应清出）→ %s" % label); bad += 1; continue
            idle = cur - rn
            if int(rel) > idle:
                fail(10, "关联次数 %s > 空转 %d（%s）" % (rel, idle, label)); bad += 1; continue
            th = MECH["th"][dkey]
            if idle < th or fix.startswith("已达门槛"):
                continue                      # 未到期；或已达门槛＝固化豁免，不参与到期
            # 连原始行一起收：到期处置要先对账正文，检索词要从原文里取
            if int(rel) >= 2:
                rep.append((label, dom, reg, idle, rel, th, l))
            else:
                due.append((label, dom, reg, idle, rel, th, l))
        info.append("待验表：%d 行（表头 %d 格），结构异常 %d" % (rows, MECH["pend_cols"], bad))
        thtxt = "流程域 %d／框架域 %d／系统域 %d" % (
            MECH["th"]["流程域"], MECH["th"]["框架域"], MECH["th"]["系统域"])
        if light:
            # 轻量档不维护待验池：结构已查，到期与池量的语义不判（属完整档）
            info.append("轻量档：到期与池量不判（属完整档）；如需启用，把台账「档位」行改回「完整」")
        else:
            if due:
                fail(10, "到期 %d 行未处置（域阈值 %s；固化＝已达门槛者豁免）——机制判定该条已失效、"
                         "留着即闭环停摆：%s"
                     % (len(due), thtxt, "；".join(d[0] for d in due[:6])))
                for lb, dm, rg, idl, rl, t, rt in due[:6]:
                    info.append("   · 对账提示 %s（%s 登记%s 空转%d 阈值%d）｜%s"
                                % (lb, dm, rg, idl, t, reconcile_hint(rt, led)))
                info.append("   · 处置：已收录的记「清出（已入册）」，未收录且未固化才降级入休眠区（非删除）")
            else:
                info.append("到期（域阈值 %s）：0 行" % thtxt)
            if rep:
                fail(10, "反复不复现型 %d 行未处置（关联 ≥2 且 空转 ≥ 域阈值 且 未固化 → 降级入休眠区并标"
                         "「反复不复现」、不再唤醒；不受固化豁免保护）：%s"
                     % (len(rep), "；".join(r[0] for r in rep[:6])))
            if rows > MECH["pool_cap"]:
                warn(10, "待验池 %d 行 > %d：触发降级入休眠区（归档而非删除；本轮该域出现的行跳过）"
                     % (rows, MECH["pool_cap"]))
            info.append("池量：%d 行（上限 %d）" % (rows, MECH["pool_cap"]))

    # 投递记录对账
    if apply_xlsx is None:
        _md = _find_md_apply(led)
        if _md is not None:
            warn(10, "发现 Markdown 形态的投递台账 `%s`——规范形态是 xlsx（v3.0.1 曾短暂改为 .md，已回退）；请把已填内容转成 xlsx 后删掉该文件，否则投递序号对账不生效" % _md.name)
        info.append("投递记录对账：跳过（未找到；--apply <投递台账.xlsx> 指定）")
    else:
        # 迁移中间态（v3.0.7 补）：xlsx 正本已建、v3.0.1 的 .md 旧件没删 → 两条投递台账并存。
        # 序号锚点可能分叉，而两支各自都不报错——正是本段要拦的结构异常（原判据只在 xlsx
        # 缺席时才探 .md，并存态反而全绿）。
        _md_left = _find_md_apply(led)
        if _md_left is not None:
            fail(10, "迁移中间态：xlsx 正本 `%s` 已存在，但 Markdown 形态的旧台账 `%s` 仍在——两条投递"
                     "台账并存会让序号锚点分叉（谁都不报错）；确认内容已完整转入 xlsx 后删掉该 .md，"
                     "只留 xlsx 一份" % (apply_xlsx.name, _md_left.name))
        seqs, strange = xlsx_first_col_int(apply_xlsx)
        if not seqs and not strange:
            # 只有表头＝刚初始化、尚无投递行（2026-09-23 补：投递台账形态回 xlsx 后，
            # 新环境初态会命中这一支——初态不是异常，不能让它一建出来就带 WARN）。
            info.append("投递记录：初态（0 行，仅表头）")
        elif not seqs:
            warn(10, "投递记录 %s 读不到序号列（%d 个非数字单元格）" % (apply_xlsx.name, strange))
        else:
            mx = max(seqs)
            gaps = sorted(set(range(1, mx + 1)) - set(seqs))
            if gaps:
                fail(10, "投递记录序号不连续（缺 %s）——锚点断裂，计数失真" % gaps[:10])
            if strange:
                warn(10, "投递记录序号列有 %d 个非数字单元格（表头除外）" % strange)
            unreviewed = sorted(set(seqs) - anchor_seqs - excluded)
            info.append("投递记录：序号 1–%d（%d 行）｜锚定 %d ｜未复核轮 %d %s" % (
                mx, len(seqs), len(anchor_seqs & set(seqs)), len(unreviewed),
                ("[" + ", ".join(str(x) for x in unreviewed[:8]) + ("…" if len(unreviewed) > 8 else "") + "]") if unreviewed else ""))
    info.extend(_check_trace(led))
    info.extend(check_registry(led))
    if not light:
        info.extend(_mech_weight_hint(s, rounds))
    return info


def main():
    deny = []
    if DENY_FILE.is_file():
        for line in read_utf8(DENY_FILE).splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                deny.append(line)
    if "--deny" in sys.argv:
        deny += [x for x in sys.argv[sys.argv.index("--deny") + 1].split(",") if x]

    if not MANUAL.is_file():
        print("FAIL 找不到 %s" % MANUAL)
        return 1
    sk = read_utf8(MANUAL)

    # 文件清单与配方目录：两档都要（输出计数与「模板自证」都用）——原先在 ⑦⑧ 里算，每轮档取不到
    all_files = []
    for dp, dn, fn in os.walk(str(ROOT)):
        # `__pycache__`＝解释器字节码缓存；`.git`／`.svn`／`.hg`＝版本控制元数据。两类都不是交付物：
        # 当文本读会报「编码无法解析」，命中词表也毫无意义（git 对象是压缩二进制）。
        # 2026-09-23 实测：包目录建仓（.git 出现）后，封装体档从 FAIL 0 变 FAIL 50，全是这两类误报。
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git", ".svn", ".hg")]
        for f in fn:
            all_files.append(Path(dp) / f)
    disk = recipe_dirs()

    if FULL_MODE:
    # ①–⑨ 属「封装体档」：九段里 7 段是维护者项，每轮跑等于把成本压在维护面上
        # ① 一级章节齐全
        for cn in ["一", "二", "三", "四", "五", "六"]:
            if not re.search(r"^##\s+%s、" % cn, sk, re.M):
                fail(1, "手册缺一级章节 ## %s、" % cn)

        # ② frontmatter
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", sk, re.S)
        if not m:
            fail(2, "手册缺 frontmatter")
            fm = ""
        else:
            fm = m.group(1)
            for k in ["name", "description", "version", "updated"]:
                if not re.search(r"^%s:" % k, fm, re.M):
                    fail(2, "手册 frontmatter 缺 %s" % k)
            vm = re.search(r"^version:\s*(\S+)", fm, re.M)
            if vm:
                ver = vm.group(1)
                n = len(re.findall(re.escape(ver), sk))
                if n > 1:
                    fail(2, "版本号 %s 在手册内出现 %d 次（应只在 frontmatter 一处）" % (ver, n))
                if not re.match(r"^v\d+\.\d+", ver):
                    fail(2, "版本号格式异常：%s" % ver)

        # ③ 配方索引 ↔ 磁盘双向一致
        disk = recipe_dirs()
        idx = set(re.findall(r"^\|\s*`([a-z0-9\-]+-autofill)`\s*\|", sk, re.M))
        for name in sorted(idx - set(disk)):
            fail(3, "§4.7 索引列了 `%s`，磁盘上不存在" % name)
        for name in sorted(set(disk) - idx):
            fail(3, "磁盘上有 `%s`，§4.7 索引未收录" % name)

        # ③附一 手册正文里所有 `recipes/<名>` 指针都要落在磁盘上（2026-09-18 补）
        # 栅栏测试实证：索引表是双向查的，但**判据表**（侦察时读的那张）里的
        # `→ recipes/xxx` 指针没人查——把 webform-autofill 改成 nonexistent-fw-autofill，
        # 退出码仍是 0。侦察时拿到一个不存在的配方名＝当场走进死路，且无人发现。
        refs = set(re.findall(r"recipes/([a-z0-9\-]+)", sk))
        for name in sorted(refs - set(disk)):
            fail(3, "手册正文引用了 `recipes/%s`，磁盘上不存在" % name)

        # ③附 配方内以表格点名的随包脚本 ↔ 磁盘（＋ 占位符声明 ↔ 脚本实际）
        # 2026-09-17 补：原来只查 §4.7 索引 ↔ recipes/ 目录，配方**内部**写明的脚本清单没人查；
        # 而清单写错/脚本改名会让按配方操作的人拿到 FileNotFoundError，且任何校验器都不会报。
        for name in disk:
            sd = RECIPES / name / "scripts"
            rf = RECIPES / name / "SKILL.md"
            if not sd.is_dir() or not rf.is_file():
                continue
            files = sorted(p.name for p in sd.iterdir() if p.is_file())
            rs = read_utf8(rf)
            declared = {}
            for m in re.finditer(r"^\|\s*`([A-Za-z0-9_.\-]+\.(?:js|py))`\s*\|([^\n]*)", rs, re.M):
                declared[m.group(1)] = m.group(2)
            for fn, cells in declared.items():
                if fn not in files:
                    fail(3, "配方 `%s` 点名了 scripts/%s，磁盘上不存在" % (name, fn))
                elif fn.endswith(".js"):
                    dph = set(re.findall(r"\{\{(\w+)\}\}", cells))
                    real = set(re.findall(r"\{\{(\w+)\}\}", read_utf8(sd / fn)))
                    if dph != real:
                        fail(3, "配方 `%s` 的 scripts/%s 占位符声明 %s ≠ 脚本实际 %s"
                             % (name, fn, sorted(dph) or "—", sorted(real) or "—"))
            for fn in files:
                if fn.endswith(".js") and fn not in declared:
                    warn(3, "配方 `%s` 的 scripts/%s 未在配方内点名（文档可能漏写）" % (name, fn))

        # ④ 配方 frontmatter
        for name in disk:
            f = RECIPES / name / "SKILL.md"
            if not f.is_file():
                fail(4, "配方 `%s` 缺 SKILL.md" % name)
                continue
            s = read_utf8(f)
            mm = re.match(r"^---\s*\n(.*?)\n---\s*\n", s, re.S)
            if not mm:
                fail(4, "配方 `%s` 缺 frontmatter" % name)
                continue
            for k in ["name", "description"]:
                if not re.search(r"^%s:" % k, mm.group(1), re.M):
                    fail(4, "配方 `%s` frontmatter 缺 %s" % (name, k))
            nm = re.search(r"^name:\s*(\S+)", mm.group(1), re.M)
            if nm and nm.group(1) != name:
                fail(4, "配方 `%s` 的 frontmatter name=%s 与目录名不一致" % (name, nm.group(1)))

        # ⑤ 启动器模板
        if not BAT.is_file():
            fail(5, "缺 scripts/launch-browser.bat")
        else:
            b = read_text(BAT)
            if b is None:
                fail(5, "launch-browser.bat 既非 UTF-8 也非 GBK")
            else:
                for ph in ["__CLI__", "__BROWSER__", "__URL__", "__LOG__"]:
                    if b.count(ph) < 2:
                        warn(5, "启动器占位符 %s 出现次数 <2（可能已被替换为实值）" % ph)
                # 护栏与扩展参数只看**有效指令行**：注释（REM／::）里的同名串不算数。
                # 2026-09-17 栅栏测试：保留注释、删掉真实启动行上的参数 → 原判据仍报 OK（假绿）。
                code_lines = [l for l in b.splitlines()
                              if l.strip() and not l.strip().upper().startswith("REM")
                              and not l.strip().startswith("::")]
                code = "\n".join(code_lines)
                # 2026-09-19 加固：原判据等价于「`:NOCONFIG` 与 `exit /b 1` 两个字样出现过」，
                # 与「护栏真的拦得住」不等价——栅栏测试实测 4 种改写假绿：删掉四条跳转判断只留标签、
                # 四条全改注释、跳转目标改名、掏空分支实体（字样仍留在标签上）。
                # 改判**控制流可达**：须存在指向该标签的条件跳转指令行 ＋ 该标签行 ＋ 标签段内的 exit /b 1。
                jumps = [l for l in code_lines
                         if re.match(r"^\s*if\b.*\bgoto\s+:?NOCONFIG\b", l, re.I)]
                lab = next((i for i, l in enumerate(code_lines)
                            if re.match(r"^\s*:NOCONFIG\b", l, re.I)), None)
                if not jumps or lab is None:
                    fail(5, "启动器缺「占位符未替换即中止」护栏：须同时存在指向 `:NOCONFIG` 的条件跳转指令行"
                            "与标签行（有效指令行内；只剩字样不算）")
                else:
                    tail = []
                    for l in code_lines[lab:]:
                        if re.match(r"^\s*:\w+", l) and not re.match(r"^\s*:NOCONFIG\b", l, re.I):
                            break
                        tail.append(l)
                    if not re.search(r"\bexit\s+/b\s+1\b", "\n".join(tail), re.I):
                        fail(5, "启动器 `:NOCONFIG` 段内无 `exit /b 1`（中止后未返回失败码）")
                sets = dict(re.findall(r'set\s+"(\w+)=(__\w+__)"', code, re.I))
                guarded = set()
                for l in jumps:
                    mg = re.match(r'^\s*if\s+"%(\w+)%"\s*==\s*"(__\w+__)"', l, re.I)
                    if mg:
                        guarded.add(mg.group(1))
                miss = sorted(set(sets) - guarded)
                if miss:
                    warn(5, "启动器护栏未覆盖全部未替换占位符：%s" % "、".join(miss))
                if "--display-invisible-extension=true" not in code:
                    fail(5, "启动器缺扩展加载参数（有效指令行内未找到；缺则命令必然 60 秒超时）")

        # ⑤-2 批处理编码（2026-09-24 加固；说明见 scan_bat_non_ascii）
        # 扫的是**包内全部** .bat，不只启动器——任何一份写进非 ASCII 都会在 cmd 下炸。
        for _rel, _ln in scan_bat_non_ascii():
            fail(5, "`%s` 含非 ASCII 字符（第 %s 行）——cmd.exe 按本地 ANSI 代码页解析批处理，"
                    "非 ASCII 文本会被撕成假命令；启动器与一切 .bat 一律纯 ASCII（手册 §3.0.1）"
                    % (_rel, "、".join(_ln[:6])))

        # ⑥ 交叉引用不悬空
        heads_num = {}
        for m in re.finditer(r"^#{2,4}\s+(\d+(?:\.\d+)*)\s", sk, re.M):
            heads_num[m.group(1)] = m.start()
        bodies = {}  # 节号 -> 节内**自身**正文（到下一个同级或更高级标题，或任意子节标题）
        hs = [(m.start(), m.group(2), len(m.group(1))) for m in
              re.finditer(r"^(#{2,4})\s+(\d+(?:\.\d+)*)[^\n]*$", sk, re.M)]
        for i, (pos, num, lvl) in enumerate(hs):
            end = len(sk)
            for pos2, num2, lvl2 in hs[i + 1:]:
                # 2026-09-18 修：原判据只在下级标题 **层级 <= 本级** 时才收边，
                # 于是 §3.0 的正文把 §3.0.1–§3.0.4 四个子节全吞了进去——
                # 子节里的编号列表（升级步骤 1./2./3.）被当成「§3.0 的第 N 条」，
                # 使 §3.0.1 这类子节引用被判为"歧义"（假阳），且父节的条目核查本就该只看自身正文。
                if lvl2 <= lvl or num2.startswith(num + "."):
                    end = pos2
                    break
            bodies[num] = sk[pos:end]
        for cn in ["一", "二", "三", "四", "五", "六"]:
            if not re.search(r"^##\s+%s、" % cn, sk, re.M):
                fail(6, "引用了 §%s，但手册无该章" % cn)
        for ref in sorted(set(re.findall(r"§(\d+(?:\.\d+)+|\d+)", sk)),
                          key=lambda x: [int(y) for y in x.split(".")]):
            if ref in heads_num:
                continue
            parts = ref.split(".")
            if len(parts) == 2:
                fail(6, "引用 §%s，手册无此节" % ref)
            else:
                parent = ".".join(parts[:-1])
                item = parts[-1]
                if parent not in bodies:
                    fail(6, "引用 §%s，但其父节 §%s 不存在" % (ref, parent))
                elif not re.search(r"^\s*%s\.\s" % re.escape(item), bodies[parent], re.M):
                    fail(6, "引用 §%s，但 §%s 内无第 %s 条" % (ref, parent, item))

        # ⑥附 配方内的 § 引用（原来只扫手册正文；配方引用悬空同样会把人指错地方）
        for name in disk:
            rf = RECIPES / name / "SKILL.md"
            if not rf.is_file():
                continue
            rs = read_utf8(rf)
            own, _ = doc_heads(rs)
            for ref in sorted(set(re.findall(r"§(\d+(?:\.\d+)+|\d+)", rs)),
                              key=lambda x: [int(y) for y in x.split(".")]):
                if ref in own or ref in heads_num:
                    continue
                if "." in ref:
                    parent, item = ".".join(ref.split(".")[:-1]), ref.split(".")[-1]
                    if parent not in bodies:
                        fail(6, "配方 `%s` 引用 §%s，手册无父节 §%s" % (name, ref, parent))
                    elif not re.search(r"^\s*%s\.\s" % re.escape(item), bodies[parent], re.M):
                        fail(6, "配方 `%s` 引用 §%s，但 §%s 内无第 %s 条" % (name, ref, parent, item))
                elif own:
                    warn(6, "配方 `%s` 里的单数字引用 §%s 在配方内无对应节（若指手册章，请写中文数字如 §三）"
                         % (name, ref))

        # ⑥附二 三位编号的语义歧义（2026-09-18 补）
        # 手册实际存在两套写法：`§2.1.5`＝§2.1 内第 5 条（无同名标题），`§3.7.5`＝§3.7 内第 5 条。
        # 校验器按后者放行是对的，但若某父节**同时**有 `### X.Y.N` 子节标题和 `N.` 编号条目，
        # 同一串引用就真歧义——一半人读成子节、一半人读成条目。仅此情形报出。
        for ref in sorted(set(re.findall(r"§(\d+\.\d+\.\d+)", sk))):
            if ref not in heads_num:
                continue  # 无同名标题 → 只能是「父节内第 N 条」，无歧义
            parent, item = ".".join(ref.split(".")[:-1]), ref.split(".")[-1]
            if parent in bodies and re.search(r"^\s*%s\.\s" % re.escape(item), bodies[parent], re.M):
                warn(6, "§%s 既有同名子节标题，父节 §%s 里又有第 %s 条编号条目——引用歧义，"
                     "建议引用改写「§%s 第 %s 条」" % (ref, parent, item, parent, item))

        # ⑥附三 根级文档的 § 引用（2026-09-22 补）：⑥ 原先只扫手册正文与配方，根级上手文档
        # （`README.md`）里「§1.1／§2.1／§6.2」这类指向手册的引用无人管——手册一旦改节号，
        # 文档就静默指错地方，而两侧校验器都不报（本文档 2026-09-22 新增时留下的缺口）。
        # 范围只取**包根**的 `.md`：`recipes/*/SKILL.md` 与 `templates/CODEBUDDY.md` 不在此列——
        # 模板里的 § 号指**生成到使用者的项目级要求文件**（及其 §〇），拿本手册的标题去比对必是假阳。
        # 只校 `§X.Y` 及更长的编号；单独的 `§3` 不校（章号在手册里用中文数字，无法判定指节还是指章），
        # `§〇.x` 因正则只认阿拉伯数字而天然不参与。
        for rp in sorted(ROOT.glob("*.md")):
            if rp.resolve() == MANUAL.resolve():
                continue  # 手册正文已在上文查过
            rs = read_text(rp)
            if rs is None:
                continue
            for ref in sorted(set(re.findall(r"§(\d+(?:\.\d+)+)", rs)),
                              key=lambda x: [int(y) for y in x.split(".")]):
                if ref in heads_num:
                    continue
                parent, item = ".".join(ref.split(".")[:-1]), ref.split(".")[-1]
                if parent not in bodies:
                    fail(6, "根级文档 `%s` 引用 §%s，手册无父节 §%s" % (rp.name, ref, parent))
                elif not re.search(r"^\s*%s\.\s" % re.escape(item), bodies[parent], re.M):
                    fail(6, "根级文档 `%s` 引用 §%s，但 §%s 内无第 %s 条" % (rp.name, ref, parent, item))

        # ⑦⑧ 全包扫描（all_files 与配方目录已在 main 开头算好，两档共用）
        for p in sorted(all_files):
            rel = p.relative_to(ROOT).as_posix()
            t = read_text(p)
            if t is None:
                fail(9, "%s 编码无法解析" % rel)
                continue
            if "\ufffd" in t:
                fail(9, "%s 含替换字符 U+FFFD（编码损坏）" % rel)
            if p.resolve() == SELF:
                continue  # 本脚本自身必然含下列模式字面量，不参与 ⑦⑧
            # 黑名单文件自身就是「被扫描词」的字面量来源，扫它必然自命中——与 SELF 同理排除。
            # （2026-09-23 实测：按手册 §6.3 末自建 scripts/verify-deny.txt 后，校验器立刻报
            #  「verify-deny.txt 命中黑名单词」并 FAIL，使这条文档化的工作流一建即坏。）
            if p.resolve() == DENY_FILE.resolve():
                continue
            for k in deny:
                if k in t:
                    fail(7, "%s 命中黑名单词「%s」" % (rel, k))
            if re.search(r"(?<!\d)1[3-9]\d{9}(?!\d)", t):
                fail(7, "%s 疑似手机号" % rel)
            if re.search(r"(?<!\d)\d{17}[\dXx](?!\d)", t):
                fail(7, "%s 疑似身份证号" % rel)
            if re.search(r"[\w.\-]+@[\w\-]+\.[A-Za-z]{2,}", t):
                fail(7, "%s 疑似邮箱" % rel)
            # 成绩／证书类**具体值**（2026-09-22 补）：配方是手法文档，示例一律用占位符，
            # 出现「599分」这种真实成绩就是把使用者数据写进了包（实测漏过一处：证书示例把
            # 使用者的六级成绩原样写进命令行）。判据取**形状**不取具体值，故不携带个人数据。
            for rx, what in ((r"(?<![\d.])\d{3}\s*分", "三位数成绩"),
                             (r"(?:雅思|托福|IELTS|TOEFL|六级|四级|CET[-\s]?[46]|GPA)\s*[（(]?[^）)\n]{0,6}[）)]?\s*[=＝:：]\s*\d", "考试名后直接跟分数")):
                m = re.search(rx, t)
                if m:
                    fail(7, "%s 含%s具体值（%s）——示例改用占位符，勿把使用者数据写进包"
                         % (rel, what, m.group(0).strip()))
            # 双端术语（2026-09-22 补）：本包面向**单环境接收方**——部署者只有一处工作环境，没有
            # "第二处"。源环境的措辞若随同步流回包内，读的人会以为哪里配漏了（实测：生成的
            # `CODEBUDDY.md` 里这类词共 22 处、全无定义，还带一条「台账两侧共同追加」的双写者规则，
            # 而接收方只有一个写入方）。判据取**词形**：`脚本端`／`文本端`／`两端对齐`／`相对端`
            # 这类正常用词已前视排除（否则「脚本端 vs 页面端」一写就误报）；
            # 手册自身描述本判据时也不得写出这些词（写出来自己就命中）。
            # 2026-09-23 补：同类词形的前约束须**一致**——原先只给第一个词加了前约束、末一个词漏加，
            # 于是常见词「版本侧」被误报（实测：新写的发布说明一次命中）。补齐前约束。
            # 2026-09-23 再补：上一句只补了「版」，末词的排除集仍与首词不一致——本轮新增的
            # 「脚本侧」（与「通道侧」对仗的措辞）在手册命中 6 处、使用说明 1 处。
            # 改为与首词同一排除集；此后两个分支的排除集永远同步。
            m = re.search(r"(?<![文脚样副版])本端|两端(?!对齐)|跨端|别端|他端|(?<!相)对端|(?<![文脚样副版])本侧", t)
            if m:
                fail(7, "%s 含双端术语「%s」——本包是单环境成品，改用「本项目」／「源环境」／「其他通道」"
                     % (rel, m.group(0)))
            # 盘符绝对路径：前视排除 http:// 这类协议串里的 "p:/"（否则每个 URL 都误报）。
            # 2026-09-17 补：斜杠开头的泛化占位符（如 `/path/to/x.py`、`/usr/bin`）不算环境专属路径，
            # 只有带真实用户名或带盘符的**具体**路径才算。判据区分靠"是否落在占位符包里"——
            # 占位符包 = 含 `path/to`、`<...>`、`...`、`示例`、`你的`、`目录` 等字样的写法。
            for m in re.finditer(r"(?<![A-Za-z:])[A-Za-z]:[\\/][^\s`\"')\]|,;]*", t):
                if m.group(0).rstrip("\\/") == m.group(0)[:2]:
                    continue
                fail(8, "%s 含本机盘符绝对路径（%s）" % (rel, m.group(0)))
            for m in re.finditer(r"/(?:Users|home)/[^/\s]+/[^\s`\"')\]|,;]*", t):
                fail(8, "%s 含本机家目录绝对路径（%s）" % (rel, m.group(0)))
            for m in re.finditer(r"/(?:[A-Za-z0-9_.\-]+/){2,}[A-Za-z0-9_.\-]+\.[A-Za-z0-9]+", t):
                seg = m.group(0)
                # 排除：泛化占位符、系统目录通用写法、包内配方相对引用、URL 路径
                if any(k in seg for k in ("path/to", "/**/", "<", ">", "示例", "你的", "目录")):
                    continue
                if re.search(r"/(usr|etc|opt|var|tmp|bin|srv|mnt|root)/", seg):
                    continue
                # 形如 /a-autofill/SKILL.md 是包内配方间的相对引用，不是绝对路径
                if re.search(r"^/[a-z0-9\-]*(autofill|recipes)/", seg, re.I):
                    continue
                # URL 路径：紧跟在域名（xx.yy/...）或协议（//...）之后；或在同一反引号段内出现域名
                pre = t[max(0, m.start() - 40):m.start()]
                if re.search(r"(?:[A-Za-z0-9\-]+\.)+[A-Za-z]{2,}/[^\s]*$", pre) or pre.endswith("/"):
                    continue
                j = t.rfind("`", 0, m.start())
                k = t.find("`", m.start())
                if j != -1 and k != -1 and re.search(r"(?:[A-Za-z0-9\-]+\.)+[A-Za-z]{2,}", t[j:k]):
                    continue
                warn(8, "%s 含斜杠绝对路径写法（%s）；若非泛化占位符请改为 `<目录>/...`" % (rel, seg))
            if p.suffix.lower() == ".md":
                check_md_tables(t, rel)

        # ⑨ 配方状态声明
        for name in disk:
            f = RECIPES / name / "SKILL.md"
            if not f.is_file():
                continue
            s = read_utf8(f)
            if ("未在本通道跑过的只有三种动作" not in s) and ("本通道已复现的动作" not in s):
                warn(9, "配方 `%s` 缺通道状态声明（未复现三动作 / 已复现）" % name)

    # ⑨附 初始化能力自证（2026-09-20 补）
    # 为什么有这段：只验证「封装体自洽」时，「照 §1.5 建的新环境是不是绿的」无人验——
    # 与 §5.4 记过的模板事故同类（模板与校验器判据不符，照建的新环境必红而无人发现）。
    INIT = ROOT / "scripts" / "init-workspace.py"
    TPL = ROOT / "templates" / "CODEBUDDY.md"
    if not INIT.is_file():
        fail(9, "缺 scripts/init-workspace.py（§1.5 首次部署初始化脚本）")
    else:
        it = read_utf8(INIT)
        # 只读封装体：生成物不得写回包自身（否则「整份复制」这个前提被破坏）
        for pat, why in [
            (r"write_if_absent\(\s*str\(ROOT\)", "把生成物写回封装体自身"),
            (r"open\([^)]*ROOT[^)]*,\s*['\"]w", "直接以写模式打开封装体内路径"),
            (r"MANUAL\.write_text|MANUAL\.open\(\s*['\"]w", "改写手册自身"),
        ]:
            if re.search(pat, it):
                fail(9, "init-workspace.py 存在「%s」的写法——初始化脚本只读封装体、只写使用者指定路径" % why)
        if "def build_requirements" not in it:
            warn(9, "init-workspace.py 未见 build_requirements（生成项目级要求文件的入口）")
        if "extract_block" not in it:
            warn(9, "init-workspace.py 未见 extract_block（应从 §5.1 模板块就地抽取，不另存副本）")

    if not TPL.is_file():
        fail(9, "缺 templates/CODEBUDDY.md（项目级要求文件模板）")
    elif INIT.is_file():
        tt = read_utf8(TPL)
        tpl_ph = set(re.findall(r"__[A-Z][A-Z0-9_]*__", tt))
        # 脚本替换表：cfg[...] 取值 + 显式常量，统一按「脚本里出现过的 __XXX__ 字面量」收集
        it = read_utf8(INIT)
        # 替换表里的键写成 t.replace("__X__", ...)，取第一个参数
        script_ph = set(re.findall(r'\.replace\(\s*"(__[A-Z][A-Z0-9_]*__)"', it))
        script_ph |= set(re.findall(r'\.replace\(\s*\'(__[A-Z][A-Z0-9_]*__)\'', it))
        # ALLOW_EMPTY 白名单里的也算「脚本认识」
        for w in re.findall(r'ALLOW_EMPTY\s*=\s*\{([^}]*)\}', it):
            script_ph |= set(re.findall(r"(__[A-Z][A-Z0-9_]*__)", w))
        orphan_tpl = sorted(tpl_ph - script_ph)
        orphan_script = sorted(script_ph - tpl_ph)
        if orphan_tpl:
            fail(9, "templates/CODEBUDDY.md 的占位符 %s 在 init-workspace.py 里没有替换——生成物会残留 __XXX__"
                 % "、".join(orphan_tpl))
        if orphan_script:
            warn(9, "init-workspace.py 替换的 %s 在 templates/CODEBUDDY.md 里不存在（替换静默失效？）"
                 % "、".join(orphan_script))
        # 模板不得含个人数据（与 ⑦ 同理，模板会被生成进新环境）
        if re.search(r"(?<!\d)1[3-9]\d{9}(?!\d)", tt) or re.search(r"[\w.\-]+@[\w\-]+\.[A-Za-z]{2,}", tt):
            fail(9, "templates/CODEBUDDY.md 疑似含个人数据（手机号／邮箱）")
        for m in re.finditer(r"(?<![A-Za-z:])[A-Za-z]:[\\/][^\s`\"')\]|,;]*", tt):
            fail(9, "templates/CODEBUDDY.md 含本机盘符绝对路径（%s）" % m.group(0))

    # ⑨附三 模板机制数值 ↔ 校验判据一致（2026-09-22 补）
    # 为什么有这段：机制数值原先在**两处各写一份**——§5.1 模板写「待验表 >20 行」、
    # 第十段却判「>30」，两侧都不报、全绿而实分叉（与 §5.4 记过的模板事故同类）。
    # 改判据：数值集中到 MECH 一处，模板文本必须与它一致，否则 FAIL。
    _head = " | ".join(MECH["pend_head"])
    for _nm, _p in [("templates/CODEBUDDY.md", TPL), ("SKILL.md（§5.1 模板）", MANUAL)]:
        _t = read_utf8(_p)
        if _head not in _t:
            fail(9, "%s 的待验表列定义与校验判据不一致（应含「%s」）" % (_nm, _head))
        if (">%d 行" % MECH["pool_cap"]) not in _t:
            fail(9, "%s 的待验池上限与校验判据不一致（应含「>%d 行」）" % (_nm, MECH["pool_cap"]))
        for _d, _n in MECH["th"].items():
            # 语序两种都认——模板写「流程域（说明）4」，§5.1 的计数口径写「流程域 4（说明）」，
            # 判据不该把一个纯排版差异当成分叉（首轮实测据此报假 FAIL）。
            if not re.search(re.escape(_d) + "(?:（[^）]*）)?\\s*\\**\\s*%d" % _n, _t):
                fail(9, "%s 的域阈值与校验判据不一致（应含「%s（…）%d」或「%s %d（…）」）"
                     % (_nm, _d, _n, _d, _n))

    # ⑨附四 模板内脚本引用可解析（2026-09-22 补）
    # 为什么有这段：模板会生成进新环境、成为**项目级要求文件**——它里面引用的脚本必须在包内真的存在。
    # 实测缺口：模板两处要求「每次收尾跑 <环境>/.workbuddy/skills/scripts/verify-ledger.ps1」，而该文件
    # 包内不提供、init 不生成、体检也不查——照它部署的新环境拿到的是指向空气的收尾校验指令，
    # 且不知道包内 scripts/verify-package.py 才是替代品（源环境未暴露，只因源环境自己就有那支脚本）。
    if TPL.is_file():
        _tt2 = read_utf8(TPL)
        _refs = sorted(set(re.findall(r"scripts/([A-Za-z0-9_.\-]+)", _tt2)))
        if not _refs:
            warn(9, "templates/CODEBUDDY.md 未引用任何包内脚本——收尾校验指令指向何处无从校验")
        for _r in _refs:
            if not (ROOT / "scripts" / _r).is_file():
                fail(9, "templates/CODEBUDDY.md 引用的 scripts/%s 在包内不存在——生成的要求文件会指向空气" % _r)

    # ⑩ 运行态：台账（可选，只读）
    led = find_ledger()
    if led is None:
        ledger_info = ["跳过（未配置台账；用 --ledger <路径> 或环境变量 VERIFY_LEDGER 指定）"]
    else:
        ledger_info = check_ledger(led, find_apply(led))

    # 输出
    print("=" * 60)
    print("机械校验（%s）—— %s" % (
        "封装体档·九段＋运行态" if FULL_MODE else "每轮档·运行态＋模板自证", ROOT))
    print("=" * 60)
    print("实物：%d 文件" % len(all_files))
    print("配方：%d 份 %s" % (len(disk), disk))
    if not FULL_MODE:
        print("提示：本档不跑九段（维护者项）。改过手册／配方／脚本／模板后请加 --package 再跑一次。")
    segs = list(range(1, CHECKS + 1)) if FULL_MODE else [9, 10]
    for i in segs:
        f = [x for x in fails if x.startswith("[%d]" % i)]
        w = [x for x in warns if x.startswith("[%d]" % i)]
        state = "FAIL" if f else ("WARN" if w else "OK  ")
        extra = "（运行态，可选）" if i == 10 else ""
        print("  %-4s 第 %d 段%s" % (state, i, extra))
        if i == 10:
            for line in ledger_info:
                print("       · " + line)
        for x in f + w:
            print("       " + x)
    print("-" * 60)
    print("FAIL %d 项 / WARN %d 项" % (len(fails), len(warns)))
    print("退出码：%d" % (1 if fails else 0))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
