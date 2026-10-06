# FileEncryptor GUI

> **English** · [中文](README.md) | [English](README_en.md)

FileEncryptor 命令行工具的图形界面封装，**支持 Windows 与 Linux**。提供文件加密、解密和批量处理功能，支持 XChaCha20-Poly1305、AEGIS-256、AES-256-GCM、SM4-GCM 四种对称算法，以及 X25519 / X448 非对称加密（默认后量子混合）；另含目录打包、分卷、水印、密钥封装等能力。

## 目录结构

```
FileEncryptor-GUI/
├── app/
│   ├── core/            # 纯逻辑层
│   │   ├── about_info.py #   「关于」页信息采集（引擎探测 + 运行环境）
│   │   ├── args.py      #   参数构建 + 输入校验
│   │   ├── config.py    #   配置读写
│   │   ├── engine.py    #   引擎服务层（查找 + 流式执行 + 取消）
│   │   ├── i18n.py      #   多语言
│   │   ├── strength.py  #   密码强度
│   │   ├── version.py   #   版本与仓库地址的单一来源
│   │   └── _runner.py   #   伪终端桥接脚本（自动调用，无需手动运行）
│   └── ui/              # 界面层
│       ├── gui.py       #   GUI 主程序
│       ├── pages.py     #   页面组件
│       ├── theme.py     #   主题管理
│       └── widgets.py   #   控件库
├── 启动GUI.bat          # Windows 启动脚本
├── 启动GUI.sh           # Linux 启动脚本
├── .gitignore / .gitattributes
└── README.md / README_en.md
```

> `tests/`（pytest 单元测试 + 无头冒烟）仅存于本地开发环境，**不随仓库分发**；`FileEncryptor.exe` / `FileEncryptor` 加密引擎需按下方说明自行获取放置，**不随仓库分发**。

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
| Windows | `FileEncryptor.exe` | **官方 CLI 3.0.0**（原项目拆分的独立 CLI 组件） |
| Linux | `FileEncryptor` | **官方 CLI 3.0.0**（提供自包含 DEB/RPM 包，安装后通常位于 `/usr/bin/FileEncryptor`，GUI 也能从 PATH 找到） |

查找位置（按优先级）：

| 位置 | 说明 |
|---|---|
| `FileEncryptor-GUI/` 目录下 | 与启动脚本同目录 |
| 项目根目录 | GUI 的父目录 |
| 祖父目录 | 父目录的父目录 |
| 系统 PATH | 任意 PATH 路径 |

> Linux 下手动放置的引擎需要可执行权限：`chmod +x FileEncryptor`

## 启动方式

### Windows

双击 `FileEncryptor-GUI\启动GUI.bat`（推荐），或：

```bash
cd FileEncryptor-GUI
python -m app.ui.gui
```

### Linux

```bash
cd FileEncryptor-GUI
./启动GUI.sh          # 首次使用先赋权：chmod +x 启动GUI.sh
# 或直接
python3 -m app.ui.gui
```

## 跨平台实现说明

GUI 与命令行引擎之间的密码注入通过伪终端（PTY）实现，按平台自动选择后端：

