#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileEncryptor GUI —— 文件加密工具图形界面
基于 FileEncryptor 命令行工具的封装（Windows / Linux / macOS）
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk  # 保留用于 StringVar, BooleanVar 等
import subprocess
import os
import sys
import threading
import json
import time
import re
import select
from pathlib import Path
from datetime import datetime
import queue
import configparser
import math

# 实验性"图片背景+模糊"功能依赖 Pillow。未安装时该功能自动禁用并友好提示。
try:
    from PIL import Image as PILImage, ImageFilter, ImageTk, ImageDraw
    _HAVE_PIL = True
except Exception:
    _HAVE_PIL = False

IS_WINDOWS = (os.name == "nt")

try:
    import winpty
except ImportError:
    winpty = None

try:
    import psutil
except ImportError:
    psutil = None


# ── 可执行文件查找策略（按优先级）：──────────────────────────────
# 1. gui.py 同目录下的引擎可执行文件
# 2. gui.py 的父目录（即项目根目录）
# 3. 父目录的父目录
# 4. 系统 PATH
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 引擎文件名按平台区分：Windows 为 FileEncryptor.exe，POSIX 为 FileEncryptor
if IS_WINDOWS:
    _ENGINE_NAMES = ["FileEncryptor.exe"]
else:
    _ENGINE_NAMES = ["FileEncryptor", "fileencryptor"]

EXE_CANDIDATES = []
for _name in _ENGINE_NAMES:
    EXE_CANDIDATES += [
        os.path.join(_SCRIPT_DIR, _name),                    # 同目录
        os.path.join(_SCRIPT_DIR, "..", _name),              # 父目录
        os.path.join(_SCRIPT_DIR, "..", "..", _name),        # 祖父目录
        _name,                                                # PATH
    ]


def find_exe():
    """查找可执行文件路径"""
    for p in EXE_CANDIDATES:
        absp = os.path.abspath(p)
        if os.path.isfile(absp) and os.access(absp, os.X_OK):
            return absp
    # 全没找到，返回最后一个候选
    return os.path.abspath(EXE_CANDIDATES[-1])


# ── 配置管理器 ─────────────────────────────────────────────────────────

class ConfigManager:
    """管理用户配置持久化"""

    def __init__(self):
        self.config_file = os.path.join(_SCRIPT_DIR, "config.ini")
        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file, encoding='utf-8')
            except Exception as e:
                print(f"加载配置失败: {e}")

    def _save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def get(self, section, key, default=None):
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    def getint(self, section, key, default=0):
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default

    def getboolean(self, section, key, default=False):
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default

    def set(self, section, key, value):
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))

    def save(self):
        self._save_config()


# 全局配置实例
_config = None

def get_config():
    global _config
    if _config is None:
        _config = ConfigManager()
    return _config


