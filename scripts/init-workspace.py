#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""封装体部署初始化（首次使用跑一次；已初始化的环境跑它只做体检，不改文件）。

用法：
  python scripts/init-workspace.py --check                # 只体检，不写任何文件
  python scripts/init-workspace.py --plan                 # 打印将要生成/引导的清单
  python scripts/init-workspace.py --clean-tmp --project "<项目根目录>"
                                                          # 清空 .workbuddy/tmp/（每轮收尾跑）
  python scripts/init-workspace.py --yes \\
      --project "<项目根目录>" \\
      --ledger  "<台账文件路径>" \\
      --changelog "<变更档案路径>"

退出码：0 = 体检通过或已成功生成；1 = 有阻塞项（缺参数／占位符未替换／目标已存在且非空）。

设计纪律（照搬 scripts/launch-browser.bat）：
  1. **占位符未替换即中止**，绝不静默产出一份带 `__XXX__` 的坏文件；
  2. **不覆盖已有文件**——目的文件已存在且非空时报 FAIL 并跳过，要重建须显式 --force；
  3. **不编造个人事实**——数据层（简历事实、字段取值）含使用者真实信息，本脚本**只建骨架并引导使用者填**，
     绝不生成占位内容冒充数据。
  4. **数据层只生成一份**（2026-09-23 补）——原先产出「主数据 ＋ 字段映射」两份 JSON 骨架，实测与使用者
     既有的 .md 数据层并存、构成**双真源**（两份不一致时两边都不会报错）。现改为**一份 Markdown**，
     同时承载事实／定稿文本与字段取值。
  5. **投递台账单列生成**（2026-09-23 补）——它是使用者唯一会主动翻的账，原先只当数据层的附属，
     实测被整个漏掉、直到使用者发问才发现。模板块在手册附录 C，脚本就地抽取。
  6. **信息目录与三类运行目录**（2026-09-23 补）——**数据层所在目录即信息目录**（默认 `<项目根>/info/`）：
     数据层、投递台账、其余信息文件与附件原件同置该目录，**项目根只留要求文件与启动器**；
     运行产物按性质分三处——`.workbuddy/tmp/`（临时，**每轮收尾清空**）、`.workbuddy/evidence/`（过程证据，保留）、
     `.workbuddy/backup/`（改前留档，保留）。`--clean-tmp` 只清 tmp，绝不触碰后两者。

本脚本只读封装体、只写使用者指定的路径，不改封装体自身。
"""
import io
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "SKILL.md"
TEMPLATES = ROOT / "templates"
SELF = Path(__file__).resolve()

# 生成物里允许残留的占位符白名单：这些是**给使用者填的**（如禁止触碰清单为空），
# 允许原样留空；其余 __XXX__ 一律视为"忘了替换"，直接中止。
ALLOW_EMPTY = {"__FORBIDDEN_PATHS__"}

fails, warns, done = [], [], []


def fail(msg):
    fails.append(msg)


def warn(msg):
    warns.append(msg)


def ok(msg):
    done.append(msg)


def read_utf8(p):
    return io.open(str(p), encoding="utf-8").read()


def write_if_absent(path, text, force=False):
    """不覆盖已有内容；返回 True 表示已写入。"""
    p = Path(path)
    if p.exists() and p.stat().st_size > 0 and not force:
        fail("目标已存在且非空，未覆盖：%s（要重建请加 --force）" % p)
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    io.open(str(p), "w", encoding="utf-8", newline="\n").write(text)
    ok("已生成 %s（%d B）" % (p, len(text.encode("utf-8"))))
    return True


def write_apply_xlsx(path, force=False):
    """生成投递台账的 xlsx 骨架（只有表头行，不依赖 Excel／openpyxl／第三方库）。

    投递台账的规范形态是**单个 xlsx**（手册附录 C／§2.1.5）：序号列是两侧计数与核查的
    公共锚点，xlsx 的单元格类型稳定，且校验器第十段直读它的 A 列做序号连续性对账。
    二进制无法用文本模板块承载，故由本函数内建（文本模板只从手册附录 A／B 抽取）。
    返回 True 表示已写入。
    """
    p = Path(path)
    if p.exists() and p.stat().st_size > 0 and not force:
        fail("目标已存在且非空，未覆盖：%s（要重建请加 --force）" % p)
        return False
    header = ["序号", "投递日期", "公司", "岗位", "投递渠道", "状态", "备注"]
    cells = "".join(
        '<c r="%s1" t="inlineStr"><is><t>%s</t></is></c>' % (chr(ord("A") + i), h)
        for i, h in enumerate(header))
    parts = {
        "[Content_Types].xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>",
        "_rels/.rels":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        "xl/workbook.xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="投递台账" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>",
        "xl/_rels/workbook.xml.rels":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        "xl/worksheets/sheet1.xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetData><row r="1">' + cells + "</row></sheetData></worksheet>",
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        import zipfile
        with zipfile.ZipFile(str(p), "w", zipfile.ZIP_DEFLATED) as z:
            for name in ("[Content_Types].xml", "_rels/.rels", "xl/workbook.xml",
                         "xl/_rels/workbook.xml.rels", "xl/worksheets/sheet1.xml"):
                z.writestr(name, parts[name])
    except (OSError, zipfile.BadZipFile) as e:
        fail("写投递台账失败 %s：%s" % (p, e))
        return False
    ok("已生成 %s（xlsx 表头行，%d B）" % (p, p.stat().st_size))
    return True


def extract_block(manual_text, header_line):
    """从手册里抽取以 header_line 开头、紧随其后的第一个 ```markdown 代码块。

    模板只留一处真源（手册 §5.1）——不另存副本，避免"手册改了、templates/ 没同步"这类漂移。
    """
    i = manual_text.find(header_line)
    if i < 0:
        return None
    j = manual_text.find("```markdown", i)
    if j < 0:
        return None
    k = manual_text.find("\n```", j)
    if k < 0:
        return None
    return manual_text[j + len("```markdown"):k].lstrip("\n")


