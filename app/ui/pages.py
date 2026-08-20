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

import customtkinter as ctk

from .theme import FONT, FONT_SM, FONT_HEAD, FONT_FAMILY
from ..core.i18n import tr
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
        self.app.dec_out = FileSelector(form, tr("output_dir_auto"), is_dir=True)
        self.app.dec_out.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 4))

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

        opt_row = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        opt_row.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        opt_row.columnconfigure(1, weight=1)

        ctk.CTkLabel(opt_row, text=tr("algorithm"), font=FONT_SM, text_color=T.TEXT_DARK
                     ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.app.benc_algo = ctk.CTkComboBox(
            opt_row, values=["XChaCha20-Poly1305", "AEGIS-256"], state="readonly", font=FONT, width=180)
        self.app.benc_algo.grid(row=0, column=1, sticky="w")
        self.app.benc_algo.set("XChaCha20-Poly1305")

        ctk.CTkLabel(opt_row, text=tr("threads"), font=FONT_SM, text_color=T.TEXT_DARK
                     ).grid(row=0, column=2, sticky="w", padx=(16, 4))
        self.app.benc_threads = ctk.CTkComboBox(
            opt_row, values=["1", "2", "4", "8"], state="readonly", font=FONT, width=60)
        self.app.benc_threads.grid(row=0, column=3, sticky="w")
        self.app.benc_threads.set("4")

        opt_row2 = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        opt_row2.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.app.benc_del_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt_row2, text=tr("delete_source"), font=FONT_SM,
                        variable=self.app.benc_del_var, text_color=T.TEXT_DARK,
                        fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER).pack(side="left", padx=(0, 16))

        self.app.benc_out = FileSelector(form, tr("output_dir"), is_dir=True)
        self.app.benc_out.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 4))

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

        opt_row = ctk.CTkFrame(form, fg_color=T.BG_CARD, corner_radius=0)
        opt_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        opt_row.columnconfigure(1, weight=1)
        ctk.CTkLabel(opt_row, text=tr("threads"), font=FONT_SM, text_color=T.TEXT_DARK
                     ).grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.app.bdec_threads = ctk.CTkComboBox(
            opt_row, values=["1", "2", "4", "8"], state="readonly", font=FONT, width=60)
        self.app.bdec_threads.grid(row=0, column=1, sticky="w")
        self.app.bdec_threads.set("4")

        self.app.bdec_out = FileSelector(form, tr("output_dir"), is_dir=True)
        self.app.bdec_out.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 4))

        btn_row = ctk.CTkFrame(card, fg_color=T.BG_CARD, corner_radius=0)
        btn_row.grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))
        self.app.bdec_go = PrimaryButton(btn_row, tr("start_batch_dec"), command=self.app._do_batch_decrypt)
        self.app.bdec_go.pack(side="right")

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


# 模式 -> 页面组件工厂（保持 gui._switch_mode 的按名分发稳定）
PAGE_FACTORIES = {
    "encrypt": EncryptPage,
    "decrypt": DecryptPage,
    "batch_enc": BatchEncryptPage,
    "batch_dec": BatchDecryptPage,
    "settings": SettingsPage,
}


def build_page(mode, app, parent):
    """按模式构建页面组件，返回页面控件。未知/未登记模式返回 None。"""
    cls = PAGE_FACTORIES.get(mode)
    if cls is None:
        return None
    return cls(app).build(parent)