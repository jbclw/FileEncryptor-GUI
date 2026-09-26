#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_engine_service.py —— EngineService 契约测试（mock subprocess.Popen，不产生真实进程）

校验服务层对外契约，守住第一步重构：
  - start: 是否按参数构建命令并正确注入密码（临时文件）/取消路径（环境变量）
  - progress / log 回调：流式输出的三种元组 (line, progress, err) 解析正确
  - 退出码透传：__EXIT__ 标记正确解析
  - 取消（新行为）：cancel() 置标志 + 写取消文件；runner 检测文件退出后 GUI 收 EOF；
    结束清理取消文件；取消不把 -1 覆盖为成功。

模拟的是 runner 层：fake Popen 的 stdout 按契约协议喂数据，且"检测到取消文件即返回 EOF"，
与 _runner.py 的真实行为（kill 后退出 -> GUI 收 EOF）一致。
"""
import os
import sys
import threading
import time
from pathlib import Path

import pytest

GUI_DIR = Path(__file__).resolve().parent.parent
if str(GUI_DIR) not in sys.path:
    sys.path.insert(0, str(GUI_DIR))

from app.core import engine as engine_mod
from app.core.engine import EngineService


# ── 模拟 runner 层 ───────────────────────────────────────────────────────

class FakeStdout:
    """模拟 runner 的 stdout 读取器：按 .read(n) 契约返回字节流。"""

    def __init__(self, controller):
        self._ctrl = controller

    def read(self, _n):
        return self._ctrl.read()


class FakeProc:
    def __init__(self, controller):
        self.stdout = FakeStdout(controller)
        self.terminated = False

    def terminate(self):
        self.terminated = True


class Controller:
    """驱动 fake runner：队列输出 + 感知取消文件（模拟 runner 30ms 内发现取消）。"""

    def __init__(self, chunks):
        self.chunks = list(chunks)   # list[bytes]：依次吐给 GUI
        self.cancel_path = None      # 由 Popen 的 env 注入

    def read(self):
        # 模拟 _runner.py 的取消行为：检测到取消文件 -> 退出（EOF）。
        # 当配置了取消路径但文件尚未出现时，模拟"引擎运行中但暂无输出"：阻塞等待，
        # 直到取消文件出现才返回 EOF（这样 cancel() 始终发生在运行尚未结束前）。
        if self.cancel_path:
            while not os.path.exists(self.cancel_path) and not self.chunks:
                time.sleep(0.01)
            if os.path.exists(self.cancel_path):
                return b""
        if not self.chunks:
            return b""
        return self.chunks.pop(0)


def collect(fn, timeout=5.0):
    """在后台线程消费生成器，返回 (items, done_event)"""
    items = []
    done = threading.Event()

    def worker():
        for it in fn:
            items.append(it)
        done.set()

    threading.Thread(target=worker, daemon=True).start()
    return items, done


@pytest.fixture
def svc():
    return EngineService()


# ── 用例 ─────────────────────────────────────────────────────────────────

def test_stream_log_progress_exit(svc, monkeypatch):
    """正常流：普通行 + 进度 + __EXIT__ 标记正确解析，退出码透传，取消文件被清理。"""
    called = {}

    def fake_popen(cmd, **kw):
        called["cmd"] = cmd
        called["env"] = kw.get("env", {})
        return FakeProc(Controller([
            b"banner text\n",
            b"[=====>        ] 512/1024 bytes | 5.2 MiB/s | 0:03\r",
            b"__EXIT__:0\n",
        ]))

    monkeypatch.setattr(engine_mod.subprocess, "Popen", fake_popen)
    dummy = GUI_DIR / "app" / "core" / "engine.py"
    monkeypatch.setattr(engine_mod, "find_exe", lambda: str(dummy))
    monkeypatch.setattr(engine_mod, "_HELPER_PYTHON", sys.executable)

    items, done = collect(svc.run(["enc", "src"], password="pw1", password2="pw2",
                                  timeout=120))
    assert done.wait(5)
    assert not svc.cancelled

    lines = [t for t, p, e in items if t]
    progress = [p for t, p, e in items if p]
    exits = [e for t, p, e in items if isinstance(e, int)]

    assert "banner text" in lines
    assert (512, 1024) in progress
    assert exits == [0]

    # 契约：密码经安全临时文件传（cmd[7]，内容为 pw1/pw2 两行），取消路径经环境变量注入
    assert called["cmd"][2] == str(dummy)
    pw_file = called["cmd"][7]
    assert pw_file and os.path.isfile(pw_file)
    with open(pw_file, "r", encoding="utf-8") as f:
        assert f.read().splitlines() == ["pw1", "pw2"]
    cancel_path = called["env"]["FE_GUI_CANCEL"]
    assert cancel_path and os.path.basename(cancel_path).startswith("fe_gui_cancel_")

    # 取消路径指向引擎可执行文件，且运行结束后已清理
    assert not os.path.exists(cancel_path)
    # 测试中的 fake runner 不会消费密码文件，手动清理避免残留
    try:
        os.unlink(pw_file)
    except OSError:
        pass


def test_progress_new_units(svc, monkeypatch):
    """CLI 2.x 进度格式（NNN B/KB/MB/GB）兼容并换算为字节。"""
    def fake_popen(cmd, **kw):
        return FakeProc(Controller([
            b"22 B/22 B | 0.00 MB/s | 0:00\r",
            b"2 KB/4 KB | 1.5 MB/s | 0:00\r",
            b"__EXIT__:0\n",
        ]))

    monkeypatch.setattr(engine_mod.subprocess, "Popen", fake_popen)
    dummy = GUI_DIR / "app" / "core" / "engine.py"
    monkeypatch.setattr(engine_mod, "find_exe", lambda: str(dummy))
    monkeypatch.setattr(engine_mod, "_HELPER_PYTHON", sys.executable)

    items, done = collect(svc.run(["enc", "src"]))
    assert done.wait(5)
    progress = [p for t, p, e in items if p]
    assert (22, 22) in progress
    assert (2048, 4096) in progress


def test_error_yield(svc, monkeypatch):
    """__ERR__ 行 yield 为 (line="", progress=None, err=str)。"""
    def fake_popen(cmd, **kw):
        return FakeProc(Controller([
            b"something\n",
            b"__ERR__:bad magic\n",
            b"__EXIT__:-1\n",
        ]))

    monkeypatch.setattr(engine_mod.subprocess, "Popen", fake_popen)
    dummy = GUI_DIR / "app" / "core" / "engine.py"
    monkeypatch.setattr(engine_mod, "find_exe", lambda: str(dummy))
    monkeypatch.setattr(engine_mod, "_HELPER_PYTHON", sys.executable)

    items, done = collect(svc.run(["dec", "x"]))

    assert done.wait(5)
    errs = [e for t, p, e in items if isinstance(e, str) and e]
    exits = [e for t, p, e in items if isinstance(e, int)]
    assert "bad magic" in errs
    assert exits == [-1]


def test_cancel_writes_file_and_stops(svc, monkeypatch):
    """取消新行为：cancel() 创建取消文件、cancelled=True、GUI 收 EOF 结束且保留 -1。"""
    def fake_popen(cmd, **kw):
        ctrl = Controller([b"working...\n", b"more\n"])
        ctrl.cancel_path = kw.get("env", {}).get("FE_GUI_CANCEL") or None
        return FakeProc(ctrl)

    monkeypatch.setattr(engine_mod.subprocess, "Popen", fake_popen)
    dummy = GUI_DIR / "app" / "core" / "engine.py"
    monkeypatch.setattr(engine_mod, "find_exe", lambda: str(dummy))
    monkeypatch.setattr(engine_mod, "_HELPER_PYTHON", sys.executable)

    items, done = collect(svc.run(["enc", "src"]))
    # 给一个输出片段足够时间被读走
    time.sleep(0.1)
    svc.cancel()
    assert svc.cancelled is True
    assert done.wait(5)

    lines = [t for t, p, e in items if t]
    exits = [e for t, p, e in items if isinstance(e, int)]
    assert "working..." in lines
    # 取消 -> runner 退出 -> GUI 收到 EOF -> 返回 -1（不被当作成功）
    assert exits == [-1]


def test_cancel_file_cleaned_after_run(svc, monkeypatch):
    """取消运行结束后，取消文件被 finally 清理，不存在残留。"""
    created_path = []

    def fake_popen(cmd, **kw):
        ctrl = Controller([b"working...\n"])
        ctrl.cancel_path = kw.get("env", {}).get("FE_GUI_CANCEL") or None
        created_path.append(ctrl.cancel_path)
        # 直到检测到取消文件才 EOF（模拟 runner 30ms 内发现取消）
        return FakeProc(ctrl)

    monkeypatch.setattr(engine_mod.subprocess, "Popen", fake_popen)
    dummy = GUI_DIR / "app" / "core" / "engine.py"
    monkeypatch.setattr(engine_mod, "find_exe", lambda: str(dummy))
    monkeypatch.setattr(engine_mod, "_HELPER_PYTHON", sys.executable)

    items, done = collect(svc.run(["enc", "src"]))
    time.sleep(0.1)
    svc.cancel()
    # 取消后文件被创建，运行仍在进行
    path = created_path[0]
    assert os.path.exists(path)

    assert done.wait(5)
    # 结束后 finally 清理，取消文件不再存在
    assert not os.path.exists(path)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))