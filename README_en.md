# FileEncryptor GUI

> **English** · [中文](README.md) | [English](README_en.md)

A graphical interface wrapper for the FileEncryptor command-line tool, **supporting Windows and Linux**. Provides single-file encryption, decryption, and batch processing, with XChaCha20-Poly1305 and AEGIS-256 encryption algorithms.

## Directory Structure

```
FileEncryptor-GUI/
├── app/
│   ├── core/            # Pure logic layer (no GUI deps, unit-testable)
│   │   ├── about_info.py #   About-page info (engine probe + environment)
│   │   ├── args.py      #   arg building + input validation
│   │   ├── config.py    #   config read/write
│   │   ├── engine.py    #   engine service (locate + stream + cancel)
│   │   ├── i18n.py      #   localization
│   │   ├── strength.py  #   password strength
│   │   ├── version.py   #   single source of version + repo URLs
│   │   └── _runner.py   #   pseudo-terminal bridge (auto-invoked, no manual run)
│   └── ui/              # UI layer
│       ├── gui.py       #   GUI main program
│       ├── pages.py     #   page components
│       ├── theme.py     #   theme management
│       └── widgets.py   #   widget library
├── 启动GUI.bat          # Windows launcher
├── 启动GUI.sh           # Linux launcher
├── .gitignore / .gitattributes
└── README.md / README_en.md
```

> `tests/` (pytest unit tests + headless smoke) exists only in the local dev environment and is **not distributed with the repo**; the `FileEncryptor.exe` / `FileEncryptor` engine must be obtained and placed as described below, and is **not distributed with the repo**.

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
pip install pywinpty psutil customtkinter

# Linux: customtkinter required (modern UI framework)
pip install customtkinter
# psutil is optional: pip install psutil