def detect_user_rules():
    """探测用户级要求文件的位置（§1.1 配置项 2）。

    原先写死 `~/.workbuddy/rules/`——实测该目录在目标机不存在，生成的要求文件里「效力顺序②」
    于是指向空气，还被误读成"配置漏填"。改为按常见约定逐个探测，全不存在时给出**明确说明**，
    而不是留一个看着像配置漏填的路径。
    """
    home = Path.home()
    for label, p in [
        ("~/.codebuddy/rules/", home / ".codebuddy" / "rules"),
        ("~/.workbuddy/rules/", home / ".workbuddy" / "rules"),
        ("~/.workbuddy/MEMORY.md", home / ".workbuddy" / "MEMORY.md"),
        ("~/.codebuddy/CODEBUDDY.md", home / ".codebuddy" / "CODEBUDDY.md"),
    ]:
        if p.exists():
            return label
    return "无（本机未见用户级要求文件）"


def clean_tmp(project_dir):
    """清空 `<项目根>/.workbuddy/tmp/` 的直接子项（每轮收尾跑一次）。

    只作用于 tmp/：`evidence/`（过程证据）与 `backup/`（改前留档）**绝不触碰**——
    它们是"要留的"，误清会让回滚与追溯失去凭据。清理前先印清单。
    """
    pd = Path(project_dir)
    if not pd.is_dir():
        # 项目根不存在＝路径多半写错了。这里必须报错：静默回「没有临时产物」会让人
        # 以为已经清完——与 §1.5「缺了不报错」是同一种失效（2026-09-23 实测）。
        print("=" * 64)
        print("临时产物清理 —— %s" % (pd / ".workbuddy" / "tmp"))
        print("=" * 64)
        print("FAIL 项目根不存在：%s（--project 指向的目录必须是已存在的项目根）" % pd)
        print("退出码：1")
        return 1
    tmp = pd / ".workbuddy" / "tmp"
    print("=" * 64)
    print("临时产物清理 —— %s" % tmp)
    print("=" * 64)
    if not tmp.is_dir():
        print("  未建 tmp/（本项目还没有临时产物）")
    else:
        items = sorted(tmp.iterdir(), key=lambda p: p.name)
        if not items:
            print("  已空，无需清理")
        total = 0
        for p in items:
            if p.is_dir() and not p.is_symlink():
                sz = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                print("  DEL  %s/（%d B）" % (p.name, sz))
                shutil.rmtree(str(p), ignore_errors=True)
            else:
                try:
                    sz = p.stat().st_size
                except OSError:
                    sz = 0
                print("  DEL  %s（%d B）" % (p.name, sz))
                try:
                    p.unlink()
                except OSError:
                    pass
            total += sz
        print("  共清理 %d 项 / %d B" % (len(items), total))
    for keep in ("evidence", "backup"):
        d = pd / ".workbuddy" / keep
        n = len([f for f in d.rglob("*") if f.is_file()]) if d.is_dir() else 0
        print("  KEEP .workbuddy/%s/（保留，%d 个文件）" % (keep, n))
    print("-" * 64)
    print("退出码：0")
    return 0


