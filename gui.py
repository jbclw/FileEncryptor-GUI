#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileEncryptor GUI —— 文件加密工具图形界面
基于 FileEncryptor.exe 命令行工具的封装
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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

try:
    import winpty
except ImportError:
    winpty = None

try:
    import psutil
except ImportError:
    psutil = None

def find_helper_python():
    """找到有 winpty 的 Python"""
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

# ── 配置 ──────────────────────────────────────────────────────────────────

# 可执行文件查找策略（按优先级）：
# 1. gui.py 同目录下的 FileEncryptor.exe
# 2. gui.py 的父目录（即项目根目录）
# 3. 父目录的父目录
# 4. 系统 PATH
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXE_CANDIDATES = [
    os.path.join(_SCRIPT_DIR, "FileEncryptor.exe"),           # 同目录
    os.path.join(_SCRIPT_DIR, "..", "FileEncryptor.exe"),     # 父目录
    os.path.join(_SCRIPT_DIR, "..", "..", "FileEncryptor.exe"),# 祖父目录
    "FileEncryptor.exe",                                        # PATH
]

def find_exe():
    """查找可执行文件路径"""
    for p in EXE_CANDIDATES:
        absp = os.path.abspath(p)
        if os.path.isfile(absp):
            return absp
    # 全没找到，返回最后一个候选
    return os.path.abspath(EXE_CANDIDATES[-1])


# 基础颜色
BG_MAIN = "#f5f0e8"       # 暖白底
BG_SIDEBAR = "#2c2822"    # 深灰棕侧栏
BG_CARD = "#faf6ef"       # 卡片底色
TEXT_DARK = "#2c2822"     # 深色文字
TEXT_MUTED = "#7a7268"    # 灰色文字
TEXT_LIGHT = "#e8e2d8"    # 浅色文字
ACCENT = "#b8864a"        # 暖金棕
ACCENT_HOVER = "#a0763a"  # 暖金棕深
BORDER = "#d8d0c4"        # 边框色
SUCCESS = "#6b8f6b"       # 暗绿
ERROR = "#b35a5a"         # 暗红
INPUT_BG = "#ffffff"      # 输入框白底
BTN_BG = "#e8e0d4"        # 按钮底色
BTN_TEXT = "#2c2822"      # 按钮文字

# 字体
FONT = ("Segoe UI", 10)
FONT_SM = ("Segoe UI", 9)
FONT_LG = ("Segoe UI", 12, "bold")
FONT_MONO = ("Consolas", 10)
FONT_HEAD = ("Segoe UI", 11, "bold")

# 动画配置
ANIM_DURATION = 200  # 毫秒
ANIM_EASING = "ease-out"


class AnimationManager:
    """动画管理器"""
    
    def __init__(self, root):
        self.root = root
        self.animations = {}
        self.anim_id = 0
    
    def animate(self, widget, prop, start, end, duration=ANIM_DURATION, callback=None):
        """执行属性动画"""
        self.anim_id += 1
        anim_key = f"{widget}_{prop}_{self.anim_id}"
        
        steps = max(10, duration // 16)  # 60fps
        step_duration = duration // steps
        
        # 解析颜色或数值
        if start.startswith("#") and end.startswith("#"):
            values = self._interpolate_color(start, end, steps)
        else:
            values = self._interpolate_number(float(start), float(end), steps)
        
        def animate_step(step):
            if step >= len(values):
                if callback:
                    callback()
                return
            
            try:
                if prop in ("bg", "fg", "background", "foreground"):
                    widget.config(**{prop: values[step]})
                else:
                    widget.config(**{prop: values[step]})
            except:
                pass
            
            self.root.after(step_duration, lambda: animate_step(step + 1))
        
        animate_step(0)
        return anim_key
    
    def _interpolate_color(self, start, end, steps):
        """颜色插值"""
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        def rgb_to_hex(rgb):
            return "#{:02x}{:02x}{:02x}".format(*rgb)
        
        start_rgb = hex_to_rgb(start)
        end_rgb = hex_to_rgb(end)
        
        colors = []
        for i in range(steps):
            t = i / (steps - 1) if steps > 1 else 0
            r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * t)
            g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * t)
            b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * t)
            colors.append(rgb_to_hex((r, g, b)))
        
        return colors
    
    def _interpolate_number(self, start, end, steps):
        """数值插值"""
        values = []
        for i in range(steps):
            t = i / (steps - 1) if steps > 1 else 0
            values.append(start + (end - start) * t)
        return values
    
    def fade_in(self, widget, duration=ANIM_DURATION, callback=None):
        """淡入效果"""
        try:
            widget.update_idletasks()
            self.animate(widget, "alpha", 0.0, 1.0, duration, callback)
        except:
            if callback:
                callback()
    
    def slide_in(self, widget, direction="left", distance=20, duration=ANIM_DURATION, callback=None):
        """滑入效果"""
        try:
            widget.update_idletasks()
            # 简单实现：通过透明度模拟
            self.animate(widget, "alpha", 0.0, 1.0, duration, callback)
        except:
            if callback:
                callback()


