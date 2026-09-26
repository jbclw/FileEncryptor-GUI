#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_args.py —— 参数构建与输入校验纯逻辑单元测试

校验第 2 步抽出的 args.py：
  - validate_*_inputs：各边界条件（空输入、密码不匹配、源文件/目录不存在、扩展名检查）
  - build_*_args：输入 -> argv 的输出形状（是否/如何附加 -o、-m、-de、-y；2.x 已删除 -j，并发由 yaml 配置）
  - ensure_output_dir：目录预创建的三种路径（未指定/已存在/需创建）

全部为纯逻辑测试，不依赖 GUI 与引擎。
"""
import os
import sys
from pathlib import Path

import pytest

GUI_DIR = Path(__file__).resolve().parent.parent
if str(GUI_DIR) not in sys.path:
    sys.path.insert(0, str(GUI_DIR))

from app.core import args as args_mod


# ── validate_encrypt_inputs ──────────────────────────────────────────────

class TestValidateEncrypt:
    def test_ok(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("x")
        assert args_mod.validate_encrypt_inputs(str(f), "pw", "pw") == []

    def test_missing_src(self):
        assert args_mod.validate_encrypt_inputs("", "pw", "pw") == [
            ("warning", "msg_select_enc_file")]

    def test_missing_pw(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("x")
        assert args_mod.validate_encrypt_inputs(str(f), "", None) == [
            ("warning", "msg_enter_enc_pw")]

    def test_pw_mismatch(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("x")
        assert args_mod.validate_encrypt_inputs(str(f), "a", "b") == [
            ("warning", "msg_pw_mismatch")]

    def test_src_not_exist(self):
        assert args_mod.validate_encrypt_inputs("nope.txt", "pw", "pw") == [
            ("error", "msg_src_not_exist")]

    def test_pw2_none_skips_mismatch(self, tmp_path):
        # 未提供 pw2 时不应报"不匹配"
        f = tmp_path / "a.txt"
        f.write_text("x")
        assert args_mod.validate_encrypt_inputs(str(f), "pw", None) == []


# ── validate_decrypt_inputs ──────────────────────────────────────────────

class TestValidateDecrypt:
    def test_ok(self, tmp_path):
        f = tmp_path / "a.ptd"
        f.write_text("x")
        assert args_mod.validate_decrypt_inputs(str(f), "pw") == []

    def test_missing_src(self):
        assert args_mod.validate_decrypt_inputs("", "pw") == [
            ("warning", "msg_select_ptd")]

    def test_missing_pw(self, tmp_path):
        f = tmp_path / "a.ptd"
        f.write_text("x")
        assert args_mod.validate_decrypt_inputs(str(f), "") == [
            ("warning", "msg_enter_dec_pw")]

    def test_not_exist(self):
        assert args_mod.validate_decrypt_inputs("nope.ptd", "pw") == [
            ("error", "msg_file_not_exist")]

    def test_wrong_extension(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("x")
        errs = args_mod.validate_decrypt_inputs(str(f), "pw")
        assert ("warning", "msg_not_ptd") in errs

    def test_ptd_passthrough(self, tmp_path):
        f = tmp_path / "a.PTD"
        f.write_text("x")
        assert args_mod.validate_decrypt_inputs(str(f), "pw") == []


# ── validate_batch_*_inputs ──────────────────────────────────────────────

class TestValidateBatch:
    def test_encrypt_ok(self, tmp_path):
        assert args_mod.validate_batch_encrypt_inputs(str(tmp_path), "pw", "pw") == []

    def test_encrypt_missing_src(self):
        assert args_mod.validate_batch_encrypt_inputs("", "pw", "pw") == [
            ("warning", "msg_select_src_dir")]

    def test_encrypt_pw_mismatch(self, tmp_path):
        assert args_mod.validate_batch_encrypt_inputs(str(tmp_path), "a", "b") == [
            ("warning", "msg_pw_mismatch")]

    def test_encrypt_src_not_dir(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("x")
        assert args_mod.validate_batch_encrypt_inputs(str(f), "pw", "pw") == [
            ("error", "msg_src_dir_not_exist")]

    def test_decrypt_ok(self, tmp_path):
        assert args_mod.validate_batch_decrypt_inputs(str(tmp_path), "pw") == []

    def test_decrypt_missing_pw(self, tmp_path):
        assert args_mod.validate_batch_decrypt_inputs(str(tmp_path), "") == [
            ("warning", "msg_enter_dec_pw")]


# ── ensure_output_dir ────────────────────────────────────────────────────

class TestEnsureOutputDir:
    def test_empty_ok(self):
        assert args_mod.ensure_output_dir("") is None

    def test_existing_ok(self, tmp_path):
        assert args_mod.ensure_output_dir(str(tmp_path)) is None

    def test_creates(self, tmp_path):
        target = tmp_path / "new" / "nested"
        assert args_mod.ensure_output_dir(str(target)) is None
        assert target.is_dir()

    def test_create_fails(self, tmp_path, monkeypatch):
        def boom(*a, **k):
            raise OSError("denied")
        monkeypatch.setattr(args_mod.os, "makedirs", boom)
        assert args_mod.ensure_output_dir(str(tmp_path / "x")) == (
            "error", "msg_cannot_create_dir")


# ── build_*_args ─────────────────────────────────────────────────────────

class TestBuildEncrypt:
    def test_basic(self):
        assert args_mod.build_encrypt_args("f") == ["-e", "f", "-y"]

    def test_full(self):
        assert args_mod.build_encrypt_args(
            "f", out="o", algo="XChaCha20-Poly1305", delete=True) == [
            "-e", "f", "-o", "o", "-m", "xchacha20", "-de", "-y"]

    def test_non_xchacha_no_mode(self):
        # 非 XChaCha20 算法不应附加 -m
        assert args_mod.build_encrypt_args("f", algo="AES-256") == ["-e", "f", "-y"]

    def test_recycle_overrides_delete(self):
        # recycle=True 时优先传 --recycle-source，忽略 delete
        assert args_mod.build_encrypt_args("f", delete=True, recycle=True) == [
            "-e", "f", "--recycle-source", "-y"]

    def test_recycle_only(self):
        assert args_mod.build_encrypt_args("f", recycle=True) == [
            "-e", "f", "--recycle-source", "-y"]


class TestBuildDecrypt:
    def test_basic(self):
        assert args_mod.build_decrypt_args("f") == ["-d", "f", "-y"]

    def test_with_out(self):
        assert args_mod.build_decrypt_args("f", out="o") == [
            "-d", "f", "-o", "o", "-y"]


class TestBuildBatch:
    def test_encrypt_basic(self):
        assert args_mod.build_batch_encrypt_args("s") == ["-be", "-i", "s", "-y"]

    def test_encrypt_full(self):
        assert args_mod.build_batch_encrypt_args(
            "s", out="o", algo="AEGIS-256", delete=True) == [
            "-be", "-i", "s", "-o", "o", "-m", "aegis256", "-de", "-y"]

    def test_encrypt_non_aegis_no_mode(self):
        assert args_mod.build_batch_encrypt_args(
            "s", algo="XChaCha20") == ["-be", "-i", "s", "-y"]

    def test_decrypt_basic(self):
        assert args_mod.build_batch_decrypt_args("s") == ["-bd", "-i", "s", "-rn", "-y"]

    def test_decrypt_full(self):
        assert args_mod.build_batch_decrypt_args("s", out="o") == [
            "-bd", "-i", "s", "-o", "o", "-rn", "-y"]