def guess_paths(project_dir):
    """按 §1.1 配置表的常见形态猜一组默认路径，供 --plan 展示。"""
    pd = Path(project_dir)
    return {
        "project_requirements": str(pd / "CODEBUDDY.md"),
        "info_dir": str(pd / "info"),
        "data_dir": str(pd / "info"),
        "data_file": str(pd / "info" / "简历信息库.md"),
        "delivery_ledger": str(pd / "info" / "投递台账.xlsx"),
        "ledger": str(pd / ".workbuddy" / "skills" / "EXPERIENCE-LEDGER.md"),
        "changelog": str(pd / ".workbuddy" / "skills" / "EXPERIENCE-CHANGELOG.md"),
        "channel_file": str(pd / ".workbuddy" / "skills" / "CHANNEL-qqbrowser.md"),
        "skills_dir": str(pd / ".workbuddy" / "skills"),
        "recipes_dir": str(ROOT / "recipes"),
        "user_rules_dir": detect_user_rules(),
    }


def _norm(v):
    """统一成正斜杠——生成的要求文件是给人读的，两种分隔符混用会被当成"哪里配错了"。

    非路径取值（如"无（本机未见用户级要求文件）"）原样返回。
    """
    s = str(v)
    if not s or s.startswith("无（"):
        return s
    return s.replace(chr(92), "/")


def build_requirements(cfg):
    """把 templates/CODEBUDDY.md 的占位符换成实值。"""
    c = dict(cfg)
    for _k in ("project_dir", "info_dir", "data_file", "delivery_ledger", "ledger", "changelog",
               "channel_file", "skills_dir", "recipes_dir"):
        if _k in c:
            c[_k] = _norm(c[_k])
    cfg = c
    tpl = TEMPLATES / "CODEBUDDY.md"
    if not tpl.is_file():
        fail("缺 templates/CODEBUDDY.md，无法生成项目级要求文件")
        return None
    t = read_utf8(tpl)
    t = t.replace("__PROJECT_DIR__", cfg["project_dir"])
    t = t.replace("__PACKAGE_NAME__", "qqbrowser-resume-fill")
    t = t.replace("__PACKAGE_VERSION__", cfg["version"])
    t = t.replace("__GENERATED_AT__", cfg["now"])
    t = t.replace("__USER_RULES_DIR__", cfg["user_rules_dir"])
    t = t.replace("__CHANNEL_FILE__", cfg["channel_file"])
    t = t.replace("__RECIPES_DIR__", cfg["recipes_dir"])
    t = t.replace("__PACKAGE_DIR__", _norm(ROOT))
    t = t.replace("__INFO_DIR__", cfg["info_dir"])
    t = t.replace("__DATA_FILE__", cfg["data_file"])
    t = t.replace("__DELIVERY_LEDGER__", cfg["delivery_ledger"])
    t = t.replace("__SKILLS_DIR__", cfg["skills_dir"])
    t = t.replace("__LEDGER_FILE__", cfg["ledger"])
    t = t.replace("__CHANGELOG_FILE__", cfg["changelog"])
    t = t.replace("__FORBIDDEN_PATHS__", cfg.get("forbidden") or "无（按目标边界补充）")
    t = t.replace("__MAX_BYTES__", cfg["max_bytes"])

    # 占位符残留检查：忘了替换就中止，不产出带 __XXX__ 的坏文件。
    leftover = [x for x in set(re.findall(r"__[A-Z][A-Z0-9_]*__", t)) if x not in ALLOW_EMPTY]
    if leftover:
        fail("项目级要求文件模板仍有未替换占位符：%s（请检查 templates/CODEBUDDY.md 与脚本的替换表是否一致）"
             % "、".join(sorted(leftover)))
        return None
    return t


