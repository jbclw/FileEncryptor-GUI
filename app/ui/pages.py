#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pages.py —— 页面组件（第 3 步抽取）

把 gui.FileEncryptorGUI 里各 _build_*_page 的内容抽为独立页面组件类。
页面与 app 状态强耦合（回调、控件引用、图片背景模式、取色），故每个页面类：
  - 构造时接收 app（FileEncryptorGUI 实例）作为上下文；
  - build() 把页面建进 app.page_frame，控件引用写回 app.<名字>，行为与内联版完全一致；
  - 语言/主题切换依赖 GUI 全量重建（_apply_settings），页面不缓存渲染后的字符串。

控件一律从冻结 Theme（app._theme）取色，不持有可变主题状态。
"""
import tkinter as tk
import webbrowser

import customtkinter as ctk

from .theme import FONT, FONT_SM, FONT_HEAD, FONT_FAMILY
from ..core.i18n import tr
from ..core.about_info import CREDITS, collect_environment, FRIEND_LINK, TEAM
from ..core.version import REPO_URL, CONTAINER_FORMAT, LICENSE_NAME
from .widgets import PasswordEntry, FileSelector, PrimaryButton


# 图片背景模式由 app 决策；页面构建仅读取 app._image_mode
# （PIL 存在性检查在 gui 层，页面无需关心，面板工厂 _new_panel 由 app 提供）


class _BasePage:
    """页面基类：保存 app 上下文，并提供页容器与取色访问的快捷方式。"""

    def __init__(self, app):
        self.app = app

    # 页面所在容器（与 gui 里 _new_panel(self.page_frame) 一致）
    def _panel(self, parent):
        return self.app._new_panel(parent)

    @property
    def T(self):
        return self.app._theme


class EncryptPage(_BasePage):
    """单文件加密页"""

    def build(self, parent):
        page = self._panel(parent)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=0)
        page.rowconfigure(1, weight=1)
        T = self.T

        card = ctk.CTkFrame(page, fg_color=T.BG_CARD, corner_radius=8, border_width=1, border_color=T.BORDER)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="\U0001F512  " + tr("encrypt_single"),
            font=FONT_HEAD, text_color=T.TEXT_DARK, anchor="w", padx=16
        ).grid(row=0, column=0, sticky="ew", pady=(14, 4))

        ctk.CTkLabel(
            card, text=tr("encrypt_single_desc"),
            font=FONT_SM, text_color=T.TEXT_MUTED, anchor="w", padx=16
        ).grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkFrame(card, height=1, fg_color=T.BORDER, corner_radius=0
                     ).grid(row=2, column=0, sticky="ew", padx=16)

        form = ctk.CTkFrame(card, fg_color=T.BG_CARD, corner_radius=0)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        row = 0
        self.app.enc_file = FileSelector(form, tr("source_file"))
        self.app.enc_file.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        row += 1

        self.app.enc_pw = PasswordEntry(form, tr("enc_password"))
        self.app.enc_pw.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        row += 1

        self.app.enc_pw2 = PasswordEntry(form, tr("confirm_password"))
        self.app.enc_pw2.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        row += 1

        self.app.enc_keyfile = FileSelector(form, tr("key_file"))
        self.app.enc_keyfile.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        row += 1

        opt_row = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        opt_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        opt_row.columnconfigure(1, weight=1)

        ctk.CTkLabel(opt_row, text=tr("algorithm"), font=FONT_SM, text_color=T.TEXT_DARK
                     ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.app.enc_algo = ctk.CTkComboBox(
            opt_row, values=["XChaCha20-Poly1305", "AEGIS-256"], state="readonly", font=FONT, width=180)
        self.app.enc_algo.grid(row=0, column=1, sticky="w")
        self.app.enc_algo.set("XChaCha20-Poly1305")

        self.app.enc_del = ctk.CTkFrame(opt_row, fg_color=T.BG_CARD, corner_radius=0)
        self.app.enc_del.grid(row=0, column=2, sticky="e", padx=(16, 0))
        ctk.CTkLabel(self.app.enc_del, text=tr("delete_source"), font=FONT_SM, text_color=T.TEXT_DARK
                     ).pack(side="left", padx=(0, 4))
        self.app.enc_del_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(self.app.enc_del, text="", variable=self.app.enc_del_var,
                        fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER).pack(side="left")

        self.app.enc_recycle = ctk.CTkFrame(opt_row, fg_color=T.BG_CARD, corner_radius=0)
        self.app.enc_recycle.grid(row=0, column=3, sticky="e", padx=(8, 0))
        ctk.CTkLabel(self.app.enc_recycle, text=tr("recycle_source"), font=FONT_SM, text_color=T.TEXT_DARK
                     ).pack(side="left", padx=(0, 4))
        self.app.enc_recycle_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(self.app.enc_recycle, text="", variable=self.app.enc_recycle_var,
                        fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER).pack(side="left")
        row += 1

        # zstd 压缩选项行
        compress_row = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        compress_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.enc_compress_row = compress_row

        self.app.enc_zstd_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(compress_row, text=tr("enable_zstd"), font=FONT_SM,
                        variable=self.app.enc_zstd_var, text_color=T.TEXT_DARK,
                        fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                        command=self.app._toggle_compression_level).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(compress_row, text=tr("compression_level"), font=FONT_SM, text_color=T.TEXT_DARK
                     ).pack(side="left", padx=(8, 4))
        self.app.enc_compression_level = ctk.CTkComboBox(
            compress_row, values=[str(i) for i in range(1, 23)],
            state="disabled", font=FONT, width=60)
        self.app.enc_compression_level.pack(side="left", padx=(0, 4))
        self.app.enc_compression_level.set("3")
        row += 1

        # SHA-256 校验单行（对称模式；rage 模式下引擎会忽略）
        sha256_row = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        sha256_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.enc_sha256_row = sha256_row
        self.app.enc_sha256_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(sha256_row, text=tr("sha256_sidecar"), font=FONT_SM,
                        variable=self.app.enc_sha256_var, text_color=T.TEXT_DARK,
                        fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER).pack(side="left")
        row += 1

        # 非对称（rage）开关行
        rage_row = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        rage_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.enc_rage_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(rage_row, text=tr("rage_asym"), font=FONT_SM,
                        variable=self.app.enc_rage_var, text_color=T.TEXT_DARK,
                        fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                        command=self.app._toggle_rage_mode).pack(side="left")
        row += 1

        # 收件人公钥行（仅 rage 模式显示；可填 age1… 字符串或公钥文件）
        recipient_row = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        recipient_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        recipient_row.columnconfigure(0, weight=1)
        self.app.enc_recipient_row = recipient_row
        self.app.enc_recipient = FileSelector(recipient_row, tr("rage_recipient"))
        self.app.enc_recipient.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(recipient_row, text=tr("gen_keypair"), width=110, height=28,
                      font=FONT_SM, fg_color=T.BTN_BG, text_color=T.BTN_TEXT,
                      hover_color=T.ACCENT_HOVER, cursor="hand2",
                      command=self.app._do_gen_keypair).grid(row=0, column=1, padx=(8, 0), sticky="s")
        recipient_row.grid_remove()
        row += 1

        self.app.enc_out = FileSelector(form, tr("output_dir_auto"), is_dir=True)
        self.app.enc_out.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 4))
        row += 1

        btn_row = ctk.CTkFrame(card, fg_color=T.BG_CARD, corner_radius=0)
        btn_row.grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))
        self.app.enc_go = PrimaryButton(btn_row, tr("start_encrypt"), command=self.app._do_encrypt)
        self.app.enc_go.pack(side="right")

        hint = ctk.CTkFrame(
            page, fg_color="transparent" if self.app._image_mode else T.BG_MAIN, corner_radius=0)
        hint.grid(row=1, column=0, sticky="nw", pady=(8, 0))
        ctk.CTkLabel(hint, text="\u2139  " + tr("strength_hint"),
                     font=(FONT_FAMILY, 8), text_color=T.TEXT_MUTED, wraplength=500,
                     justify="left").pack(anchor="w")

        return page


class DecryptPage(_BasePage):
    """单文件解密页"""

    def build(self, parent):
        page = self._panel(parent)
        page.columnconfigure(0, weight=1)
        T = self.T

        card = ctk.CTkFrame(page, fg_color=T.BG_CARD, corner_radius=8, border_width=1, border_color=T.BORDER)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="\U0001F513  " + tr("decrypt_single"),
                     font=FONT_HEAD, text_color=T.TEXT_DARK, anchor="w", padx=16
                     ).grid(row=0, column=0, sticky="ew", pady=(14, 4))
        ctk.CTkLabel(card, text=tr("decrypt_single_desc"),
                     font=FONT_SM, text_color=T.TEXT_MUTED, anchor="w", padx=16
                     ).grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkFrame(card, height=1, fg_color=T.BORDER, corner_radius=0
                     ).grid(row=2, column=0, sticky="ew", padx=16)

        form = ctk.CTkFrame(card, fg_color=T.BG_CARD, corner_radius=0)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        self.app.dec_file = FileSelector(form, tr("enc_file_ptd"))
        self.app.dec_file.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.dec_pw = PasswordEntry(form, tr("dec_password"))
        self.app.dec_pw.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.dec_keyfile = FileSelector(form, tr("key_file"))
        self.app.dec_keyfile.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        rage_row = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        rage_row.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.dec_rage_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(rage_row, text=tr("rage_decrypt"), font=FONT_SM,
                        variable=self.app.dec_rage_var, text_color=T.TEXT_DARK,
                        fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                        command=self.app._toggle_rage_mode).pack(side="left")

        self.app.dec_out = FileSelector(form, tr("output_dir_auto"), is_dir=True)
        self.app.dec_out.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 4))

        btn_row = ctk.CTkFrame(card, fg_color=T.BG_CARD, corner_radius=0)
        btn_row.grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))
        self.app.dec_go = PrimaryButton(btn_row, tr("start_decrypt"), command=self.app._do_decrypt)
        self.app.dec_go.pack(side="right")

        return page


class BatchEncryptPage(_BasePage):
    """批量加密页"""

    def build(self, parent):
        page = self._panel(parent)
        page.columnconfigure(0, weight=1)
        T = self.T

        card = ctk.CTkFrame(page, fg_color=T.BG_CARD, corner_radius=8, border_width=1, border_color=T.BORDER)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="\u2750  " + tr("batch_enc"),
                     font=FONT_HEAD, text_color=T.TEXT_DARK, anchor="w", padx=16
                     ).grid(row=0, column=0, sticky="ew", pady=(14, 4))
        ctk.CTkLabel(card, text=tr("batch_enc_desc"),
                     font=FONT_SM, text_color=T.TEXT_MUTED, anchor="w", padx=16
                     ).grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkFrame(card, height=1, fg_color=T.BORDER, corner_radius=0
                     ).grid(row=2, column=0, sticky="ew", padx=16)

        form = ctk.CTkFrame(card, fg_color=T.BG_CARD, corner_radius=0)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        self.app.benc_dir = FileSelector(form, tr("source_dir"), is_dir=True)
        self.app.benc_dir.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.benc_pw = PasswordEntry(form, tr("enc_password"))
        self.app.benc_pw.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.benc_pw2 = PasswordEntry(form, tr("confirm_password"))
        self.app.benc_pw2.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.app.benc_keyfile = FileSelector(form, tr("key_file"))
        self.app.benc_keyfile.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        opt_row = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        opt_row.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        opt_row.columnconfigure(1, weight=1)

        ctk.CTkLabel(opt_row, text=tr("algorithm"), font=FONT_SM, text_color=T.TEXT_DARK
                     ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.app.benc_algo = ctk.CTkComboBox(
            opt_row, values=["XChaCha20-Poly1305", "AEGIS-256"], state="readonly", font=FONT, width=180)
        self.app.benc_algo.grid(row=0, column=1, sticky="w")
        self.app.benc_algo.set("XChaCha20-Poly1305")

        opt_row2 = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        opt_row2.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.benc_del_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt_row2, text=tr("delete_source"), font=FONT_SM,
                        variable=self.app.benc_del_var, text_color=T.TEXT_DARK,
                        fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER).pack(side="left", padx=(0, 16))

        self.app.benc_recycle_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt_row2, text=tr("recycle_source"), font=FONT_SM,
                        variable=self.app.benc_recycle_var, text_color=T.TEXT_DARK,
                        fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER).pack(side="left")

        # zstd 压缩选项行
        compress_row = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        compress_row.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.app.benc_zstd_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(compress_row, text=tr("enable_zstd"), font=FONT_SM,
                        variable=self.app.benc_zstd_var, text_color=T.TEXT_DARK,
                        fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                        command=self.app._toggle_compression_level).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(compress_row, text=tr("compression_level"), font=FONT_SM, text_color=T.TEXT_DARK
                     ).pack(side="left", padx=(8, 4))
        self.app.benc_compression_level = ctk.CTkComboBox(
            compress_row, values=[str(i) for i in range(1, 23)],
            state="disabled", font=FONT, width=60)
        self.app.benc_compression_level.pack(side="left", padx=(0, 4))
        self.app.benc_compression_level.set("3")

        sha256_row = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        sha256_row.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.benc_sha256_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(sha256_row, text=tr("sha256_sidecar"), font=FONT_SM,
                        variable=self.app.benc_sha256_var, text_color=T.TEXT_DARK,
                        fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER).pack(side="left")

        self.app.benc_out = FileSelector(form, tr("output_dir"), is_dir=True)
        self.app.benc_out.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(0, 4))

        btn_row = ctk.CTkFrame(card, fg_color=T.BG_CARD, corner_radius=0)
        btn_row.grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))
        self.app.benc_go = PrimaryButton(btn_row, tr("start_batch_enc"), command=self.app._do_batch_encrypt)
        self.app.benc_go.pack(side="right")

        return page


class BatchDecryptPage(_BasePage):
    """批量解密页"""

    def build(self, parent):
        page = self._panel(parent)
        page.columnconfigure(0, weight=1)
        T = self.T

        card = ctk.CTkFrame(page, fg_color=T.BG_CARD, corner_radius=8, border_width=1, border_color=T.BORDER)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="\u2751  " + tr("batch_dec"),
                     font=FONT_HEAD, text_color=T.TEXT_DARK, anchor="w", padx=16
                     ).grid(row=0, column=0, sticky="ew", pady=(14, 4))
        ctk.CTkLabel(card, text=tr("batch_dec_desc"),
                     font=FONT_SM, text_color=T.TEXT_MUTED, anchor="w", padx=16
                     ).grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkFrame(card, height=1, fg_color=T.BORDER, corner_radius=0
                     ).grid(row=2, column=0, sticky="ew", padx=16)

        form = ctk.CTkFrame(card, fg_color=T.BG_CARD, corner_radius=0)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        self.app.bdec_dir = FileSelector(form, tr("source_dir_ptd"), is_dir=True)
        self.app.bdec_dir.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.bdec_pw = PasswordEntry(form, tr("dec_password"))
        self.app.bdec_pw.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.app.bdec_keyfile = FileSelector(form, tr("key_file"))
        self.app.bdec_keyfile.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.app.bdec_out = FileSelector(form, tr("output_dir"), is_dir=True)
        self.app.bdec_out.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 4))

        btn_row = ctk.CTkFrame(card, fg_color=T.BG_CARD, corner_radius=0)
        btn_row.grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))
        self.app.bdec_go = PrimaryButton(btn_row, tr("start_batch_dec"), command=self.app._do_batch_decrypt)
        self.app.bdec_go.pack(side="right")

        return page


class RewrapPage(_BasePage):
    """密钥轮换页：为已有 .ptd 容器更换密码（--rewrap，payload 不变）"""

    def build(self, parent):
        page = self._panel(parent)
        page.columnconfigure(0, weight=1)
        T = self.T

        card = ctk.CTkFrame(page, fg_color=T.BG_CARD, corner_radius=8, border_width=1, border_color=T.BORDER)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="\U0001F511  " + tr("nav_rewrap"),
                     font=FONT_HEAD, text_color=T.TEXT_DARK, anchor="w", padx=16
                     ).grid(row=0, column=0, sticky="ew", pady=(14, 4))
        ctk.CTkLabel(card, text=tr("rewrap_desc"),
                     font=FONT_SM, text_color=T.TEXT_MUTED, anchor="w", padx=16
                     ).grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkFrame(card, height=1, fg_color=T.BORDER, corner_radius=0
                     ).grid(row=2, column=0, sticky="ew", padx=16)

        form = ctk.CTkFrame(card, fg_color=T.BG_CARD, corner_radius=0)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        self.app.rw_file = FileSelector(form, tr("target_container"))
        self.app.rw_file.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.rw_old_pw = PasswordEntry(form, tr("old_password"))
        self.app.rw_old_pw.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.rw_old_keyfile = FileSelector(form, tr("key_file"))
        self.app.rw_old_keyfile.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.rw_new_pw = PasswordEntry(form, tr("new_password"))
        self.app.rw_new_pw.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.rw_new_pw2 = PasswordEntry(form, tr("confirm_new_password"))
        self.app.rw_new_pw2.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        btn_row = ctk.CTkFrame(card, fg_color=T.BG_CARD, corner_radius=0)
        btn_row.grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))
        self.app.rw_go = PrimaryButton(btn_row, tr("start_rewrap"), command=self.app._do_rewrap)
        self.app.rw_go.pack(side="right")

        return page


class SettingsPage(_BasePage):
    """设置页（语言 / 主题 / 图片背景）"""

    def build(self, parent):
        app = self.app
        T = self.T
        page = self._panel(parent)
        page.columnconfigure(0, weight=1)

        card = ctk.CTkFrame(page, fg_color=T.BG_CARD, corner_radius=8, border_width=1, border_color=T.BORDER)
        card.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="\u2699  " + tr("settings"),
                     font=FONT_HEAD, text_color=T.TEXT_DARK, anchor="w", padx=16
                     ).grid(row=0, column=0, sticky="ew", pady=(14, 4))
        ctk.CTkLabel(card, text=tr("settings_desc"),
                     font=FONT_SM, text_color=T.TEXT_MUTED, anchor="w", padx=16
                     ).grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkFrame(card, height=1, fg_color=T.BORDER, corner_radius=0
                     ).grid(row=2, column=0, sticky="ew", padx=16)

        form = ctk.CTkFrame(card, fg_color=T.BG_CARD, corner_radius=0)
        form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        form.columnconfigure(1, weight=1)

        # 语言
        lang_row = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        lang_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(lang_row, text=tr("language"), font=FONT_SM, text_color=T.TEXT_DARK,
                     anchor="w").pack(side="left")
        app.lang_combo = ctk.CTkComboBox(
            lang_row, values=["中文", "English"], state="readonly",
            font=(FONT_FAMILY, 9), width=120, height=28, fg_color=T.INPUT_BG)
        app.lang_combo.set("中文" if app.lang == "zh" else "English")
        app.lang_combo.pack(side="right")
        app.lang_combo.configure(command=app._on_language_change)

        # 主题
        theme_row = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        theme_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(theme_row, text=tr("theme"), font=FONT_SM, text_color=T.TEXT_DARK,
                     anchor="w").pack(side="left")
        app.theme_combo = ctk.CTkComboBox(
            theme_row, values=[tr("theme_light"), tr("theme_dark")], state="readonly",
            font=(FONT_FAMILY, 9), width=120, height=28, fg_color=T.INPUT_BG)
        app.theme_combo.set(tr("theme_light") if app.theme == "light" else tr("theme_dark"))
        app.theme_combo.pack(side="right")
        app.theme_combo.configure(command=app._on_theme_change)
        if app._image_mode:
            app.theme_combo.configure(state="disabled")

        # 实验性：图片背景
        exp_card = ctk.CTkFrame(page, fg_color=T.BG_CARD, corner_radius=8, border_width=1, border_color=T.BORDER)
        exp_card.grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 16))
        exp_card.columnconfigure(0, weight=1)

        ctk.CTkLabel(exp_card, text="\u26A0  " + tr("exp_section"),
                     font=FONT_HEAD, text_color=T.TEXT_DARK, anchor="w", padx=16
                     ).grid(row=0, column=0, sticky="ew", pady=(14, 4))
        ctk.CTkLabel(exp_card, text=tr("exp_note"),
                     font=FONT_SM, text_color=T.TEXT_MUTED, anchor="w", padx=16
                     ).grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkFrame(exp_card, height=1, fg_color=T.BORDER, corner_radius=0
                     ).grid(row=2, column=0, sticky="ew", padx=16)

        exp_form = ctk.CTkFrame(exp_card, fg_color=T.BG_CARD, corner_radius=0)
        exp_form.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 16))
        exp_form.columnconfigure(1, weight=1)

        # 启用图片背景
        img_row = ctk.CTkFrame(exp_form, fg_color=T.BG_CARD, corner_radius=0)
        img_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(img_row, text=tr("exp_image_bg"), font=FONT_SM, text_color=T.TEXT_DARK,
                     anchor="w").pack(side="left")
        app.imagebg_switch = ctk.CTkSwitch(
            img_row, text="", width=50, height=24, progress_color=T.ACCENT,
            command=lambda: app._on_imagebg_toggle(app.imagebg_switch.get()))
        if app._image_mode:
            app.imagebg_switch.select()
        app.imagebg_switch.pack(side="right")

        # 选择图片
        pick_row = ctk.CTkFrame(exp_form, fg_color=T.BG_CARD, corner_radius=0)
        pick_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(pick_row, text=tr("exp_pick_image"), font=FONT_SM, text_color=T.TEXT_DARK,
                     anchor="w").pack(side="left")
        app.imagebg_pick_btn = ctk.CTkButton(
            pick_row, text="\u2026", width=50, height=26, font=(FONT_FAMILY, 10),
            fg_color=T.BTN_BG, text_color=T.BTN_TEXT, hover_color=T.ACCENT_HOVER,
            command=app._on_imagebg_pick)
        app.imagebg_pick_btn.pack(side="right")

        # 模糊设置（滑杆 + 数值输入）
        blur_specs = (
            (2, "wall", "exp_blur_wall"),
            (3, "panel", "exp_blur_panel"),
        )
        for row_i, which, label_key in blur_specs:
            row = ctk.CTkFrame(exp_form, fg_color=T.BG_CARD, corner_radius=0)
            row.grid(row=row_i, column=0, sticky="ew", pady=(0, 4))
            ctk.CTkLabel(row, text=tr(label_key), font=FONT_SM, text_color=T.TEXT_DARK,
                         anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, width=52, height=24, font=(FONT_FAMILY, 9),
                                 fg_color=T.INPUT_BG, text_color=T.TEXT_DARK, justify="center",
                                 border_width=1, border_color=T.BORDER)
            entry.pack(side="right", padx=(8, 0))
            slider = ctk.CTkSlider(
                row, from_=0, to=50, number_of_steps=50, width=110, height=18,
                progress_color=T.ACCENT, button_color=T.ACCENT, button_hover_color=T.ACCENT_HOVER,
                command=(app._on_wall_blur_change if which == "wall" else app._on_panel_blur_change))
            slider.pack(side="right")
            val = app._image_blur if which == "wall" else app._panel_blur
            slider.set(val)
            entry.insert(0, str(val))
            entry.bind("<Return>", lambda e, w=which: app._on_blur_entry(w))
            entry.bind("<FocusOut>", lambda e, w=which: app._on_blur_entry(w))
            setattr(app, f"{which}_blur_slider", slider)
            setattr(app, f"{which}_blur_entry", entry)
            if not app._image_mode:
                slider.configure(state="disabled")
                entry.configure(state="disabled")

        return page


class AboutPage(_BasePage):
    """关于页：版本信息 / 运行环境 / 开源依赖 / 友情链接 / 关于我们 / 仓库与操作

    页面容器不支持滚动且最小窗口高度 540，故采用紧凑双列布局。
    引擎信息在 build 时同步探测一次（--help/--features 均为毫秒级），
    之后由「重新检测」按钮刷新（app._refresh_about）。
    """

    def build(self, parent):
        app = self.app
        T = self.T
        page = self._panel(parent)
        page.columnconfigure(0, weight=1)

        app.about_labels = {}   # 值标签登记表：key -> CTkLabel，供 app._refresh_about() 回填

        def _card(row, bottom=0):
            card = ctk.CTkFrame(page, fg_color=T.BG_CARD, corner_radius=8,
                                border_width=1, border_color=T.BORDER)
            card.grid(row=row, column=0, sticky="ew", padx=16,
                      pady=(16 if row == 0 else 8, bottom))
            card.columnconfigure(0, weight=1)
            return card

        def _head(card, title, desc_key=None):
            ctk.CTkLabel(card, text=title, font=FONT_HEAD, text_color=T.TEXT_DARK,
                         anchor="w", padx=16).grid(row=0, column=0, sticky="ew", pady=(12, 2))
            if desc_key:
                ctk.CTkLabel(card, text=tr(desc_key), font=FONT_SM, text_color=T.TEXT_MUTED,
                             anchor="w", padx=16).grid(row=1, column=0, sticky="ew", pady=(0, 8))
            ctk.CTkFrame(card, height=1, fg_color=T.BORDER, corner_radius=0
                         ).grid(row=2, column=0, sticky="ew", padx=16)
            body = ctk.CTkFrame(card, fg_color=T.BG_CARD, corner_radius=0)
            body.grid(row=3, column=0, sticky="ew", padx=16, pady=(10, 12))
            return body

        def _field(body, r, c, label, key, span=1, wrap=0):
            """单行字段：`标签  值`（省高度；页面区高度按请求高度分配，必须紧凑）"""
            cell = ctk.CTkFrame(body, fg_color=T.BG_CARD, corner_radius=0)
            cell.grid(row=r, column=c, columnspan=span, sticky="ew", padx=(0, 14), pady=(0, 2))
            ctk.CTkLabel(cell, text=tr(label), font=(FONT_FAMILY, 9),
                         text_color=T.TEXT_MUTED, anchor="w").pack(side="left")
            lbl = ctk.CTkLabel(cell, text="—", font=FONT_SM, text_color=T.TEXT_DARK,
                               anchor="w", justify="left", wraplength=wrap)
            lbl.pack(side="left", padx=(8, 0))
            app.about_labels[key] = lbl

        def _link(parent, text, url, row=None, col=0, pad=(0, 16)):
            """可点击链接：文字 + ↗、手型光标、悬停变色（主题刻意无彩色，故不用彩色链接）

            row 为 None 时用 pack（用于与按钮混排的行），否则用 grid。
            """
            lbl = ctk.CTkLabel(parent, text=text + "  \u2197", font=FONT_SM,
                               text_color=T.TEXT_DARK, cursor="hand2", anchor="w")
            if row is None:
                lbl.pack(side="left")
            else:
                lbl.grid(row=row, column=col, sticky="w", padx=pad, pady=(0, 4))
            lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
            lbl.bind("<Enter>", lambda e, w=lbl: w.configure(text_color=T.ACCENT_HOVER))
            lbl.bind("<Leave>", lambda e, w=lbl: w.configure(text_color=T.TEXT_DARK))
            return lbl

        # ── 卡片 1：版本信息（3 列） ──
        body1 = _head(_card(0), "\u24D8  " + tr("nav_about"), "about_desc")
        for c in (0, 1, 2):
            body1.columnconfigure(c, weight=1, uniform="about")
        _field(body1, 0, 0, "about_gui_version", "gui_version")
        _field(body1, 0, 1, "about_engine_version", "engine_version")
        _field(body1, 0, 2, "about_container_format", "container_format")
        _field(body1, 1, 0, "about_engine_caps", "engine_caps")
        _field(body1, 1, 1, "about_engine_path", "engine_path", span=2, wrap=300)
        if LICENSE_NAME:
            _field(body1, 2, 0, "about_license", "license", span=3)

        # ── 卡片 2：运行环境（Python + 4 个可选依赖，3 列 2 行） ──
        body2 = _head(_card(1), tr("about_env"))
        for c in (0, 1, 2):
            body2.columnconfigure(c, weight=1, uniform="about")
        _field(body2, 0, 0, "Python", "env:python")
        for i, (name, _v, _u) in enumerate(collect_environment()[1]):
            r, c = divmod(i + 1, 3)
            _field(body2, r, c, name, "env:" + name)

        # ── 卡片 3：开源依赖（名称 + 可点击链接，3 列） ──
        body3 = _head(_card(2), tr("about_deps"))
        for c in (0, 1, 2):
            body3.columnconfigure(c, weight=1, uniform="credit")
        for i, (name, url) in enumerate(CREDITS):
            r, c = divmod(i, 3)
            _link(body3, name, url, r, c)

        # ── 卡片 4：友情链接 ──
        body4 = _head(_card(3), tr("about_friends"))
        _link(body4, FRIEND_LINK[0], FRIEND_LINK[1], 0, 0)

        # ── 卡片 5：关于我们（每人一行：名字 · B 站主页 · GitHub 主页） ──
        body5 = _head(_card(4), tr("about_team"))
        for c in (0, 1, 2):
            body5.columnconfigure(c, weight=1, uniform="team")
        for r, (name, bili_url, gh_url) in enumerate(TEAM):
            cell = ctk.CTkFrame(body5, fg_color=T.BG_CARD, corner_radius=0)
            cell.grid(row=r, column=0, sticky="ew", padx=(0, 14), pady=(0, 4))
            ctk.CTkLabel(cell, text=name, font=FONT_SM, text_color=T.TEXT_DARK,
                         anchor="w").pack(side="left")
            _link(body5, tr("about_link_bilibili"), bili_url, r, 1)
            if gh_url:
                _link(body5, tr("about_link_github"), gh_url, r, 2)

        # ── 卡片 6：仓库与操作 ──
        card6 = _card(5, bottom=16)
        body6 = ctk.CTkFrame(card6, fg_color=T.BG_CARD, corner_radius=0)
        body6.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 12))
        _link(body6, tr("about_repo"), REPO_URL)
        ctk.CTkButton(body6, text=tr("about_refresh"), width=96, height=26, font=FONT_SM,
                      fg_color=T.BTN_BG, text_color=T.BTN_TEXT, hover_color=T.ACCENT_HOVER,
                      cursor="hand2", command=app._refresh_about).pack(side="right")
        app.about_copy_btn = ctk.CTkButton(
            body6, text=tr("about_copy_all"), width=120, height=26, font=FONT_SM,
            fg_color=T.BTN_BG, text_color=T.BTN_TEXT, hover_color=T.ACCENT_HOVER,
            cursor="hand2", command=app._copy_about_info)
        app.about_copy_btn.pack(side="right", padx=(0, 8))

        app._refresh_about()
        return page


# 模式 -> 页面组件工厂（保持 gui._switch_mode 的按名分发稳定）
PAGE_FACTORIES = {
    "encrypt": EncryptPage,
    "decrypt": DecryptPage,
    "batch_enc": BatchEncryptPage,
    "batch_dec": BatchDecryptPage,
    "rewrap": RewrapPage,
    "about": AboutPage,
    "settings": SettingsPage,
}


def build_page(mode, app, parent):
    """按模式构建页面组件，返回页面控件。未知/未登记模式返回 None。"""
    cls = PAGE_FACTORIES.get(mode)
    if cls is None:
        return None
    return cls(app).build(parent)