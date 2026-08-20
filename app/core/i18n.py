#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
i18n.py —— 多语言翻译（纯逻辑，第 2 步抽取）

把 STRINGS 翻译表与 tr()/apply_lang() 从 GUI 层抽出，使语言切换逻辑可独立测试。
GUI 层只调用 tr(key) 取文本；控件只存翻译键 key，不存渲染后的字符串，
语言切换统一由 GUI 的 _apply_settings 全量重建触发。
"""
# 居中：zh（简体中文）/ en（English）
STRINGS = {
    "zh": {
        "app_subtitle": "文件加密工具",
        "nav_encrypt": "加密文件",
        "nav_decrypt": "解密文件",
        "nav_batch_enc": "批量加密",
        "nav_batch_dec": "批量解密",
        "nav_settings": "设置",
        "settings": "设置",
        "settings_desc": "配置应用程序的基本选项和实验性功能",
        "language": "语言",
        "theme": "主题",
        "theme_light": "浅色",
        "theme_dark": "深色",
        "ready": "就绪",
        "running": "运行中...",
        "done": "完成",
        "failed": "失败",
        "log_title": "运行日志",
        "export": "导出",
        "clear": "清空",
        "encrypt_single": "加密单个文件",
        "encrypt_single_desc": "选择一个文件，设置密码后加密为 .ptd 格式",
        "source_file": "源文件",
        "enc_password": "加密密码",
        "confirm_password": "确认密码",
        "algorithm": "算法",
        "delete_source": "加密后删除源文件",
        "output_dir_auto": "输出目录（留空为源文件所在目录）",
        "output_dir": "输出目录",
        "start_encrypt": "开始加密",
        "strength_hint": "密码强度仅作参考。实际安全性取决于密码长度和复杂度。",
        "decrypt_single": "解密单个文件",
        "decrypt_single_desc": "选择一个 .ptd 加密文件，输入密码还原为原始文件",
        "enc_file_ptd": "加密文件（.ptd）",
        "dec_password": "解密密码",
        "start_decrypt": "开始解密",
        "batch_enc": "批量加密目录",
        "batch_enc_desc": "递归加密整个目录下所有文件为 .ptd 格式",
        "source_dir": "源目录",
        "threads": "线程数",
        "start_batch_enc": "开始批量加密",
        "batch_dec": "批量解密目录",
        "batch_dec_desc": "递归解密目录下所有 .ptd 文件还原为原始文件",
        "source_dir_ptd": "源目录（包含 .ptd 文件）",
        "start_batch_dec": "开始批量解密",
        "paste_path": "粘贴路径",
        "clear_item": "清空",
        "select_dir": "选择目录",
        "select_file": "选择文件",
        "hint": "提示",
        "error": "错误",
        "msg_select_enc_file": "请选择要加密的文件",
        "msg_enter_enc_pw": "请输入加密密码",
        "msg_pw_mismatch": "两次输入的密码不一致",
        "msg_src_not_exist": "源文件不存在",
        "msg_cannot_create_dir": "无法创建输出目录",
        "msg_select_ptd": "请选择要解密的 .ptd 文件",
        "msg_enter_dec_pw": "请输入解密密码",
        "msg_file_not_exist": "文件不存在",
        "msg_not_ptd": "选中的文件不是 .ptd 格式",
        "msg_select_src_dir": "请选择源目录",
        "msg_src_dir_not_exist": "源目录不存在",
        "msg_log_empty": "日志为空",
        "msg_export_fail": "导出失败",
        "msg_log_exported": "日志已导出",
        "msg_busy": "已有操作正在执行，请等待完成",
        "msg_cancel": "用户取消操作",
        "strength_weak": "弱",
        "strength_medium": "中",
        "strength_strong": "强",
        "exp_section": "实验性 · 图片背景",
        "exp_image_bg": "启用图片背景",
        "exp_pick_image": "选择图片",
        "exp_blur_wall": "壁纸模糊",
        "exp_blur_panel": "面板模糊",
        "exp_note": "开启后将忽略主题色；侧栏与内容面板呈半透明毛玻璃（面板模糊 0 为完全透明），文字不受模糊影响。",
        "msg_need_pillow": "图片背景功能需要 Pillow，请先安装：pip install pillow",
    },
    "en": {
        "app_subtitle": "File Encryption Tool",
        "nav_encrypt": "Encrypt File",
        "nav_decrypt": "Decrypt File",
        "nav_batch_enc": "Batch Encrypt",
        "nav_batch_dec": "Batch Decrypt",
        "nav_settings": "Settings",
        "settings": "Settings",
        "settings_desc": "Configure application options and experimental features",
        "language": "Language",
        "theme": "Theme",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "ready": "Ready",
        "running": "Running...",
        "done": "Done",
        "failed": "Failed",
        "log_title": "Running Log",
        "export": "Export",
        "clear": "Clear",
        "encrypt_single": "Encrypt Single File",
        "encrypt_single_desc": "Select a file, set a password, encrypt to .ptd format",
        "source_file": "Source File",
        "enc_password": "Encryption Password",
        "confirm_password": "Confirm Password",
        "algorithm": "Algorithm",
        "delete_source": "Delete source after encrypt",
        "output_dir_auto": "Output dir (blank = source dir)",
        "output_dir": "Output Directory",
        "start_encrypt": "Encrypt",
        "strength_hint": "Password strength is only a reference. Real security depends on its length and complexity.",
        "decrypt_single": "Decrypt Single File",
        "decrypt_single_desc": "Select a .ptd file, enter the password to restore the original",
        "enc_file_ptd": "Encrypted file (.ptd)",
        "dec_password": "Decryption Password",
        "start_decrypt": "Decrypt",
        "batch_enc": "Encrypt Directory",
        "batch_enc_desc": "Recursively encrypt all files in the directory to .ptd",
        "source_dir": "Source Directory",
        "threads": "Threads",
        "start_batch_enc": "Batch Encrypt",
        "batch_dec": "Decrypt Directory",
        "batch_dec_desc": "Recursively decrypt all .ptd files in the directory",
        "source_dir_ptd": "Source dir (contains .ptd files)",
        "start_batch_dec": "Batch Decrypt",
        "paste_path": "Paste Path",
        "clear_item": "Clear",
        "select_dir": "Select Directory",
        "select_file": "Select File",
        "hint": "Notice",
        "error": "Error",
        "msg_select_enc_file": "Please select a file to encrypt",
        "msg_enter_enc_pw": "Please enter the encryption password",
        "msg_pw_mismatch": "The two passwords do not match",
        "msg_src_not_exist": "Source file does not exist",
        "msg_cannot_create_dir": "Could not create output directory",
        "msg_select_ptd": "Please select a .ptd file to decrypt",
        "msg_enter_dec_pw": "Please enter the decryption password",
        "msg_file_not_exist": "File does not exist",
        "msg_not_ptd": "The selected file is not in .ptd format",
        "msg_select_src_dir": "Please select a source directory",
        "msg_src_dir_not_exist": "Source directory does not exist",
        "msg_log_empty": "Log is empty",
        "msg_export_fail": "Export failed",
        "msg_log_exported": "Log exported",
        "msg_busy": "An operation is already running, please wait",
        "msg_cancel": "User cancelled the operation",
        "strength_weak": "Weak",
        "strength_medium": "Medium",
        "strength_strong": "Strong",
        "exp_section": "Experimental · Image BG",
        "exp_image_bg": "Enable image bg",
        "exp_pick_image": "Choose image",
        "exp_blur_wall": "Wallpaper blur",
        "exp_blur_panel": "Panel blur",
        "exp_note": "Ignores theme colors; the sidebar and content panels become translucent frosted glass (panel blur 0 = fully transparent). Text is never blurred.",
        "msg_need_pillow": "Image background needs Pillow. Install with: pip install pillow",
    },
}


_LANG = "zh"


def available_langs():
    """返回当前支持的翻译语言列表。"""
    return list(STRINGS.keys())


def get_lang():
    return _LANG


def set_lang(lang):
    """切换当前语言。仅接受已知语言，否则保持原语言。"""
    global _LANG
    if lang in STRINGS:
        _LANG = lang


def tr(key):
    """返回当前语言下的翻译文本（无则原样返回 key）。"""
    table = STRINGS.get(_LANG) or STRINGS["zh"]
    return table.get(key, key)