class LoadingIndicator(tk.Canvas):
    """加载指示器"""
    
    def __init__(self, parent, size=20, color=ACCENT, **kwargs):
        super().__init__(parent, width=size, height=size, 
                        bg=parent.cget("bg"), highlightthickness=0, **kwargs)
        self.size = size
        self.color = color
        self.angle = 0
        self.running = False
        self.dots = 8
        
    def start(self):
        """开始动画"""
        if self.running:
            return
        self.running = True
        self._animate()
    
    def stop(self):
        """停止动画"""
        self.running = False
        self.delete("all")
    
    def _animate(self):
        """动画循环"""
        if not self.running:
            return
        
        self.delete("all")
        
        center = self.size // 2
        radius = self.size // 2 - 2
        
        for i in range(self.dots):
            angle = self.angle + (i * 360 / self.dots)
            rad = angle * 3.14159 / 180
            x = center + radius * 0.6 * (1 + 0.3 * (i / self.dots)) * (1 - 0.5 * (1 + (i % 2))) * (1 if i % 2 == 0 else 0.7)
            y = center + radius * 0.6 * (1 + 0.3 * (i / self.dots)) * (1 - 0.5 * (1 + (i % 2))) * (1 if i % 2 == 0 else 0.7)
            
            # 计算位置
            import math
            x = center + radius * 0.5 * math.cos(rad)
            y = center + radius * 0.5 * math.sin(rad)
            
            # 透明度效果
            alpha = (i + 1) / self.dots
            dot_size = 2 + alpha * 1.5
            
            self.create_oval(
                x - dot_size, y - dot_size,
                x + dot_size, y + dot_size,
                fill=self.color, outline=""
            )
        
        self.angle = (self.angle + 30) % 360
        self.after(80, self._animate)


def run_fileencryptor_stream(args, password=None, password2=None, timeout=300,
                              overwrite=None, fallback=None):
    """
    通过 _runner.py + winpty 流式运行 FileEncryptor.exe
    解决 _getch() 密码输入问题：伪终端模拟键盘输入

    Yields (line_text, progress_info, error) 三元组
      - line_text: 当前行文本（空字符串表示控制消息）
      - progress_info: (current, total) 或 None
      - error: 错误文本（空字符串表示正常），最后一条为退出码(整数)
    """
    global _HELPER_PYTHON
    exe = find_exe()

    # 查找有 winpty 的 Python
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
    args_json = json.dumps(args)
    ow = "" if overwrite is None else ("y" if overwrite else "n")
    fb = "" if fallback is None else ("y" if fallback else "n")
    pw1 = password or ""
    pw2 = password2 or ""

    cmd = [
        _HELPER_PYTHON, runner_script,
        exe, args_json, pw1, pw2, ow, fb, str(int(timeout))
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
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

        # 按行处理
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.rstrip("\r")

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

            # 解析进度
            progress = None
            m = re.search(r'\[(\d+)\s*/\s*(\d+)\]', line)
            if m:
                progress = (int(m.group(1)), int(m.group(2)))
            else:
                m2 = re.match(r'enc:\s*(\d+)\s+dec:\s*(\d+)', line)
                if m2:
                    progress = (int(m2.group(1)) + int(m2.group(2)), None)

            if line.strip():
                yield (line, progress, "")

    # 处理 buffer 中剩余内容
    if buffer.strip():
        line = buffer.rstrip("\r")
        if line.startswith("__EXIT__:"):
            try:
                exit_code = int(line.split(":", 1)[1])
            except ValueError:
                exit_code = -1
        elif line.startswith("__ERR__:"):
            pass
        elif line.strip():
            yield (line, None, "")

    yield ("", None, exit_code)


# ── 自定义控件 ────────────────────────────────────────────────────────────

class PasswordEntry(tk.Frame):
    """带显隐切换的密码输入框"""

    def __init__(self, parent, label="", **kwargs):
        super().__init__(parent, bg=BG_CARD)
        self.show_password = False
        self._password = tk.StringVar()

        # 标签
        self.lbl = tk.Label(
            self, text=label, font=FONT_SM, fg=TEXT_DARK,
            bg=BG_CARD, anchor="w"
        )
        self.lbl.pack(fill="x", pady=(0, 2))

        # 输入行
        row = tk.Frame(self, bg=BG_CARD)
        row.pack(fill="x")

        self.entry = tk.Entry(
            row, textvariable=self._password, show="\u2022",
            font=FONT, bg=INPUT_BG, fg=TEXT_DARK,
            relief="solid", bd=1, highlightthickness=0,
            insertbackground=TEXT_DARK,
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=3)

        self.toggle_btn = tk.Label(
            row, text="\u25cf", font=("Segoe UI", 12),
            bg=INPUT_BG, fg=TEXT_MUTED, cursor="hand2",
            padx=6,
        )
        self.toggle_btn.pack(side="right", before=self.entry)
        self.toggle_btn.bind("<Button-1>", self._toggle_show)

        # 密码强度指示
        self.strength = tk.Frame(self, height=3, bg=BG_CARD)
        self.strength.pack(fill="x", pady=(3, 0))
        self.strength_bar = tk.Frame(self.strength, bg=BG_CARD)
        self.strength_bar.place(x=0, y=0, relwidth=0, relheight=1)

        self._password.trace_add("write", self._update_strength)

    def _toggle_show(self, event=None):
        self.show_password = not self.show_password
        self.entry.config(show="" if self.show_password else "\u2022")
        self.toggle_btn.config(text="\u25cb" if self.show_password else "\u25cf")

    def _update_strength(self, *args):
        pwd = self._password.get()
        w = 0
        if len(pwd) >= 8:
            w += 0.3
        if re.search(r"[A-Z]", pwd) and re.search(r"[a-z]", pwd):
            w += 0.2
        if re.search(r"\d", pwd):
            w += 0.2
        if re.search(r"[^a-zA-Z0-9]", pwd):
            w += 0.3
        w = min(w, 1.0)

        if w < 0.3:
            color = ERROR
        elif w < 0.6:
            color = "#c4a050"
        else:
            color = SUCCESS

        self.strength_bar.config(bg=color)
        self.strength_bar.place(relwidth=w, relheight=1)

    def get(self):
        return self._password.get()

    def set(self, val):
        self._password.set(val)

    def clear(self):
        self._password.set("")


class FileSelector(tk.Frame):
    """文件/目录选择器"""

    def __init__(self, parent, label="", is_dir=False, **kwargs):
        super().__init__(parent, bg=BG_CARD)
        self.is_dir = is_dir
        self._path = tk.StringVar()

        self.lbl = tk.Label(
            self, text=label, font=FONT_SM, fg=TEXT_DARK,
            bg=BG_CARD, anchor="w"
        )
        self.lbl.pack(fill="x", pady=(0, 2))

        row = tk.Frame(self, bg=BG_CARD)
        row.pack(fill="x")

        self.entry = tk.Entry(
            row, textvariable=self._path,
            font=FONT, bg=INPUT_BG, fg=TEXT_DARK,
            relief="solid", bd=1, highlightthickness=0,
            insertbackground=TEXT_DARK,
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=3)

        self.btn = tk.Label(
            row, text="\u2026", font=("Segoe UI", 14),
            bg=INPUT_BG, fg=TEXT_DARK, cursor="hand2",
            padx=8, pady=0,
        )
        self.btn.pack(side="right", before=self.entry)
        self.btn.bind("<Button-1>", self._browse)

    def _browse(self, event=None):
        if self.is_dir:
            p = filedialog.askdirectory(title="选择目录")
        else:
            p = filedialog.askopenfilename(title="选择文件")
        if p:
            self._path.set(p)

    def get(self):
        return self._path.get()

    def set(self, val):
        self._path.set(val)

    def clear(self):
        self._path.set("")


class FlatButton(tk.Label):
    """扁平按钮"""

    def __init__(self, parent, text="", command=None, **kwargs):
        super().__init__(
            parent, text=text, font=FONT,
            bg=BTN_BG, fg=BTN_TEXT, cursor="hand2",
            padx=20, pady=6,
            **kwargs
        )
        self._cmd = command
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda e: self.config(bg="#dcd4c4"))
        self.bind("<Leave>", lambda e: self.config(bg=BTN_BG))

    def _on_click(self, event=None):
        if self._cmd:
            self._cmd()


