# FileEncryptor GUI

FileEncryptor 命令行工具的图形界面封装。提供文件加密、解密和批量处理功能，支持 XChaCha20-Poly1305 和 AEGIS-256 两种加密算法。

## 目录结构

```
FileEncryptor-GUI/
├── gui.py              # GUI 主程序
├── _runner.py          # winpty 桥接脚本（自动调用，无需手动运行）
├── 启动GUI.bat         # Windows 启动脚本
├── FileEncryptor.exe   # 加密引擎（需自行获取）
└── README.md
```

## 环境要求

### 1. Python 3.10+

从 [python.org](https://www.python.org/downloads/) 下载安装。

> 安装时务必勾选 **"Add Python to PATH"**，并在"Optional Features"中确保 **"tcl/tk and IDLE"** 已选中（这是 tkinter 的依赖）。

### 2. Python 依赖

```bash
pip install pywinpty psutil
```

- **pywinpty** — 用于向命令行程序注入密码（解决 `_getch()` 不读标准输入的问题）
- **psutil** — 用于监控子进程状态

### 3. FileEncryptor.exe

GUI 需要 `FileEncryptor.exe` 才能运行，将 exe 放置在以下任一位置（按优先级）：

| 位置 | 说明 |
|---|---|
| `FileEncryptor-GUI/` 目录下 | 与 gui.py 同目录 |
| 项目根目录 | GUI 的父目录 |
| 祖父目录 | 父目录的父目录 |
| 系统 PATH | 任意 PATH 路径 |

## 启动方式

### 方式一：双击启动脚本（推荐）

双击 `FileEncryptor-GUI\启动GUI.bat`，脚本会自动查找可用的 Python 解释器并启动 GUI。

### 方式二：命令行

```bash
cd FileEncryptor-GUI
python gui.py
```

## 功能说明

### 1. 加密单个文件

选择源文件 → 输入密码（两次确认）→ 选择算法 → 开始加密。输出为 `.ptd` 格式。

可选勾选"断点续传"以支持中断后继续加密（见下方注意事项）。

### 2. 解密单个文件

选择 `.ptd` 文件 → 输入密码 → 开始解密。

### 3. 批量加密目录

选择源目录 → 输入密码 → 设置线程数 → 开始批量加密。递归加密目录下所有文件。

可选勾选"断点续传"以支持中断后继续加密（见下方注意事项）。

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

> 需要 `FileEncryptor.exe` **v1.3.0** 及以上版本，以支持 XChaCha20-Poly1305 / AEGIS-256 算法。

## 注意事项

- **密码强度仅供参考**：界面上显示的密码强度评分仅用于提示，实际安全性取决于密码长度和复杂度
- **加密后删除源文件**：勾选后加密完成会自动删除原始文件，建议先确认加密成功再使用此功能
- **输出目录留空**：默认输出到源文件所在目录
- **算法选择**：默认使用 XChaCha20-Poly1305；AEGIS-256 适用于支持该指令集的 CPU，如不支持将自动回退
- **断点续传（实验性功能）**：勾选后可在中断后继续加密，但此功能目前存在已知问题（参见 [Issue #4](https://github.com/Texas-albe/FileEncryptor/issues/4)），可能导致数据损坏。**默认不勾选**，仅在明确了解风险且需要处理大文件时使用。建议重要文件先关闭此功能

## 常见问题

**Q: 启动时提示 "No Python with winpty found"**

A: 确保已安装 pywinpty 和 tkinter：
```bash
pip install pywinpty psutil
python -c "import tkinter; import winpty; print('OK')"
```

**Q: 提示 "FileEncryptor.exe not found"**

A: 将 `FileEncryptor.exe` 放在 `FileEncryptor-GUI/` 目录下，或放在项目根目录。

**Q: 加密/解密没有反应**

A: 检查日志区的输出信息。常见原因：密码输入错误、输出目录已存在同名文件、exe 版本不兼容。