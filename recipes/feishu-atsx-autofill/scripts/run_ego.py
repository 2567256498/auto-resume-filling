import subprocess, sys, base64, shlex, os, tempfile, shutil

# ego 通道运行器（替代 QQ 浏览器时代的 run_cli.py，接口不变）。
# CLI 探测链：环境变量 EGO_BROWSER -> 包内 runtime/ego-browser.cmd（相对本脚本定位）-> PATH。
_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG_RUNTIME = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "runtime", "ego-browser.cmd"))
CLI = (os.environ.get("EGO_BROWSER")
       or (_PKG_RUNTIME if os.path.exists(_PKG_RUNTIME) else None)
       or shutil.which("ego-browser")
       or shutil.which("ego-browser.cmd"))
if not CLI:
    raise SystemExit("[run_ego] 未找到 ego-browser：设环境变量 EGO_BROWSER 指向它，或确认包内 runtime/ego-browser.cmd 在位")
OUT = os.path.join(tempfile.gettempdir(), "ego_cli_out.txt")

def js_escape(v):
    return v.replace("\\", "\\\\").replace("'", "\\'").replace("\r", "").replace("\n", "\\n")

def expand(a, subs):
    if a.startswith("@b64=") or a.startswith("@tpl="):
        path = a.split("=", 1)[1]
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read()
        for k, v in subs.items():
            txt = txt.replace("{{" + k + "}}", v)
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
    # ego 通道形态：每条命令是一段 JS，经 stdin 喂给 ego-browser.cmd。
    with open(OUT, "w", encoding="utf-8") as f:
        for c in cmds:
            js = c[0] if c else ""
            f.write(">>> JS: " + js[:80].replace("\n", " ") + "\n"); f.flush()
            try:
                p = subprocess.run([CLI], input=js, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=300)
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
