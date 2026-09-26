#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_widgets.py —— widgets.py 控件库单元测试（第 3 步）

控件直接依赖 ctk/tk 与一个真实 root，故用隐藏的 Tk 根实例化并做行为断言。
Headless（无显示环境）时跳过；行为和取色都验证，控件不缓存渲染字符串（语言/主题切换靠 GUI 重建）。
"""
import sys

import pytest

# 无显示环境（如纯 CI 无 xvfb）时跳过整个模块；tkinter 缺失也跳过
try:
    import tkinter as tk
    _tk = tk.Tk()
    _tk.withdraw()
    _tk.update_idletasks()
except Exception:  # noqa: BLE001
    pytest.skip("tkinter/显示环境不可用", allow_module_level=True)

from app.ui.widgets import PasswordEntry, FileSelector, FlatButton, PrimaryButton  # noqa: E402
from app.ui.theme import get_theme  # noqa: E402
from app.core.strength import password_score  # noqa: E402


@pytest.fixture(scope="module")
def root():
    r = tk.Tk()
    r.withdraw()
    yield r
    r.destroy()


# ── PasswordEntry ───────────────────────────────────────────────────────

def test_password_entry_get_set_clear(root):
    e = PasswordEntry(root, label="pwd")
    e.set("secret")
    assert e.get() == "secret"
    e.clear()
    assert e.get() == ""
    e.destroy()


def test_password_entry_hidden_by_default_and_toggle(root):
    e = PasswordEntry(root)
    assert e.show_password is False
    from customtkinter import CTkEntry
    assert isinstance(e.entry, CTkEntry)
    assert e.entry.cget("show") == "\u2022"
    e._toggle_show()
    assert e.show_password is True
    assert e.entry.cget("show") == ""
    e.destroy()


def test_password_entry_strength_updates(root):
    e = PasswordEntry(root)
    e.set("")
    # 空密码应判为弱
    score = password_score("")
    e._update_strength()
    assert 0.0 <= score < 0.6
    e.set("Correct-Horse-Battery-Staple!2heng")
    e._update_strength()
    assert password_score(e.get()) >= 0.6
    e.destroy()


# ── FileSelector ────────────────────────────────────────────────────────

def test_file_selector_get_set_clear(root):
    fs = FileSelector(root, label="src")
    fs.set(r"C:\tmp\a.txt")
    assert fs.get() == r"C:\tmp\a.txt"
    fs.clear()
    assert fs.get() == ""
    fs.destroy()


def test_file_selector_dir_flag(root):
    assert FileSelector(root, is_dir=True).is_dir is True
    assert FileSelector(root, is_dir=False).is_dir is False


# ── 按钮 ────────────────────────────────────────────────────────────────

def test_flat_button_invokes_command(root):
    calls = []
    b = FlatButton(root, text="x", command=lambda: calls.append(1))
    b._on_click()
    assert calls == [1]
    b.destroy()


def test_primary_button_invokes_command(root):
    calls = []
    b = PrimaryButton(root, text="go", command=lambda: calls.append("go"))
    b._on_click()
    assert calls == ["go"]
    b.destroy()


def test_buttons_use_current_theme_colors(root):
    t = get_theme()
    fb = FlatButton(root, text="f")
    pb = PrimaryButton(root, text="p")
    assert fb.cget("fg_color") == t.BTN_BG
    assert pb.cget("fg_color") == t.ACCENT
    fb.destroy()
    pb.destroy()