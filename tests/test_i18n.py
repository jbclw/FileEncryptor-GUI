#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_i18n.py —— 多语言纯逻辑单元测试（i18n.py）

校验第 2 步抽出的 i18n：
  - available_langs / get_lang / set_lang 的语言切换
  - tr() 取当前语言文本；未知 key 原样返回；未知语言不生效
  - 中英 key 集合一致（避免漏译）
"""
import sys
from pathlib import Path

GUI_DIR = Path(__file__).resolve().parent.parent
if str(GUI_DIR) not in sys.path:
    sys.path.insert(0, str(GUI_DIR))

from app.core import i18n as i18n_mod
from app.core.i18n import tr, get_lang, set_lang, available_langs, STRINGS


def test_available_langs():
    langs = available_langs()
    assert set(["zh", "en"]).issubset(langs)


def test_default_lang_zh():
    set_lang("zh")
    assert get_lang() == "zh"
    assert tr("app_subtitle") == "文件加密工具"


def test_switch_to_en():
    set_lang("en")
    assert get_lang() == "en"
    assert tr("app_subtitle") == "File Encryption Tool"


def test_unknown_lang_ignored():
    set_lang("zh")
    set_lang("fr")
    assert get_lang() == "zh"  # 未知语言不生效


def test_tr_unknown_key_passthrough():
    set_lang("zh")
    assert tr("definitely_missing_key") == "definitely_missing_key"


def test_key_sets_identical():
    # 中英 key 必须一致，防止漏译
    assert set(STRINGS["zh"].keys()) == set(STRINGS["en"].keys())


def test_all_keys_translatable():
    # 每个 key 在两语言下都有非空文本
    for k in STRINGS["zh"]:
        assert STRINGS["zh"][k] != ""
        assert STRINGS["en"][k] != ""