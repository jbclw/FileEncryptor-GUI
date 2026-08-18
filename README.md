# FileEncryptor GUI

> **English** · [中文](README.md) | [English](README_en.md)

FileEncryptor 命令行工具的图形界面封装，**支持 Windows 与 Linux**。提供文件加密、解密和批量处理功能，支持 XChaCha20-Poly1305 和 AEGIS-256 两种加密算法。

## 目录结构

```
FileEncryptor-GUI/
├── gui.py              # GUI 主程序
├── _runner.py          # 伪终端桥接脚本（自动调用，无需手动运行）
├── 启动GUI.bat         # Windows 启动脚本
├── 启动GUI.sh          # Linux 启动脚本
├── FileEncryptor.exe   # 加密引擎（Windows，需自行获取）
├── FileEncryptor       # 加密引擎（Linux，需自行获取）
└── README.md
```

## 环境要求

### 1. Python 3.8+

- **Windows**：从 [python.org](https://www.python.org/downloads/) 下载安装。安装时务必勾选 **"Add Python to PATH"**，并在"Optional Features"中确保 **"tcl/tk and IDLE"** 已选中（这是 tkinter 的依赖）
- **Linux**：使用发行版自带的 python3，并安装 tkinter：
  ```bash
  # Debian/Ubuntu
  sudo apt install python3 python3-tk
  # Fedora
  sudo dnf install python3 python3-tkinter
  # Arch
  sudo pacman -S python tk
  ```

### 2. Python 依赖

```bash
# Windows：需要 pywinpty（伪终端密码注入）；psutil 为可选加速
pip install pywinpty psutil customtkinter

# Linux：需要 customtkinter（现代 UI 框架）
pip install customtkinter
# psutil 为可选加速，可安装：pip install psutil

# 实验性"图片背景+模糊"功能需要 Pillow（可选）
pip install pillow
```

- **customtkinter**（双平台）— 现代 UI 框架，提供圆角控件和深色主题支持
- **pywinpty**（仅 Windows）— 通过 ConPTY 向命令行程序注入密码（解决 `_getch()` 不读标准输入的问题）
- **psutil**（可选，双平台）— 用于更可靠地监控子进程退出
- **Pillow**（可选，双平台）— 用于"图片背景+模糊"实验性主题（未安装时该功能自动禁用）

### 3. FileEncryptor 引擎

从 [原项目 Releases](https://github.com/Texas-albe/FileEncryptor/releases) 获取加密引擎，放置在以下任一位置（按优先级）：

| 平台 | 引擎文件名 | 说明 |
|---|---|---|
| Windows | `FileEncryptor.exe` | **v1.4.1 及以上版本** |
| Linux | `FileEncryptor` | **v1.4.1 及以上版本**（提供自包含 DEB/RPM 包，安装后通常位于 `/usr/bin/FileEncryptor`，GUI 也能从 PATH 找到） |

查找位置（按优先级）：

| 位置 | 说明 |
|---|---|
| `FileEncryptor-GUI/` 目录下 | 与 gui.py 同目录 |
| 项目根目录 | GUI 的父目录 |
| 祖父目录 | 父目录的父目录 |
| 系统 PATH | 任意 PATH 路径 |

> Linux 下手动放置的引擎需要可执行权限：`chmod +x FileEncryptor`

## 启动方式

### Windows

双击 `FileEncryptor-GUI\启动GUI.bat`（推荐），或：

```bash
cd FileEncryptor-GUI
python gui.py
```

### Linux

```bash
cd FileEncryptor-GUI
./启动GUI.sh          # 首次使用先赋权：chmod +x 启动GUI.sh
# 或直接
python3 gui.py
```

## 跨平台实现说明

GUI 与命令行引擎之间的密码注入通过伪终端（PTY）实现，按平台自动选择后端：

- **Windows**：[pywinpty](https://pypi.org/project/pywinpty/)（ConPTY）
- **Linux**：Python 内置 `pty` 模块，零外部依赖

密码不经过命令行参数传递（Linux 上 `/proc/<pid>/cmdline` 对所有用户可读），而是通过环境变量传给桥接进程，且不会继续传给引擎进程。

## 功能说明

### 1. 加密单个文件

选择源文件 → 输入密码（两次确认）→ 选择算法 → 开始加密。输出为 `.ptd` 格式。

### 2. 解密单个文件

选择 `.ptd` 文件 → 输入密码 → 开始解密。

### 3. 批量加密目录

选择源目录 → 输入密码 → 设置线程数 → 开始批量加密。递归加密目录下所有文件。若存在 `.progress` 续传文件，引擎会自动从中断点继续。

### 4. 批量解密目录

选择包含 `.ptd` 文件的目录 → 输入密码 → 设置线程数 → 开始批量解密。

### 日志与进度

- 运行日志实时显示在界面底部
- 进度条显示当前任务进度
- 支持中途取消操作
- 支持导出日志到文件（点击日志区右侧"导出"按钮）

### 快捷键

| 快捷键 | 功能 |
|---|---|
| `Ctrl+E` | 切换到加密文件页面 |
| `Ctrl+D` | 切换到解密文件页面 |
| `Ctrl+Shift+E` | 切换到批量加密页面 |
| `Ctrl+Shift+D` | 切换到批量解密页面 |
| `Ctrl+L` | 导出日志 |
| `Ctrl+W` | 清空日志 |
| `Esc` | 取消当前操作 |

### 实用功能

- **窗口状态记忆**：关闭窗口后自动保存位置和大小，下次启动时恢复
- **路径粘贴**：在文件选择框右键可选择"粘贴路径"，快速输入剪贴板中的文件路径
- **拖放支持**：支持将文件拖放到文件选择框（需安装 tkinterdnd2）
- **配置持久化**：用户偏好设置自动保存到 `config.ini`
- **中英文切换**：设置区可选择"中文 / English"，即时切换界面语言
- **主题切换**：设置区可在浅色/深色两种预设主题间切换

> 引擎版本要求：Windows 与 Linux 均需 **v1.4.1+**（v1.3.0+ 支持 XChaCha20-Poly1305 / AEGIS-256 算法选择；续传仅在批量模式下自动生效，无需额外参数）。

### 实验性功能：图片背景

在设置页"实验性"卡片中，可：
- **启用图片背景**：开启后选择一张本地图片作为壁纸（未选择时使用内置渐变底图）。
- **忽略主题色**：开启后界面不再受浅色/深色主题影响（主题下拉禁用）。
- **毛玻璃面板**：侧栏与内容面板本身即为半透明"毛玻璃"——直接显示其下方壁纸对应区域的模糊版本（真实高斯模糊），壁纸只在窗口边缘露出。
- **取色伪透明**：卡片、输入框、日志框等不支持透明的控件会取其所在位置的壁纸色调作为底色（卡片为磨砂白、日志框为深色玻璃），整体融入背景。
- **壁纸模糊 / 面板模糊**：两个独立滑杆（0–50），均可通过旁边的数值框直接输入数值；面板模糊为 0 时面板完全透明（清晰显示壁纸），文字始终清晰、不受模糊影响。

> **关于"透明"的说明（重要）**
> CustomTkinter 控件不支持真正的背景透明，因此：
> - **结构性面板**（侧栏、内容区、各页面卡片）使用 `tk.Canvas` 直接把其所在位置的壁纸**模糊裁剪**画进去，实现真实毛玻璃；
> - **卡片/输入框/日志框等不支持透明的控件**采用**取色伪透明**：取其所在位置的壁纸色调作为底色（卡片为磨砂白、日志框为深色玻璃），视觉上与背景连续——这是一种近似，不是像素级透明。
>
> **性能策略**：清晰壁纸只生成一次并缓存复用；待染色的控件按下标登记一次（`id -> 控件`），之后仅对缓存取样、不做全量 `cget`；滑块拖动只重画面板/壁纸层，不再触发整窗重渲染，也不会反复重载（无限重试已移除，仅在布局未稳定时用 idle 补一帧）。

## 注意事项

- **密码强度仅供参考**：界面上显示的密码强度评分仅用于提示，实际安全性取决于密码长度和复杂度
- **加密后删除源文件**：勾选后加密完成会自动删除原始文件，建议先确认加密成功再使用此功能
- **输出目录留空**：默认输出到源文件所在目录
- **算法选择**：默认使用 XChaCha20-Poly1305；AEGIS-256 适用于支持该指令集的 CPU，如不支持将自动回退
- **断点续传**：批量加密/解密时，若检测到 `.progress` 续传文件，引擎会自动从中断点继续（单文件模式不支持续传）。无需任何手动设置
- **Linux 字体**：界面默认使用 DejaVu Sans（主流发行版自带）；若系统缺失会自动回退到默认字体

## 常见问题

**Q: 启动时提示 "No Python with winpty found"（仅 Windows）**

A: 确保已安装 pywinpty 和 tkinter：
```bash
pip install pywinpty psutil
python -c "import tkinter; import winpty; print('OK')"
```

**Q: 提示 "FileEncryptor engine not found"**

A: Windows 将 `FileEncryptor.exe`、Linux 将 `FileEncryptor`（注意无扩展名且需可执行权限）放在 `FileEncryptor-GUI/` 目录下、项目根目录或系统 PATH 中。

**Q: Linux 下 GUI 无法启动，报 tkinter 相关错误**

A: 安装发行版对应的 tkinter 包（见"环境要求"），Linux 上 tkinter 通常不随 python3 默认安装。

**Q: 加密/解密没有反应**

A: 检查日志区的输出信息。常见原因：密码输入错误、输出目录已存在同名文件、引擎版本不兼容（请确认使用 v1.4.1+）。

## 致谢

本项目围绕 [FileEncryptor](https://github.com/Texas-albe/FileEncryptor) 命令行引擎构建图形界面，并使用了以下开源项目。在此向所有作者与维护者致谢：

| 项目 | 用途 | 链接 |
|---|---|---|
| FileEncryptor | 底层加密引擎（XChaCha20-Poly1305 / AEGIS-256） | [GitHub](https://github.com/Texas-albe/FileEncryptor) |
| CustomTkinter | 现代化 GUI 控件框架 | [GitHub](https://github.com/TomSchimansky/CustomTkinter) |
| pywinpty | Windows 伪终端（ConPTY）密码注入 | [GitHub](https://github.com/spyder-ide/pywinpty) |
| Pillow | 图片背景与模糊（实验性主题） | [GitHub](https://github.com/python-pillow/Pillow) |
| psutil | 子进程监控（可选） | [GitHub](https://github.com/giampaolo/psutil) |
| tkinterdnd2 | 文件拖放支持（可选） | [GitHub](https://github.com/Eliav2/tkinterdnd2) |
| libsodium | 引擎底层加密原语库 | [GitHub](https://github.com/jedisct1/libsodium) |
