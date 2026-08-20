#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
theme.py —— 主题与设计令牌（纯数据，第 3 步抽取）

以冻结数据对象代替"模块级颜色全局变量 + apply_theme 写回 globals 的可变状态"。
UI 构建时取 `theme = get_theme()`，控件从对象取色；禁止 `from theme import BG_MAIN`。

主题切换依赖全量重建（GUI._apply_settings），与冻结对象天然契合，无需实时换肤。
"""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Theme:
    """一组不可变的颜色令牌。"""
    BG_MAIN: str
    BG_SIDEBAR: str
    BG_CARD: str
    TEXT_DARK: str
    TEXT_MUTED: str
    TEXT_LIGHT: str
    ACCENT: str
    ACCENT_HOVER: str
    BORDER: str
    SUCCESS: str
    ERROR: str
    INPUT_BG: str
    BTN_BG: str
    BTN_TEXT: str
    PROG_TRACK: str
    OUT_BG: str
    NAV_ACTIVE: str
    NAV_INACTIVE: str
    NAV_HOVER: str
    VER_TEXT: str


THEMES = {
    "light": Theme(
        BG_MAIN="#f0f0f0",      # 中性灰底
        BG_SIDEBAR="#3a3a3a",   # 深灰侧栏
        BG_CARD="#fafafa",      # 卡片底色（接近白）
        TEXT_DARK="#2a2a2a",    # 深色文字
        TEXT_MUTED="#7a7a7a",   # 灰色文字
        TEXT_LIGHT="#e0e0e0",   # 浅色文字
        ACCENT="#5a5a5a",       # 中性深灰（避免彩色）
        ACCENT_HOVER="#4a4a4a", # 悬停更深
        BORDER="#d0d0d0",       # 边框色
        SUCCESS="#5a8a5a",      # 暗绿（低饱和）
        ERROR="#a05a5a",        # 暗红（低饱和）
        INPUT_BG="#ffffff",     # 输入框白底
        BTN_BG="#e0e0e0",       # 按钮底色
        BTN_TEXT="#2a2a2a",     # 按钮文字
        PROG_TRACK="#e0e0e0",  # 进度条轨道
        OUT_BG="#1e1e1e",       # 日志区背景
        NAV_ACTIVE="#e0e0e0",   # 导航选中
        NAV_INACTIVE="#a0a0a0", # 导航未选中
        NAV_HOVER="#c0c0c0",    # 导航悬停
        VER_TEXT="#5a5a5a",     # 版本文字
    ),
    "dark": Theme(
        BG_MAIN="#1e1e1e",
        BG_SIDEBAR="#141414",
        BG_CARD="#252525",
        TEXT_DARK="#d8d8d8",
        TEXT_MUTED="#9a9a9a",
        TEXT_LIGHT="#e0e0e0",
        ACCENT="#8a8a8a",
        ACCENT_HOVER="#9a9a9a",
        BORDER="#3a3a3a",
        SUCCESS="#6fbf6f",
        ERROR="#d07a7a",
        INPUT_BG="#1a1a1a",
        BTN_BG="#333333",
        BTN_TEXT="#d8d8d8",
        PROG_TRACK="#3a3a3a",
        OUT_BG="#101010",
        NAV_ACTIVE="#f0f0f0",
        NAV_INACTIVE="#9a9a9a",
        NAV_HOVER="#c8c8c8",
        VER_TEXT="#6a6a6a",
    ),
}

# 当前主题名（仅一个字符串状态；get_theme() 返回不可变冻结对象）
_CURRENT = "light"


def get_theme(name=None):
    """返回名字对应的冻结 Theme（缺省用当前主题名）。未知名字回退浅色。"""
    key = name if name in THEMES else _CURRENT
    return THEMES.get(key, THEMES["light"])


def set_theme_name(name):
    """记录当前主题名。UI 全量重建前调用，随后控件经 get_theme() 取色。"""
    global _CURRENT
    if name in THEMES:
        _CURRENT = name


def theme_names():
    return list(THEMES.keys())


# ── 字体与动效（与主题无关的静态令牌）───────────────────────────────────

_IS_WINDOWS = (os.name == "nt")

if _IS_WINDOWS:
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

ANIM_DURATION = 200  # 毫秒
ANIM_EASING = "ease-out"