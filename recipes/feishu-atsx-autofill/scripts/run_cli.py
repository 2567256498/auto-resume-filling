import subprocess, sys, base64, shlex, os, re, tempfile, shutil

# 通道 CLI 路径：优先环境变量 QQBROWSER_SKILL，其次在 PATH 中查找
CLI = os.environ.get("QQBROWSER_SKILL") or shutil.which("qqbrowser-skill")
if not CLI:
    raise SystemExit("[run_cli] 未找到 qqbrowser-skill：请把环境变量 QQBROWSER_SKILL 指向其可执行文件，或把它加入 PATH")
OUT = os.path.join(tempfile.gettempdir(), "qqbrowser_cli_out.txt")

def js_escape(v):
    return v.replace("\\", "\\\\").replace("'", "\\'").replace("\r", "").replace("\n", "\\n")

def expand(a, subs):
    # @tpl= 与 @b64= 行为一致：都是「读文件 → 替换 {{k}} → base64」。保留两个名字只为可读性。
    if a.startswith("@b64=") or a.startswith("@tpl="):
        path = a.split("=", 1)[1]
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read()
        for k, v in subs.items():
            txt = txt.replace("{{" + k + "}}", v)
        # 占位符未替换即中止：否则残稿会被原样发出，浏览器侧才炸（或更糟——静默按字面量执行）
        left = sorted(set(re.findall(r"\{\{(\w+)\}\}", txt)))
        if left:
            raise SystemExit(
                "[run_cli] 占位符未替换即中止：%s 里还剩 %s —— 补上 %s"
                % (path, "、".join("{{%s}}" % x for x in left),
                   " ".join("--set:%s=<值>" % x for x in left)))
        return base64.b64encode(txt.encode("utf-8")).decode("ascii")
    return a

def build(tokens):
    subs = {}
    keep = []
    for t in tokens:
        if t.startswith("--set:"):
            k, v = t[6:].split("=", 1)
            if "@file=" in v:
                pre, path = v.split("@file=", 1)
                with open(path, "r", encoding="utf-8") as f:
                    raw = f.read().replace("\r\n", "\n").rstrip("\n")
                v = pre + js_escape(raw)
            subs[k] = v
        else:
            keep.append(t)
    return [expand(x, subs) for x in keep]

def run(cmds):
    with open(OUT, "w", encoding="utf-8") as f:
        for c in cmds:
            f.write(">>> CMD: " + " ".join(x[:80] for x in c) + "\n"); f.flush()
            try:
                p = subprocess.run([CLI] + c, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
                f.write("EXIT: " + str(p.returncode) + "\n")
                f.write((p.stdout or "") + (p.stderr or ""))
            except Exception as e:
                f.write("EXC: " + repr(e) + "\n")
            f.write("=" * 60 + "\n"); f.flush()

if len(sys.argv) > 1 and sys.argv[1].startswith("@cmdlist="):
    path = sys.argv[1][9:]
    cmds = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                cmds.append(build(shlex.split(line)))
    run(cmds)
else:
    run([build(sys.argv[1:])])
print("done")