def find_helper_python():
    """找到可运行 _runner.py 的 Python
    POSIX：_runner.py 使用内置 pty，直接返回当前解释器
    Windows：_runner.py 依赖 winpty，需找到装有 pywinpty 的解释器
    """
    if not IS_WINDOWS:
        return sys.executable

    # 1. 先检查当前运行的 Python 是否有 winpty（最常见情况）
    if winpty is not None:
        return sys.executable

    # 2. 查找外部 Python（PATH 中的 python）
    for cmd in ["python", "python3"]:
        try:
            r = subprocess.run(
                [cmd, "-c", "import winpty; print('OK')"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0 and "OK" in r.stdout:
                return cmd
        except Exception:
            pass

    # 3. 常见安装路径
    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python310", "python.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python311", "python.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python312", "python.exe"),
        "C:\\Python310\\python.exe",
        "C:\\Python311\\python.exe",
    ]
    for p in candidates:
        if os.path.isfile(p):
            try:
                r = subprocess.run([p, "-c", "import winpty"], capture_output=True, timeout=5)
                if r.returncode == 0:
                    return p
            except Exception:
                pass
    return None


_HELPER_PYTHON = None


# ── 多语言（i18n）───────────────────────────────────────────────────────

STRINGS = {
    "zh": {
        "app_subtitle": "文件加密工具",
        "nav_encrypt": "加密文件",
        "nav_decrypt": "解密文件",
        "nav_batch_enc": "批量加密",
        "nav_batch_dec": "批量解密",
        "nav_settings": "设置",
        "settings": "设置",
        "settings_desc": "配置应用程序的基本选项和实验性功能",
        "language": "语言",
        "theme": "主题",
        "theme_light": "浅色",
        "theme_dark": "深色",
        "ready": "就绪",
        "running": "运行中...",
        "done": "完成",
        "failed": "失败",
        "log_title": "运行日志",
        "export": "导出",
        "clear": "清空",
        "encrypt_single": "加密单个文件",
        "encrypt_single_desc": "选择一个文件，设置密码后加密为 .ptd 格式",
        "source_file": "源文件",
        "enc_password": "加密密码",
        "confirm_password": "确认密码",
        "algorithm": "算法",
        "delete_source": "加密后删除源文件",
        "output_dir_auto": "输出目录（留空为源文件所在目录）",
        "output_dir": "输出目录",
        "start_encrypt": "开始加密",
        "strength_hint": "密码强度仅作参考。实际安全性取决于密码长度和复杂度。",
        "decrypt_single": "解密单个文件",
        "decrypt_single_desc": "选择一个 .ptd 加密文件，输入密码还原为原始文件",
        "enc_file_ptd": "加密文件（.ptd）",
        "dec_password": "解密密码",
        "start_decrypt": "开始解密",
        "batch_enc": "批量加密目录",
        "batch_enc_desc": "递归加密整个目录下所有文件为 .ptd 格式",
        "source_dir": "源目录",
        "threads": "线程数",
        "start_batch_enc": "开始批量加密",
        "batch_dec": "批量解密目录",
        "batch_dec_desc": "递归解密目录下所有 .ptd 文件还原为原始文件",
        "source_dir_ptd": "源目录（包含 .ptd 文件）",
        "start_batch_dec": "开始批量解密",
        "paste_path": "粘贴路径",
        "clear_item": "清空",
        "select_dir": "选择目录",
        "select_file": "选择文件",
        "hint": "提示",
        "error": "错误",
        "msg_select_enc_file": "请选择要加密的文件",
        "msg_enter_enc_pw": "请输入加密密码",
        "msg_pw_mismatch": "两次输入的密码不一致",
        "msg_src_not_exist": "源文件不存在",
        "msg_cannot_create_dir": "无法创建输出目录",
        "msg_select_ptd": "请选择要解密的 .ptd 文件",
        "msg_enter_dec_pw": "请输入解密密码",
        "msg_file_not_exist": "文件不存在",
        "msg_not_ptd": "选中的文件不是 .ptd 格式",
        "msg_select_src_dir": "请选择源目录",
        "msg_src_dir_not_exist": "源目录不存在",
        "msg_log_empty": "日志为空",
        "msg_export_fail": "导出失败",
        "msg_log_exported": "日志已导出",
        "msg_busy": "已有操作正在执行，请等待完成",
        "msg_cancel": "用户取消操作",
        "strength_weak": "弱",
        "strength_medium": "中",
        "strength_strong": "强",
        "exp_section": "实验性 · 图片背景",
        "exp_image_bg": "启用图片背景",
        "exp_pick_image": "选择图片",
        "exp_blur_wall": "壁纸模糊",
        "exp_blur_panel": "面板模糊",
        "exp_note": "开启后将忽略主题色；侧栏与内容面板呈半透明毛玻璃（面板模糊 0 为完全透明），文字不受模糊影响。",
        "msg_need_pillow": "图片背景功能需要 Pillow，请先安装：pip install pillow",
    },
    "en": {
        "app_subtitle": "File Encryption Tool",
        "nav_encrypt": "Encrypt File",
        "nav_decrypt": "Decrypt File",
        "nav_batch_enc": "Batch Encrypt",
        "nav_batch_dec": "Batch Decrypt",
        "nav_settings": "Settings",
        "settings": "Settings",
        "settings_desc": "Configure application options and experimental features",
        "language": "Language",
        "theme": "Theme",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "ready": "Ready",
        "running": "Running...",
        "done": "Done",
        "failed": "Failed",
        "log_title": "Running Log",
        "export": "Export",
        "clear": "Clear",
        "encrypt_single": "Encrypt Single File",
        "encrypt_single_desc": "Select a file, set a password, encrypt to .ptd format",
        "source_file": "Source File",
        "enc_password": "Encryption Password",
        "confirm_password": "Confirm Password",
        "algorithm": "Algorithm",
        "delete_source": "Delete source after encrypt",
        "output_dir_auto": "Output dir (blank = source dir)",
        "output_dir": "Output Directory",
        "start_encrypt": "Encrypt",
        "strength_hint": "Password strength is only a reference. Real security depends on its length and complexity.",
        "decrypt_single": "Decrypt Single File",
        "decrypt_single_desc": "Select a .ptd file, enter the password to restore the original",
        "enc_file_ptd": "Encrypted file (.ptd)",
        "dec_password": "Decryption Password",
        "start_decrypt": "Decrypt",
        "batch_enc": "Encrypt Directory",
        "batch_enc_desc": "Recursively encrypt all files in the directory to .ptd",
        "source_dir": "Source Directory",
        "threads": "Threads",
        "start_batch_enc": "Batch Encrypt",
        "batch_dec": "Decrypt Directory",
        "batch_dec_desc": "Recursively decrypt all .ptd files in the directory",
        "source_dir_ptd": "Source dir (contains .ptd files)",
        "start_batch_dec": "Batch Decrypt",
        "paste_path": "Paste Path",
        "clear_item": "Clear",
        "select_dir": "Select Directory",
        "select_file": "Select File",
        "hint": "Notice",
        "error": "Error",
        "msg_select_enc_file": "Please select a file to encrypt",
        "msg_enter_enc_pw": "Please enter the encryption password",
        "msg_pw_mismatch": "The two passwords do not match",
        "msg_src_not_exist": "Source file does not exist",
        "msg_cannot_create_dir": "Could not create output directory",
        "msg_select_ptd": "Please select a .ptd file to decrypt",
        "msg_enter_dec_pw": "Please enter the decryption password",
        "msg_file_not_exist": "File does not exist",
        "msg_not_ptd": "The selected file is not in .ptd format",
        "msg_select_src_dir": "Please select a source directory",
        "msg_src_dir_not_exist": "Source directory does not exist",
        "msg_log_empty": "Log is empty",
        "msg_export_fail": "Export failed",
        "msg_log_exported": "Log exported",
        "msg_busy": "An operation is already running, please wait",
        "msg_cancel": "User cancelled the operation",
        "strength_weak": "Weak",
        "strength_medium": "Medium",
        "strength_strong": "Strong",
        "exp_section": "Experimental · Image BG",
        "exp_image_bg": "Enable image bg",
        "exp_pick_image": "Choose image",
        "exp_blur_wall": "Wallpaper blur",
        "exp_blur_panel": "Panel blur",
        "exp_note": "Ignores theme colors; the sidebar and content panels become translucent frosted glass (panel blur 0 = fully transparent). Text is never blurred.",
        "msg_need_pillow": "Image background needs Pillow. Install with: pip install pillow",
    },
}

_LANG = "zh"

def tr(key):
    """返回当前语言下的翻译文本"""
    table = STRINGS.get(_LANG) or STRINGS["zh"]
    return table.get(key, key)

def apply_lang(lang):
    global _LANG
    if lang in STRINGS:
        _LANG = lang


# ── 主题（实用工具风格，中性克制）───────────────────────────────────────

# 浅色主题（默认）
BG_MAIN = "#f0f0f0"       # 中性灰底
BG_SIDEBAR = "#3a3a3a"    # 深灰侧栏
BG_CARD = "#fafafa"       # 卡片底色（接近白）
TEXT_DARK = "#2a2a2a"     # 深色文字
TEXT_MUTED = "#7a7a7a"    # 灰色文字
TEXT_LIGHT = "#e0e0e0"    # 浅色文字
ACCENT = "#5a5a5a"        # 中性深灰（避免彩色）
ACCENT_HOVER = "#4a4a4a"  # 悬停更深
BORDER = "#d0d0d0"        # 边框色
SUCCESS = "#5a8a5a"       # 暗绿（低饱和）
ERROR = "#a05a5a"         # 暗红（低饱和）
INPUT_BG = "#ffffff"      # 输入框白底
BTN_BG = "#e0e0e0"        # 按钮底色
BTN_TEXT = "#2a2a2a"      # 按钮文字
PROG_TRACK = "#e0e0e0"    # 进度条轨道
OUT_BG = "#1e1e1e"        # 日志区背景
NAV_ACTIVE = "#e0e0e0"    # 导航选中
NAV_INACTIVE = "#a0a0a0"  # 导航未选中
NAV_HOVER = "#c0c0c0"     # 导航悬停
VER_TEXT = "#5a5a5a"      # 版本文字

# 深色主题（黑色系）
_DARK = {
    "BG_MAIN": "#1e1e1e",
    "BG_SIDEBAR": "#141414",
    "BG_CARD": "#252525",
    "TEXT_DARK": "#d8d8d8",
    "TEXT_MUTED": "#9a9a9a",
    "TEXT_LIGHT": "#e0e0e0",
    "ACCENT": "#8a8a8a",
    "ACCENT_HOVER": "#9a9a9a",
    "BORDER": "#3a3a3a",
    "SUCCESS": "#6fbf6f",
    "ERROR": "#d07a7a",
    "INPUT_BG": "#1a1a1a",
    "BTN_BG": "#333333",
    "BTN_TEXT": "#d8d8d8",
    "PROG_TRACK": "#3a3a3a",
    "OUT_BG": "#101010",
    "NAV_ACTIVE": "#f0f0f0",
    "NAV_INACTIVE": "#9a9a9a",
    "NAV_HOVER": "#c8c8c8",
    "VER_TEXT": "#6a6a6a",
}

THEMES = {"light": {k: globals()[k] for k in _DARK.keys()}, "dark": _DARK}

def apply_theme(name):
    """将主题色写回模块级颜色全局变量（调用时读取，故先应用再建 UI）"""
    palette = THEMES.get(name, THEMES["light"])
    for k, v in palette.items():
        globals()[k] = v


# ── 字体 ───────────────────────────────────────────────────────────────

if IS_WINDOWS:
    FONT_FAMILY = "Segoe UI"
    FONT_FAMILY_MONO = "Consolas"
else:
    FONT_FAMILY = "DejaVu Sans"
    FONT_FAMILY_MONO = "DejaVu Sans Mono"

FONT = (FONT_FAMILY, 10)
FONT_SM = (FONT_FAMILY, 9)
FONT_LG = (FONT_FAMILY, 12, "bold")
FONT_MONO = (FONT_FAMILY_MONO, 10)
FONT_HEAD = (FONT_FAMILY, 11, "bold")

# 动画配置
ANIM_DURATION = 200  # 毫秒
ANIM_EASING = "ease-out"


class AnimationManager:
    """动画管理器（预留，界面以克制为准则，暂未大量使用）"""

    def __init__(self, root):
        self.root = root


def run_fileencryptor_stream(args, password=None, password2=None, timeout=300,
                              overwrite=None, fallback=None):
    """
    通过 _runner.py 流式运行 FileEncryptor 引擎
    伪终端模拟键盘输入，解决 _getch()/termios 密码注入问题
    （Windows 走 pywinpty，POSIX 走内置 pty 模块）

    Yields (line_text, progress_info, error) 三元组
      - line_text: 当前行文本（空字符串表示控制消息/进度行）
      - progress_info: (current, total) 字节数 或 None
      - error: 错误文本（空字符串表示正常），最后一条为退出码(整数)
    """
    global _HELPER_PYTHON
    exe = find_exe()

    # 引擎不存在时提前报错（避免 runner 侧晦涩的失败信息）
    if not os.path.isfile(exe):
        engine_name = _ENGINE_NAMES[0]
        yield ("", None, f"FileEncryptor engine not found: {engine_name}")
        return

    # 查找可运行 _runner.py 的 Python（POSIX 直接用当前解释器）
    if _HELPER_PYTHON is None:
        _HELPER_PYTHON = find_helper_python()

    if _HELPER_PYTHON is None:
        yield ("", None, "No Python with winpty found. Run: pip install pywinpty")
        return

    runner_script = os.path.join(_SCRIPT_DIR, "_runner.py")
    if not os.path.isfile(runner_script):
        yield ("", None, f"Runner script not found: {runner_script}")
        return

    # 构建 helper 命令行
    # 密码经环境变量传递：/proc/<pid>/environ 仅本用户可读，比命令行参数安全
    args_json = json.dumps(args)
    ow = "" if overwrite is None else ("y" if overwrite else "n")
    fb = "" if fallback is None else ("y" if fallback else "n")

    cmd = [
        _HELPER_PYTHON, runner_script,
        exe, args_json, ow, fb, str(int(timeout))
    ]
    env = dict(os.environ)
    env["FE_GUI_PW1"] = password or ""
    env["FE_GUI_PW2"] = password2 or ""

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            env=env,
        )
    except Exception as e:
        yield ("", None, f"Failed to spawn runner: {e}")
        return

    exit_code = -1
    buffer = ""

    while True:
        # 改为读 4KB 缓冲区，大幅减少 syscall 开销
        chunk = proc.stdout.read(4096)
        if not chunk:
            break
        buffer += chunk.decode("utf-8", errors="replace")

        # 引擎进度用 \r 原地覆盖（不换行），故同时按 \n 与 \r 切分，
        # 这样每条进度更新都会被单独处理，进度条才能实时前进。
        while True:
            idx_n = buffer.find('\n')
            idx_r = buffer.find('\r')
            if idx_n < 0 and idx_r < 0:
                break
            if idx_n < 0:
                cut = idx_r
            elif idx_r < 0:
                cut = idx_n
            else:
                cut = idx_n if idx_n < idx_r else idx_r
            line = buffer[:cut]
            buffer = buffer[cut + 1:]

            # 检查退出标记
            if line.startswith("__EXIT__:"):
                try:
                    exit_code = int(line.split(":", 1)[1])
                except ValueError:
                    exit_code = -1
                continue

            if line.startswith("__ERR__:"):
                err_msg = line.split(":", 1)[1] if ":" in line else ""
                yield ("", None, err_msg)
                continue

            # 解析引擎进度：`[=====>         ] 12345/100000 bytes | 5.2 MiB/s | 0:03`
            progress = None
            m = re.search(r'(\d+)\s*/\s*(\d+)\s+bytes', line)
            if m:
                progress = (int(m.group(1)), int(m.group(2)))
                yield ("", progress, "")   # 进度行不入日志，仅驱动进度条
            elif line.strip():
                yield (line, None, "")

    # 处理 buffer 中剩余内容（兜底；一般 __EXIT__ 都带换行）
    if buffer.startswith("__EXIT__:"):
        try:
            exit_code = int(buffer.split(":", 1)[1].strip())
        except ValueError:
            exit_code = -1
    elif buffer.strip():
        m = re.search(r'(\d+)\s*/\s*(\d+)\s+bytes', buffer)
        if m:
            yield ("", (int(m.group(1)), int(m.group(2))), "")
        else:
            yield (buffer.rstrip("\r"), None, "")

    yield ("", None, exit_code)


# ── 密码强度判断逻辑（基于熵的评分，参考 zxcvbn）────────────────────

def password_score(pwd):
    """返回密码强度 0.0 ~ 1.0（基于熵计算，参考 zxcvbn 算法）"""
    if not pwd:
        return 0.0

    n = len(pwd)

    # 计算字符集大小
    charset_size = 0
    if re.search(r"[a-z]", pwd):
        charset_size += 26
    if re.search(r"[A-Z]", pwd):
        charset_size += 26
    if re.search(r"\d", pwd):
        charset_size += 10
    if re.search(r"[^a-zA-Z0-9]", pwd):
        charset_size += 33  # 常见特殊字符

    if charset_size == 0:
        return 0.0

    # 计算熵（bits）
    entropy = n * math.log2(charset_size)

    # 惩罚常见模式
    penalty = 0.0

    # 重复字符惩罚
    if len(set(pwd)) == 1:
        penalty += entropy * 0.8

    # 连续字符惩罚（如 abc, 123）
    for i in range(len(pwd) - 2):
        if ord(pwd[i+1]) == ord(pwd[i]) + 1 and ord(pwd[i+2]) == ord(pwd[i]) + 2:
            penalty += 10

    # 常见密码模式惩罚
    common_patterns = [
        r"123", r"abc", r"qwerty", r"password", r"admin", r"letmein",
        r"welcome", r"monkey", r"dragon", r"master", r"login", r"princess"
    ]
    pwd_lower = pwd.lower()
    for pattern in common_patterns:
        if pattern in pwd_lower:
            penalty += 20

    # 应用惩罚
    entropy = max(0, entropy - penalty)

    # 将熵映射到 0-1 分数
    # < 28 bits: 非常弱 (0-0.2)
    # 28-35 bits: 弱 (0.2-0.4)
    # 35-60 bits: 中等 (0.4-0.7)
    # 60-80 bits: 强 (0.7-0.9)
    # > 80 bits: 非常强 (0.9-1.0)
    if entropy < 28:
        score = entropy / 28 * 0.2
    elif entropy < 35:
        score = 0.2 + (entropy - 28) / 7 * 0.2
    elif entropy < 60:
        score = 0.4 + (entropy - 35) / 25 * 0.3
    elif entropy < 80:
        score = 0.7 + (entropy - 60) / 20 * 0.2
    else:
        score = 0.9 + min(1, (entropy - 80) / 40) * 0.1

    return min(score, 1.0)


