#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileEncryptor winpty runner - bridge script
Runs FileEncryptor.exe via winpty (ConPTY) to handle _getch() password input.
Called by gui.py as a subprocess; streams output to stdout.

Usage:
    python _runner.py <exe_path> <args_json> <password> <password2> <overwrite> <fallback> <timeout>

Output format:
    Normal lines: raw program output
    Final line: __EXIT__:<code>
"""
import sys
import os
import json
import time
import re

try:
    import winpty
except ImportError:
    print("__EXIT__:-1")
    print("__ERR__:winpty not installed")
    sys.exit(1)

try:
    import psutil
except ImportError:
    psutil = None


def main():
    if len(sys.argv) < 3:
        print("__EXIT__:-1")
        print("__ERR__:not enough arguments")
        return

    exe_path = sys.argv[1]
    args = json.loads(sys.argv[2])
    password = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None
    password2 = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None
    overwrite = sys.argv[5] if len(sys.argv) > 5 else None
    fallback = sys.argv[6] if len(sys.argv) > 6 else None
    timeout = float(sys.argv[7]) if len(sys.argv) > 7 else 300

    if overwrite == "":
        overwrite = None
    elif overwrite is not None:
        overwrite = overwrite.lower() in ("y", "yes", "true", "1")

    if fallback == "":
        fallback = None
    elif fallback is not None:
        fallback = fallback.lower() in ("y", "yes", "true", "1")

    argv = [exe_path] + args
    cwd = os.path.dirname(exe_path) if os.path.dirname(exe_path) else None

    try:
        proc = winpty.PtyProcess.spawn(argv, cwd=cwd)
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

    try:
        sock = proc.fileobj
        sock.setblocking(False)
    except Exception:
        sock = None

    def drain():
        chunks = []
        if sock is None:
            return chunks
        while True:
            try:
                data = sock.recv(65536)
            except (BlockingIOError, OSError):
                break
            except Exception:
                break
            if not data:
                break
            chunks.append(data.decode("utf-8", errors="replace"))
        return chunks

    t0 = time.time()
    all_text = ""
    sent_pw1 = False
    sent_pw2 = False
    sent_overwrite = False
    sent_fallback = False
    exit_code = None
    last_flush_len = 0
    out = getattr(sys.stdout, "buffer", sys.stdout)

    while True:
        if timeout and (time.time() - t0) > timeout:
            try:
                proc.kill()
            except Exception:
                pass
            sys.stdout.write("__ERR__:timeout\n")
            sys.stdout.flush()
            break

        new_chunks = drain()
        if new_chunks:
            all_text += "".join(new_chunks)

        # Password injection
        if password and not sent_pw1 and "Enter password" in all_text:
            time.sleep(0.15)
            proc.write(password + "\r")
            sent_pw1 = True

        if not sent_pw2 and "Re-enter password" in all_text:
            pw = password2 if password2 else password
            if pw:
                time.sleep(0.15)
                proc.write(pw + "\r")
                sent_pw2 = True

        # Overwrite confirmation
        if overwrite is not None and not sent_overwrite and "Overwrite?" in all_text:
            time.sleep(0.15)
            proc.write(("y" if overwrite else "n") + "\r")
            sent_overwrite = True

        # AES fallback
        if fallback is not None and not sent_fallback and "switch to XChaCha20" in all_text:
            time.sleep(0.15)
            proc.write(("y" if fallback else "n") + "\r")
            sent_fallback = True

        # Flush new output to stdout
        if len(all_text) > last_flush_len:
            new_part = all_text[last_flush_len:]
            last_flush_len = len(all_text)
            sys.stdout.write(new_part)
            sys.stdout.flush()

        # Check if process exited
        exited = False
        if psutil_proc is not None:
            try:
                if not psutil_proc.is_running():
                    exit_code = psutil_proc.wait(timeout=2)
                    time.sleep(0.3)
                    new_chunks = drain()
                    if new_chunks:
                        remaining = "".join(new_chunks)
                        sys.stdout.write(remaining)
                        sys.stdout.flush()
                    exited = True
            except psutil.NoSuchProcess:
                exit_code = -999
                exited = True
            except Exception:
                pass
        else:
            if not proc.isalive():
                time.sleep(0.5)
                try:
                    exit_code = proc.exitstatus
                except Exception:
                    exit_code = -999
                new_chunks = drain()
                if new_chunks:
                    remaining = "".join(new_chunks)
                    sys.stdout.write(remaining)
                    sys.stdout.flush()
                exited = True

        if exited:
            break

        time.sleep(0.03)

    try:
        proc.close()
    except Exception:
        pass

    sys.stdout.write(f"\n__EXIT__:{exit_code if exit_code is not None else -1}\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()