#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_config.py —— 用户配置持久化单元测试（config.py）

校验第 2 步抽出的 ConfigManager / get_config：
  - 缺失文件时默认值返回
  - 写入后 get/getint/getboolean 正确读回
  - save() 落盘后再实例化可从盘上读回
  - 不可解析值回退默认
"""
import sys
from pathlib import Path

GUI_DIR = Path(__file__).resolve().parent.parent
if str(GUI_DIR) not in sys.path:
    sys.path.insert(0, str(GUI_DIR))

from app.core.config import ConfigManager


def _cm(tmp_path):
    return ConfigManager(config_file=str(tmp_path / "config.ini"))


def test_defaults_when_missing(tmp_path):
    cm = _cm(tmp_path)
    assert cm.get("ui", "lang", "zh") == "zh"
    assert cm.getboolean("ui", "image_mode", False) is False
    assert cm.getint("ui", "threads", 0) == 0


def test_set_and_get(tmp_path):
    cm = _cm(tmp_path)
    cm.set("ui", "lang", "en")
    cm.set("ui", "theme", "dark")
    assert cm.get("ui", "lang") == "en"
    assert cm.get("ui", "theme") == "dark"


def test_getint_getboolean(tmp_path):
    cm = _cm(tmp_path)
    cm.set("ui", "threads", "8")
    cm.set("ui", "image_mode", "true")
    assert cm.getint("ui", "threads") == 8
    assert cm.getboolean("ui", "image_mode") is True


def test_save_and_reload(tmp_path):
    cm = _cm(tmp_path)
    cm.set("ui", "lang", "en")
    cm.save()
    cm2 = _cm(tmp_path)
    assert cm2.get("ui", "lang") == "en"


def test_invalid_value_falls_back(tmp_path):
    cm = _cm(tmp_path)
    cm.set("ui", "threads", "not-a-number")
    assert cm.getint("ui", "threads", 4) == 4


def test_config_file_path(tmp_path):
    target = tmp_path / "custom.ini"
    cm = ConfigManager(config_file=str(target))
    assert cm.config_file == str(target)