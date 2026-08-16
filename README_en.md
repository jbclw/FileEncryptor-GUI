# FileEncryptor GUI

> **English** · [中文](README.md) | [English](README_en.md)

A graphical interface wrapper for the FileEncryptor command-line tool, **supporting Windows and Linux**. Provides single-file encryption, decryption, and batch processing, with XChaCha20-Poly1305 and AEGIS-256 encryption algorithms.

## Directory Structure

```
FileEncryptor-GUI/
├── gui.py              # GUI main program
├── _runner.py          # Pseudo-terminal bridge script (auto-invoked, no manual run)
├── 启动GUI.bat         # Windows launcher
├── 启动GUI.sh          # Linux launcher
├── FileEncryptor.exe   # Encryption engine (Windows, obtain separately)
├── FileEncryptor       # Encryption engine (Linux, obtain separately)
└── README.md
```

## Requirements

### 1. Python 3.8+

- **Windows**: Download from [python.org](https://www.python.org/downloads/). During installation, check **"Add Python to PATH"**, and make sure **"tcl/tk and IDLE"** is selected under "Optional Features" (required for tkinter).
- **Linux**: Use the distro's python3 and install tkinter:
  ```bash
  # Debian/Ubuntu
  sudo apt install python3 python3-tk
  # Fedora
  sudo dnf install python3 python3-tkinter
  # Arch
  sudo pacman -S python tk
  ```

### 2. Python Dependencies

```bash
# Windows: pywinpty required (PTY password injection); psutil optional
pip install pywinpty psutil

# Linux: no extra dependencies (uses Python's built-in pty module)
# psutil is optional: pip install psutil
```

- **pywinpty** (Windows only) — injects the password through ConPTY (solves `_getch()` not reading stdin)
- **psutil** (optional, both platforms) — more reliable child-process exit detection

### 3. FileEncryptor Engine

Get the encryption engine from the [original project Releases](https://github.com/Texas-albe/FileEncryptor/releases), and place it in one of the following locations (in priority order):

| Platform | Engine name | Notes |
|---|---|---|
| Windows | `FileEncryptor.exe` | **v1.4.1 or later** |
| Linux | `FileEncryptor` | **v1.4.1 or later** (self-contained DEB/RPM packages; after install it's usually at `/usr/bin/FileEncryptor`, which the GUI can find via PATH) |

Search locations (in priority order):

| Location | Notes |
|---|---|
| `FileEncryptor-GUI/` directory | Same directory as gui.py |
| Project root | Parent of the GUI |
| Grandparent directory | Parent of the parent |
| System PATH | Any PATH entry |

> On Linux, a manually placed engine needs executable permission: `chmod +x FileEncryptor`

## Launch

### Windows

Double-click `FileEncryptor-GUI\启动GUI.bat` (recommended), or:

```bash
cd FileEncryptor-GUI
python gui.py
```

### Linux

```bash
cd FileEncryptor-GUI
./启动GUI.sh          # first time: chmod +x 启动GUI.sh
# or directly
python3 gui.py
```

## Cross-Platform Implementation

Password injection between the GUI and the CLI engine is done through a pseudo-terminal (PTY), with the backend chosen automatically per platform:

- **Windows**: [pywinpty](https://pypi.org/project/pywinpty/) (ConPTY)
- **Linux**: Python's built-in `pty` module, zero external dependencies

Passwords are not passed via command-line arguments (on Linux, `/proc/<pid>/cmdline` is readable by all users). Instead they are passed to the bridge process via environment variables, and are never forwarded to the engine process itself.

## Features

### 1. Encrypt a Single File

Select a source file → enter the password (twice) → choose the algorithm → start encrypting. Output is `.ptd` format.

### 2. Decrypt a Single File

Select a `.ptd` file → enter the password → start decrypting.

### 3. Batch-Encrypt a Directory

Select a source directory → enter the password → set thread count → start. Recursively encrypts all files in the directory. If a `.progress` file is detected, the engine will automatically resume from where it left off.

### 4. Batch-Decrypt a Directory

Select a directory containing `.ptd` files → enter the password → set thread count → start.

### Logging & Progress

- Runtime log displayed live at the bottom of the window
- Progress bar shows current task progress
- Cancel an operation midway
- Export the log to a file (click the "Export" button on the right of the log area)

### Shortcuts

| Shortcut | Function |
|---|---|
| `Ctrl+E` | Switch to encrypt-file page |
| `Ctrl+D` | Switch to decrypt-file page |
| `Ctrl+Shift+E` | Switch to batch-encrypt page |
| `Ctrl+Shift+D` | Switch to batch-decrypt page |
| `Ctrl+L` | Export log |
| `Ctrl+W` | Clear log |
| `Esc` | Cancel current operation |

### Utilities

- **Window state memory**: saves position and size on close, restores on next launch
- **Paste path**: right-click in a file field to paste the clipboard path
- **Drag & drop**: drop files onto the field (requires tkinterdnd2)
- **Config persistence**: user preferences auto-saved to `config.ini`

> Engine version requirements: both Windows and Linux need **v1.4.1+** (v1.3.0+ for XChaCha20-Poly1305 / AEGIS-256 algorithm selection; resume is automatic in batch mode, no extra parameter needed).

## Notes

- **Password strength is informational only**: the strength meter shown is just a hint; real security depends on password length and complexity
- **Delete source after encryption**: when checked, the original file is deleted after successful encryption. Confirm encryption succeeded before using this
- **Empty output directory**: defaults to the source file's directory
- **Algorithm selection**: XChaCha20-Poly1305 is the default; AEGIS-256 suits CPUs with the required instruction set and falls back automatically if unsupported
- **Resume**: in batch mode, if a `.progress` file is detected, the engine automatically continues from where it left off (single-file mode does not support resume). No manual configuration needed
- **Linux fonts**: the UI defaults to DejaVu Sans (bundled with mainstream distros); it falls back to the default font if missing

## FAQ

**Q: "No Python with winpty found" on startup (Windows only)**

A: Make sure pywinpty and tkinter are installed:
```bash
pip install pywinpty psutil
python -c "import tkinter; import winpty; print('OK')"
```

**Q: "FileEncryptor engine not found"**

A: Put `FileEncryptor.exe` (Windows) or `FileEncryptor` (Linux, no extension and executable) in the `FileEncryptor-GUI/` directory, the project root, or the system PATH.

**Q: GUI won't start on Linux, tkinter-related error**

A: Install the distro's tkinter package (see Requirements). On Linux, tkinter is usually not installed with python3 by default.

**Q: Encrypt/Decrypt does nothing**

A: Check the log area. Common causes: wrong password, an existing file with the same name in the output directory, or an incompatible engine version (confirm you're using v1.4.1+).