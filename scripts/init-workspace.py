#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""封装体部署初始化（首次使用跑一次；已初始化的环境跑它只做体检，不改文件）。

用法：
  python scripts/init-workspace.py --check                # 只体检，不写任何文件
  python scripts/init-workspace.py --plan                 # 打印将要生成/引导的清单
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

本脚本只读封装体、只写使用者指定的路径，不改封装体自身。
"""
import io
import os
import re
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


def guess_paths(project_dir):
    """按 §1.1 配置表的常见形态猜一组默认路径，供 --plan 展示。"""
    pd = Path(project_dir)
    return {
        "project_requirements": str(pd / "CODEBUDDY.md"),
        "data_dir": str(pd / "简历信息库"),
        "ledger": str(pd / ".workbuddy" / "skills" / "EXPERIENCE-LEDGER.md"),
        "changelog": str(pd / ".workbuddy" / "skills" / "EXPERIENCE-CHANGELOG.md"),
        "channel_file": str(pd / ".workbuddy" / "skills" / "CHANNEL-qqbrowser.md"),
        "recipes_dir": str(pd / ".workbuddy" / "skills"),
        "user_rules_dir": "~/.workbuddy/rules/",
    }


def build_requirements(cfg):
    """把 templates/CODEBUDDY.md 的占位符换成实值。"""
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
    t = t.replace("__PACKAGE_DIR__", str(ROOT))
    t = t.replace("__DATA_DIR__", cfg["data_dir"])
    t = t.replace("__SKILLS_DIR__", cfg["recipes_dir"])
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
    """数据层骨架：**只建结构、不填内容**。

    简历事实与字段取值属使用者个人数据，脚本无从生成——这里给出最小合法 JSON 骨架
    （键名取自本封装体已确认可用的结构），值一律留空/待填，并明确标注。
    """
    resume = {
        "_说明": "简历事实数据主文件骨架——由封装体初始化脚本生成，**内容须使用者逐项填写**；"
                 "本文件只存数据本身，不存版本变更历史（手册 §1.1 配置项 4）。",
        "meta": {"owner": "", "updated": "", "purpose": "简历信息库主数据。"},
        "basic": {},
        "contact": {},
        "education": [],
        "internships": [],
        "campus": [],
        "projects": [],
        "awards": [],
        "family": [],
        "hobbies": "",
        "self_evaluation": "",
        "job_reason": "",
        "求职意向": {},
        "tags": [],
    }
    formmap = {
        "_说明": "招聘系统字段映射表骨架——key 为中文标准字段名，aliases 为该字段在各类招聘系统里"
                 "可能出现的标签写法，value 为待填值；null 表示信息库中暂无该数据。"
                 "操作配方的分层归属见手册 §5.2。",
        "meta": {"purpose": "招聘系统表单自动填写的字段映射表。", "owner": "", "updated": ""},
        "fields": [],
        "section_hints": {},
        "system_fields": {},
    }
    import json
    return (json.dumps(resume, ensure_ascii=False, indent=2) + "\n",
            json.dumps(formmap, ensure_ascii=False, indent=2) + "\n")


def main():
    argv = sys.argv[1:]
    mode_check = "--check" in argv
    mode_plan = "--plan" in argv
    force = "--force" in argv

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
    cfg["ledger"] = opt("--ledger", cfg["ledger"])
    cfg["changelog"] = opt("--changelog", cfg["changelog"])
    cfg["data_dir"] = opt("--data-dir", cfg["data_dir"])
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
        ("数据层·主数据", os.path.join(cfg["data_dir"], "resume.json")),
        ("数据层·字段映射", os.path.join(cfg["data_dir"], "表单字段映射.json")),
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
        print()
        for label, path in checks:
            print("  [%s] %s\n        %s" % ("✓" if Path(path).exists() else " ", label, path))
        for label, path in optional:
            print("  [%s] %s\n        %s" % ("✓" if Path(path).exists() else "·", label, path))
        print()
        print("可机械生成（脚本直接产出）：")
        print("  · 项目级要求文件 ← templates/CODEBUDDY.md（占位符按 §1.1 配置表替换）")
        print("  · 证据台账／变更档案 ← 手册 §5.1 模板块（**唯一真源**，脚本就地抽取，不另存副本）")
        print("  · 数据层骨架 ← 仅结构、值为空，**须使用者填**")
        print()
        print("必须使用者提供（脚本不代填、不编造）：")
        print("  · 简历事实与字段取值（填入数据层两份文件）")
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
    text = build_requirements(cfg)
    if text is not None:
        write_if_absent(cfg["project_dir"] + "/CODEBUDDY.md", text, force)

    led_tpl = extract_block(manual, "**台账模板**")
    chg_tpl = extract_block(manual, "**变更档案模板**")
    if led_tpl is None:
        fail("未能从手册 §5.1 抽取台账模板（模板块标题或围栏格式变了？）")
    else:
        write_if_absent(cfg["ledger"], led_tpl, force)
    if chg_tpl is None:
        fail("未能从手册 §5.1 抽取变更档案模板（模板块标题或围栏格式变了？）")
    else:
        write_if_absent(cfg["changelog"], chg_tpl, force)

    rj, fm = data_skeleton(cfg)
    write_if_absent(os.path.join(cfg["data_dir"], "resume.json"), rj, force)
    write_if_absent(os.path.join(cfg["data_dir"], "表单字段映射.json"), fm, force)

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
    print("  1. 打开 %s/CODEBUDDY.md 核对 §〇.5 禁止触碰清单，以及 §〇.1／§一 的数据层路径、"
          "卷首效力顺序与 §五／§六 的通道文件路径" % cfg["project_dir"])
    print("  2. 把简历事实与字段取值逐项填入数据层（%s）—— 这是取数的唯一真源" % cfg["data_dir"])
    print("  3. 按手册 §1.1 配置项 8 制备浏览器启动器（可用 scripts/launch-browser.bat 模板）")
    print("  4. 复制 recipes/ 下配方到环境侧配方目录 %s（此后它是唯一活跃源头）" % cfg["recipes_dir"])
    print("  5. 跑一次 %s 确认包自洽（退出码 0）" % (ROOT / "scripts" / "verify-package.py"))
    print("  6. 此后每次任务收尾，用同一支脚本带 --ledger 指向本环境台账（%s）跑**运行态**校验"
          "（第十段：轮次基准／待验表／到期／池量／登记簿对账）" % cfg["ledger"])
    print("  7. （可选）若本环境要有独立通道文件（%s），按 §1.1 配置项 3 自行落盘；"
          "没有则由本手册 §三 独立生效" % cfg["channel_file"])
    print("退出码：%d" % (1 if fails else 0))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
