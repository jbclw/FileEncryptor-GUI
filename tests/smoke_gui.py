#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smoke_gui.py —— 无头 GUI 实例化冒烟（第三层测试）
每次搬移后运行一次，抓取重构破坏：漏 import、改名、初始化顺序错。
Windows 下不入库时无显示环境，用 withdraw() 隐藏窗口后只做 update_idletasks()。

用法：
    python tests/smoke_gui.py
返回码 0 表示 import + 实例化成功。
"""
import sys
import os
from pathlib import Path

GUI_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GUI_DIR))

# 冒烟不引入取色/图片背景的计时负载，但保持默认行为
os.environ.setdefault("FE_SMOKE", "1")

try:
    from app.ui import gui
except Exception as e:  # noqa: BLE001
    print(f"SMOKE_FAIL import: {e!r}")
    sys.exit(1)

try:
    app = gui.FileEncryptorGUI()
    # 隐藏窗口后推进一次空闲事件，触发建 UI 的正常路径
    app.root.withdraw()
    # 遍历所有模式构建全部页面组件，覆盖 pages.build_page 各分支
    for mode in ("encrypt", "decrypt", "batch_enc", "batch_dec", "settings"):
        app._switch_mode(mode)
        for _ in range(3):
            app.root.update_idletasks()
    for _ in range(5):
        app.root.update_idletasks()
    app.root.destroy()
except Exception as e:  # noqa: BLE001
    print(f"SMOKE_FAIL instantiate: {e!r}")
    sys.exit(1)

print("SMOKE_OK")
sys.exit(0)