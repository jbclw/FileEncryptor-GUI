#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""about_info.py —— 「关于」页所需的信息采集

两块内容：
  1. probe_engine()      —— 引擎版本与能力（运行时探测，失败一律降级，不抛异常）
  2. collect_environment() —— Python 版本与关键依赖是否可用/版本

引擎版本为什么不能用 -V：
  CLI 2.4.x 的 `-V` 是 `--verify`（校验 .ptd 完整性，还会索取密钥），并非版本号。
  版本只能从 `--help` 首行 `FileEncryptor vX.Y.Z` 解析；能力用 `--features`。
"""
import os
import subprocess
import sys

from .engine import find_exe

_PROBE_TIMEOUT = 3
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _run_engine(args):
    """运行引擎子进程，返回 (ok, 合并后的输出文本)。

    stdin 接 DEVNULL：引擎某些参数会进入交互提示，不能让它挂住。
    """
    exe = find_exe()
    if not os.path.isfile(exe):
        return False, ""
    try:
        p = subprocess.run(
            [exe] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, timeout=_PROBE_TIMEOUT,
            creationflags=_NO_WINDOW,
        )
    except Exception:
        return False, ""
    return True, (p.stdout or b"").decode("utf-8", errors="replace")


def probe_engine():
    """探测引擎。返回 dict：

    found  : 是否找到引擎文件
    path   : 引擎路径
    version: 版本号字符串（探测失败为空）
    zstd   : True/False/None（None 表示未知）
    aegis  : True/False/None
    """
    exe = find_exe()
    info = {"found": os.path.isfile(exe), "path": exe,
            "version": "", "zstd": None, "aegis": None}
    if not info["found"]:
        return info

    ok, text = _run_engine(["--help"])
    if ok:
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("FileEncryptor v"):
                info["version"] = line[len("FileEncryptor "):].strip()
                break

    ok, text = _run_engine(["--features"])
    if ok:
        for line in text.splitlines():
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip().lower(), v.strip()
            if k in ("zstd", "aegis"):
                info[k] = (v == "1")
    return info


# (import 名, 发行包名, 显示名, 链接)
_DEPENDENCIES = (
    ("customtkinter", "customtkinter", "CustomTkinter",
     "https://github.com/TomSchimansky/CustomTkinter"),
    ("winpty", "pywinpty", "pywinpty",
     "https://github.com/spyder-ide/pywinpty"),
    ("PIL", "Pillow", "Pillow",
     "https://github.com/python-pillow/Pillow"),
    ("psutil", "psutil", "psutil",
     "https://github.com/giampaolo/psutil"),
)


def _dep_version(import_name, dist_name):
    """已安装返回版本号字符串，未安装/不可用返回 None"""
    try:
        __import__(import_name)
    except Exception:
        return None
    try:
        from importlib.metadata import version as dist_version
        return dist_version(dist_name)
    except Exception:
        return "?"


def collect_environment():
    """返回 (python 版本, [(显示名, 版本或 None, 链接), ...])"""
    deps = [(name, _dep_version(mod, dist), url)
            for mod, dist, name, url in _DEPENDENCIES]
    return sys.version.split()[0], deps


# 「关于」页致谢列表（名称 + 链接），与 README 致谢表一致
CREDITS = (
    ("FileEncryptor", "https://github.com/Texas-albe/FileEncryptor"),
    ("CustomTkinter", "https://github.com/TomSchimansky/CustomTkinter"),
    ("pywinpty", "https://github.com/spyder-ide/pywinpty"),
    ("Pillow", "https://github.com/python-pillow/Pillow"),
    ("psutil", "https://github.com/giampaolo/psutil"),
    ("tkinterdnd2", "https://github.com/Eliav2/tkinterdnd2"),
    ("libsodium", "https://github.com/jedisct1/libsodium"),
)

# 「关于」页友情链接（显示名 + 链接；属专有名称，不随语言切换）
FRIEND_LINK = ("Twilight飞友 · FileEncryptor-UI",
               "https://github.com/TwilightFY801/FileEncryptor-UI")

# 「关于」页「关于我们」：成员（显示名, B 站主页, GitHub 主页）
# GitHub 主页为空串时该成员只显示 B 站链接
TEAM = (
    ("就不错了我", "https://space.bilibili.com/1705671238",
     "https://github.com/jbclw"),
    ("Twilight飞友", "https://space.bilibili.com/3546728261224829",
     "https://github.com/TwilightFY801"),
    ("瑶璎珞", "https://space.bilibili.com/3546692557212318",
     "https://github.com/Texas-albe"),
)
