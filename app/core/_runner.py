#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileEncryptor PTY runner - bridge script
Runs the FileEncryptor engine through a pseudo-terminal so the CLI's
_getch()/termios password prompt can be fed programmatically.

Platform backends:
    Windows -> pywinpty (ConPTY)
    POSIX   -> built-in pty module (no external dependency)

Called by gui.py as a subprocess; streams output to stdout.

Usage:
    python _runner.py <engine_path> <args_json> <overwrite> <fallback> <timeout>

Passwords are passed via environment variables FE_GUI_PW1 / FE_GUI_PW2
(/proc/<pid>/environ is only readable by the owner, safer than argv).

Cancellation is handled via the environment variable FE_GUI_CANCEL, which
holds the path to a cancel signal file. The GUI writes that file to request
a stop; this script detects it during its polling loop, kills the engine and
exits immediately (~30ms). A file (not a signal) is used so behaviour is
identical on Windows and POSIX, and so the engine is always killed as a
child of this process rather than left orphaned.

Output format:
    Normal lines: raw program output
    Final line: __EXIT__:<code>
"""
import sys
import os
import subprocess
import json
import time

IS_WINDOWS = (os.name == "nt")

if IS_WINDOWS:
    try:
        import winpty
    except ImportError:
        winpty = None
else:
    winpty = None

try:
    import psutil
except ImportError:
    psutil = None


# ── 进程后端抽象（统一接口）──────────────────────────────────────────────

class WinPtyProcess:
    """Windows 后端：winpty (ConPTY)"""

    def __init__(self, argv, cwd, env=None):
        if winpty is None:
            raise RuntimeError("pywinpty not installed")
        self.proc = winpty.PtyProcess.spawn(argv, cwd=cwd, env=env)
        self.pid = self.proc.pid
        try:
            self.sock = self.proc.fileobj
            self.sock.setblocking(False)
        except Exception:
            self.sock = None

    def read(self):
        """非阻塞读取，返回 str（无数据返回空串）"""
        if self.sock is None:
            return ""
        try:
            data = self.sock.recv(65536)
        except Exception:
            return ""
        if not data:
            return ""
        return data.decode("utf-8", errors="replace")

    def writeline(self, text):
        self.proc.write(text + "\r")

    def isalive(self):
        return self.proc.isalive()

    def exitstatus(self):
        try:
            return self.proc.exitstatus
        except Exception:
            return -999

    def close(self):
        try:
            self.proc.close()
        except Exception:
            pass

    def kill(self):
        try:
            self.proc.kill()
        except Exception:
            pass


class PosixPtyProcess:
    """Linux/macOS 后端：内置 pty 模块，零外部依赖"""

    def __init__(self, argv, cwd, env=None):
        import pty
        import fcntl
        self.master_fd, slave_fd = pty.openpty()
        self.proc = subprocess.Popen(
            argv,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            cwd=cwd,
            env=env,
        )
        os.close(slave_fd)
        # 设为非阻塞
        fl = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self.master_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        self.pid = self.proc.pid

    def read(self):
        """非阻塞读取，返回 str（无数据返回空串；EIO 表示对端已关闭）"""
        try:
            data = os.read(self.master_fd, 65536)
        except BlockingIOError:
            return ""
        except OSError:
            return ""
        if not data:
            return ""
        return data.decode("utf-8", errors="replace")

    def writeline(self, text):
        # termios 默认 ICRNL 会把 \r 翻译为 \n，但直接发 \n 最稳妥
        os.write(self.master_fd, (text + "\n").encode("utf-8"))

    def isalive(self):
        return self.proc.poll() is None

    def exitstatus(self):
        return self.proc.returncode

    def close(self):
        try:
            os.close(self.master_fd)
        except Exception:
            pass

    def kill(self):
        try:
            self.proc.kill()
        except Exception:
            pass


def spawn_backend(argv, cwd):
    """按平台选择后端并启动进程（密码环境变量不传给引擎）"""
    child_env = {k: v for k, v in os.environ.items()
                 if not k.startswith("FE_GUI_PW")}
    if IS_WINDOWS:
        return WinPtyProcess(argv, cwd, child_env)
    return PosixPtyProcess(argv, cwd, child_env)


# ── 主流程 ──────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print("__EXIT__:-1")
        print("__ERR__:not enough arguments")
        return

    engine_path = sys.argv[1]
    args = json.loads(sys.argv[2])
    # 密码经环境变量传递（比命令行参数安全，见文件头说明）
    password = os.environ.get("FE_GUI_PW1") or None
    password2 = os.environ.get("FE_GUI_PW2") or None
    # 取消信号文件路径：GUI 写入该文件即请求取消（详见文件头"取消机制"注释）
    cancel_path = os.environ.get("FE_GUI_CANCEL") or None
    overwrite = sys.argv[3] if len(sys.argv) > 3 else None
    fallback = sys.argv[4] if len(sys.argv) > 4 else None
    timeout = float(sys.argv[5]) if len(sys.argv) > 5 else 300

    if overwrite == "":
        overwrite = None
    elif overwrite is not None:
        overwrite = overwrite.lower() in ("y", "yes", "true", "1")

    if fallback == "":
        fallback = None
    elif fallback is not None:
        fallback = fallback.lower() in ("y", "yes", "true", "1")

    argv = [engine_path] + args
    cwd = os.path.dirname(engine_path) if os.path.dirname(engine_path) else None

    try:
        proc = spawn_backend(argv, cwd)
    except Exception as e:
        print(f"__ERR__:{e}")
        print("__EXIT__:-1")
        return

    psutil_proc = None
    if psutil:
        try:
            psutil_proc = psutil.Process(proc.pid)
        except Exception:
            pass

    t0 = time.time()
    all_text = ""
    sent_pw1 = False
    sent_pw2 = False
    sent_overwrite = False
    sent_fallback = False
    exit_code = None
    last_flush_len = 0

    while True:
        if timeout and (time.time() - t0) > timeout:
            proc.kill()
            sys.stdout.write("__ERR__:timeout\n")
            sys.stdout.flush()
            break

        # 取消检查：GUI 写入取消文件即请求终止。
        # 命中后 kill 引擎直接 break，走文件尾 __EXIT__:-1，规避正常退出路径
        # 中 sleep(0.3) 与 psutil.wait(timeout=2) 的等待，保证取消即时（~30ms）。
        if cancel_path and os.path.exists(cancel_path):
            proc.kill()
            break

        # 读取新输出
        new_text = proc.read()
        if new_text:
            all_text += new_text

        # 密码注入
        if password and not sent_pw1 and "Enter password" in all_text:
            time.sleep(0.15)
            proc.writeline(password)
            sent_pw1 = True

        if not sent_pw2 and "Re-enter password" in all_text:
            pw = password2 if password2 else password
            if pw:
                time.sleep(0.15)
                proc.writeline(pw)
                sent_pw2 = True

        # 覆盖确认
        if overwrite is not None and not sent_overwrite and "Overwrite?" in all_text:
            time.sleep(0.15)
            proc.writeline("y" if overwrite else "n")
            sent_overwrite = True

        # 算法回退确认
        if fallback is not None and not sent_fallback and "switch to XChaCha20" in all_text:
            time.sleep(0.15)
            proc.writeline("y" if fallback else "n")
            sent_fallback = True

        # 增量输出到 stdout
        if len(all_text) > last_flush_len:
            new_part = all_text[last_flush_len:]
            last_flush_len = len(all_text)
            sys.stdout.write(new_part)
            sys.stdout.flush()

        # 检查进程退出
        exited = False
        if psutil_proc is not None:
            try:
                if not psutil_proc.is_running():
                    exit_code = psutil_proc.wait(timeout=2)
                    time.sleep(0.3)
                    remaining = proc.read()
                    if remaining:
                        sys.stdout.write(remaining)
                        sys.stdout.flush()
                    exited = True
            except psutil.NoSuchProcess:
                exit_code = -999
                exited = True
            except Exception:
                pass
        if not exited and not proc.isalive():
            time.sleep(0.3)
            remaining = proc.read()
            if remaining:
                sys.stdout.write(remaining)
                sys.stdout.flush()
            exit_code = proc.exitstatus()
            exited = True

        if exited:
            break

        time.sleep(0.03)

    proc.close()

    sys.stdout.write(f"\n__EXIT__:{exit_code if exit_code is not None else -1}\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
