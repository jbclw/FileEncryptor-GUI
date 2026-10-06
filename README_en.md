# FileEncryptor GUI

> **English** · [中文](README.md) | [English](README_en.md)

A graphical interface wrapper for the FileEncryptor command-line tool, **supporting Windows and Linux**. Provides single-file encryption, decryption, and batch processing, with four symmetric algorithms — XChaCha20-Poly1305, AEGIS-256, AES-256-GCM and SM4-GCM — plus X25519 / X448 asymmetric encryption (post-quantum hybrid by default), along with directory packing, splitting, watermarking and key wrapping.

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
| Windows | `FileEncryptor.exe` | **Official CLI 3.0.0** (the separate CLI component of the original project) |
| Linux | `FileEncryptor` | **Official CLI 3.0.0** (self-contained DEB/RPM packages; after install it's usually at `/usr/bin/FileEncryptor`, which the GUI can find via PATH) |

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

Passwords are not passed via command-line arguments (on Linux, `/proc/<pid>/cmdline` is readable by all users). Instead they are passed to the bridge process via a temp password file owned by the current user, and are never forwarded to the engine process itself.

## Features

### 1. Encrypt a Single File

Select a source file → enter the password (twice) → choose the algorithm → start encrypting. Output is `.ptd` format.

Optional options:

- **Delete source after encrypt**: delete the original file once encryption succeeds
- **Move to Recycle Bin**: move the original file to the system Recycle Bin on success (safer than deleting; takes priority over "Delete source")
- **Enable zstd compression**: compress with zstd before encrypting (compression level 1–22), greatly shrinking the output for text-like files
- **Write SHA-256 sidecar**: also write a `<output>.ptd.sha256` checksum file on success (in asymmetric mode the engine writes no sidecar, so the UI hides this option)
- **Embed watermark**: write a traceable watermark into the ciphertext tail; you may supply a **watermark signing key (PEM)** for a signed watermark, or click "Generate signing key" to create a keypair on the spot (private key saved to the chosen file, public key shown in the log)
- **Split volumes**: split the output by size (e.g. 512MB / 4GB) into `<name>.001.ptd`, `<name>.002.ptd`, …; picking any volume restores the whole file automatically on decryption
- **Pack into a single file**: switch the source to a **directory** and pack the whole tree into one `.ptd` (CLI `-p`); decryption expands the tree automatically. **Packing and asymmetric encryption are mutually exclusive** (the engine rejects the combination)
- **X25519 asymmetric (PQC hybrid)**: encrypt to a **recipient public key** instead (an `age1…` / `MLKEM1-…` / `X448-…` string or a public key file); no password is needed and the output is still a `.ptd` container. "Generate keypair" creates a keypair on the spot (default **X25519 + ML-KEM-768 hybrid**; private key saved as `rage_private.txt` in the chosen directory, public key shown in the log). Tick "Use X448 curve" or "Disable post-quantum (classic X25519)" to change the generated key type. `--sha256` does not apply in this mode, but zstd and splitting still work

> You can also use a **key file** instead of a password: pick a file in the "Key file" field and its contents are used as the password (CLI `-k`, read non-interactively); the password field is then ignored.

### 2. Decrypt a Single File

Select a `.ptd` file → enter the password → start decrypting. To decrypt an asymmetric output, tick "Decrypt with private key" and pick the **private key file** in the "Key file" field (no algorithm needed — the engine detects it from the key material).

Optional options:

- **Preview plaintext only (no write)**: print the first bytes of the decrypted plaintext to the log to confirm the password/content, writing no file
- **Keep as single file (don't expand)**: for packed outputs, keep the result as a single file instead of expanding the tree
- **Force decrypt a damaged file**: best-effort recovery when the container is partially corrupted (not needed for healthy files)
- **Extract watermark (no decryption)**: read the watermark in the ciphertext tail without a password; optionally verify it with a **watermark public key (PEM)**

### 3. Batch-Encrypt a Directory

Select a source directory → enter the password → choose an algorithm → start. Recursively encrypts all files in the directory (output-name obfuscation is on by default, producing `<16-hex>.<3-letter>.ptd`). If a `.prs` resume file is detected, the engine automatically continues from where it left off. The concurrency is configured via the engine's `fileencryptor.yaml` (`worker_threads`, 0=auto); the GUI no longer provides a thread-count option. The same "Delete source / Move to Recycle Bin", zstd compression, SHA-256 sidecar and key-file options are supported. (**Batch mode does not support asymmetric encryption** — `-be` rejects recipient keys on the engine side.)

### 4. Batch-Decrypt a Directory

Select a directory containing `.ptd` files → enter the password → start. Original file names (including CJK) are restored automatically.

### 5. Rotate Key

Change the password of an existing `.ptd` container: pick the container → enter the current password (or select the current key file) → enter and confirm the new password → start (CLI `--rewrap`). Only the header key is rewritten, the **payload ciphertext is untouched**, and the file is updated in place; afterwards it must be decrypted with the new password.

### 6. Key Wrapping

Key wrapping operates on a **32-byte data key (DEK)**, not on file content:

- **Wrap**: pick a 32-byte key file → choose the wrap algorithm (`kwp` RFC 5649 default / `aes-kw` RFC 3394 / `pubkey`) → use a password or key file (the `pubkey` route uses a recipient public key instead) → output a `.fekw` blob
- **Unwrap**: pick a `.fekw` → use the password / key file (or an identity private key on the `pubkey` route) → recover the 32-byte DEK

> Key wrapping is independent of file encryption/decryption and is commonly used to distribute a data key securely.

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
| `Ctrl+K` | Switch to key-wrapping page |
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
- **About page**: shows the GUI version, the **runtime-probed** engine version and capabilities (zstd / AEGIS / AES-GCM / SM4 / PQC / split / pack / keywrap / vault), engine path, runtime environment, open-source dependencies, friendly links and team pages (Bilibili / GitHub), plus "Copy all info" for pasting into a bug report

> Engine version requirements: both Windows and Linux need **Official CLI 3.0.0 or later** (verified 3.0.0; format v6; operational parameters such as thread count are configured via the engine's `fileencryptor.yaml`; batch decrypt restores original names via `-rn`).

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
- **Algorithm selection**: XChaCha20-Poly1305 is the default; AEGIS-256 suits CPUs with the required instruction set and falls back automatically if unsupported; AES-256-GCM / SM4-GCM target AES-NI and Chinese SM4 scenarios respectively
- **Single-file encryption uses an obfuscated output name**: output-name obfuscation is on by default (`<16-hex>.<3-letter>.ptd`); after a successful run the GUI logs the output location, and decryption restores the original name automatically
- **Packing vs. asymmetric**: `-p` (pack a directory) cannot be combined with a recipient public key (asymmetric) — the engine errors on that combination; the UI cancels packing when asymmetric is ticked
- **Resume**: in batch mode, if a `.prs` file is detected, the engine automatically continues from where it left off (single-file mode does not support resume). No manual configuration needed
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

A: Check the log area. Common causes: wrong password, an existing file with the same name in the output directory, or an incompatible engine version (confirm you're using Official CLI 3.0.0).

## Credits

This project builds a GUI around the [FileEncryptor](https://github.com/Texas-albe/FileEncryptor) CLI engine and uses the following open-source projects. Many thanks to all their authors and maintainers:

| Project | Used for | Link |
|---|---|---|
| FileEncryptor | Underlying encryption engine (XChaCha20-Poly1305 / AEGIS-256 / AES-GCM / SM4) | [GitHub](https://github.com/Texas-albe/FileEncryptor) |
| CustomTkinter | Modern GUI widget framework | [GitHub](https://github.com/TomSchimansky/CustomTkinter) |
| pywinpty | Windows pseudo-terminal (ConPTY) password injection | [GitHub](https://github.com/spyder-ide/pywinpty) |
| Pillow | Image background & blur (experimental theme) | [GitHub](https://github.com/python-pillow/Pillow) |
| psutil | Child-process monitoring (optional) | [GitHub](https://github.com/giampaolo/psutil) |
| tkinterdnd2 | File drag & drop support (optional) | [GitHub](https://github.com/Eliav2/tkinterdnd2) |
| libsodium | Low-level crypto primitives for the engine | [GitHub](https://github.com/jedisct1/libsodium) |