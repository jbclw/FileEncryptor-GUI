#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_theme.py —— theme.py 单元测试（第 3 步）

主题为纯数据对象，无 GUI/引擎依赖，是最便宜、价值最高的测试缝：
  - 冻结不可变：Theme 为 frozen dataclass，杜绝主题切换状态突变。
  - 名 -> 对象解析：get_theme() 按名取主题，未知名回退浅色。
  - 时间语义：所有字段齐全、浅色/深色取色一致。
"""
import pytest

from app.ui.theme import (Theme, THEMES, get_theme, set_theme_name,
                          theme_names, FONT, FONT_SM, FONT_LG, FONT_MONO,
                          FONT_HEAD, FONT_FAMILY, FONT_FAMILY_MONO)

# 预定义主题应覆盖的全部颜色令牌
_FIELDS = [
    "BG_MAIN", "BG_SIDEBAR", "BG_CARD", "TEXT_DARK", "TEXT_MUTED",
    "TEXT_LIGHT", "ACCENT", "ACCENT_HOVER", "BORDER", "SUCCESS", "ERROR",
    "INPUT_BG", "BTN_BG", "BTN_TEXT", "PROG_TRACK", "OUT_BG", "NAV_ACTIVE",
    "NAV_INACTIVE", "NAV_HOVER", "VER_TEXT",
]


def test_frozen_object_cannot_mutate():
    t = get_theme()
    with pytest.raises(AttributeError):
        t.BG_MAIN = "#000000"


def test_all_fields_defined_for_both_themes():
    for name in THEMES:
        t = THEMES[name]
        for f in _FIELDS:
            val = getattr(t, f)
            assert isinstance(val, str) and val.startswith("#"), f"{name}.{f}"


def test_theme_names_returns_all_keys():
    assert set(theme_names()) == set(THEMES.keys())
    assert "light" in theme_names() and "dark" in theme_names()


def test_get_theme_default_uses_current():
    prev = get_theme().BG_CARD
    set_theme_name("dark")
    try:
        assert get_theme().BG_CARD != prev
    finally:
        set_theme_name("light")


def test_get_theme_explicit_name():
    assert get_theme("light") is THEMES["light"]
    assert get_theme("dark") is THEMES["dark"]


def test_get_theme_unknown_falls_back_to_light():
    assert get_theme("no_such_theme") is THEMES["light"]


def test_set_theme_name_ignores_unknown():
    set_theme_name("bogus")
    assert get_theme() is THEMES["light"]


def test_light_dark_share_field_names_but_differ():
    light, dark = THEMES["light"], THEMES["dark"]
    # 字段名一致
    assert {f for f in _FIELDS} == {f for f in light.__dataclass_fields__}
    # 至少 BG_MAIN 深浅不同
    assert light.BG_MAIN != dark.BG_MAIN


def test_font_tokens_are_tuples_with_family():
    assert FONT_FAMILY
    assert FONT_FAMILY_MONO
    for font in (FONT, FONT_SM, FONT_LG, FONT_MONO, FONT_HEAD):
        assert isinstance(font, tuple) and font[0] == FONT_FAMILY or font[0] == FONT_FAMILY_MONO