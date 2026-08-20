#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
args.py —— 参数构建与输入校验（纯逻辑，第 2 步抽取）

把 CLI 参数构建（输入 -> argv）与输入校验（输入 -> 错误消息）从 GUI 层抽出，
使它们可脱离 GUI/引擎独立单元测试，并让 GUI 层保持"薄"。

设计约定：
  - validate_*_inputs(...) -> list[(severity, key)]：
      返回错误消息列表，每项为 (severity, key)。severity ∈ {"warning","error"}，
      key 为 i18n 字符串键（如 "msg_select_enc_file"）。空列表表示合法。
      GUI 层只负责取首条并用 messagebox 展示，不做业务判断。
  - build_*_args(...) -> list[str]：纯"输入 -> argv"，不含验证、不含文件系统副作用。
  - ensure_output_dir(out)：目录预创建（含其自身更严重的错误路径），返回
      (severity, key) 或 None。GUI 层选择是否调用，以复现原"先建目录再传参"的顺序。
"""
import os


# ── 输入校验 ─────────────────────────────────────────────────────────────

def validate_encrypt_inputs(src, pw, pw2=None):
    """校验单文件加密输入，返回错误列表（空列表=合法）。"""
    errs = []
    if not src:
        errs.append(("warning", "msg_select_enc_file"))
    if not pw:
        errs.append(("warning", "msg_enter_enc_pw"))
    elif pw2 is not None and pw != pw2:
        errs.append(("warning", "msg_pw_mismatch"))
    if src and not os.path.isfile(src):
        errs.append(("error", "msg_src_not_exist"))
    return errs


def validate_decrypt_inputs(src, pw):
    """校验单文件解密输入，返回错误列表（空列表=合法）。"""
    errs = []
    if not src:
        errs.append(("warning", "msg_select_ptd"))
    if not pw:
        errs.append(("warning", "msg_enter_dec_pw"))
    if src and not os.path.isfile(src):
        errs.append(("error", "msg_file_not_exist"))
    if src and os.path.isfile(src) and not src.lower().endswith(".ptd"):
        errs.append(("warning", "msg_not_ptd"))
    return errs


def validate_batch_encrypt_inputs(src, pw, pw2=None):
    """校验批量加密输入，返回错误列表（空列表=合法）。"""
    errs = []
    if not src:
        errs.append(("warning", "msg_select_src_dir"))
    if not pw:
        errs.append(("warning", "msg_enter_enc_pw"))
    elif pw2 is not None and pw != pw2:
        errs.append(("warning", "msg_pw_mismatch"))
    if src and not os.path.isdir(src):
        errs.append(("error", "msg_src_dir_not_exist"))
    return errs


def validate_batch_decrypt_inputs(src, pw):
    """校验批量解密输入，返回错误列表（空列表=合法）。"""
    errs = []
    if not src:
        errs.append(("warning", "msg_select_src_dir"))
    if not pw:
        errs.append(("warning", "msg_enter_dec_pw"))
    if src and not os.path.isdir(src):
        errs.append(("error", "msg_src_dir_not_exist"))
    return errs


def ensure_output_dir(out):
    """若指定了输出目录且尚不存在，则创建。
    成功或未指定输出目录返回 None；创建失败返回 (severity, key)。
    """
    if not out:
        return None
    if os.path.isdir(out):
        return None
    try:
        os.makedirs(out, exist_ok=True)
    except Exception:
        return ("error", "msg_cannot_create_dir")
    return None


# ── 参数构建 ─────────────────────────────────────────────────────────────

def build_encrypt_args(src, out="", algo="", delete=False):
    """由单文件加密表单输入构建 CLI argv。"""
    args = ["-e", src]
    if out:
        args += ["-o", out]
    if algo.startswith("XChaCha20"):
        args += ["-m", "xchacha20"]
    if delete:
        args.append("-de")
    args.append("-y")
    return args


def build_decrypt_args(src, out=""):
    """由单文件解密表单输入构建 CLI argv。"""
    args = ["-d", src]
    if out:
        args += ["-o", out]
    args.append("-y")
    return args


def build_batch_encrypt_args(src, out="", algo="", threads="", delete=False):
    """由批量加密表单输入构建 CLI argv。"""
    args = ["-be", "-i", src]
    if out:
        args += ["-o", out]
    if algo.startswith("AEGIS"):
        args += ["-m", "aegis256"]
    if threads:
        args += ["-j", threads]
    if delete:
        args.append("-de")
    args.append("-y")
    return args


def build_batch_decrypt_args(src, out="", threads=""):
    """由批量解密表单输入构建 CLI argv。"""
    args = ["-bd", "-i", src]
    if out:
        args += ["-o", out]
    if threads:
        args += ["-j", threads]
    args.append("-y")
    return args