# Experimental "image background + blur" feature needs Pillow (optional)
pip install pillow
```

- **customtkinter** (both platforms) — modern UI framework with rounded widgets and dark theme support
- **pywinpty** (Windows only) — injects the password through ConPTY (solves `_getch()` not reading stdin)
- **psutil** (optional, both platforms) — more reliable child-process exit detection
- **Pillow** (optional, both platforms) — powers the experimental "image background + blur" theme (disabled automatically when not installed)

### 3. FileEncryptor Engine

Get the encryption engine from the [original project Releases](https://github.com/Texas-albe/FileEncryptor/releases), and place it in one of the following locations (in priority order):

| Platform | Engine name | Notes |
|---|---|---|
| Windows | `FileEncryptor.exe` | **Official CLI 2.4.0** (the separate CLI component of the original project) |
| Linux | `FileEncryptor` | **Official CLI 2.4.0** (self-contained DEB/RPM packages; after install it's usually at `/usr/bin/FileEncryptor`, which the GUI can find via PATH) |

Search locations (in priority order):

| Location | Notes |
|---|---|
| `FileEncryptor-GUI/` directory | Same directory as the launcher scripts |
| Project root | Parent of the GUI |
| Grandparent directory | Parent of the parent |
| System PATH | Any PATH entry |

> On Linux, a manually placed engine needs executable permission: `chmod +x FileEncryptor`

## Launch

### Windows

Double-click `FileEncryptor-GUI\启动GUI.bat` (recommended), or:

```bash
cd FileEncryptor-GUI
python -m app.ui.gui
```

### Linux

```bash
cd FileEncryptor-GUI
./启动GUI.sh          # first time: chmod +x 启动GUI.sh
# or directly
python3 -m app.ui.gui
```

## Cross-Platform Implementation

Password injection between the GUI and the CLI engine is done through a pseudo-terminal (PTY), with the backend chosen automatically per platform:

- **Windows**: [pywinpty](https://pypi.org/project/pywinpty/) (ConPTY)
- **Linux**: Python's built-in `pty` module, zero external dependencies

Passwords are not passed via command-line arguments (on Linux, `/proc/<pid>/cmdline` is readable by all users). Instead they are passed to the bridge process via environment variables, and are never forwarded to the engine process itself.

## Features

### 1. Encrypt a Single File

Select a source file → enter the password (twice) → choose the algorithm → start encrypting. Output is `.ptd` format.

Optional options:

- **Delete source after encrypt**: delete the original file once encryption succeeds
- **Move to Recycle Bin**: move the original file to the system Recycle Bin on success (safer than deleting; takes priority over "Delete source")
- **Enable zstd compression**: compress with zstd before encrypting (compression level 1–22), greatly shrinking the output for text-like files
- **Write SHA-256 sidecar**: also write a `<output>.ptd.sha256` checksum file on success
- **Asymmetric (rage)**: encrypt to a **recipient public key** instead (an `age1…` string or a public key file); no password is needed and the output is a `.age` file. The "Generate keypair" button creates an X25519 pair on the spot (private key saved as `rage_private.txt` in the chosen directory, public key printed in the log). zstd and SHA-256 do not apply in this mode (the engine ignores them)

> You can also use a **key file** instead of a password: pick a file in the "Key file" field and its contents are used as the password (CLI `-k`, read non-interactively); the password field is then ignored.

### 2. Decrypt a Single File

Select a `.ptd` file → enter the password → start decrypting. To decrypt a rage output (`.age`), tick "rage asymmetric decrypt" and pick the **private key file** (`AGE-SECRET-KEY-…`) in the "Key file" field.

### 3. Batch-Encrypt a Directory

Select a source directory → enter the password → choose an algorithm → start. Recursively encrypts all files in the directory (CLI 2.x writes obfuscated output names). If a `.prs` resume file is detected, the engine automatically continues from where it left off. The concurrency is configured via the engine's `fileencryptor.yaml` (`worker_threads`, 0=auto); the GUI no longer provides a thread-count option. The same "Delete source / Move to Recycle Bin", zstd compression, SHA-256 sidecar and key-file options are supported. (**Batch mode does not support rage** — `-be` rejects `-m rage` on the engine side.)

### 4. Batch-Decrypt a Directory

Select a directory containing `.ptd` files → enter the password → start. Original file names are restored automatically.

### 5. Rotate Key

Change the password of an existing `.ptd` container: pick the container → enter the current password (or select the current key file) → enter and confirm the new password → start (CLI `--rewrap`). Only the header key is rewritten, the **payload ciphertext is untouched**, and the file is updated in place; afterwards it must be decrypted with the new password.

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
| `Ctrl+R` | Switch to rotate-key page |
| `Ctrl+I` | Switch to about page |
| `Ctrl+L` | Export log |
| `Ctrl+W` | Clear log |
| `Esc` | Cancel current operation |

### Utilities

- **Window state memory**: saves position and size on close, restores on next launch
- **Paste path**: right-click in a file field to paste the clipboard path
- **Drag & drop**: drop files onto the field (requires tkinterdnd2)
- **Config persistence**: user preferences auto-saved to `config.ini`
- **Language switch**: choose "中文 / English" in the settings area to switch the UI language instantly
- **Theme switch**: toggle between the two preset light/dark themes in the settings area
- **About page**: shows the GUI version, the **runtime-probed** engine version and capabilities (zstd / AEGIS), engine path, runtime environment, open-source dependencies, friendly links and team pages (Bilibili / GitHub), plus "Copy all info" for pasting into a bug report

> Engine version requirements: both Windows and Linux need **Official CLI 2.4.0 or later** (verified 2.4.1; format v6; operational parameters such as thread count are configured via the engine's `fileencryptor.yaml`; batch decrypt restores original names via `-rn`).

### Experimental: image background

In the "Experimental" card of the settings page you can:

- **Enable image background**: pick a local image as the wallpaper (a built-in gradient is used if none is chosen).
- **Ignores theme colors**: while enabled, the interface no longer follows the light/dark theme (the theme dropdown is disabled).
- **Frosted-glass panels**: the sidebar and content panels themselves are translucent "frosted glass" — they show a real Gaussian-blurred crop of the wallpaper beneath them; the wallpaper is only exposed around the window edges.
- **Color-sampled pseudo-transparency**: controls that cannot be truly transparent (cards, entries, the log box) take their base color from the wallpaper tone at their location (frosted white cards, dark glass log box) so everything blends into the background.
- **Wallpaper blur / Panel blur**: two independent sliders (0–50), each with a numeric box for typing an exact value; panel blur 0 makes the panels fully transparent (wallpaper shown clearly). Text is never blurred.

> **About "transparency" (important)**
> CustomTkinter widgets do not support real background transparency, so:
> - **Structural panels** (sidebar, content area, per-page cards) are `tk.Canvas` that draw the **blurred crop** of the wallpaper at their location, producing genuine frosted glass;
> - **Controls that cannot be transparent** (cards, entries, the log box) use **color-sampled pseudo-transparency**: they take the wallpaper tone at their location as a base color (frosted white cards, dark glass log box) — an approximation, not pixel-level transparency.
>
> **Performance strategy**: the sharp wallpaper is generated once and cached; widgets to tint are registered once by index (`id -> widget`) and only sampled from the cache afterwards (no full `cget` pass); dragging a slider only re-renders the panel/wallpaper layer, never triggers a full window re-render, and never repeatedly reloads (the infinite retry loop was removed — it now only re-tints one idle frame if the layout is not yet stable).

## Notes

- **Password strength is informational only**: the strength meter shown is just a hint; real security depends on password length and complexity
- **Delete source after encryption**: when checked, the original file is deleted after successful encryption. Confirm encryption succeeded before using this
- **Empty output directory**: defaults to the source file's directory
- **Algorithm selection**: XChaCha20-Poly1305 is the default; AEGIS-256 suits CPUs with the required instruction set and falls back automatically if unsupported
- **Resume**: in batch mode, if a `.prs` file is detected, the engine automatically continues from where it left off (single-file mode does not support resume). No manual configuration needed
- **Single-file encryption uses an obfuscated output name**: CLI 2.x obfuscates output names by default (hex name + `.ptd`); after a successful run the GUI logs the output location
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

A: Check the log area. Common causes: wrong password, an existing file with the same name in the output directory, or an incompatible engine version (confirm you're using Official CLI 2.4.0).

## Credits

This project builds a GUI around the [FileEncryptor](https://github.com/Texas-albe/FileEncryptor) CLI engine and uses the following open-source projects. Many thanks to all their authors and maintainers:

| Project | Used for | Link |
|---|---|---|
| FileEncryptor | Underlying encryption engine (XChaCha20-Poly1305 / AEGIS-256) | [GitHub](https://github.com/Texas-albe/FileEncryptor) |
| CustomTkinter | Modern GUI widget framework | [GitHub](https://github.com/TomSchimansky/CustomTkinter) |
| pywinpty | Windows pseudo-terminal (ConPTY) password injection | [GitHub](https://github.com/spyder-ide/pywinpty) |
| Pillow | Image background & blur (experimental theme) | [GitHub](https://github.com/python-pillow/Pillow) |
| psutil | Child-process monitoring (optional) | [GitHub](https://github.com/giampaolo/psutil) |
| tkinterdnd2 | File drag & drop support (optional) | [GitHub](https://github.com/Eliav2/tkinterdnd2) |
| libsodium | Low-level crypto primitives for the engine | [GitHub](https://github.com/jedisct1/libsodium) |