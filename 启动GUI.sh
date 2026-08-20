#!/usr/bin/env bash
# FileEncryptor GUI Linux/macOS 启动脚本
# 自动查找可用的 Python 3 解释器并启动 GUI

cd "$(dirname "$0")" || exit 1

# 按优先级查找 Python 3
PY=""
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        if "$cmd" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
            PY="$cmd"
            break
        fi
    fi
done

if [ -z "$PY" ]; then
    echo "[错误] 未找到 Python 3.8+，请先安装："
    echo "  Debian/Ubuntu:  sudo apt install python3 python3-tk"
    echo "  Fedora:         sudo dnf install python3 python3-tkinter"
    echo "  Arch:           sudo pacman -S python tk"
    exit 1
fi

# 检查 tkinter
if ! "$PY" -c "import tkinter" 2>/dev/null; then
    echo "[错误] 缺少 tkinter，请安装："
    echo "  Debian/Ubuntu:  sudo apt install python3-tk"
    echo "  Fedora:         sudo dnf install python3-tkinter"
    echo "  Arch:           sudo pacman -S tk"
    exit 1
fi

exec "$PY" -m app.ui.gui "$@"
