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

if IS_WINDOWS:
    _ENGINE_NAMES = ["FileEncryptor.exe"]
else:
    _ENGINE_NAMES = ["FileEncryptor", "fileencryptor"]

EXE_CANDIDATES = []
for _name in _ENGINE_NAMES:
    EXE_CANDIDATES += [
        os.path.join(_SCRIPT_DIR, _name),
        os.path.join(_SCRIPT_DIR, "..", _name),
        os.path.join(_SCRIPT_DIR, "..", "..", _name),
        _name,
    ]


def find_exe():
    """查找可执行文件路径"""
    for p in EXE_CANDIDATES:
        absp = os.path.abspath(p)
        if os.path.isfile(absp) and os.access(absp, os.X_OK):
            return absp
    return os.path.abspath(EXE_CANDIDATES[-1])


def find_helper_python():
    """找到可运行 _runner.py 的 Python
    POSIX：_runner.py 使用内置 pty，直接返回当前解释器
    Windows：_runner.py 依赖 winpty，优先当前解释器（venv），次选 PATH 中装有 winpty 的解释器
    """
    if not IS_WINDOWS:
        return sys.executable
    if winpty is not None:
        return sys.executable
    for cmd in ["python", "python3"]:
        try:
            r = subprocess.run([cmd, "-c", "import winpty; print('OK')"],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and "OK" in r.stdout:
                return cmd
        except Exception:
            pass
    return None


_HELPER_PYTHON = None

# 进度行单位 -> 字节倍数（CLI 2.x 输出 NNN B/KB/MB/GB，1.x 为 NNN/NNN bytes）
_UNIT_BYTES = {"B": 1, "KB": 1024, "KiB": 1024, "MB": 1024 ** 2, "MiB": 1024 ** 2,
               "GB": 1024 ** 3, "GiB": 1024 ** 3, "bytes": 1}
_PROGRESS_RE = re.compile(r'(\d+(?:\.\d+)?)\s*([A-Za-z]*)\s*/\s*(\d+(?:\.\d+)?)\s+'
                          r'(B|KB|KiB|MB|MiB|GB|GiB|bytes)\b', re.IGNORECASE)


def _parse_progress(line):
    """解析进度行 -> (current, total) 字节数；不匹配返回 None。

    兼容两种格式：1.x `512/1024 bytes` 与 2.x `22 B/22 B`（单位在斜杠两侧）。
    换算单位取斜杠右侧（两种格式右侧都有单位）。
    """
    m = _PROGRESS_RE.search(line)
    if not m:
        return None
    k = _UNIT_BYTES.get(m.group(4), 1)
    return (round(float(m.group(1)) * k), round(float(m.group(3)) * k))


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
    if not os.path.isfile(exe):
        engine_name = _ENGINE_NAMES[0]
        yield ("", None, f"FileEncryptor engine not found: {engine_name}")
        return
    if _HELPER_PYTHON is None:
        _HELPER_PYTHON = find_helper_python()
    if _HELPER_PYTHON is None:
        yield ("", None, "No Python with winpty found. Run: pip install pywinpty")
        return
    runner_script = os.path.join(_SCRIPT_DIR, "_runner.py")
    if not os.path.isfile(runner_script):
        runner_script = os.path.join(os.path.dirname(_SCRIPT_DIR), "_runner.py")
    args_json = json.dumps(args)
    ow = "" if overwrite is None else ("y" if overwrite else "n")
    fb = "" if fallback is None else ("y" if fallback else "n")
    pw_file = ""
    try:
        fd, pw_file = tempfile.mkstemp(prefix="fe_pw_", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write((password or "") + "\n")
            f.write((password2 or "") + "\n")
        if not IS_WINDOWS:
            try:
                os.chmod(pw_file, 0o600)
            except Exception:
                pass
        cmd = [_HELPER_PYTHON, runner_script, exe, args_json, ow, fb, str(int(timeout)), pw_file]
        env = dict(os.environ)
        env["FE_GUI_CANCEL"] = cancel_path or ""
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                env=env,
            )
        except Exception as e:
            yield ("", None, f"Failed to spawn runner: {e}")
            return
    except Exception as e:
        yield ("", None, f"Failed to create password file: {e}")
        if pw_file and os.path.exists(pw_file):
            try:
                os.unlink(pw_file)
            except Exception:
                pass
        return
    try:
        exit_code = -1
        buffer = ""
        while True:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")
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
                progress = _parse_progress(line)
                if progress:
                    yield ("", progress, "")
                elif line.strip():
                    yield (line, None, "")
        if buffer.startswith("__EXIT__:"):
            try:
                exit_code = int(buffer.split(":", 1)[1].strip())
            except ValueError:
                exit_code = -1
        elif buffer.strip():
            progress = _parse_progress(buffer)
            if progress:
                yield ("", progress, "")
            else:
                yield (buffer.rstrip("\r"), None, "")
        yield ("", None, exit_code)
    finally:
        # 删除临时密码文件，避免每次运行都在临时目录残留明文密码
        try:
            os.unlink(pw_file)
        except OSError:
            pass


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
        """请求取消：置标志并写入取消文件。"""
        self.cancelled = True
        if self._cancel_path:
            try:
                Path(self._cancel_path).touch()
            except Exception:
                pass

    def run(self, args, password=None, password2=None, timeout=300,
            overwrite=None, fallback=None):
        """流式运行引擎，yield (line_text, progress, error)。"""
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
        self._cancel_path = None