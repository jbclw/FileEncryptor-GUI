#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""version.py —— 版本与仓库地址的单一来源

此前 GUI 版本号在侧栏两处写死且不一致（v1.4.1 / v2.0.0，两者在仓库中都没有对应 tag），
统一收敛到本模块，并与 git tag 对齐。
「关于」页与侧栏均从此处取值。

注意：这里只有 **GUI 自身**的版本；加密引擎的版本是运行时探测的
（见 about_info.probe_engine），因为它取决于用户手上放置的 CLI 文件。
"""

# GUI 版本（semver；须与 git tag 保持一致：v2.1.0 → v2.2.0）
GUI_VERSION = "2.2.0"

# 本 GUI 仓库
REPO_URL = "https://github.com/jbclw/FileEncryptor-GUI"

# 容器格式版本（CLI 2.x）
CONTAINER_FORMAT = "v6"

# 许可证名称。留空则「关于」页不显示许可证行（待确定后填写，如 "MIT"）。
LICENSE_NAME = ""