class PrimaryButton(tk.Label):
    """主操作按钮（暖金色）"""

    def __init__(self, parent, text="", command=None, **kwargs):
        super().__init__(
            parent, text=text, font=FONT_LG,
            bg=ACCENT, fg="#ffffff", cursor="hand2",
            padx=28, pady=8,
            **kwargs
        )
        self._cmd = command
        self._original_bg = ACCENT
        self._hover_bg = ACCENT_HOVER
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress>", self._on_press)
        self.bind("<ButtonRelease>", self._on_release)

    def _on_click(self, event=None):
        if self._cmd:
            self._cmd()
    
    def _on_enter(self, event=None):
        """鼠标进入 - 平滑过渡"""
        self.config(bg=self._hover_bg)
    
    def _on_leave(self, event=None):
        """鼠标离开 - 平滑过渡"""
        self.config(bg=self._original_bg)
    
    def _on_press(self, event=None):
        """鼠标按下 - 按压效果"""
        self.config(bg="#9a6a3a")
    
    def _on_release(self, event=None):
        """鼠标释放"""
        if self.winfo_containing(event.x_root, event.y_root) == self:
            self.config(bg=self._hover_bg)
        else:
            self.config(bg=self._original_bg)


# ── 主应用 ────────────────────────────────────────────────────────────────

class FileEncryptorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FileEncryptor")
        self.root.geometry("880x620")
        self.root.minsize(760, 540)
        self.root.configure(bg=BG_MAIN)

        # 窗口图标（如果有）
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

        # 居中显示
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2 - 30
        self.root.geometry(f"+{x}+{y}")

    # ── 构建 UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        # 主容器
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # ── 侧栏 ──
        self._build_sidebar()

        # ── 内容区 ──
        main = tk.Frame(self.root, bg=BG_MAIN)
        main.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=0)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        self.content = tk.Frame(main, bg=BG_MAIN)
        self.content.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=0)
        self.content.rowconfigure(1, weight=1)

        # 页面容器（不同模式切换）
        self.page_frame = tk.Frame(self.content, bg=BG_MAIN)
        self.page_frame.grid(row=0, column=0, sticky="nsew")
        self.page_frame.columnconfigure(0, weight=1)
        self.page_frame.rowconfigure(0, weight=1)

        # 输出区域
        self._build_output()

    def _build_sidebar(self):
        sidebar = tk.Frame(self.root, bg=BG_SIDEBAR)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.columnconfigure(0, weight=1)

        # 标题区域
        head = tk.Frame(sidebar, bg=BG_SIDEBAR)
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(22, 16))
        title = tk.Label(
            head, text="FileEncryptor",
            font=("Segoe UI", 14, "bold"),
            bg=BG_SIDEBAR, fg=TEXT_LIGHT, anchor="w"
        )
        title.pack(fill="x")
        subtitle = tk.Label(
            head, text="文件加密工具",
            font=("Segoe UI", 9),
            bg=BG_SIDEBAR, fg="#8a8278", anchor="w"
        )
        subtitle.pack(fill="x", pady=(2, 0))

        # 导航按钮
        self.nav_btns = {}
        nav_items = [
            ("encrypt",  "\U0001F512  加密文件"),
            ("decrypt",  "\U0001F513  解密文件"),
            ("batch_enc", "\u25C9  批量加密"),
            ("batch_dec", "\u25CB  批量解密"),
        ]

        for i, (mode, label) in enumerate(nav_items, start=1):
            btn = tk.Label(
                sidebar, text=label, font=FONT,
                bg=BG_SIDEBAR, fg="#a09888", cursor="hand2",
                padx=18, pady=8, anchor="w",
            )
            btn.grid(row=i, column=0, sticky="ew")
            btn.bind("<Button-1>", lambda e, m=mode: self._switch_mode(m))
            self.nav_btns[mode] = btn

        # 弹性空间
        spacer = tk.Frame(sidebar, bg=BG_SIDEBAR)
        spacer.grid(row=5, column=0, sticky="ew", pady=0)
        sidebar.rowconfigure(5, weight=1)

        # 底部版本信息（用 pack 固定在底部）
        ver_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        ver_frame.grid(row=10, column=0, sticky="ew")
        ver = tk.Label(
            ver_frame, text="v1.1.1 \u00b7 libsodium",
            font=("Segoe UI", 8), fg="#5a544c",
            bg=BG_SIDEBAR, anchor="w", padx=18, pady=12,
        )
        ver.pack(fill="x")

    def _build_output(self):
        """输出日志区域（含进度条）"""
        out_frame = tk.Frame(self.content, bg=BG_MAIN)
        out_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        out_frame.columnconfigure(0, weight=1)
        out_frame.rowconfigure(0, weight=0)
        out_frame.rowconfigure(1, weight=0)
        out_frame.rowconfigure(2, weight=1)

        # 进度条
        prog_frame = tk.Frame(out_frame, bg=BG_MAIN)
        prog_frame.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        self._progress_label = tk.Label(
            prog_frame, text="", font=FONT_SM,
            fg=TEXT_MUTED, bg=BG_MAIN, anchor="w", width=10,
        )
        self._progress_label.pack(side="left")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Encrypt.Horizontal.TProgressbar",
            background=ACCENT,
            troughcolor="#e0d8cc",
            bordercolor=BORDER,
            lightcolor=ACCENT,
            darkcolor=ACCENT_HOVER,
            thickness=6,
        )

        self._progress_bar = ttk.Progressbar(
            prog_frame, style="Encrypt.Horizontal.TProgressbar",
            mode="determinate", length=200,
        )
        self._progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 0))
        self._progress_bar["value"] = 0

        self._progress_pct = tk.Label(
            prog_frame, text="", font=FONT_SM,
            fg=TEXT_MUTED, bg=BG_MAIN, anchor="e", width=4,
        )
        self._progress_pct.pack(side="right", padx=(4, 0))

        # 标题行
        head_row = tk.Frame(out_frame, bg=BG_MAIN)
        head_row.grid(row=1, column=0, sticky="ew")
        tk.Label(
            head_row, text="\u25b6 运行日志",
            font=FONT_SM, fg=TEXT_MUTED, bg=BG_MAIN
        ).pack(side="left")

        self.clear_out_btn = tk.Label(
            head_row, text="\u00d7 清除", font=FONT_SM,
            fg=TEXT_MUTED, bg=BG_MAIN, cursor="hand2",
        )
        self.clear_out_btn.pack(side="right")
        self.clear_out_btn.bind("<Button-1>", lambda e: self._clear_output())

        # 日志文本框
        out_bg = "#1e1e1e"
        self.output_text = tk.Text(
            out_frame, font=FONT_MONO, fg="#c0b8a8", bg=out_bg,
            relief="solid", bd=1, highlightthickness=0,
            padx=10, pady=8, wrap="word", state="disabled",
            cursor="arrow",
        )
        self.output_text.grid(row=2, column=0, sticky="nsew")

        # 滚动条
        scroll = tk.Scrollbar(
            out_frame, orient="vertical",
            command=self.output_text.yview,
            bg=out_bg, troughcolor="#2a2a2a",
        )
        scroll.grid(row=2, column=1, sticky="ns")
        self.output_text.config(yscrollcommand=scroll.set)

        # 状态栏
        self.status_bar = tk.Label(
            out_frame, text="就绪", font=FONT_SM,
            fg=TEXT_MUTED, bg=BG_MAIN, anchor="w",
        )
        self.status_bar.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    # ── 页面预加载 ────────────────────────────────────────────────────────

    def _preload_pages(self):
        """异步预加载其他页面"""
        modes = ["decrypt", "batch_enc", "batch_dec"]
        for i, mode in enumerate(modes):
            self.root.after(100 * (i + 1), lambda m=mode: self._preload_page(m))
    
    def _preload_page(self, mode):
        """预加载单个页面"""
        if mode in self._pages_loaded:
            return
        
        # 临时隐藏页面
        temp_frame = tk.Frame(self.page_frame, bg=BG_MAIN)
        
        # 构建页面
        if mode == "encrypt":
            self._build_encrypt_page()
        elif mode == "decrypt":
            self._build_decrypt_page()
        elif mode == "batch_enc":
            self._build_batch_encrypt_page()
        elif mode == "batch_dec":
            self._build_batch_decrypt_page()
        
        # 立即隐藏
        for w in self.page_frame.winfo_children():
            w.pack_forget()
        
        self._pages_loaded.add(mode)
        
        # 切回当前模式
        self._switch_mode(self._current_mode, animate=False)

    # ── 页面切换 ──────────────────────────────────────────────────────────

    def _switch_mode(self, mode, animate=True):
        self._current_mode = mode

        # 更新导航高亮
        for m, btn in self.nav_btns.items():
            is_active = m == mode
            btn.config(
                bg="#3d3832" if is_active else BG_SIDEBAR,
                fg="#e8e2d8" if is_active else "#a09888",
            )
            # 清除旧绑定再重新绑定 hover
            for seq in ("<Enter>", "<Leave>"):
                try:
                    btn.unbind(seq)
                except Exception:
                    pass
            if not is_active:
                btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#3a3530"))
                btn.bind("<Leave>", lambda e, b=btn: b.config(bg=BG_SIDEBAR))

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

        # 显示当前页面
        self._pages[mode].pack(fill="both", expand=True)

        self._set_status("就绪")
        
        # 页面切换动画
        if animate and hasattr(self, 'page_frame'):
            try:
                current = self._pages[mode]
                self.root.after(10, lambda: self._fade_in_widget(current))
            except:
                pass
    
    def _fade_in_widget(self, widget, alpha=0.0, step=0.1):
        """淡入效果（通过背景色模拟）"""
        if alpha >= 1.0:
            return
        try:
            # 通过逐渐改变背景色模拟淡入
            alpha = min(1.0, alpha + step)
            self.root.after(20, lambda: self._fade_in_widget(widget, alpha, step))
        except:
            pass

    # ── 加密页面 ──────────────────────────────────────────────────────────

    def _build_encrypt_page(self):
        page = tk.Frame(self.page_frame, bg=BG_MAIN)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=0)
        page.rowconfigure(1, weight=1)

        # 卡片
        card = tk.Frame(page, bg=BG_CARD, relief="solid", bd=1, highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=0, column=0, sticky="ew", pady=(0, 0))
        card.columnconfigure(0, weight=1)

        # 标题
        tk.Label(
            card, text="\U0001F512  加密单个文件",
            font=FONT_HEAD, fg=TEXT_DARK, bg=BG_CARD,
            anchor="w", padx=16
        ).grid(row=0, column=0, sticky="ew", pady=(14, 4))

        tk.Label(
            card, text="选择一个文件，设置密码后加密为 .ptd 格式",
            font=FONT_SM, fg=TEXT_MUTED, bg=BG_CARD,
            anchor="w", padx=16
        ).grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # 分隔
        sep = tk.Frame(card, height=1, bg=BORDER)
        sep.grid(row=2, column=0, sticky="ew", padx=16)

        # 表单区域
        form = tk.Frame(card, bg=BG_CARD)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        row = 0
        self.enc_file = FileSelector(form, "源文件")
        self.enc_file.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        row += 1

        self.enc_pw = PasswordEntry(form, "加密密码")
        self.enc_pw.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        row += 1

        self.enc_pw2 = PasswordEntry(form, "确认密码")
        self.enc_pw2.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        row += 1

        # 算法选择 + 输出选项
        opt_row = tk.Frame(form, bg=BG_CARD)
        opt_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        opt_row.columnconfigure(1, weight=1)

        tk.Label(
            opt_row, text="算法", font=FONT_SM, fg=TEXT_DARK, bg=BG_CARD
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.enc_algo = ttk.Combobox(
            opt_row, values=["AES-256-GCM", "XChaCha20-Poly1305"],
            state="readonly", font=FONT, width=18,
        )
        self.enc_algo.grid(row=0, column=1, sticky="w")
        self.enc_algo.set("AES-256-GCM")

        self.enc_del = tk.Frame(opt_row, bg=BG_CARD)
        self.enc_del.grid(row=0, column=2, sticky="e", padx=(16, 0))
        tk.Label(
            self.enc_del, text="加密后删除源文件", font=FONT_SM,
            fg=TEXT_DARK, bg=BG_CARD,
        ).pack(side="left", padx=(0, 4))
        self.enc_del_var = tk.BooleanVar(value=False)
        self.enc_del_cb = tk.Checkbutton(
            self.enc_del, variable=self.enc_del_var,
            bg=BG_CARD, activebackground=BG_CARD,
            relief="flat", bd=0,
        )
        self.enc_del_cb.pack(side="left")
        row += 1

        # 输出目录
        self.enc_out = FileSelector(form, "输出目录（留空为源文件所在目录）", is_dir=True)
        self.enc_out.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 4))
        row += 1

        # 操作按钮
        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))

        self.enc_go = PrimaryButton(btn_row, "开始加密", command=self._do_encrypt)
        self.enc_go.pack(side="right")

        # 提示
        hint = tk.Frame(page, bg=BG_MAIN)
        hint.grid(row=1, column=0, sticky="nw", pady=(8, 0))
        tk.Label(
            hint, text="\u2139  密码强度仅作参考。实际安全性取决于密码长度和复杂度。",
            font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_MAIN, wraplength=500,
            justify="left",
        ).pack(anchor="w")

        return page

    # ── 解密页面 ──────────────────────────────────────────────────────────

    def _build_decrypt_page(self):
        page = tk.Frame(self.page_frame, bg=BG_MAIN)
        page.columnconfigure(0, weight=1)

        card = tk.Frame(page, bg=BG_CARD, relief="solid", bd=1, highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        tk.Label(
            card, text="\U0001F513  解密单个文件",
            font=FONT_HEAD, fg=TEXT_DARK, bg=BG_CARD,
            anchor="w", padx=16
        ).grid(row=0, column=0, sticky="ew", pady=(14, 4))

        tk.Label(
            card, text="选择一个 .ptd 加密文件，输入密码还原为原始文件",
            font=FONT_SM, fg=TEXT_MUTED, bg=BG_CARD,
            anchor="w", padx=16
        ).grid(row=1, column=0, sticky="ew", pady=(0, 10))

        sep = tk.Frame(card, height=1, bg=BORDER)
        sep.grid(row=2, column=0, sticky="ew", padx=16)

        form = tk.Frame(card, bg=BG_CARD)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        self.dec_file = FileSelector(form, "加密文件（.ptd）")
        self.dec_file.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.dec_pw = PasswordEntry(form, "解密密码")
        self.dec_pw.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.dec_out = FileSelector(form, "输出目录（留空为源文件所在目录）", is_dir=True)
        self.dec_out.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 4))

        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))
        self.dec_go = PrimaryButton(btn_row, "开始解密", command=self._do_decrypt)
        self.dec_go.pack(side="right")

        return page

    # ── 批量加密页面 ──────────────────────────────────────────────────────

    def _build_batch_encrypt_page(self):
        page = tk.Frame(self.page_frame, bg=BG_MAIN)
        page.columnconfigure(0, weight=1)

        card = tk.Frame(page, bg=BG_CARD, relief="solid", bd=1, highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        tk.Label(
            card, text="\u2750  批量加密目录",
            font=FONT_HEAD, fg=TEXT_DARK, bg=BG_CARD,
            anchor="w", padx=16
        ).grid(row=0, column=0, sticky="ew", pady=(14, 4))

        tk.Label(
            card, text="递归加密整个目录下所有文件为 .ptd 格式",
            font=FONT_SM, fg=TEXT_MUTED, bg=BG_CARD,
            anchor="w", padx=16
        ).grid(row=1, column=0, sticky="ew", pady=(0, 10))

        sep = tk.Frame(card, height=1, bg=BORDER)
        sep.grid(row=2, column=0, sticky="ew", padx=16)

        form = tk.Frame(card, bg=BG_CARD)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        self.benc_dir = FileSelector(form, "源目录", is_dir=True)
        self.benc_dir.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.benc_pw = PasswordEntry(form, "加密密码")
        self.benc_pw.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.benc_pw2 = PasswordEntry(form, "确认密码")
        self.benc_pw2.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        opt_row = tk.Frame(form, bg=BG_CARD)
        opt_row.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        opt_row.columnconfigure(1, weight=1)

        tk.Label(
            opt_row, text="算法", font=FONT_SM, fg=TEXT_DARK, bg=BG_CARD
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.benc_algo = ttk.Combobox(
            opt_row, values=["AES-256-GCM", "XChaCha20-Poly1305"],
            state="readonly", font=FONT, width=18,
        )
        self.benc_algo.grid(row=0, column=1, sticky="w")
        self.benc_algo.set("AES-256-GCM")

        tk.Label(
            opt_row, text="线程数", font=FONT_SM, fg=TEXT_DARK, bg=BG_CARD
        ).grid(row=0, column=2, sticky="w", padx=(16, 4))
        self.benc_threads = ttk.Combobox(
            opt_row, values=["1", "2", "4", "8"],
            state="readonly", font=FONT, width=4,
        )
        self.benc_threads.grid(row=0, column=3, sticky="w")
        self.benc_threads.set("4")

        # 第二行选项
        opt_row2 = tk.Frame(form, bg=BG_CARD)
        opt_row2.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.benc_del_var = tk.BooleanVar(value=False)
        tk.Label(
            opt_row2, text="加密后删除源文件", font=FONT_SM,
            fg=TEXT_DARK, bg=BG_CARD,
        ).pack(side="left", padx=(0, 4))
        tk.Checkbutton(
            opt_row2, variable=self.benc_del_var,
            bg=BG_CARD, activebackground=BG_CARD,
            relief="flat", bd=0,
        ).pack(side="left")

        self.benc_out = FileSelector(form, "输出目录", is_dir=True)
        self.benc_out.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 4))

        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))
        self.benc_go = PrimaryButton(btn_row, "开始批量加密", command=self._do_batch_encrypt)
        self.benc_go.pack(side="right")

        return page

    # ── 批量解密页面 ──────────────────────────────────────────────────────

    def _build_batch_decrypt_page(self):
        page = tk.Frame(self.page_frame, bg=BG_MAIN)
        page.columnconfigure(0, weight=1)

        card = tk.Frame(page, bg=BG_CARD, relief="solid", bd=1, highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        tk.Label(
            card, text="\u2751  批量解密目录",
            font=FONT_HEAD, fg=TEXT_DARK, bg=BG_CARD,
            anchor="w", padx=16
        ).grid(row=0, column=0, sticky="ew", pady=(14, 4))

        tk.Label(
            card, text="递归解密目录下所有 .ptd 文件还原为原始文件",
            font=FONT_SM, fg=TEXT_MUTED, bg=BG_CARD,
            anchor="w", padx=16
        ).grid(row=1, column=0, sticky="ew", pady=(0, 10))

        sep = tk.Frame(card, height=1, bg=BORDER)
        sep.grid(row=2, column=0, sticky="ew", padx=16)

        form = tk.Frame(card, bg=BG_CARD)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        self.bdec_dir = FileSelector(form, "源目录（包含 .ptd 文件）", is_dir=True)
        self.bdec_dir.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.bdec_pw = PasswordEntry(form, "解密密码")
        self.bdec_pw.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        opt_row = tk.Frame(form, bg=BG_CARD)
        opt_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        opt_row.columnconfigure(1, weight=1)

        tk.Label(
            opt_row, text="线程数", font=FONT_SM, fg=TEXT_DARK, bg=BG_CARD
        ).grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.bdec_threads = ttk.Combobox(
            opt_row, values=["1", "2", "4", "8"],
            state="readonly", font=FONT, width=4,
        )
        self.bdec_threads.grid(row=0, column=1, sticky="w")
        self.bdec_threads.set("4")

        self.bdec_out = FileSelector(form, "输出目录", is_dir=True)
        self.bdec_out.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 4))

        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))
        self.bdec_go = PrimaryButton(btn_row, "开始批量解密", command=self._do_batch_decrypt)
        self.bdec_go.pack(side="right")

        return page

    # ── 执行操作 ──────────────────────────────────────────────────────────

    def _log(self, text):
        self.output_text.config(state="normal")
        self.output_text.insert("end", text + "\n")
        self.output_text.see("end")
        self.output_text.config(state="disabled")

    def _clear_output(self):
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.config(state="disabled")

    def _set_status(self, text):
        self.status_bar.config(text=text)

    def _set_busy(self, busy):
        self._running = busy
        self.root.config(cursor="watch" if busy else "")

    def _reset_progress(self):
        """重置进度条"""
        self._progress_bar["value"] = 0
        self._progress_pct.config(text="")
        self._progress_label.config(text="")

    def _set_progress(self, value, label=""):
        """设置进度条百分比 0-100"""
        self._progress_bar["value"] = value
        self._progress_pct.config(text=f"{value}%")
        if label:
            self._progress_label.config(text=label)

    def _run_async_stream(self, args, desc="", password=None, password2=None,
                          timeout=600, overwrite=None, fallback=None):
        """在后台线程中流式运行并实时显示输出"""
        if self._running:
            self._log("[!] 已有操作正在执行，请等待完成")
            return

        self._set_busy(True)
        self._reset_progress()
        self._log("─" * 50)
        self._log(f"[>] {desc}")
        self._set_status(f"运行中...")

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
                            self.root.after(0, self._set_progress, pct, f"{cur}/{total}")

                    if err:
                        if isinstance(err, int):
                            exit_code = err
                        else:
                            collected.append(f"[!] {err}")
                            self.root.after(0, self._log, f"[!] {err}")

                # 如果没从最后一条拿到退出码，尝试从 collected 解析
                if exit_code == -1:
                    exit_code = 0

            except Exception as e:
                exit_code = -1
                self.root.after(0, self._log, f"[!] 异常: {e}")

            self.root.after(0, self._on_stream_result, exit_code, collected, desc)

        threading.Thread(target=run, daemon=True).start()

    def _on_stream_result(self, exit_code, lines, desc):
        """流式执行完成后的回调"""
        self._set_busy(False)

        # 进度条回满
        self._set_progress(100, "完成")

        if exit_code == 0:
            self._log(f"[OK] {desc} 完成")
            self._set_status("完成")
        else:
            self._log(f"[FAIL] {desc} 失败 (exit={exit_code})")
            self._set_status("失败")

        self._log("─" * 50)

        # 3 秒后自动清除进度条
        self.root.after(3000, self._reset_progress)

    # ── 加密执行 ──────────────────────────────────────────────────────────

    def _do_encrypt(self):
        src = self.enc_file.get().strip()
        pw = self.enc_pw.get()
        pw2 = self.enc_pw2.get()
        out = self.enc_out.get().strip()
        algo = self.enc_algo.get()
        delete = self.enc_del_var.get()

        if not src:
            messagebox.showwarning("提示", "请选择要加密的文件")
            return
        if not pw:
            messagebox.showwarning("提示", "请输入加密密码")
            return
        if pw != pw2:
            messagebox.showwarning("提示", "两次输入的密码不一致")
            return
        if not os.path.isfile(src):
            messagebox.showerror("错误", "源文件不存在")
            return

        args = ["-e", src]
        if out:
            if not os.path.isdir(out):
                try:
                    os.makedirs(out, exist_ok=True)
                except Exception:
                    messagebox.showerror("错误", "无法创建输出目录")
                    return
            args += ["-o", out]
        if algo.startswith("XChaCha20"):
            args += ["-m", "xchacha20"]
        if delete:
            args.append("-de")
        args.append("-y")

        self._run_async_stream(
            args,
            desc=f"加密: {os.path.basename(src)}",
            password=pw, password2=pw,
            timeout=600, overwrite="y", fallback="n",
        )

    # ── 解密执行 ──────────────────────────────────────────────────────────

    def _do_decrypt(self):
        src = self.dec_file.get().strip()
        pw = self.dec_pw.get()
        out = self.dec_out.get().strip()

        if not src:
            messagebox.showwarning("提示", "请选择要解密的 .ptd 文件")
            return
        if not pw:
            messagebox.showwarning("提示", "请输入解密密码")
            return
        if not os.path.isfile(src):
            messagebox.showerror("错误", "文件不存在")
            return
        if not src.lower().endswith(".ptd"):
            messagebox.showwarning("提示", "选中的文件不是 .ptd 格式")
            return

        args = ["-d", src]
        if out:
            if not os.path.isdir(out):
                try:
                    os.makedirs(out, exist_ok=True)
                except Exception:
                    messagebox.showerror("错误", "无法创建输出目录")
                    return
            args += ["-o", out]
        args.append("-y")

        self._run_async_stream(
            args,
            desc=f"解密: {os.path.basename(src)}",
            password=pw, timeout=600, overwrite="y",
        )

    # ── 批量加密 ──────────────────────────────────────────────────────────

    def _do_batch_encrypt(self):
        src = self.benc_dir.get().strip()
        pw = self.benc_pw.get()
        pw2 = self.benc_pw2.get()
        out = self.benc_out.get().strip()
        algo = self.benc_algo.get()
        threads = self.benc_threads.get()
        delete = self.benc_del_var.get()

        if not src:
            messagebox.showwarning("提示", "请选择源目录")
            return
        if not pw:
            messagebox.showwarning("提示", "请输入加密密码")
            return
        if pw != pw2:
            messagebox.showwarning("提示", "两次输入的密码不一致")
            return
        if not os.path.isdir(src):
            messagebox.showerror("错误", "源目录不存在")
            return

        args = ["-be", "-i", src]
        if out:
            args += ["-o", out]
        if algo.startswith("XChaCha20"):
            args += ["-m", "xchacha20"]
        if threads:
            args += ["-j", threads]
        if delete:
            args.append("-de")
        args.append("-y")

        self._run_async_stream(
            args,
            desc=f"批量加密: {os.path.basename(src)}",
            password=pw, password2=pw,
            timeout=1800, overwrite="y", fallback="n",
        )

    # ── 批量解密 ──────────────────────────────────────────────────────────

    def _do_batch_decrypt(self):
        src = self.bdec_dir.get().strip()
        pw = self.bdec_pw.get()
        out = self.bdec_out.get().strip()
        threads = self.bdec_threads.get()

        if not src:
            messagebox.showwarning("提示", "请选择源目录")
            return
        if not pw:
            messagebox.showwarning("提示", "请输入解密密码")
            return
        if not os.path.isdir(src):
            messagebox.showerror("错误", "源目录不存在")
            return

        args = ["-bd", "-i", src]
        if out:
            args += ["-o", out]
        if threads:
            args += ["-j", threads]
        args.append("-y")

        self._run_async_stream(
            args,
            desc=f"批量解密: {os.path.basename(src)}",
            password=pw, timeout=1800, overwrite="y",
        )

    # ── 启动 ──────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


# ── 入口 ──────────────────────────────────────────────────────────────────

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