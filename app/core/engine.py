#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
engine.py —— 引擎服务层
封装 FileEncryptor 引擎的查找与流式执行，GUI 不再直接接触 subprocess / PTY。

职责：
  - find_exe / find_helper_python：定位引擎与可运行 _runner.py 的解释器
  - run_fileencryptor_stream：通过 _runner.py 流式运行引擎（yield 输出）
  - EngineService：持有取消状态，向 _runner.py 下发取消信号并提供可测试接口

设计要点（取消机制）：
  - GUI 侧的样例读是阻塞的，但取消的关键在于 _runner.py 退出后 GUI 会收到 EOF
    自动解锁，故不需要在 GUI 侧做非阻塞读。
  - 取消信号通过"取消文件"传递：GUI 在 tempfile 下生成唯一路径，借助环境变量
    FE_GUI_CANCEL 传给 _runner.py；_runner.py 在其 30ms 轮询里检测该文件，
    命中即 kill 引擎并退出（跳过正常退出路径的 sleep/psutil.wait），总延迟约 30-50ms。
  - 用文件而非信号：Windows 上 SIGTERM 不可靠且 proc.terminate() 是硬杀，
    会留下孤儿引擎；文件方案两端行为一致，且 _runner.py 能先杀引擎再退出。
"""
import os
import sys
import re
import json
import subprocess
import tempfile
import uuid
from pathlib import Path

IS_WINDOWS = (os.name == "nt")

try:
    import winpty
except ImportError:
    winpty = None

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 引擎文件名按平台区分：Windows 为 FileEncryptor.exe，POSIX 为 FileEncryptor
if IS_WINDOWS:
    _ENGINE_NAMES = ["FileEncryptor.exe"]
else:
    _ENGINE_NAMES = ["FileEncryptor", "fileencryptor"]

# 可执行文件查找策略（按优先级）：
#   1. 本模块（gui.py 同目录）下的引擎可执行文件
#   2. 父目录（即项目根目录）
#   3. 祖父目录
#   4. 系统 PATH
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


def run_fileencryptor_stream(args, password=None, password2=None, timeout=300,
                             overwrite=None, fallback=None, cancel_path=None):
    """
    通过 _runner.py 流式运行 FileEncryptor 引擎
    伪终端模拟键盘输入，解决 _getch()/termios 密码注入问题
    （Windows 走 pywinpty，POSIX 走内置 pty 模块）

    Yields (line_text, progress_info, error) 三元组
      - line_text: 当前行文本（空字符串表示控制消息/进度行）
      - progress_info: (current, total) 字节数 或 None
      - error: 错误文本（空字符串表示正常），最后一条为退出码(整数)

    cancel_path: 取消信号文件路径。由 EngineService 生成，经环境变量
      FE_GUI_CANCEL 传给 _runner.py；取消路径在 run() 的 finally 中清理。
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
    env["FE_GUI_CANCEL"] = cancel_path or ""

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


class EngineService:
    """引擎执行服务：封装取消状态，向 _runner.py 下发取消信号。

    GUI 只需调用 run() 消费流式输出，以及 cancel() 请求取消。
    """

    def __init__(self):
        self.cancelled = False
        self._cancel_path = None

    def _new_cancel_path(self):
        """生成一个唯一的取消信号文件路径（临时目录 + 进程 pid + 随机串）"""
        return os.path.join(
            tempfile.gettempdir(),
            f"fe_gui_cancel_{os.getpid()}_{uuid.uuid4().hex}.tmp",
        )

    def cancel(self):
        """请求取消：置标志并写入取消文件。
        取消信号即时通知引擎侧（_runner.py 前台读取），可能失败但返回信息。
        _runner.py 的 30ms 轮询会发现它并杀掉引擎，随后退出，GUI 收到 EOF 完成取消。
        """
        self.cancelled = True
        if self._cancel_path:
            try:
                Path(self._cancel_path).touch()
            except Exception:
                pass

    def run(self, args, password=None, password2=None, timeout=300,
            overwrite=None, fallback=None):
        """流式运行引擎，yield (line_text, progress, error)。
        每次调用会重置取消状态并新建取消文件路径，结束时清理取消文件。
        """
        self.cancelled = False
        self._cancel_path = self._new_cancel_path()
        try:
            yield from run_fileencryptor_stream(
                args, password=password, password2=password2,
                timeout=timeout, overwrite=overwrite, fallback=fallback,
                cancel_path=self._cancel_path,
            )
        finally:
            self._cleanup()

    def _cleanup(self):
        if self._cancel_path:
            try:
                os.remove(self._cancel_path)
            except FileNotFoundError:
                pass
            except Exception:
                pass
            self._cancel_path = None