# ── 自定义控件 ────────────────────────────────────────────────────────

class PasswordEntry(ctk.CTkFrame):
    """带显隐切换与强度指示的密码输入框"""

    def __init__(self, parent, label="", **kwargs):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=6, **kwargs)
        self.show_password = False  # 默认隐藏
        self.text = tk.StringVar()

        # 标签
        self.lbl = ctk.CTkLabel(
            self, text=label, font=FONT_SM, text_color=TEXT_DARK,
            anchor="w"
        )
        self.lbl.pack(fill="x", pady=(0, 2))

        # 输入行
        row = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0)
        row.pack(fill="x")

        self.entry = ctk.CTkEntry(
            row, textvariable=self.text, show="\u2022",  # 默认掩码
            font=FONT, fg_color=INPUT_BG, text_color=TEXT_DARK,
            border_width=1, border_color=BORDER,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.toggle_btn = ctk.CTkLabel(
            row, text="\u25cf", font=(FONT_FAMILY, 12),
            fg_color=INPUT_BG, text_color=TEXT_MUTED, cursor="hand2",
            width=24,
        )
        self.toggle_btn.pack(side="right")
        self.toggle_btn.bind("<Button-1>", self._toggle_show)

        # 强度指示（进度条 + 等级文字）
        foot = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0)
        foot.pack(fill="x", pady=(4, 0))
        self.strength_bar = ctk.CTkProgressBar(
            foot, height=4, fg_color=PROG_TRACK, progress_color=ERROR
        )
        self.strength_bar.set(0)  # 默认归零
        self.strength_bar.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.strength_lbl = ctk.CTkLabel(
            foot, text="", font=(FONT_FAMILY, 8), text_color=TEXT_MUTED,
            width=24, anchor="e",
        )
        self.strength_lbl.pack(side="right")

        self.text.trace_add("write", self._update_strength)

    def _toggle_show(self, event=None):
        self.show_password = not self.show_password
        self.entry.configure(show="" if self.show_password else "\u2022")
        self.toggle_btn.configure(text="\u25cb" if self.show_password else "\u25cf")

    def _update_strength(self, *args):
        pwd = self.text.get()
        score = password_score(pwd)
        if score < 0.3:
            color, level = ERROR, "strength_weak"
        elif score < 0.6:
            color, level = "#c4a050", "strength_medium"
        else:
            color, level = SUCCESS, "strength_strong"
        self.strength_bar.configure(progress_color=color)
        self.strength_bar.set(score)
        self.strength_lbl.configure(text=tr(level))

    def get(self):
        return self.text.get()

    def set(self, val):
        self.text.set(val)

    def clear(self):
        self.text.set("")


class FileSelector(ctk.CTkFrame):
    """文件/目录选择器，支持拖放和粘贴"""

    def __init__(self, parent, label="", is_dir=False, **kwargs):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=6, **kwargs)
        self.is_dir = is_dir
        self._path = tk.StringVar()

        self.lbl = ctk.CTkLabel(
            self, text=label, font=FONT_SM, text_color=TEXT_DARK,
            anchor="w"
        )
        self.lbl.pack(fill="x", pady=(0, 2))

        row = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0)
        row.pack(fill="x")

        self.entry = ctk.CTkEntry(
            row,
            textvariable=self._path,
            font=FONT,
            fg_color=INPUT_BG,
            text_color=TEXT_DARK,
            border_width=1,
            border_color=BORDER,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        # 添加右键菜单
        self._create_context_menu()

        # 绑定拖放事件（如果支持）
        try:
            import tkinterdnd2
            self.entry.dnd_bind('<<Drop>>', self._on_drop)
        except ImportError:
            pass

        self.btn = ctk.CTkLabel(
            row, text="\u2026", font=(FONT_FAMILY, 14),
            fg_color=INPUT_BG, text_color=TEXT_DARK, cursor="hand2",
            width=32,
        )
        self.btn.pack(side="right")
        self.btn.bind("<Button-1>", self._browse)

    def _create_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label=tr("paste_path"), command=self._paste_path)
        self.context_menu.add_command(label=tr("clear_item"), command=self.clear)
        self.entry.bind("<Button-3>", self._show_context_menu)

    def _show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _paste_path(self):
        try:
            path = self.entry.clipboard_get()
            if path:
                path = path.strip().strip('"').strip("'")
                self.set(path)
        except tk.TclError:
            pass

    def _on_drop(self, event):
        path = event.data
        if path:
            path = path.strip().strip('"').strip("'")
            self.set(path)

    def _browse(self, event=None):
        if self.is_dir:
            p = filedialog.askdirectory(title=tr("select_dir"))
        else:
            p = filedialog.askopenfilename(title=tr("select_file"))
        if p:
            self._path.set(p)

    def get(self):
        return self._path.get()

    def set(self, val):
        self._path.set(val)

    def clear(self):
        self._path.set("")


class FlatButton(ctk.CTkButton):
    """扁平按钮"""

    def __init__(self, parent, text="", command=None, **kwargs):
        super().__init__(
            parent, text=text, font=FONT,
            fg_color=BTN_BG, text_color=BTN_TEXT, cursor="hand2",
            height=32, corner_radius=6,
            **kwargs
        )
        self._cmd = command
        self.configure(command=self._on_click)

    def _on_click(self, event=None):
        if self._cmd:
            self._cmd()


class PrimaryButton(ctk.CTkButton):
    """主操作按钮（中性深灰）"""

    def __init__(self, parent, text="", command=None, **kwargs):
        super().__init__(
            parent, text=text, font=FONT_LG,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
            cursor="hand2", height=36, corner_radius=8,
            **kwargs
        )
        self._cmd = command
        self.configure(command=self._on_click)

    def _on_click(self, event=None):
        if self._cmd:
            self._cmd()


# ── 主应用 ─────────────────────────────────────────────────────────────

class FileEncryptorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FileEncryptor")
        self.root.configure(bg=BG_MAIN)

        # 加载配置
        self.config = get_config()

        # 恢复语言与主题（应用后再建 UI，颜色/文案随主题变化）
        self.lang = self.config.get("ui", "lang", "zh")
        if self.lang not in STRINGS:
            self.lang = "zh"
        self.theme = self.config.get("ui", "theme", "light")
        if self.theme not in THEMES:
            self.theme = "light"
        apply_lang(self.lang)
        apply_theme(self.theme)

        # 实验性图片背景相关配置
        self._image_mode = self.config.getboolean("ui", "image_mode", False)
        self._image_blur = self.config.getint("ui", "image_blur", 0)      # 壁纸模糊
        self._panel_blur = self.config.getint("ui", "panel_blur", 14)     # 面板模糊
        self._image_path = self.config.get("ui", "image_path", "")
        self._bg_canvas = None    # 底层壁纸画布
        self._bg_photo = None
        self._bg_item = None
        self._resize_job = None
        self._render_job = None
        # 取色伪透明状态（缓存与防重入）
        self._cover_cache = None        # 缓存清晰壁纸，供取色复用
        self._tint_map = {}             # id(widget) -> (widget, key)
        self._tint_pending = False
        self._tint_retries = 0
        self._root_x = 0
        self._root_y = 0
        # 毛玻璃面板：图片模式下结构性容器改为 tk.Canvas，直接绘制壁纸模糊裁剪
        self._glass_canvases = []   # 注册的毛玻璃画布列表
        self._glass_items = {}      # canvas id -> image item id
        self._glass_photos = {}     # canvas id -> PhotoImage（保持引用防 GC）
        self._nav_items = {}        # 侧栏画布文本项：mode -> item id
        self._ver_item = None       # 侧栏版本文本项

        # 图片背景模式下，切换主题色无意义，故运行中强制浅色，避免视觉错乱
        if self._image_mode:
            apply_theme("light")

        # 恢复窗口状态
        self._restore_window_state()

        self.root.minsize(760, 540)

        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self._current_mode = "encrypt"
        self._running = False
        self._process = None

        # 动画管理器
        self.anim = AnimationManager(self.root)

        # 页面复用缓存：创建一次，切换时只 show/hide
        self._pages = {}

        self._build_ui()
        self._switch_mode("encrypt")
        self._setup_shortcuts()

        # 窗口尺寸变化时重绘图片背景（防抖），并初始化图片背景布局
        self.root.bind("<Configure>", self._on_root_resize)
        if self._image_mode:
            self.root.after(60, self._apply_imagebg_layout)

        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # 如果没有保存的窗口状态，则居中显示
        if not self.config.getboolean("window", "has_saved_state", False):
            self.root.update_idletasks()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 2 - 30
            self.root.geometry(f"+{x}+{y}")

    def _restore_window_state(self):
        x = self.config.getint("window", "x", -1)
        y = self.config.getint("window", "y", -1)
        width = self.config.getint("window", "width", 880)
        height = self.config.getint("window", "height", 620)

        if x >= 0 and y >= 0:
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        else:
            self.root.geometry(f"{width}x{height}")

    def _save_window_state(self):
        try:
            self.root.update_idletasks()
            self.config.set("window", "x", self.root.winfo_x())
            self.config.set("window", "y", self.root.winfo_y())
            self.config.set("window", "width", self.root.winfo_width())
            self.config.set("window", "height", self.root.winfo_height())
            self.config.set("window", "has_saved_state", True)
            self.config.save()
        except Exception as e:
            print(f"保存窗口状态失败: {e}")

    def _on_closing(self):
        self._save_window_state()
        self.root.destroy()

    def _setup_shortcuts(self):
        self.root.bind("<Control-e>", lambda e: self._switch_mode("encrypt"))
        self.root.bind("<Control-d>", lambda e: self._switch_mode("decrypt"))
        self.root.bind("<Control-E>", lambda e: self._switch_mode("batch_enc"))
        self.root.bind("<Control-D>", lambda e: self._switch_mode("batch_dec"))
        self.root.bind("<Control-l>", lambda e: self._export_log())
        self.root.bind("<Control-w>", lambda e: self._clear_output())
        self.root.bind("<F5>", lambda e: self._refresh())
        self.root.bind("<Escape>", lambda e: self._cancel_operation())

    def _refresh(self):
        pass

    def _cancel_operation(self):
        if self._running:
            self._log(f"[!] {tr('msg_cancel')}")

    # ── 设置 ───────────────────────────────────────────────────────────

    def _apply_settings(self):
        """重建整个界面以应用新的语言/主题/图片背景模式"""
        mode = self._current_mode
        for w in self.root.winfo_children():
            w.destroy()
        self._pages.clear()
        self._bg_canvas = None
        self._bg_photo = None
        self._bg_item = None
        self._glass_canvases = []
        self._glass_items = {}
        self._glass_photos = {}
        self._nav_items = {}
        self._ver_item = None
        # 清空取色缓存：旧控件 id 失效，壁纸尺寸可能变化
        self._cover_cache = None
        self._tint_map = {}
        self._tint_pending = False
        self._tint_retries = 0
        self._build_ui()
        self._switch_mode(mode)
        if self._image_mode:
            self.root.after(60, self._apply_imagebg_layout)

    def _on_language_change(self, label):
        if self._running:
            return
        key = "zh" if label == "中文" else "en"
        if key != self.lang:
            self.lang = key
            self.config.set("ui", "lang", key)
            self.config.save()
            apply_lang(key)
            # 延迟重建，避免回调中销毁触发控件
            self.root.after(0, self._apply_settings)

    def _on_theme_change(self, label):
        if self._running or self._image_mode:
            return
        key = "dark" if label == tr("theme_dark") else "light"
        if key != self.theme:
            self.theme = key
            self.config.set("ui", "theme", key)
            self.config.save()
            apply_theme(key)
            self.root.after(0, self._apply_settings)

    # ── 实验性：图片背景 + 模糊 ────────────────────────────────────────

    def _on_root_resize(self, event):
        """窗口尺寸变化时防抖重绘图片背景；仅当图片背景模式开启且画布已存在"""
        if not self._image_mode or self._bg_canvas is None:
            return
        if getattr(event, "widget", None) is not self.root:
            return
        if self._resize_job is not None:
            try:
                self.root.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.root.after(150, self._render_imagebg)

    def _on_imagebg_toggle(self, checked):
        """实验性功能开关：开启则切换到图片背景模式，关闭则还原"""
        if not _HAVE_PIL:
            messagebox.showwarning(tr("hint"), tr("msg_need_pillow") or
                                   "图片背景功能需要 Pillow，请先安装：pip install pillow")
            self.imagebg_switch.deselect()
            return
        if self._running:
            self.imagebg_switch.select() if checked else self.imagebg_switch.deselect()
            messagebox.showinfo(tr("hint"), tr("msg_busy"))
            return
        if checked and not self._image_path:
            self._on_imagebg_pick()
            if not self._image_path:
                # 用户放弃选择：自动生成默认渐变背景，保证特性开箱即用
                self._image_path = ""
        self._image_mode = bool(checked)
        self.config.set("ui", "image_mode", self._image_mode)
        self.config.save()
        # 开启时忽略主题色（强制浅色基座）并重建界面；关闭时恢复主题色
        if self._image_mode:
            self.theme = "light"
            apply_theme("light")
        else:
            self.theme = self.config.get("ui", "theme", "light")
            if self.theme not in THEMES:
                self.theme = "light"
            apply_theme(self.theme)
        self.root.after(0, self._apply_settings)

    def _on_imagebg_pick(self):
        """选择背景图片文件"""
        p = filedialog.askopenfilename(
            title=tr("select_file"),
            filetypes=[("Image", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All", "*.*")]
        )
        if p:
            self._image_path = p
            self.config.set("ui", "image_path", p)
            self.config.save()
            if self._image_mode and self._bg_canvas is not None:
                self._render_imagebg()

    # ── 模糊值设置（滑杆 + 数值输入，0-50）────────────────────────────

    def _on_wall_blur_change(self, value):
        """壁纸模糊滑杆"""
        self._image_blur = max(0, min(50, int(value)))
        self.config.set("ui", "image_blur", self._image_blur)
        self.config.save()
        self._sync_blur_entry("wall")
        if self._image_mode:
            self._schedule_render()

    def _on_panel_blur_change(self, value):
        """面板模糊滑杆（0 为完全透明）"""
        self._panel_blur = max(0, min(50, int(value)))
        self.config.set("ui", "panel_blur", self._panel_blur)
        self.config.save()
        self._sync_blur_entry("panel")
        if self._image_mode:
            self._schedule_render()

    def _on_blur_entry(self, which):
        """数值输入框提交（Return / 失焦），非法输入回退为当前值"""
        e = getattr(self, f"{which}_blur_entry", None)
        if e is None or not e.winfo_exists():
            return
        try:
            v = int(e.get().strip())
        except ValueError:
            self._sync_blur_entry(which)
            return
        v = max(0, min(50, v))
        if which == "wall":
            self._image_blur = v
            self.config.set("ui", "image_blur", v)
        else:
            self._panel_blur = v
            self.config.set("ui", "panel_blur", v)
        self.config.save()
        s = getattr(self, f"{which}_blur_slider", None)
        if s is not None:
            s.set(v)
        self._sync_blur_entry(which)
        if self._image_mode:
            self._schedule_render()

    def _sync_blur_entry(self, which):
        """让输入框显示当前值"""
        e = getattr(self, f"{which}_blur_entry", None)
        if e is None or not e.winfo_exists():
            return
        v = self._image_blur if which == "wall" else self._panel_blur
        e.delete(0, "end")
        e.insert(0, str(v))

    def _schedule_render(self):
        """防抖重渲染（滑杆拖动时避免每步全量高斯模糊）"""
        if self._render_job is not None:
            try:
                self.root.after_cancel(self._render_job)
            except Exception:
                pass
        self._render_job = self.root.after(120, self._render_imagebg)

    def _load_bg_source(self):
        """加载背景图片源（PIL Image）或生成默认渐变。返回 (w, h, RGBA Image)"""
        path = self._image_path
        if path and os.path.isfile(path):
            try:
                img = PILImage.open(path).convert("RGB")
                return img
            except Exception:
                pass
        # 默认渐变背景（无网络依赖），深灰到浅灰的横向缓变
        W, H = 1920, 1080
        img = PILImage.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)
        for x in range(W):
            t = x / W
            c = tuple(int(0x14 + (0xF0 - 0x14) * t)
                      for _ in range(3))
            draw.line([(x, 0), (x, H)], fill=c)
        return img

    @staticmethod
    def _cover_resize(src, tw, th):
        """cover 等比裁剪缩放，返回 (Image, offset_x, offset_y)"""
        sw, sh = src.size
        scale = max(tw / sw, th / sh)
        nw, nh = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
        img = src.resize((nw, nh), PILImage.LANCZOS)
        ox, oy = (nw - tw) // 2, (nh - th) // 2
        return img, ox, oy

    def _new_panel(self, parent):
        """结构性容器工厂：普通模式返回 CTkFrame；图片模式返回注册的毛玻璃画布，
        由 _render_imagebg 在其上绘制壁纸对应区域的模糊裁剪"""
        if self._image_mode and _HAVE_PIL:
            c = tk.Canvas(parent, highlightthickness=0, bd=0)
            self._glass_canvases.append(c)
            return c
        return ctk.CTkFrame(parent, fg_color=BG_MAIN, corner_radius=0)

    def _apply_imagebg_layout(self):
        """开启图片背景：创建底层壁纸画布、面板四周留边，然后整体渲染。
        面板本身已是毛玻璃画布（见 _new_panel / _build_sidebar_canvas）。"""
        if not _HAVE_PIL or not self._image_mode:
            return
        try:
            if self._bg_canvas is None or not self._bg_canvas.winfo_exists():
                canvas = tk.Canvas(self.root, highlightthickness=0, bd=0)
                canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
                # tk.Canvas 的 lower() 是画布条目操作，须用底层 Tk 命令降层
                self.root.tk.call('lower', canvas._w)
                self._bg_canvas = canvas
            # 面板四周留边，露出壁纸
            self.sidebar.grid_configure(padx=(12, 0), pady=12)
            self.main.grid_configure(padx=12, pady=12)
            self._render_imagebg()
        except Exception as e:
            if not self.root.winfo_exists():
                return
            print(f"图片背景布局异常: {e}")

    def _tint_rules(self):
        # 需要替换的实体色 -> (方向, 系数)：light 向白混合、dark 向黑压暗
        return {
            BG_CARD: ("light", 0.52),    # 卡片：磨砂白玻璃
            INPUT_BG: ("light", 0.60),   # 输入框/下拉框：更亮保证深色文字可读
            OUT_BG: ("dark", 0.55),      # 日志框：深色玻璃配浅色文字
            PROG_TRACK: ("light", 0.35), # 进度条轨道
        }

    def _collect_tint_targets(self):
        """扫描控件树，把需要用到的实体色控件登记到 _tint_map（id -> (widget, key)）。
        已登记控件跳过 cget；仅在控件树变化时才有开销。返回新增数量。"""
        rules = self._tint_rules()
        added = 0

        def walk(w):
            for ch in w.winfo_children():
                yield ch
                yield from walk(ch)

        for w in walk(self.root):
            wid = id(w)
            if wid in self._tint_map:
                continue
            try:
                fg = w.cget("fg_color")
            except Exception:
                continue
            bases = fg if isinstance(fg, (tuple, list)) else (fg,)
            for b in bases:
                if isinstance(b, str) and b in rules:
                    self._tint_map[wid] = (w, b)
                    added += 1
                    break
        return added

    def _sample_tint(self, widget, key, cover, pad=12):
        """对单个控件取色伪透明，返回是否成功（未映射/尺寸过小则 False）"""
        rules = self._tint_rules()
        mode, t = rules[key]
        cw, chh = cover.size
        try:
            if not widget.winfo_ismapped():
                return False
            x = widget.winfo_rootx() - self._root_x
            y = widget.winfo_rooty() - self._root_y
            w = widget.winfo_width()
            h = widget.winfo_height()
            x = max(0, min(x - pad, cw - 2))
            y = max(0, min(y - pad, chh - 2))
            w = min(w + pad * 2, cw - x)
            h = min(h + pad * 2, chh - y)
            if w < 2 or h < 2:
                return False
            avg = cover.crop((x, y, x + w, y + h)).resize(
                (1, 1), PILImage.LANCZOS).getpixel((0, 0))[:3]
            if mode == "light":
                px = tuple(int(v + (255 - v) * t) for v in avg)
            else:
                px = tuple(int(v * t) for v in avg)
            widget.configure(fg_color="#%02x%02x%02x" % px)
            return True
        except Exception:
            return False

    def _do_tint(self):
        """实体色控件"取色伪透明"：把卡片/输入框/日志框等融入毛玻璃背景。
        CTk 控件不支持真透明，以所在位置壁纸取样色作底色折中实现。
        - 只登记一次控件集合（_collect_tint_targets），之后仅对缓存取样，不做全量 cget；
        - 用 _tint_pending 防重入，避免反复重渲染（配合 update_idletasks 只补染一次）。"""
        if not _HAVE_PIL or not self._image_mode:
            self._tint_pending = False
            self._tint_retries = 0
            return
        cover = self._cover_cache
        if cover is None:
            self._tint_pending = False
            return
        try:
            self.root.update_idletasks()   # 布局稳定后再取色，减少空跑
            self._root_x = self.root.winfo_rootx()
            self._root_y = self.root.winfo_rooty()
            self._collect_tint_targets()   # 增量登记新控件（懒加载页面）
            pending = 0
            for _id, (w, key) in list(self._tint_map.items()):
                try:
                    if not self._sample_tint(w, key, cover):
                        pending += 1
                except Exception:
                    pending += 1
            self._tint_pending = False
            # 布局未映射的控件，用 idle 补一次（不再整窗重渲染）
            if pending and self._tint_retries < 3:
                self._tint_retries += 1
                self.root.after_idle(self._do_tint)
            else:
                self._tint_retries = 0
        except Exception as e:
            self._tint_pending = False
            print(f"取色伪透明异常: {e}")

    def _schedule_tint(self):
        """安排一次取色伪透明（防重入，不触发整窗重渲染）"""
        if self._tint_pending or not (self._image_mode and _HAVE_PIL):
            return
        self._tint_pending = True
        self.root.after_idle(self._do_tint)

    def _render_imagebg(self):
        """渲染两层：
        1) 底层画布：整窗壁纸（壁纸模糊 + 轻微压暗），仅窗口边缘露出；
        2) 毛玻璃画布：各面板区域壁纸清晰裁剪 -> 面板模糊 + 随模糊度轻微加深。
        面板上的文字均为画布文本项或上层控件，始终清晰、不受模糊影响。
        取色伪透明不再内嵌于此（独立 _schedule_tint），避免拖动滑块时全量重染。"""
        if not _HAVE_PIL or not self._image_mode:
            return
        cw = self.root.winfo_width()
        ch = self.root.winfo_height()
        if cw <= 10 or ch <= 10:
            return
        try:
            src = self._load_bg_source()
            cover, ox, oy = self._cover_resize(src, cw, ch)
            cover = cover.crop((ox, oy, ox + cw, oy + ch))  # 整窗清晰壁纸
            # 缓存清晰壁纸供取色伪透明复用，尺寸不变则不重算
            if self._cover_cache is None or self._cover_cache.size != cover.size:
                self._cover_cache = cover

            # 1) 底层壁纸
            wp = cover
            if self._image_blur > 0:
                wp = wp.filter(ImageFilter.GaussianBlur(self._image_blur))
            wp = PILImage.eval(wp, lambda v: int(v * 0.88))
            self._bg_photo = ImageTk.PhotoImage(wp)
            if self._bg_canvas is not None and self._bg_canvas.winfo_exists():
                if self._bg_item is None:
                    self._bg_item = self._bg_canvas.create_image(
                        0, 0, image=self._bg_photo, anchor="nw")
                else:
                    self._bg_canvas.itemconfig(self._bg_item, image=self._bg_photo)

            # 2) 毛玻璃面板
            veil = min(0.35, self._panel_blur / 50 * 0.35)
            root_x = self.root.winfo_rootx()
            root_y = self.root.winfo_rooty()
            for c in self._glass_canvases:
                try:
                    if not c.winfo_exists():
                        continue
                    w, h = c.winfo_width(), c.winfo_height()
                    if w < 10 or h < 10:
                        continue
                    x = c.winfo_rootx() - root_x
                    y = c.winfo_rooty() - root_y
                    x = max(0, min(x, cw - 1))
                    y = max(0, min(y, ch - 1))
                    w = min(w, cw - x)
                    h = min(h, ch - y)
                    if w < 10 or h < 10:
                        continue
                    region = cover.crop((x, y, x + w, y + h))
                    if self._panel_blur > 0:
                        region = region.filter(
                            ImageFilter.GaussianBlur(self._panel_blur))
                        if veil > 0:
                            region = PILImage.blend(
                                region,
                                PILImage.new("RGB", region.size, (16, 16, 16)),
                                veil)
                    # 平均色作为画布底色：透明 CTk 子控件会解析为该色，
                    # 视觉上接近重度磨砂，不会突兀
                    avg = region.resize((1, 1), PILImage.LANCZOS).getpixel((0, 0))
                    try:
                        c.configure(bg="#%02x%02x%02x" % avg[:3])
                    except Exception:
                        pass
                    photo = ImageTk.PhotoImage(region)
                    if str(c) in self._glass_photos:
                        self._glass_photos[str(c)] = photo  # 复用引用槽
                    else:
                        self._glass_photos[str(c)] = photo
                    c.delete("glassbg")
                    c.create_image(0, 0, image=photo, anchor="nw",
                                   tags=("glassbg",))
                    c.tag_lower("glassbg")
                except Exception:
                    continue

            # 侧栏版本文字贴底
            if self._ver_item is not None and self.sidebar.winfo_exists():
                try:
                    self.sidebar.coords(self._ver_item, 18,
                                        self.sidebar.winfo_height() - 24)
                except Exception:
                    pass

            # 取色伪透明独立调度（不阻塞、不重复整窗重渲染）
            self._schedule_tint()
        except Exception as e:
            print(f"壁纸渲染异常: {e}")

    # ── 构建 UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        # 主容器
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # ── 侧栏 ──
        self._build_sidebar()

        # ── 内容区 ──
        main = self._new_panel(self.root)
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)
        self.main = main

        self.content = self._new_panel(main)
        self.content.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=0)
        self.content.rowconfigure(1, weight=1)

        # 页面容器（不同模式切换）
        self.page_frame = self._new_panel(self.content)
        self.page_frame.grid(row=0, column=0, sticky="nsew")
        self.page_frame.columnconfigure(0, weight=1)
        self.page_frame.rowconfigure(0, weight=1)

        # 输出区域
        self._build_output()

    def _build_sidebar(self):
        # 图片背景模式：侧栏为毛玻璃画布 + 画布文本项（文字不受模糊影响）
        if self._image_mode and _HAVE_PIL:
            self._build_sidebar_canvas()
            return

        sidebar = ctk.CTkFrame(self.root, fg_color=BG_SIDEBAR, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.columnconfigure(0, weight=1)

        # 标题区域
        head = ctk.CTkFrame(sidebar, fg_color=BG_SIDEBAR, corner_radius=0)
        self.sidebar = sidebar
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(22, 16))
        title = ctk.CTkLabel(
            head, text="FileEncryptor",
            font=(FONT_FAMILY, 14, "bold"),
            text_color=TEXT_LIGHT, anchor="w"
        )
        title.pack(fill="x")
        subtitle = ctk.CTkLabel(
            head, text=tr("app_subtitle"),
            font=(FONT_FAMILY, 9),
            text_color=TEXT_MUTED, anchor="w"
        )
        subtitle.pack(fill="x", pady=(2, 0))

        # 导航按钮
        self.nav_btns = {}
        nav_items = [
            ("encrypt",   "\U0001F512  " + tr("nav_encrypt")),
            ("decrypt",   "\U0001F513  " + tr("nav_decrypt")),
            ("batch_enc", "\u25C9  " + tr("nav_batch_enc")),
            ("batch_dec", "\u25CB  " + tr("nav_batch_dec")),
            ("settings",  "\u2699  " + tr("nav_settings")),
        ]

        for i, (mode, label) in enumerate(nav_items, start=1):
            btn = ctk.CTkLabel(
                sidebar, text=label, font=FONT,
                text_color=NAV_INACTIVE, cursor="hand2",
                anchor="w",
            )
            btn.grid(row=i, column=0, sticky="ew", padx=18, pady=4)
            btn.bind("<Button-1>", lambda e, m=mode: self._switch_mode(m))
            self.nav_btns[mode] = btn

        # 弹性空间（放在所有按钮之后，即第6行）
        spacer = ctk.CTkFrame(sidebar, fg_color=BG_SIDEBAR, corner_radius=0)
        spacer.grid(row=6, column=0, sticky="ew")
        sidebar.rowconfigure(6, weight=1)

        # 底部版本信息
        ver_frame = ctk.CTkFrame(sidebar, fg_color=BG_SIDEBAR, corner_radius=0)
        ver_frame.grid(row=10, column=0, sticky="ew")
        ver = ctk.CTkLabel(
            ver_frame, text="v1.4.1 \u00b7 libsodium",
            font=(FONT_FAMILY, 8), text_color=VER_TEXT,
            anchor="w", padx=18, pady=12,
        )
        ver.pack(fill="x")

    def _build_sidebar_canvas(self):
        """图片背景模式：侧栏为毛玻璃画布。
        标题/导航/版本均为画布文本项，绘制在模糊背景之上，始终清晰。"""
        sb = tk.Canvas(self.root, width=196, highlightthickness=0, bd=0)
        sb.grid(row=0, column=0, sticky="ns")
        self.sidebar = sb
        self._glass_canvases.append(sb)

        sb.create_text(
            18, 30, text="FileEncryptor", anchor="w",
            font=(FONT_FAMILY, 14, "bold"), fill=TEXT_LIGHT)
        sb.create_text(
            18, 50, text=tr("app_subtitle"), anchor="w",
            font=(FONT_FAMILY, 9), fill=TEXT_MUTED)

        nav_items = [
            ("encrypt",   "\U0001F512  " + tr("nav_encrypt")),
            ("decrypt",   "\U0001F513  " + tr("nav_decrypt")),
            ("batch_enc", "\u25C9  " + tr("nav_batch_enc")),
            ("batch_dec", "\u25CB  " + tr("nav_batch_dec")),
            ("settings",  "\u2699  " + tr("nav_settings")),
        ]
        self._nav_items = {}
        y = 92
        for mode, label in nav_items:
            tag = f"nav:{mode}"
            item = sb.create_text(
                18, y, text=label, anchor="w",
                font=FONT, fill=NAV_INACTIVE, tags=(tag,))
            self._nav_items[mode] = item
            sb.tag_bind(tag, "<Enter>", lambda e, m=mode: self._nav_hover(m, True))
            sb.tag_bind(tag, "<Leave>", lambda e, m=mode: self._nav_hover(m, False))
            sb.tag_bind(tag, "<Button-1>", lambda e, m=mode: self._switch_mode(m))
            y += 34

        self._ver_item = sb.create_text(
            18, 80, text="v2.0.0 \u00b7 libsodium",
            anchor="w", font=(FONT_FAMILY, 8), fill=VER_TEXT)
        self._update_nav_canvas()

    def _nav_hover(self, mode, enter):
        """导航项悬停（画布文本项填色）"""
        if mode == self._current_mode:
            return
        try:
            self.sidebar.itemconfig(
                self._nav_items[mode],
                fill=NAV_HOVER if enter else NAV_INACTIVE)
        except Exception:
            pass

    def _update_nav_canvas(self):
        """导航高亮更新（图片背景模式的画布文本项）"""
        for m, item in self._nav_items.items():
            try:
                fill = NAV_ACTIVE if m == self._current_mode else NAV_INACTIVE
                self.sidebar.itemconfig(item, fill=fill)
            except Exception:
                pass

    def _build_output(self):
        """输出日志区域（含进度条）"""
        out_frame = self._new_panel(self.content)
        out_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        out_frame.columnconfigure(0, weight=1)
        out_frame.rowconfigure(0, weight=0)
        out_frame.rowconfigure(1, weight=0)
        out_frame.rowconfigure(2, weight=1)
        self.output_region = out_frame

        # 图片模式下小容器透明，透出毛玻璃画布底色（取自壁纸平均色）
        _fg = "transparent" if self._image_mode else BG_MAIN

        # 进度条
        prog_frame = ctk.CTkFrame(out_frame, fg_color=_fg, corner_radius=0)
        prog_frame.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        self._progress_label = ctk.CTkLabel(
            prog_frame, text="", font=FONT_SM,
            text_color=TEXT_MUTED, anchor="w", width=10,
        )
        self._progress_label.pack(side="left")

        self._progress_bar = ctk.CTkProgressBar(
            prog_frame, width=200, height=6,
            fg_color=PROG_TRACK,
            progress_color=ACCENT,
        )
        self._progress_bar.pack(side="left", fill="x", expand=True)
        self._progress_bar.set(0)

        self._progress_pct = ctk.CTkLabel(
            prog_frame, text="", font=FONT_SM,
            text_color=TEXT_MUTED, anchor="e", width=4,
        )
        self._progress_pct.pack(side="right", padx=(4, 0))

        # 标题行
        head_row = ctk.CTkFrame(out_frame, fg_color=_fg, corner_radius=0)
        head_row.grid(row=1, column=0, sticky="ew")
        ctk.CTkLabel(
            head_row, text="\u25b6 " + tr("log_title"),
            font=FONT_SM, text_color=TEXT_MUTED
        ).pack(side="left")

        export_btn = ctk.CTkLabel(
            head_row, text="\u2193 " + tr("export"), font=FONT_SM,
            text_color=TEXT_MUTED, cursor="hand2", padx=8,
        )
        export_btn.pack(side="right", padx=(0, 8))
        export_btn.bind("<Button-1>", lambda e: self._export_log())
        export_btn.bind("<Enter>", lambda e: export_btn.configure(text_color=ACCENT))
        export_btn.bind("<Leave>", lambda e: export_btn.configure(text_color=TEXT_MUTED))

        self.clear_out_btn = ctk.CTkLabel(
            head_row, text="\u00d7 " + tr("clear"), font=FONT_SM,
            text_color=TEXT_MUTED, cursor="hand2",
        )
        self.clear_out_btn.pack(side="right")
        self.clear_out_btn.bind("<Button-1>", lambda e: self._clear_output())
        self.clear_out_btn.bind("<Enter>", lambda e: self.clear_out_btn.configure(text_color=ERROR))
        self.clear_out_btn.bind("<Leave>", lambda e: self.clear_out_btn.configure(text_color=TEXT_MUTED))

        # 日志文本框
        self.output_text = ctk.CTkTextbox(
            out_frame, font=FONT_MONO, text_color="#c0c0c0", fg_color=OUT_BG,
            border_width=1, border_color=BORDER,
            wrap="word", state="disabled",
            corner_radius=4,
        )
        self.output_text.grid(row=2, column=0, sticky="nsew")

        # 状态栏
        self.status_bar = ctk.CTkLabel(
            out_frame, text=tr("ready"), font=FONT_SM,
            text_color=TEXT_MUTED, anchor="w",
        )
        self.status_bar.grid(row=3, column=0, sticky="ew", pady=(4, 0))

    # ── 页面切换 ───────────────────────────────────────────────────────

    def _switch_mode(self, mode):
        self._current_mode = mode

        # 更新导航高亮（图片模式为画布文本项，普通模式为标签）
        if self._image_mode and self._nav_items:
            self._update_nav_canvas()
        else:
            for m, btn in self.nav_btns.items():
                is_active = m == mode
                btn.configure(text_color=NAV_ACTIVE if is_active else NAV_INACTIVE)
                for seq in ("<Enter>", "<Leave>"):
                    try:
                        btn.unbind(seq)
                    except Exception:
                        pass
                if not is_active:
                    btn.bind("<Enter>", lambda e, b=btn: b.configure(text_color=NAV_HOVER))
                    btn.bind("<Leave>", lambda e, b=btn: b.configure(text_color=NAV_INACTIVE))

        # 设置页不显示日志/进度条区域，其余页面显示
        if getattr(self, "output_region", None) is not None:
            if mode == "settings":
                self.output_region.grid_remove()
            elif not self.output_region.winfo_ismapped():
                self.output_region.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        # 隐藏所有已创建的页面
        for page in self._pages.values():
            page.pack_forget()

        # 创建页面（如果尚未创建）或显示已缓存的页面
        if mode not in self._pages:
            if mode == "encrypt":
                self._pages[mode] = self._build_encrypt_page()
            elif mode == "decrypt":
                self._pages[mode] = self._build_decrypt_page()
            elif mode == "batch_enc":
                self._pages[mode] = self._build_batch_encrypt_page()
            elif mode == "batch_dec":
                self._pages[mode] = self._build_batch_decrypt_page()
            elif mode == "settings":
                self._pages[mode] = self._build_settings_page()

        self._pages[mode].pack(fill="both", expand=True)
        # 图片模式下，懒加载的新页面画布需要绘制毛玻璃背景
        if self._image_mode:
            self.root.after_idle(self._render_imagebg)

        self._set_status(tr("ready"))

    # ── 加密页面 ───────────────────────────────────────────────────────

    def _build_encrypt_page(self):
        page = self._new_panel(self.page_frame)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=0)
        page.rowconfigure(1, weight=1)

        card = ctk.CTkFrame(page, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="\U0001F512  " + tr("encrypt_single"),
            font=FONT_HEAD, text_color=TEXT_DARK,
            anchor="w", padx=16
        ).grid(row=0, column=0, sticky="ew", pady=(14, 4))

        ctk.CTkLabel(
            card, text=tr("encrypt_single_desc"),
            font=FONT_SM, text_color=TEXT_MUTED,
            anchor="w", padx=16
        ).grid(row=1, column=0, sticky="ew", pady=(0, 10))

        sep = ctk.CTkFrame(card, height=1, fg_color=BORDER, corner_radius=0)
        sep.grid(row=2, column=0, sticky="ew", padx=16)

        form = ctk.CTkFrame(card, fg_color=BG_CARD, corner_radius=0)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        row = 0
        self.enc_file = FileSelector(form, tr("source_file"))
        self.enc_file.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        row += 1

        self.enc_pw = PasswordEntry(form, tr("enc_password"))
        self.enc_pw.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        row += 1

        self.enc_pw2 = PasswordEntry(form, tr("confirm_password"))
        self.enc_pw2.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        row += 1

        opt_row = ctk.CTkFrame(form, fg_color=BG_CARD, corner_radius=0)
        opt_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        opt_row.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            opt_row, text=tr("algorithm"), font=FONT_SM, text_color=TEXT_DARK
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.enc_algo = ctk.CTkComboBox(
            opt_row, values=["XChaCha20-Poly1305", "AEGIS-256"],
            state="readonly", font=FONT, width=180,
        )
        self.enc_algo.grid(row=0, column=1, sticky="w")
        self.enc_algo.set("XChaCha20-Poly1305")

        self.enc_del = ctk.CTkFrame(opt_row, fg_color=BG_CARD, corner_radius=0)
        self.enc_del.grid(row=0, column=2, sticky="e", padx=(16, 0))
        ctk.CTkLabel(
            self.enc_del, text=tr("delete_source"), font=FONT_SM,
            text_color=TEXT_DARK,
        ).pack(side="left", padx=(0, 4))
        self.enc_del_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self.enc_del, text="", variable=self.enc_del_var,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(side="left")
        row += 1

        self.enc_out = FileSelector(form, tr("output_dir_auto"), is_dir=True)
        self.enc_out.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 4))
        row += 1

        btn_row = ctk.CTkFrame(card, fg_color=BG_CARD, corner_radius=0)
        btn_row.grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))

        self.enc_go = PrimaryButton(btn_row, tr("start_encrypt"), command=self._do_encrypt)
        self.enc_go.pack(side="right")

        hint = ctk.CTkFrame(
            page, fg_color="transparent" if self._image_mode else BG_MAIN,
            corner_radius=0)
        hint.grid(row=1, column=0, sticky="nw", pady=(8, 0))
        ctk.CTkLabel(
            hint, text="\u2139  " + tr("strength_hint"),
            font=(FONT_FAMILY, 8), text_color=TEXT_MUTED, wraplength=500,
            justify="left",
        ).pack(anchor="w")

        return page

    # ── 解密页面 ───────────────────────────────────────────────────────

    def _build_decrypt_page(self):
        page = self._new_panel(self.page_frame)
        page.columnconfigure(0, weight=1)

        card = ctk.CTkFrame(page, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="\U0001F513  " + tr("decrypt_single"),
            font=FONT_HEAD, text_color=TEXT_DARK,
            anchor="w", padx=16
        ).grid(row=0, column=0, sticky="ew", pady=(14, 4))

        ctk.CTkLabel(
            card, text=tr("decrypt_single_desc"),
            font=FONT_SM, text_color=TEXT_MUTED,
            anchor="w", padx=16
        ).grid(row=1, column=0, sticky="ew", pady=(0, 10))

        sep = ctk.CTkFrame(card, height=1, fg_color=BORDER, corner_radius=0)
        sep.grid(row=2, column=0, sticky="ew", padx=16)

        form = ctk.CTkFrame(card, fg_color=BG_CARD, corner_radius=0)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        self.dec_file = FileSelector(form, tr("enc_file_ptd"))
        self.dec_file.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.dec_pw = PasswordEntry(form, tr("dec_password"))
        self.dec_pw.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.dec_out = FileSelector(form, tr("output_dir_auto"), is_dir=True)
        self.dec_out.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 4))

        btn_row = ctk.CTkFrame(card, fg_color=BG_CARD, corner_radius=0)
        btn_row.grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))
        self.dec_go = PrimaryButton(btn_row, tr("start_decrypt"), command=self._do_decrypt)
        self.dec_go.pack(side="right")

        return page

    # ── 批量加密页面 ───────────────────────────────────────────────────

    def _build_batch_encrypt_page(self):
        page = self._new_panel(self.page_frame)
        page.columnconfigure(0, weight=1)

        card = ctk.CTkFrame(page, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="\u2750  " + tr("batch_enc"),
            font=FONT_HEAD, text_color=TEXT_DARK,
            anchor="w", padx=16
        ).grid(row=0, column=0, sticky="ew", pady=(14, 4))

        ctk.CTkLabel(
            card, text=tr("batch_enc_desc"),
            font=FONT_SM, text_color=TEXT_MUTED,
            anchor="w", padx=16
        ).grid(row=1, column=0, sticky="ew", pady=(0, 10))

        sep = ctk.CTkFrame(card, height=1, fg_color=BORDER, corner_radius=0)
        sep.grid(row=2, column=0, sticky="ew", padx=16)

        form = ctk.CTkFrame(card, fg_color=BG_CARD, corner_radius=0)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        self.benc_dir = FileSelector(form, tr("source_dir"), is_dir=True)
        self.benc_dir.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.benc_pw = PasswordEntry(form, tr("enc_password"))
        self.benc_pw.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.benc_pw2 = PasswordEntry(form, tr("confirm_password"))
        self.benc_pw2.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        opt_row = ctk.CTkFrame(form, fg_color=BG_CARD, corner_radius=0)
        opt_row.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        opt_row.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            opt_row, text=tr("algorithm"), font=FONT_SM, text_color=TEXT_DARK
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.benc_algo = ctk.CTkComboBox(
            opt_row, values=["XChaCha20-Poly1305", "AEGIS-256"],
            state="readonly", font=FONT, width=180,
        )
        self.benc_algo.grid(row=0, column=1, sticky="w")
        self.benc_algo.set("XChaCha20-Poly1305")

        ctk.CTkLabel(
            opt_row, text=tr("threads"), font=FONT_SM, text_color=TEXT_DARK
        ).grid(row=0, column=2, sticky="w", padx=(16, 4))
        self.benc_threads = ctk.CTkComboBox(
            opt_row, values=["1", "2", "4", "8"],
            state="readonly", font=FONT, width=60,
        )
        self.benc_threads.grid(row=0, column=3, sticky="w")
        self.benc_threads.set("4")

        opt_row2 = ctk.CTkFrame(form, fg_color=BG_CARD, corner_radius=0)
        opt_row2.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.benc_del_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            opt_row2, text=tr("delete_source"), font=FONT_SM,
            variable=self.benc_del_var,
            text_color=TEXT_DARK, fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(side="left", padx=(0, 16))

        self.benc_out = FileSelector(form, tr("output_dir"), is_dir=True)
        self.benc_out.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 4))

        btn_row = ctk.CTkFrame(card, fg_color=BG_CARD, corner_radius=0)
        btn_row.grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))
        self.benc_go = PrimaryButton(btn_row, tr("start_batch_enc"), command=self._do_batch_encrypt)
        self.benc_go.pack(side="right")

        return page

    # ── 批量解密页面 ───────────────────────────────────────────────────

    def _build_batch_decrypt_page(self):
        page = self._new_panel(self.page_frame)
        page.columnconfigure(0, weight=1)

        card = ctk.CTkFrame(page, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="\u2751  " + tr("batch_dec"),
            font=FONT_HEAD, text_color=TEXT_DARK,
            anchor="w", padx=16
        ).grid(row=0, column=0, sticky="ew", pady=(14, 4))

        ctk.CTkLabel(
            card, text=tr("batch_dec_desc"),
            font=FONT_SM, text_color=TEXT_MUTED,
            anchor="w", padx=16
        ).grid(row=1, column=0, sticky="ew", pady=(0, 10))

        sep = ctk.CTkFrame(card, height=1, fg_color=BORDER, corner_radius=0)
        sep.grid(row=2, column=0, sticky="ew", padx=16)

        form = ctk.CTkFrame(card, fg_color=BG_CARD, corner_radius=0)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        self.bdec_dir = FileSelector(form, tr("source_dir_ptd"), is_dir=True)
        self.bdec_dir.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.bdec_pw = PasswordEntry(form, tr("dec_password"))
        self.bdec_pw.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        opt_row = ctk.CTkFrame(form, fg_color=BG_CARD, corner_radius=0)
        opt_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        opt_row.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            opt_row, text=tr("threads"), font=FONT_SM, text_color=TEXT_DARK
        ).grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.bdec_threads = ctk.CTkComboBox(
            opt_row, values=["1", "2", "4", "8"],
            state="readonly", font=FONT, width=60,
        )
        self.bdec_threads.grid(row=0, column=1, sticky="w")
        self.bdec_threads.set("4")

        self.bdec_out = FileSelector(form, tr("output_dir"), is_dir=True)
        self.bdec_out.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 4))

        btn_row = ctk.CTkFrame(card, fg_color=BG_CARD, corner_radius=0)
        btn_row.grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))
        self.bdec_go = PrimaryButton(btn_row, tr("start_batch_dec"), command=self._do_batch_decrypt)
        self.bdec_go.pack(side="right")

        return page

    # ── 设置页面 ───────────────────────────────────────────────────────

    def _build_settings_page(self):
        page = self._new_panel(self.page_frame)
        page.columnconfigure(0, weight=1)

        # 基本设置卡片
        card = ctk.CTkFrame(page, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER)
        card.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="\u2699  " + tr("settings"),
            font=FONT_HEAD, text_color=TEXT_DARK,
            anchor="w", padx=16
        ).grid(row=0, column=0, sticky="ew", pady=(14, 4))

        ctk.CTkLabel(
            card, text=tr("settings_desc"),
            font=FONT_SM, text_color=TEXT_MUTED,
            anchor="w", padx=16
        ).grid(row=1, column=0, sticky="ew", pady=(0, 10))

        sep = ctk.CTkFrame(card, height=1, fg_color=BORDER, corner_radius=0)
        sep.grid(row=2, column=0, sticky="ew", padx=16)

        form = ctk.CTkFrame(card, fg_color=BG_CARD, corner_radius=0)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        # 语言
        lang_row = ctk.CTkFrame(form, fg_color=BG_CARD, corner_radius=0)
        lang_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(
            lang_row, text=tr("language"), font=FONT_SM,
            text_color=TEXT_DARK, anchor="w",
        ).pack(side="left")
        self.lang_combo = ctk.CTkComboBox(
            lang_row, values=["中文", "English"], state="readonly",
            font=(FONT_FAMILY, 9), width=120, height=28, fg_color=INPUT_BG,
        )
        self.lang_combo.set("中文" if self.lang == "zh" else "English")
        self.lang_combo.pack(side="right")
        self.lang_combo.configure(command=self._on_language_change)

        # 主题
        theme_row = ctk.CTkFrame(form, fg_color=BG_CARD, corner_radius=0)
        theme_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(
            theme_row, text=tr("theme"), font=FONT_SM,
            text_color=TEXT_DARK, anchor="w",
        ).pack(side="left")
        self.theme_combo = ctk.CTkComboBox(
            theme_row, values=[tr("theme_light"), tr("theme_dark")], state="readonly",
            font=(FONT_FAMILY, 9), width=120, height=28, fg_color=INPUT_BG,
        )
        self.theme_combo.set(tr("theme_light") if self.theme == "light" else tr("theme_dark"))
        self.theme_combo.pack(side="right")
        self.theme_combo.configure(command=self._on_theme_change)
        # 图片背景模式忽略主题色，禁用其切换
        if self._image_mode:
            self.theme_combo.configure(state="disabled")

        # 实验性功能：图片背景
        exp_card = ctk.CTkFrame(page, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER)
        exp_card.grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 16))
        exp_card.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            exp_card, text="\u26A0  " + tr("exp_section"),
            font=FONT_HEAD, text_color=TEXT_DARK,
            anchor="w", padx=16
        ).grid(row=0, column=0, sticky="ew", pady=(14, 4))

        ctk.CTkLabel(
            exp_card, text=tr("exp_note"),
            font=FONT_SM, text_color=TEXT_MUTED,
            anchor="w", padx=16
        ).grid(row=1, column=0, sticky="ew", pady=(0, 10))

        sep2 = ctk.CTkFrame(exp_card, height=1, fg_color=BORDER, corner_radius=0)
        sep2.grid(row=2, column=0, sticky="ew", padx=16)

        exp_form = ctk.CTkFrame(exp_card, fg_color=BG_CARD, corner_radius=0)
        exp_form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        exp_form.columnconfigure(1, weight=1)

        # 启用图片背景
        img_row = ctk.CTkFrame(exp_form, fg_color=BG_CARD, corner_radius=0)
        img_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(
            img_row, text=tr("exp_image_bg"), font=FONT_SM,
            text_color=TEXT_DARK, anchor="w",
        ).pack(side="left")
        self.imagebg_switch = ctk.CTkSwitch(
            img_row, text="", width=50, height=24,
            progress_color=ACCENT,
            command=lambda: self._on_imagebg_toggle(self.imagebg_switch.get()),
        )
        if self._image_mode:
            self.imagebg_switch.select()
        self.imagebg_switch.pack(side="right")

        # 选择图片
        pick_row = ctk.CTkFrame(exp_form, fg_color=BG_CARD, corner_radius=0)
        pick_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(
            pick_row, text=tr("exp_pick_image"), font=FONT_SM,
            text_color=TEXT_DARK, anchor="w",
        ).pack(side="left")
        self.imagebg_pick_btn = ctk.CTkButton(
            pick_row, text="\u2026", width=50, height=26,
            font=(FONT_FAMILY, 10), fg_color=BTN_BG, text_color=BTN_TEXT,
            hover_color=ACCENT_HOVER, command=self._on_imagebg_pick,
        )
        self.imagebg_pick_btn.pack(side="right")

        # 模糊设置：壁纸模糊 / 面板模糊，均支持滑杆与数值输入（0-50）
        blur_specs = (
            (2, "wall", "exp_blur_wall"),
            (3, "panel", "exp_blur_panel"),
        )
        for row_i, which, label_key in blur_specs:
            row = ctk.CTkFrame(exp_form, fg_color=BG_CARD, corner_radius=0)
            row.grid(row=row_i, column=0, sticky="ew", pady=(0, 4))
            ctk.CTkLabel(
                row, text=tr(label_key), font=FONT_SM,
                text_color=TEXT_DARK, anchor="w",
            ).pack(side="left")
            entry = ctk.CTkEntry(
                row, width=52, height=24, font=(FONT_FAMILY, 9),
                fg_color=INPUT_BG, text_color=TEXT_DARK, justify="center",
                border_width=1, border_color=BORDER,
            )
            entry.pack(side="right", padx=(8, 0))
            slider = ctk.CTkSlider(
                row, from_=0, to=50, number_of_steps=50,
                width=110, height=18, progress_color=ACCENT,
                button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                command=(self._on_wall_blur_change if which == "wall"
                         else self._on_panel_blur_change),
            )
            slider.pack(side="right")
            val = self._image_blur if which == "wall" else self._panel_blur
            slider.set(val)
            entry.insert(0, str(val))
            entry.bind("<Return>", lambda e, w=which: self._on_blur_entry(w))
            entry.bind("<FocusOut>", lambda e, w=which: self._on_blur_entry(w))
            setattr(self, f"{which}_blur_slider", slider)
            setattr(self, f"{which}_blur_entry", entry)
            if not self._image_mode:
                slider.configure(state="disabled")
                entry.configure(state="disabled")

        return page

    # ── 执行操作 ───────────────────────────────────────────────────────

    def _log(self, text):
        self.output_text.configure(state="normal")
        self.output_text.insert("end", text + "\n")
        self.output_text.see("end")
        self.output_text.configure(state="disabled")

    def _clear_output(self):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")

    def _export_log(self):
        self.output_text.configure(state="normal")
        log_content = self.output_text.get("1.0", "end").strip()
        self.output_text.configure(state="disabled")

        if not log_content:
            messagebox.showinfo(tr("hint"), tr("msg_log_empty"))
            return

        last_path = self.config.get("paths", "last_export_dir", "")

        file_path = filedialog.asksaveasfilename(
            title=tr("export"),
            defaultextension=".txt",
            initialdir=last_path if last_path else None,
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(log_content)
                export_dir = os.path.dirname(file_path)
                self.config.set("paths", "last_export_dir", export_dir)
                self.config.save()
                self._set_status(f"{tr('msg_log_exported')}: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror(tr("error"), f"{tr('msg_export_fail')}:\n{str(e)}")

    def _set_status(self, text):
        self.status_bar.configure(text=text)

    def _set_busy(self, busy):
        self._running = busy
        self.root.configure(cursor="watch" if busy else "")

    def _reset_progress(self):
        self._progress_bar.set(0)
        self._progress_pct.configure(text="")
        self._progress_label.configure(text="")

    def _set_progress(self, value, label=""):
        self._progress_bar.set(value / 100.0)
        self._progress_pct.configure(text=f"{value}%")
        if label:
            self._progress_label.configure(text=label)

    def _run_async_stream(self, args, desc="", password=None, password2=None,
                          timeout=600, overwrite=None, fallback=None):
        """在后台线程中流式运行并实时显示输出"""
        if self._running:
            self._log(f"[!] {tr('msg_busy')}")
            return

        self._set_busy(True)
        self._reset_progress()
        self._log("─" * 50)
        self._log(f"[>] {desc}")
        self._set_status(tr("running"))

        def run():
            exit_code = -1
            collected = []
            try:
                for line_text, progress, err in run_fileencryptor_stream(
                    args, password=password, password2=password2,
                    timeout=timeout, overwrite=overwrite, fallback=fallback
                ):
                    if line_text:
                        collected.append(line_text)
                        self.root.after(0, self._log, line_text)

                    if progress:
                        cur, total = progress
                        if total and total > 0:
                            pct = int(cur * 100 / total)
                            pct = max(0, min(100, pct))
                            label = f"{cur / 1048576.0:.1f}/{total / 1048576.0:.1f} MiB"
                            self.root.after(0, self._set_progress, pct, label)

                    if err:
                        if isinstance(err, int):
                            exit_code = err
                        else:
                            collected.append(f"[!] {err}")
                            self.root.after(0, self._log, f"[!] {err}")

                if exit_code == -1:
                    exit_code = 0

            except Exception as e:
                exit_code = -1
                self.root.after(0, self._log, f"[!] 异常: {e}")

            self.root.after(0, self._on_stream_result, exit_code, collected, desc)

        threading.Thread(target=run, daemon=True).start()

    def _on_stream_result(self, exit_code, lines, desc):
        self._set_busy(False)

        self._set_progress(100, tr("done"))

        if exit_code == 0:
            self._log(f"[OK] {desc} {tr('done')}")
            self._set_status(tr("done"))
        else:
            self._log(f"[FAIL] {desc} {tr('failed')} (exit={exit_code})")
            self._set_status(tr("failed"))

        self._log("─" * 50)

        # 3 秒后自动清除进度条
        self.root.after(3000, self._reset_progress)

    # ── 加密执行 ───────────────────────────────────────────────────────

    def _do_encrypt(self):
        src = self.enc_file.get().strip()
        pw = self.enc_pw.get()
        pw2 = self.enc_pw2.get()
        out = self.enc_out.get().strip()
        algo = self.enc_algo.get()
        delete = self.enc_del_var.get()

        if not src:
            messagebox.showwarning(tr("hint"), tr("msg_select_enc_file"))
            return
        if not pw:
            messagebox.showwarning(tr("hint"), tr("msg_enter_enc_pw"))
            return
        if pw != pw2:
            messagebox.showwarning(tr("hint"), tr("msg_pw_mismatch"))
            return
        if not os.path.isfile(src):
            messagebox.showerror(tr("error"), tr("msg_src_not_exist"))
            return

        args = ["-e", src]
        if out:
            if not os.path.isdir(out):
                try:
                    os.makedirs(out, exist_ok=True)
                except Exception:
                    messagebox.showerror(tr("error"), tr("msg_cannot_create_dir"))
                    return
            args += ["-o", out]
        if algo.startswith("XChaCha20"):
            args += ["-m", "xchacha20"]
        if delete:
            args.append("-de")
        args.append("-y")

        self._run_async_stream(
            args,
            desc=f"{tr('start_encrypt')}: {os.path.basename(src)}",
            password=pw, password2=pw,
            timeout=600, overwrite="y", fallback="n",
        )

    # ── 解密执行 ───────────────────────────────────────────────────────

    def _do_decrypt(self):
        src = self.dec_file.get().strip()
        pw = self.dec_pw.get()
        out = self.dec_out.get().strip()

        if not src:
            messagebox.showwarning(tr("hint"), tr("msg_select_ptd"))
            return
        if not pw:
            messagebox.showwarning(tr("hint"), tr("msg_enter_dec_pw"))
            return
        if not os.path.isfile(src):
            messagebox.showerror(tr("error"), tr("msg_file_not_exist"))
            return
        if not src.lower().endswith(".ptd"):
            messagebox.showwarning(tr("hint"), tr("msg_not_ptd"))
            return

        args = ["-d", src]
        if out:
            if not os.path.isdir(out):
                try:
                    os.makedirs(out, exist_ok=True)
                except Exception:
                    messagebox.showerror(tr("error"), tr("msg_cannot_create_dir"))
                    return
            args += ["-o", out]
        args.append("-y")

        self._run_async_stream(
            args,
            desc=f"{tr('start_decrypt')}: {os.path.basename(src)}",
            password=pw, timeout=600, overwrite="y",
        )

    # ── 批量加密 ───────────────────────────────────────────────────────

    def _do_batch_encrypt(self):
        src = self.benc_dir.get().strip()
        pw = self.benc_pw.get()
        pw2 = self.benc_pw2.get()
        out = self.benc_out.get().strip()
        algo = self.benc_algo.get()
        threads = self.benc_threads.get()
        delete = self.benc_del_var.get()

        if not src:
            messagebox.showwarning(tr("hint"), tr("msg_select_src_dir"))
            return
        if not pw:
            messagebox.showwarning(tr("hint"), tr("msg_enter_enc_pw"))
            return
        if pw != pw2:
            messagebox.showwarning(tr("hint"), tr("msg_pw_mismatch"))
            return
        if not os.path.isdir(src):
            messagebox.showerror(tr("error"), tr("msg_src_dir_not_exist"))
            return

        args = ["-be", "-i", src]
        if out:
            args += ["-o", out]
        if algo.startswith("AEGIS"):
            args += ["-m", "aegis256"]
        if threads:
            args += ["-j", threads]
        if delete:
            args.append("-de")
        args.append("-y")

        self._run_async_stream(
            args,
            desc=f"{tr('start_batch_enc')}: {os.path.basename(src)}",
            password=pw, password2=pw,
            timeout=1800, overwrite="y", fallback="n",
        )

    # ── 批量解密 ───────────────────────────────────────────────────────

    def _do_batch_decrypt(self):
        src = self.bdec_dir.get().strip()
        pw = self.bdec_pw.get()
        out = self.bdec_out.get().strip()
        threads = self.bdec_threads.get()

        if not src:
            messagebox.showwarning(tr("hint"), tr("msg_select_src_dir"))
            return
        if not pw:
            messagebox.showwarning(tr("hint"), tr("msg_enter_dec_pw"))
            return
        if not os.path.isdir(src):
            messagebox.showerror(tr("error"), tr("msg_src_dir_not_exist"))
            return

        args = ["-bd", "-i", src]
        if out:
            args += ["-o", out]
        if threads:
            args += ["-j", threads]
        args.append("-y")

        self._run_async_stream(
            args,
            desc=f"{tr('start_batch_dec')}: {os.path.basename(src)}",
            password=pw, timeout=1800, overwrite="y",
        )

    # ── 启动 ──────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


# ── 入口 ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 检查 tkinter 可用性
    try:
        root = tk.Tk()
        root.withdraw()
        root.destroy()
    except Exception as e:
        print(f"[ERROR] tkinter 不可用：{e}")
        print("请确保系统安装了 Python 的 tkinter 支持。")
        print("Windows: 重新安装 Python 时勾选 'tcl/tk and IDLE'")
        input("按 Enter 退出...")
        sys.exit(1)

    app = FileEncryptorGUI()
    app.run()