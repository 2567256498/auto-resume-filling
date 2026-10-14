#!/usr/bin/env python3
# ego-resume-fill 前置探测链（只读，不碰页面、不启动任何东西）。
# 用法：python scripts/probe-browser.py [--json]
# 判据分四段，有序、不许跳段（与 SKILL.md 前置段一致）：
#   1. Node >= 22 在不在            —— ego 客户端要 Node 运行时
#   2. ego 实例在不在跑             —— 读 %LOCALAPPDATA%\ego-lite-linux\browser.json 探 CDP 端口
#   3. 系统浏览器在不在             —— Chrome / Edge（ego 运行时按候选链找）
#   4. ego 专用 profile 在不在      —— 登录态的家；没有它连上也等于没登录
# 退出码：0 = 四段全过；1 = 有段不过（明细在输出里）。
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

WIN = os.name == "nt"


def _appdata(*parts):
    base = os.environ.get("LOCALAPPDATA") or (
        Path(os.environ["USERPROFILE"]) / "AppData" / "Local" if WIN else Path.home() / ".local" / "share"
    )
    return Path(base, *parts)


EGO_STATE = _appdata("ego-lite-linux", "browser.json")
EGO_PROFILE = os.environ.get("EGO_LINUX_PROFILE") or str(_appdata("ego-lite-linux", "profile"))


def probe_node():
    """Node 探测链：PATH -> 常见安装位置 -> WorkBuddy managed node。"""
    cands = ["node"]
    if WIN:
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if base:
                cands.append(str(Path(base, "nodejs", "node.exe")))
        local = os.environ.get("LOCALAPPDATA")
        if local:
            cands.append(str(Path(local, "Programs", "nodejs", "node.exe")))
        home = os.environ.get("USERPROFILE")
        if home:
            cands.append(str(Path(home, ".workbuddy", "binaries", "node")))
    for c in cands:
        if c == "node":
            p = shutil.which(c)
        else:
            cp = Path(c)
            p = str(cp if cp.is_file() else cp / "node.exe") if cp.exists() else None
        if not p or not Path(p).exists():
            continue
        try:
            out = subprocess.run([p, "--version"], capture_output=True, text=True, timeout=15)
            ver = (out.stdout or "").strip().lstrip("v")
            if out.returncode == 0 and ver:
                major = int(ver.split(".")[0])
                return {"ok": major >= 22, "path": p, "version": ver,
                        "hint": "" if major >= 22 else "ego 客户端需要 Node >= 22"}
        except Exception:
            continue
    return {"ok": False, "path": None, "version": None,
            "hint": "未找到 Node.js：装 LTS（nodejs.org）或把 node.exe 加入 PATH"}


def probe_instance():
    """ego 实例：读 browser.json 的 CDP 端口，探 /json/version。"""
    if not EGO_STATE.exists():
        return {"ok": False, "hint": "ego 实例未启动（无 browser.json）：双击 launch-browser.bat 启动，或见 SKILL.md 前置段"}
    try:
        st = json.loads(EGO_STATE.read_text(encoding="utf-8"))
        port = st.get("port")
        if not port:
            return {"ok": False, "hint": "browser.json 无 port 字段：实例状态异常，重启浏览器"}
        req = urllib.request.Request(f"http://127.0.0.1:{port}/json/version", method="GET")
        with urllib.request.urlopen(req, timeout=3) as r:
            data = json.loads(r.read().decode("utf-8"))
        return {"ok": True, "port": port, "browser": data.get("Browser"),
                "hint": ""}
    except Exception as e:
        return {"ok": False, "hint": f"browser.json 在但 CDP 端口探不通（{e.__class__.__name__}）：实例可能已死，重启浏览器"}


def probe_system_browser():
    """系统浏览器：ego 运行时的候选链（chrome.mjs BINARY_CANDIDATES 同序）。"""
    if not WIN:
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "brave-browser", "microsoft-edge"):
            p = shutil.which(name)
            if p:
                return {"ok": True, "path": p}
        return {"ok": False, "hint": "未找到 Chrome/Chromium/Edge：装一个（browser.qq.com 不适用，装 Chrome 或 Edge）"}
    bases = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")]
    names = [("Google", "Chrome", "Application", "chrome.exe"), ("Microsoft", "Edge", "Application", "msedge.exe")]
    cands = []
    for base in bases:
        if not base:
            continue
        for parts in names:
            cands.append(Path(base, *parts))
    local = os.environ.get("LOCALAPPDATA")
    if local:
        cands.append(Path(local, "Google", "Chrome", "Application", "chrome.exe"))
    for c in cands:
        try:
            if c.exists():
                return {"ok": True, "path": str(c)}
        except Exception:
            continue
    return {"ok": False, "hint": "未找到 Chrome/Edge 可执行文件：Windows 一般自带 Edge；都没有就装一个"}


def probe_profile():
    """ego 专用 profile：登录态的家。"""
    p = Path(EGO_PROFILE)
    if not p.exists():
        return {"ok": False, "path": EGO_PROFILE, "hint": "profile 目录不存在：首次启动后是空的，各网站需重新登录（或用 ego-browser --import-chrome-profile 从真实 Chrome 继承）"}
    has_data = any(p.glob("*")) and (p / "Default").exists() or any(p.glob("**/Cookies"))
    if not has_data:
        return {"ok": True, "path": EGO_PROFILE, "empty": True,
                "hint": "profile 在但还没有登录数据：打开各招聘网站登录一次即可"}
    return {"ok": True, "path": EGO_PROFILE, "hint": ""}


def main():
    as_json = "--json" in sys.argv
    results = [
        ("1-Node 运行时", probe_node()),
        ("2-ego 实例", probe_instance()),
        ("3-系统浏览器", probe_system_browser()),
        ("4-ego profile(登录态)", probe_profile()),
    ]
    if as_json:
        print(json.dumps({k: v for k, v in results}, ensure_ascii=False, indent=1))
    else:
        allok = True
        for name, r in results:
            mark = "OK  " if r.get("ok") else "FAIL"
            line = f"[{mark}] {name}"
            for k in ("path", "version", "port", "browser"):
                if r.get(k):
                    line += f"  {k}={r[k]}"
            print(line)
            if r.get("hint"):
                print(f"       -> {r['hint']}")
            if not r.get("ok"):
                allok = False
        print("---")
        print("结论：" + ("前置四段全过，可以开工。" if allok else "有段不过，按上面提示处置；未就位前不要动表单。"))
    sys.exit(0 if all(r.get("ok") for _, r in results) else 1)


if __name__ == "__main__":
    main()
