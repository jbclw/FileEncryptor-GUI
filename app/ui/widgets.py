#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
widgets.py —— 控件库（第 3 步抽取）

把 PasswordEntry / FileSelector / FlatButton / PrimaryButton 从 GUI 层抽出为可复用控件库。
控件经 `get_theme()` 从冻结 Theme 对象取色，不含可变主题状态。
语言文本在构建时由调用方以 tr(key) 传入；语言/主题切换依赖 GUI 全量重建，控件不缓存渲染字符串。
"""
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog

from .theme import FONT, FONT_SM, FONT_LG, FONT_FAMILY, get_theme
from ..core.i18n import tr
from ..core.strength import password_score


class PasswordEntry(ctk.CTkFrame):
    """带显隐切换与强度指示的密码输入框"""

    def __init__(self, parent, label="", **kwargs):
        t = get_theme()
        super().__init__(parent, fg_color=t.BG_CARD, corner_radius=6, **kwargs)
        self.show_password = False  # 默认隐藏
        self.text = tk.StringVar()

        # 标签
        self.lbl = ctk.CTkLabel(
            self, text=label, font=FONT_SM, text_color=t.TEXT_DARK,
            anchor="w"
        )
        self.lbl.pack(fill="x", pady=(0, 2))

        # 输入行
        row = ctk.CTkFrame(self, fg_color=t.BG_CARD, corner_radius=0)
        row.pack(fill="x")

        self.entry = ctk.CTkEntry(
            row, textvariable=self.text, show="\u2022",  # 默认掩码
            font=FONT, fg_color=t.INPUT_BG, text_color=t.TEXT_DARK,
            border_width=1, border_color=t.BORDER,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.toggle_btn = ctk.CTkLabel(
            row, text="\u25cf", font=(FONT_FAMILY, 12),
            fg_color=t.INPUT_BG, text_color=t.TEXT_MUTED, cursor="hand2",
            width=24,
        )
        self.toggle_btn.pack(side="right")
        self.toggle_btn.bind("<Button-1>", self._toggle_show)

        # 强度指示（进度条 + 等级文字）
        foot = ctk.CTkFrame(self, fg_color=t.BG_CARD, corner_radius=0)
        foot.pack(fill="x", pady=(4, 0))
        self.strength_bar = ctk.CTkProgressBar(
            foot, height=4, fg_color=t.PROG_TRACK, progress_color=t.ERROR
        )
        self.strength_bar.set(0)  # 默认归零
        self.strength_bar.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.strength_lbl = ctk.CTkLabel(
            foot, text="", font=(FONT_FAMILY, 8), text_color=t.TEXT_MUTED,
            width=24, anchor="e",
        )
        self.strength_lbl.pack(side="right")

        self.text.trace_add("write", self._update_strength)

    def _toggle_show(self, event=None):
        self.show_password = not self.show_password
        self.entry.configure(show="" if self.show_password else "\u2022")
        self.toggle_btn.configure(text="\u25cb" if self.show_password else "\u25cf")

    def _update_strength(self, *args):
        t = get_theme()
        pwd = self.text.get()
        score = password_score(pwd)
        if score < 0.3:
            color, level = t.ERROR, "strength_weak"
        elif score < 0.6:
            color, level = "#c4a050", "strength_medium"
        else:
            color, level = t.SUCCESS, "strength_strong"
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
        t = get_theme()
        super().__init__(parent, fg_color=t.BG_CARD, corner_radius=6, **kwargs)
        self.is_dir = is_dir
        self._path = tk.StringVar()

        self.lbl = ctk.CTkLabel(
            self, text=label, font=FONT_SM, text_color=t.TEXT_DARK,
            anchor="w"
        )
        self.lbl.pack(fill="x", pady=(0, 2))

        row = ctk.CTkFrame(self, fg_color=t.BG_CARD, corner_radius=0)
        row.pack(fill="x")

        self.entry = ctk.CTkEntry(
            row,
            textvariable=self._path,
            font=FONT,
            fg_color=t.INPUT_BG,
            text_color=t.TEXT_DARK,
            border_width=1,
            border_color=t.BORDER,
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
            fg_color=t.INPUT_BG, text_color=t.TEXT_DARK, cursor="hand2",
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
        t = get_theme()
        super().__init__(
            parent, text=text, font=FONT,
            fg_color=t.BTN_BG, text_color=t.BTN_TEXT, cursor="hand2",
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
        t = get_theme()
        super().__init__(
            parent, text=text, font=FONT_LG,
            fg_color=t.ACCENT, hover_color=t.ACCENT_HOVER, text_color="#ffffff",
            cursor="hand2", height=36, corner_radius=8,
            **kwargs
        )
        self._cmd = command
        self.configure(command=self._on_click)

    def _on_click(self, event=None):
        if self._cmd:
            self._cmd()