- **Windows**：[pywinpty](https://pypi.org/project/pywinpty/)（ConPTY）
- **Linux**：Python 内置 `pty` 模块，零外部依赖

密码不经过命令行参数传递（Linux 上 `/proc/<pid>/cmdline` 对所有用户可读），而是经当前用户独占的临时密码文件传给桥接进程，且不会继续传给引擎进程。

## 功能说明

### 1. 加密单个文件

选择源文件 → 输入密码（两次确认）→ 选择算法 → 开始加密。输出为 `.ptd` 格式。

可选选项：

- **加密后删除源文件**：加密成功后直接删除原文件
- **移到回收站**：加密成功后把原文件移入系统回收站（比直接删除更安全，优先于"删除源文件"）
- **启用 zstd 压缩**：加密前先用 zstd 压缩（可指定压缩级别 1–22），显著减小文本类文件的产物体积
- **生成 SHA-256 校验单**：加密成功后额外输出 `<产物>.ptd.sha256` 校验文件（非对称模式下引擎不生成 sidecar，界面会隐藏该项）
- **嵌入水印**：在密文尾部写入可追溯水印；勾选后可指定「水印签名私钥（PEM）」实现**签名水印**，或点「生成签名密钥」现场生成一对密钥（私钥存为所选文件，公钥显示在运行日志中）
- **分卷加密**：按指定大小（如 512MB / 4GB）把产物切分为 `<名>.001.ptd`、`<名>.002.ptd`……解密时选中任意一卷即可自动合并还原
- **打包为单个文件**：源选择改为**目录**，把整棵目录树打包成单个 `.ptd`（对应 CLI 的 `-p`）；解密时自动展开目录结构。**打包与非对称加密互斥**（引擎不支持组合）
- **X25519 非对称加密（PQC 混合）**：勾选后改为用**收件人公钥**加密（填 `age1…` / `MLKEM1-…` / `X448-…` 字符串或公钥文件），不需要密码，产物同样为 `.ptd` 容器；点「生成密钥对」可现场生成密钥（默认 **X25519 + ML-KEM-768 混合**，私钥存为所选目录下的 `rage_private.txt`，公钥显示在运行日志中）。可勾选「改用 X448 曲线」或「关闭后量子（经典 X25519）」调整生成的密钥类型。该模式下 `--sha256` 不适用，但 zstd 与分卷仍可用

> 也可用**密钥文件**代替密码：在"密钥文件"栏选择一个文件，其内容即作为密码（对应 CLI 的 `-k`，非交互读取），此时忽略密码输入框。

### 2. 解密单个文件

选择 `.ptd` 文件 → 输入密码 → 开始解密。解密非对称产物时勾选「用私钥解密」，并在"密钥文件"栏选择**私钥文件**（无需指定算法，引擎会按密钥材料自动识别）。

可选选项：

- **仅预览明文（不落盘）**：把解密出的明文前若干字节输出到运行日志，便于快速确认密码/内容是否正确，不写任何文件
- **保留为单个文件（不展开归档）**：针对打包产物，解密后保留为单个文件而不展开目录树
- **强制解密损坏文件**：当容器部分损坏时尽力恢复可读内容（正常文件无需勾选）
- **查看水印（不解密）**：读取密文尾部的水印信息，无需密码；可另选「水印公钥（PEM）」进行验签

### 3. 批量加密目录

选择源目录 → 输入密码 → 选择算法 → 开始批量加密。递归加密目录下所有文件（默认开启输出名混淆，产物形如 `<16位十六进制>.<3字母>.ptd`）。若存在续传文件（`.prs`），引擎会自动从中断点继续。并发线程数由引擎的 `fileencryptor.yaml`（`worker_threads`，0=自动）配置，GUI 不再提供线程数选项。同样支持"删除源文件 / 移到回收站"、zstd 压缩、SHA-256 校验单与密钥文件。（**批量模式不支持非对称加密**，引擎侧 `-be` 不接受收件人公钥。）

### 4. 批量解密目录

选择包含 `.ptd` 文件的目录 → 输入密码 → 开始批量解密，自动还原原始文件名（含中文）。

### 5. 密钥轮换

为已有的 `.ptd` 容器更换密码：选择目标容器 → 填写当前密码（或选当前密钥文件）→ 填写新密码并确认 → 开始轮换（对应 CLI 的 `--rewrap`）。轮换只重写头部密钥、**payload 密文不变**，原地更新文件；之后需用新密码解密。

### 6. 密钥封装

密钥封装（Key Wrapping）针对 **32 字节数据密钥（DEK）**，而非文件内容：

- **封装**：选择一个 32 字节密钥文件 → 选择封装算法（`kwp` RFC 5649 默认 / `aes-kw` RFC 3394 / `pubkey`）→ 用密码或密钥文件（`pubkey` 路线改用收件人公钥）→ 输出 `.fekw` 封装块
- **解封**：选择 `.fekw` → 用密码 / 密钥文件（或 `pubkey` 路线用身份私钥）→ 还原出 32 字节 DEK

> 密钥封装与文件加解密相互独立，常用于把数据密钥安全地分发给他人。

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
| `Ctrl+R` | 切换到密钥轮换页面 |
| `Ctrl+K` | 切换到密钥封装页面 |
| `Ctrl+I` | 切换到关于页面 |
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
- **关于页**：显示 GUI 版本、**运行时探测**的引擎版本与能力（zstd / AEGIS / AES-GCM / SM4 / PQC / 分卷 / 打包 / 密钥封装 / 加密盘）、引擎路径、运行环境、开源依赖、友情链接与成员主页（B 站 / GitHub），并支持「复制全部信息」便于反馈问题时粘贴

> 引擎版本要求：Windows 与 Linux 均需 **官方 CLI 3.0.0 及以上**（已验证 3.0.0；格式 v6；线程数等运维参数由引擎 `fileencryptor.yaml` 配置；批量解密经 `-rn` 自动还原原始文件名）。

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
- **算法选择**：默认使用 XChaCha20-Poly1305；AEGIS-256 适用于支持该指令集的 CPU，如不支持将自动回退；AES-256-GCM / SM4-GCM 分别对应 AES-NI 与国密 SM4 场景
- **单文件加密输出名为混淆名**：引擎默认开启输出名混淆（`<16位十六进制>.<3字母>.ptd`），加密成功后 GUI 会在日志中提示输出位置；解密时引擎自动还原原始文件名
- **打包与非对称互斥**：`-p`（打包目录）不能与收件人公钥（非对称）同时使用，引擎对二者组合会直接报错；界面在勾选非对称时会自动取消打包
- **断点续传**：批量加密/解密时，若检测到续传文件（`.prs`），引擎会自动从中断点继续（单文件模式不支持续传）。无需任何手动设置
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

A: 检查日志区的输出信息。常见原因：密码输入错误、输出目录已存在同名文件、引擎版本不兼容（请确认使用官方 CLI 3.0.0）。

## 致谢

本项目围绕 [FileEncryptor](https://github.com/Texas-albe/FileEncryptor) 命令行引擎构建图形界面，并使用了以下开源项目。在此向所有作者与维护者致谢：

| 项目 | 用途 | 链接 |
|---|---|---|
| FileEncryptor | 底层加密引擎（XChaCha20-Poly1305 / AEGIS-256 / AES-GCM / SM4） | [GitHub](https://github.com/Texas-albe/FileEncryptor) |
| CustomTkinter | 现代化 GUI 控件框架 | [GitHub](https://github.com/TomSchimansky/CustomTkinter) |
| pywinpty | Windows 伪终端（ConPTY）密码注入 | [GitHub](https://github.com/spyder-ide/pywinpty) |
| Pillow | 图片背景与模糊（实验性主题） | [GitHub](https://github.com/python-pillow/Pillow) |
| psutil | 子进程监控（可选） | [GitHub](https://github.com/giampaolo/psutil) |
| tkinterdnd2 | 文件拖放支持（可选） | [GitHub](https://github.com/Eliav2/tkinterdnd2) |
| libsodium | 引擎底层加密原语库 | [GitHub](https://github.com/jedisct1/libsodium) |