def data_skeleton(cfg):
    """数据层骨架：**只建结构、不填内容**，且**只生成一份**（2026-09-23 改）。

    简历事实与字段取值属使用者个人数据，脚本无从生成——这里给出一份 Markdown 骨架，
    同时承载「主数据」与「字段取值」两种角色。原先拆成两份 JSON，实测与使用者既有的
    .md 数据层并存、构成双真源，而两份不一致时**两边都不会报错**。
    """
    return """# 简历信息库（数据层 · 单文件真源）

> **本文件是取数的唯一真源**——快照、记忆、上一轮读数、页面现状一律不算数（手册 §1.1 配置项 4）。
> 本文件由封装体初始化脚本生成，**只搭结构、不填内容**：所有取值一律留空，**须使用者逐项填写**。
> **一个文件兼两职**：简历事实与定稿文本 ＋ 各招聘系统字段取值、附件与照片路径、问卷类取值。
> **不要拆成两份**——拆开即双真源，而两份不一致时两边都不会报错。
> **只存数据本身、不存版本变更历史**：changelog／version／更新记录类元信息一律不写入本文件；
> 填写与投递过程只进投递台账。
> **本文件所在目录即信息目录**：投递台账、其余信息文件与附件原件（简历 PDF／证件照）同置该目录；
> 项目根只留项目级要求文件与浏览器启动器，信息文件不得散落在根目录。

## 一、基本信息

| 字段 | 取值 |
|---|---|
| 姓名 |  |
| 性别 |  |
| 出生日期 |  |
| 民族 |  |
| 政治面貌 |  |
| 籍贯 |  |
| 户籍所在地 |  |
| 证件类型／号码 |  |

## 二、联系方式

| 字段 | 取值 |
|---|---|
| 手机 |  |
| 邮箱 |  |
| 通讯地址 |  |
| 紧急联系人／电话 |  |

## 三、教育背景

| 起止年月 | 学校 | 学院／系 | 专业 | 学历 | 学位 | GPA／排名 | 是否最高学历 |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

## 四、实习经历

| 起止年月 | 公司全称 | 部门 | 职位 | 工作描述（编号分行） | 使用技能 |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## 五、校园工作经历

| 起止年月 | 组织 | 职务 | 描述 |
|---|---|---|---|
|  |  |  |  |

## 六、项目经历

| 起止年月 | 项目名称 | 角色 | 描述 |
|---|---|---|---|
|  |  |  |  |

## 七、荣誉奖项

| 时间 | 奖项名称 | 级别 | 备注 |
|---|---|---|---|
|  |  |  |  |

## 八、技能与证书

| 类别 | 名称 | 水平／成绩 | 取得时间 |
|---|---|---|---|
|  |  |  |  |

## 九、语言能力

| 语种 | 读／写 | 听／说 | 考试与成绩 |
|---|---|---|---|
|  |  |  |  |

## 十、自我评价与求职意向

- 自我评价（定稿文本；若按表单字数上限备多版，各版都写在这里并标字数）：
- 求职意向（岗位／城市／是否服从调剂）：

## 十一、成绩明细

（核心课程与成绩；口径与使用规则一并写在这里）

## 十二、填表口径与附件路径

- 附件与照片的**绝对路径**（简历、证件照、成绩单、获奖证明……）：
- 各系统专属口径（某字段该写成什么样）：

## 十三、待补事项

（库内暂无、需使用者确认的数据；确认后回填上面各节）

## 字段取值的写法约定

- 取值直接写在各节表格的「取值」列。
- 需要按招聘系统区分写法时，在该节下另起一条「〈系统名〉：……」，**不要新建文件**。
"""


def main():
    argv = sys.argv[1:]
    mode_check = "--check" in argv
    mode_plan = "--plan" in argv
    force = "--force" in argv
    mode_clean = "--clean-tmp" in argv

    def opt(name, default=None):
        if name in argv:
            i = argv.index(name)
            if i + 1 < len(argv):
                return argv[i + 1]
        return default

    manual = read_utf8(MANUAL) if MANUAL.is_file() else ""
    if not manual:
        print("FAIL 找不到 %s" % MANUAL)
        return 1
    vm = re.search(r"^version:\s*(\S+)", manual, re.M)
    version = vm.group(1) if vm else "v?"
    mb = re.search(r"上限\s*([\d,]+)\s*B", manual)
    max_bytes = mb.group(1) if mb else "40,000"

    project_dir = opt("--project")
    if mode_plan and not project_dir:
        project_dir = os.getcwd()
    if not (mode_check or mode_plan) and not project_dir:
        print("FAIL 缺 --project <项目根目录>（或用 --check／--plan 先看清单）")
        return 1

    cfg = guess_paths(project_dir or os.getcwd())
    cfg["project_dir"] = project_dir or os.getcwd()

    if mode_clean:
        return clean_tmp(cfg["project_dir"])
    cfg["ledger"] = opt("--ledger", cfg["ledger"])
    cfg["changelog"] = opt("--changelog", cfg["changelog"])
    if "--data-dir" in argv:
        _d = opt("--data-dir")
        cfg["data_dir"] = _d
        cfg["info_dir"] = _d
        cfg["data_file"] = os.path.join(_d, "简历信息库.md")
        cfg["delivery_ledger"] = os.path.join(_d, "投递台账.xlsx")
    cfg["data_file"] = opt("--data-file", cfg["data_file"])
    cfg["delivery_ledger"] = opt("--delivery-ledger", cfg["delivery_ledger"])
    # **信息目录＝数据层所在目录**（不另设配置项）：数据层、投递台账、附件原件同置一处，
    # 项目根只留要求文件与启动器。可用 --info-dir 显式覆盖。
    cfg["info_dir"] = opt("--info-dir",
                          os.path.dirname(cfg["data_file"]) or cfg["data_dir"])
    cfg["channel_file"] = opt("--channel", cfg["channel_file"])
    cfg["recipes_dir"] = opt("--recipes-dir", cfg["recipes_dir"])
    cfg["user_rules_dir"] = opt("--user-rules", cfg["user_rules_dir"])
    cfg["forbidden"] = opt("--forbidden", "")
    cfg["version"] = version
    cfg["max_bytes"] = max_bytes
    cfg["now"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── 体检：五类必须存在的产物 ＋ 一项可选项 ──────────────────────────
    checks = [
        ("项目级要求文件（环境启动时自动注入，必须落在项目根）", cfg["project_dir"] + "/CODEBUDDY.md"),
        ("数据层（**单文件真源**，配置项 4 点名的那个）", cfg["data_file"]),
        ("**投递台账**（使用者唯一会主动翻的账）", cfg["delivery_ledger"]),
        ("证据台账", cfg["ledger"]),
        ("变更档案", cfg["changelog"]),
    ]
    # 通道文件是**可选项**（§1.1 配置项 3：手册 §三 已自包含，该项通常留空）：
    # 只报状态、**不计退出码**——旧写法把它并入必检 checks，实测新环境「五项齐全却报
    # 缺失 1 项／退出码 1」，被误读成部署失败（2026-09-22 实测并修正）。
    optional = [
        ("通道文件（可选，§1.1 配置项 3）", cfg["channel_file"]),
    ]

    if mode_plan:
        print("=" * 64)
        print("部署初始化清单 —— 封装体 %s（%s）" % (ROOT.name, version))
        print("=" * 64)
        print("项目根：%s" % cfg["project_dir"])
        print("信息目录：%s（数据层／投递台账／附件原件同置此目录，项目根只留要求文件与启动器）"
              % cfg["info_dir"])
        print()
        for label, path in checks:
            print("  [%s] %s\n        %s" % ("✓" if Path(path).exists() else " ", label, path))
        for label, path in optional:
            print("  [%s] %s\n        %s" % ("✓" if Path(path).exists() else "·", label, path))
        print()
        print("可机械生成（脚本直接产出）：")
        print("  · 项目级要求文件 ← templates/CODEBUDDY.md（占位符按 §1.1 配置表替换）")
        print("  · 证据台账／变更档案／投递台账 ← 手册附录 A／B／C 模板块（**唯一真源**，脚本就地抽取，不另存副本）")
        print("  · 数据层骨架 ← **一份** Markdown、仅结构、值为空，**须使用者填**")
        print()
        print("必须使用者提供（脚本不代填、不编造）：")
        print("  · 简历事实与字段取值（填入数据层那一份文件）")
        print("  · §1.1 配置项 7 禁止触碰清单、配置项 8 浏览器启动方式")
        print()
        print("下一步：python scripts/init-workspace.py --yes --project \"%s\"" % cfg["project_dir"])
        return 0

    if mode_check:
        print("=" * 64)
        print("部署体检 —— 封装体 %s（%s）" % (ROOT.name, version))
        print("=" * 64)
        for label, path in checks:
            if Path(path).exists():
                sz = Path(path).stat().st_size
                print("  OK    %s（%d B）\n        %s" % (label, sz, path))
            else:
                print("  MISS  %s\n        %s" % (label, path))
        for label, path in optional:
            if Path(path).exists():
                sz = Path(path).stat().st_size
                print("  OK    %s（%d B）\n        %s" % (label, sz, path))
            else:
                print("  --    %s（未建，可选项不计缺失）\n        %s" % (label, path))
        print("-" * 64)
        miss = sum(1 for _, p in checks if not Path(p).exists())
        print("缺失 %d 项 / 共 %d 项必检（另 %d 项可选）；退出码：%d"
              % (miss, len(checks), len(optional), 1 if miss else 0))
        return 1 if miss else 0

    # ── 生成 ────────────────────────────────────────────────────────
    # 信息目录与三类运行目录先建好：数据层、投递台账与附件原件同置信息目录（项目根只留
    # 要求文件与启动器）；tmp/ 每轮收尾清空，evidence/ 与 backup/ 保留。
    for _d in (cfg["info_dir"],
               os.path.join(cfg["project_dir"], ".workbuddy", "tmp"),
               os.path.join(cfg["project_dir"], ".workbuddy", "evidence"),
               os.path.join(cfg["project_dir"], ".workbuddy", "backup")):
        try:
            Path(_d).mkdir(parents=True, exist_ok=True)
            done.append("建目录 %s" % _norm(_d))
        except OSError as e:
            fail("建目录失败 %s：%s" % (_d, e))

    text = build_requirements(cfg)
    if text is not None:
        write_if_absent(cfg["project_dir"] + "/CODEBUDDY.md", text, force)

    # 台账／变更档案同源同路：模板块都在手册附录（A／B），就地抽取、不另存副本。
    for key, header, label in [
        ("ledger", "**台账模板**", "台账"),
        ("changelog", "**变更档案模板**", "变更档案"),
    ]:
        blk = extract_block(manual, header)
        if blk is None:
            fail("未能从手册附录抽取%s模板（模板块标题或围栏格式变了？）" % label)
        else:
            write_if_absent(cfg[key], blk, force)

    # 投递台账是 xlsx（二进制，无法用模板块承载）：列结构见手册附录 C／§2.1.5，
    # 由脚本内建表头行生成；校验器第十段的投递记录对账直读它的 A 列。
    write_apply_xlsx(cfg["delivery_ledger"], force)

    write_if_absent(cfg["data_file"], data_skeleton(cfg), force)

    # 通道文件的可选性由上方 optional 清单承载（只报状态、不计退出码），此处不重复检查。

    print("=" * 64)
    print("部署初始化 —— 封装体 %s（%s）" % (ROOT.name, version))
    print("=" * 64)
    for x in done:
        print("  " + x)
    for x in warns:
        print("  WARN " + x)
    for x in fails:
        print("  FAIL " + x)
    print("-" * 64)
    print("生成 %d 项 / WARN %d / FAIL %d" % (len(done), len(warns), len(fails)))
    print()
    print("**接下来必须由使用者完成的**（脚本不代填、不编造）：")
    print("  1. 打开 %s/CODEBUDDY.md 核对 §〇.5 禁止触碰清单，以及 §〇.1／§一 的数据层**单文件**路径、"
          "投递台账路径、卷首效力顺序与 §五／§六 的通道文件路径" % cfg["project_dir"])
    print("  2. 把简历事实与字段取值逐项填入数据层（%s）—— 这是取数的唯一真源" % cfg["data_file"])
    print("  3. 按手册 §1.1 配置项 8 制备浏览器启动器（可用 scripts/launch-browser.bat 模板）")
    print("  4. 配方取用**二选一**（手册 §1.1 配置项 5）：默认**就地引用**包内 recipes/"
          "（多数环境已把它注册成技能，直接可用）；仅当包不在技能扫描路径内，才复制到 %s。"
          "**同一环境同名配方只能存在一份**" % cfg["recipes_dir"])
    print("  5. 跑一次 %s --package 确认包自洽（封装体档·九段，退出码 0）"
          % (ROOT / "scripts" / "verify-package.py"))
    print("  6. 此后每次任务收尾，用同一支脚本带 --ledger 指向本环境台账（%s）跑**每轮档**"
          "（默认：运行态第十段＋模板自证）；改过手册／配方／脚本／模板时再加 --package"
          % cfg["ledger"])
    print("  7. （可选）若本环境要有独立通道文件（%s），按 §1.1 配置项 3 自行落盘；"
          "没有则由本手册 §三 独立生效" % cfg["channel_file"])
    print("  8. 临时产物一律落 %s（**每轮收尾清空**，不留到下轮）："
          "python \"%s\" --clean-tmp --project \"%s\"；过程证据落 .workbuddy/evidence/<轮次>/、"
          "改前留档落 .workbuddy/backup/<日期>/，两者保留"
          % (_norm(os.path.join(cfg["project_dir"], ".workbuddy", "tmp")),
             _norm(SELF), _norm(cfg["project_dir"])))
    print("退出码：%d" % (1 if fails else 0))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
