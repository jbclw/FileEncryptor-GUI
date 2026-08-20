#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileEncryptor GUI —— 文件加密工具图形界面
基于 FileEncryptor 命令行工具的封装（Windows / Linux / macOS）
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk  # 保留用于 StringVar, BooleanVar 等
from ..core.engine import EngineService
from ..core.args import (
    validate_encrypt_inputs, validate_decrypt_inputs,
    validate_batch_encrypt_inputs, validate_batch_decrypt_inputs,
    ensure_output_dir, build_encrypt_args, build_decrypt_args,
    build_batch_encrypt_args, build_batch_decrypt_args,
)
from ..core.i18n import tr, set_lang, available_langs
from ..core.config import get_config
from ..core.strength import password_score
from .theme import get_theme, set_theme_name, theme_names, FONT, FONT_SM, FONT_LG, FONT_MONO, FONT_HEAD, FONT_FAMILY
from .pages import build_page
import os
import sys
import threading
import time
from pathlib import Path
from datetime import datetime
import queue

# 实验性"图片背景+模糊"功能依赖 Pillow。未安装时该功能自动禁用并友好提示。
try:
    from PIL import Image as PILImage, ImageFilter, ImageTk, ImageDraw
    _HAVE_PIL = True
except Exception:
    _HAVE_PIL = False


# 全局引擎服务实例（承载取消状态与引擎执行）
_engine_service = EngineService()


class AnimationManager:
    """动画管理器（预留，界面以克制为准则，暂未大量使用）"""

    def __init__(self, root):
        self.root = root


# ── 主应用 ─────────────────────────────────────────────────────────────

class FileEncryptorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FileEncryptor")

        # 加载配置
        self.config = get_config()

        # 恢复语言与主题（应用后再建 UI，颜色/文案随主题变化）
        self.lang = self.config.get("ui", "lang", "zh")
        if self.lang not in available_langs():
            self.lang = "zh"
        self.theme = self.config.get("ui", "theme", "light")
        if self.theme not in theme_names():
            self.theme = "light"
        set_lang(self.lang)
        set_theme_name(self.theme)
        self._theme = get_theme()

        self.root.configure(bg=self._theme.BG_MAIN)

        # 实验性图片背景相关配置
        self._image_mode = self.config.getboolean("ui", "image_mode", False)
        self._image_blur = self.config.getint("ui", "image_blur", 0)      # 壁纸模糊
        self._panel_blur = self.config.getint("ui", "panel_blur", 14)     # 面板模糊
        self._image_path = self.config.get("ui", "image_path", "")
        self._bg_canvas = None    # 底层壁纸画布
        self._bg_photo = None
        self._bg_item = None
        self._resize_job = None
        self._render_job = None
        # 取色伪透明状态（缓存与防重入）
        self._cover_cache = None        # 缓存清晰壁纸，供取色复用
        self._tint_map = {}             # id(widget) -> (widget, key)
        self._tint_pending = False
        self._tint_retries = 0
        self._root_x = 0
        self._root_y = 0
        # 毛玻璃面板：图片模式下结构性容器改为 tk.Canvas，直接绘制壁纸模糊裁剪
        self._glass_canvases = []   # 注册的毛玻璃画布列表
        self._glass_items = {}      # canvas id -> image item id
        self._glass_photos = {}     # canvas id -> PhotoImage（保持引用防 GC）
        self._nav_items = {}        # 侧栏画布文本项：mode -> item id
        self._ver_item = None       # 侧栏版本文本项

        # 图片背景模式下，切换主题色无意义，故运行中强制浅色，避免视觉错乱
        if self._image_mode:
            set_theme_name("light")
            self._theme = get_theme()

        # 恢复窗口状态
        self._restore_window_state()

        self.root.minsize(760, 540)

        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self._current_mode = "encrypt"
        self._running = False
        self._process = None

        # 动画管理器
        self.anim = AnimationManager(self.root)

        # 页面复用缓存：创建一次，切换时只 show/hide
        self._pages = {}

        self._build_ui()
        self._switch_mode("encrypt")
        self._setup_shortcuts()

        # 窗口尺寸变化时重绘图片背景（防抖），并初始化图片背景布局
        self.root.bind("<Configure>", self._on_root_resize)
        if self._image_mode:
            self.root.after(60, self._apply_imagebg_layout)

        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # 如果没有保存的窗口状态，则居中显示
        if not self.config.getboolean("window", "has_saved_state", False):
            self.root.update_idletasks()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 2 - 30
            self.root.geometry(f"+{x}+{y}")

    def _restore_window_state(self):
        x = self.config.getint("window", "x", -1)
        y = self.config.getint("window", "y", -1)
        width = self.config.getint("window", "width", 880)
        height = self.config.getint("window", "height", 620)

        if x >= 0 and y >= 0:
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        else:
            self.root.geometry(f"{width}x{height}")

    def _save_window_state(self):
        try:
            self.root.update_idletasks()
            self.config.set("window", "x", self.root.winfo_x())
            self.config.set("window", "y", self.root.winfo_y())
            self.config.set("window", "width", self.root.winfo_width())
            self.config.set("window", "height", self.root.winfo_height())
            self.config.set("window", "has_saved_state", True)
            self.config.save()
        except Exception as e:
            print(f"保存窗口状态失败: {e}")

    def _on_closing(self):
        self._save_window_state()
        self.root.destroy()

    def _setup_shortcuts(self):
        self.root.bind("<Control-e>", lambda e: self._switch_mode("encrypt"))
        self.root.bind("<Control-d>", lambda e: self._switch_mode("decrypt"))
        self.root.bind("<Control-E>", lambda e: self._switch_mode("batch_enc"))
        self.root.bind("<Control-D>", lambda e: self._switch_mode("batch_dec"))
        self.root.bind("<Control-l>", lambda e: self._export_log())
        self.root.bind("<Control-w>", lambda e: self._clear_output())
        self.root.bind("<F5>", lambda e: self._refresh())
        self.root.bind("<Escape>", lambda e: self._cancel_operation())

    def _refresh(self):
        pass

    def _cancel_operation(self, event=None):
        if self._running:
            self._log(f"[!] {tr('msg_cancel')}")
            # 下发取消信号：EngineService 写入取消文件，_runner.py 收到后杀进程退出
            _engine_service.cancel()

    # ── 设置 ───────────────────────────────────────────────────────────

    def _apply_settings(self):
        """重建整个界面以应用新的语言/主题/图片背景模式"""
        mode = self._current_mode
        for w in self.root.winfo_children():
            w.destroy()
        self._pages.clear()
        self._bg_canvas = None
        self._bg_photo = None
        self._bg_item = None
        self._glass_canvases = []
        self._glass_items = {}
        self._glass_photos = {}
        self._nav_items = {}
        self._ver_item = None
        # 清空取色缓存：旧控件 id 失效，壁纸尺寸可能变化
        self._cover_cache = None
        self._tint_map = {}
        self._tint_pending = False
        self._tint_retries = 0
        self._build_ui()
        self._switch_mode(mode)
        if self._image_mode:
            self.root.after(60, self._apply_imagebg_layout)

    def _on_language_change(self, label):
        if self._running:
            return
        key = "zh" if label == "中文" else "en"
        if key != self.lang:
            self.lang = key
            self.config.set("ui", "lang", key)
            self.config.save()
            set_lang(key)
            # 延迟重建，避免回调中销毁触发控件
            self.root.after(0, self._apply_settings)

    def _on_theme_change(self, label):
        if self._running or self._image_mode:
            return
        key = "dark" if label == tr("theme_dark") else "light"
        if key != self.theme:
            self.theme = key
            self.config.set("ui", "theme", key)
            self.config.save()
            set_theme_name(key)
            self._theme = get_theme()
            self.root.after(0, self._apply_settings)

    # ── 实验性：图片背景 + 模糊 ────────────────────────────────────────

    def _on_root_resize(self, event):
        """窗口尺寸变化时防抖重绘图片背景；仅当图片背景模式开启且画布已存在"""
        if not self._image_mode or self._bg_canvas is None:
            return
        if getattr(event, "widget", None) is not self.root:
            return
        if self._resize_job is not None:
            try:
                self.root.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.root.after(150, self._render_imagebg)

    def _on_imagebg_toggle(self, checked):
        """实验性功能开关：开启则切换到图片背景模式，关闭则还原"""
        if not _HAVE_PIL:
            messagebox.showwarning(tr("hint"), tr("msg_need_pillow") or
                                   "图片背景功能需要 Pillow，请先安装：pip install pillow")
            self.imagebg_switch.deselect()
            return
        if self._running:
            self.imagebg_switch.select() if checked else self.imagebg_switch.deselect()
            messagebox.showinfo(tr("hint"), tr("msg_busy"))
            return
        if checked and not self._image_path:
            self._on_imagebg_pick()
            if not self._image_path:
                # 用户放弃选择：自动生成默认渐变背景，保证特性开箱即用
                self._image_path = ""
        self._image_mode = bool(checked)
        self.config.set("ui", "image_mode", self._image_mode)
        self.config.save()
        # 开启时忽略主题色（强制浅色基座）并重建界面；关闭时恢复主题色
        if self._image_mode:
            self.theme = "light"
            set_theme_name("light")
            self._theme = get_theme()
        else:
            self.theme = self.config.get("ui", "theme", "light")
            if self.theme not in theme_names():
                self.theme = "light"
            set_theme_name(self.theme)
            self._theme = get_theme()
        self.root.after(0, self._apply_settings)

    def _on_imagebg_pick(self):
        """选择背景图片文件"""
        p = filedialog.askopenfilename(
            title=tr("select_file"),
            filetypes=[("Image", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All", "*.*")]
        )
        if p:
            self._image_path = p
            self.config.set("ui", "image_path", p)
            self.config.save()
            if self._image_mode and self._bg_canvas is not None:
                self._render_imagebg()

    # ── 模糊值设置（滑杆 + 数值输入，0-50）────────────────────────────

    def _on_wall_blur_change(self, value):
        """壁纸模糊滑杆"""
        self._image_blur = max(0, min(50, int(value)))
        self.config.set("ui", "image_blur", self._image_blur)
        self.config.save()
        self._sync_blur_entry("wall")
        if self._image_mode:
            self._schedule_render()

    def _on_panel_blur_change(self, value):
        """面板模糊滑杆（0 为完全透明）"""
        self._panel_blur = max(0, min(50, int(value)))
        self.config.set("ui", "panel_blur", self._panel_blur)
        self.config.save()
        self._sync_blur_entry("panel")
        if self._image_mode:
            self._schedule_render()

    def _on_blur_entry(self, which):
        """数值输入框提交（Return / 失焦），非法输入回退为当前值"""
        e = getattr(self, f"{which}_blur_entry", None)
        if e is None or not e.winfo_exists():
            return
        try:
            v = int(e.get().strip())
        except ValueError:
            self._sync_blur_entry(which)
            return
        v = max(0, min(50, v))
        if which == "wall":
            self._image_blur = v
            self.config.set("ui", "image_blur", v)
        else:
            self._panel_blur = v
            self.config.set("ui", "panel_blur", v)
        self.config.save()
        s = getattr(self, f"{which}_blur_slider", None)
        if s is not None:
            s.set(v)
        self._sync_blur_entry(which)
        if self._image_mode:
            self._schedule_render()

    def _sync_blur_entry(self, which):
        """让输入框显示当前值"""
        e = getattr(self, f"{which}_blur_entry", None)
        if e is None or not e.winfo_exists():
            return
        v = self._image_blur if which == "wall" else self._panel_blur
        e.delete(0, "end")
        e.insert(0, str(v))

    def _schedule_render(self):
        """防抖重渲染（滑杆拖动时避免每步全量高斯模糊）"""
        if self._render_job is not None:
            try:
                self.root.after_cancel(self._render_job)
            except Exception:
                pass
        self._render_job = self.root.after(120, self._render_imagebg)

    def _load_bg_source(self):
        """加载背景图片源（PIL Image）或生成默认渐变。返回 (w, h, RGBA Image)"""
        path = self._image_path
        if path and os.path.isfile(path):
            try:
                img = PILImage.open(path).convert("RGB")
                return img
            except Exception:
                pass
        # 默认渐变背景（无网络依赖），深灰到浅灰的横向缓变
        W, H = 1920, 1080
        img = PILImage.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)
        for x in range(W):
            t = x / W
            c = tuple(int(0x14 + (0xF0 - 0x14) * t)
                      for _ in range(3))
            draw.line([(x, 0), (x, H)], fill=c)
        return img

    @staticmethod
    def _cover_resize(src, tw, th):
        """cover 等比裁剪缩放，返回 (Image, offset_x, offset_y)"""
        sw, sh = src.size
        scale = max(tw / sw, th / sh)
        nw, nh = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
        img = src.resize((nw, nh), PILImage.LANCZOS)
        ox, oy = (nw - tw) // 2, (nh - th) // 2
        return img, ox, oy

    def _new_panel(self, parent):
        """结构性容器工厂：普通模式返回 CTkFrame；图片模式返回注册的毛玻璃画布，
        由 _render_imagebg 在其上绘制壁纸对应区域的模糊裁剪"""
        if self._image_mode and _HAVE_PIL:
            c = tk.Canvas(parent, highlightthickness=0, bd=0)
            self._glass_canvases.append(c)
            return c
        return ctk.CTkFrame(parent, fg_color=self._theme.BG_MAIN, corner_radius=0)

    def _apply_imagebg_layout(self):
        """开启图片背景：创建底层壁纸画布、面板四周留边，然后整体渲染。
        面板本身已是毛玻璃画布（见 _new_panel / _build_sidebar_canvas）。"""
        if not _HAVE_PIL or not self._image_mode:
            return
        try:
            if self._bg_canvas is None or not self._bg_canvas.winfo_exists():
                canvas = tk.Canvas(self.root, highlightthickness=0, bd=0)
                canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
                # tk.Canvas 的 lower() 是画布条目操作，须用底层 Tk 命令降层
                self.root.tk.call('lower', canvas._w)
                self._bg_canvas = canvas
            # 面板四周留边，露出壁纸
            self.sidebar.grid_configure(padx=(12, 0), pady=12)
            self.main.grid_configure(padx=12, pady=12)
            self._render_imagebg()
        except Exception as e:
            if not self.root.winfo_exists():
                return
            print(f"图片背景布局异常: {e}")

    def _tint_rules(self):
        # 需要替换的实体色 -> (方向, 系数)：light 向白混合、dark 向黑压暗
        return {
            self._theme.BG_CARD: ("light", 0.52),    # 卡片：磨砂白玻璃
            self._theme.INPUT_BG: ("light", 0.60),   # 输入框/下拉框：更亮保证深色文字可读
            self._theme.OUT_BG: ("dark", 0.55),      # 日志框：深色玻璃配浅色文字
            self._theme.PROG_TRACK: ("light", 0.35), # 进度条轨道
        }

    def _collect_tint_targets(self):
        """扫描控件树，把需要用到的实体色控件登记到 _tint_map（id -> (widget, key)）。
        已登记控件跳过 cget；仅在控件树变化时才有开销。返回新增数量。"""
        rules = self._tint_rules()
        added = 0

        def walk(w):
            for ch in w.winfo_children():
                yield ch
                yield from walk(ch)

        for w in walk(self.root):
            wid = id(w)
            if wid in self._tint_map:
                continue
            try:
                fg = w.cget("fg_color")
            except Exception:
                continue
            bases = fg if isinstance(fg, (tuple, list)) else (fg,)
            for b in bases:
                if isinstance(b, str) and b in rules:
                    self._tint_map[wid] = (w, b)
                    added += 1
                    break
        return added

    def _sample_tint(self, widget, key, cover, pad=12):
        """对单个控件取色伪透明，返回是否成功（未映射/尺寸过小则 False）"""
        rules = self._tint_rules()
        mode, t = rules[key]
        cw, chh = cover.size
        try:
            if not widget.winfo_ismapped():
                return False
            x = widget.winfo_rootx() - self._root_x
            y = widget.winfo_rooty() - self._root_y
            w = widget.winfo_width()
            h = widget.winfo_height()
            x = max(0, min(x - pad, cw - 2))
            y = max(0, min(y - pad, chh - 2))
            w = min(w + pad * 2, cw - x)
            h = min(h + pad * 2, chh - y)
            if w < 2 or h < 2:
                return False
            avg = cover.crop((x, y, x + w, y + h)).resize(
                (1, 1), PILImage.LANCZOS).getpixel((0, 0))[:3]
            if mode == "light":
                px = tuple(int(v + (255 - v) * t) for v in avg)
            else:
                px = tuple(int(v * t) for v in avg)
            widget.configure(fg_color="#%02x%02x%02x" % px)
            return True
        except Exception:
            return False

    def _do_tint(self):
        """实体色控件"取色伪透明"：把卡片/输入框/日志框等融入毛玻璃背景。
        CTk 控件不支持真透明，以所在位置壁纸取样色作底色折中实现。
        - 只登记一次控件集合（_collect_tint_targets），之后仅对缓存取样，不做全量 cget；
        - 用 _tint_pending 防重入，避免反复重渲染（配合 update_idletasks 只补染一次）。"""
        if not _HAVE_PIL or not self._image_mode:
            self._tint_pending = False
            self._tint_retries = 0
            return
        cover = self._cover_cache
        if cover is None:
            self._tint_pending = False
            return
        try:
            self.root.update_idletasks()   # 布局稳定后再取色，减少空跑
            self._root_x = self.root.winfo_rootx()
            self._root_y = self.root.winfo_rooty()
            self._collect_tint_targets()   # 增量登记新控件（懒加载页面）
            pending = 0
            for _id, (w, key) in list(self._tint_map.items()):
                try:
                    if not self._sample_tint(w, key, cover):
                        pending += 1
                except Exception:
                    pending += 1
            self._tint_pending = False
            # 布局未映射的控件，用 idle 补一次（不再整窗重渲染）
            if pending and self._tint_retries < 3:
                self._tint_retries += 1
                self.root.after_idle(self._do_tint)
            else:
                self._tint_retries = 0
        except Exception as e:
            self._tint_pending = False
            print(f"取色伪透明异常: {e}")

    def _schedule_tint(self):
        """安排一次取色伪透明（防重入，不触发整窗重渲染）"""
        if self._tint_pending or not (self._image_mode and _HAVE_PIL):
            return
        self._tint_pending = True
        self.root.after_idle(self._do_tint)

    def _render_imagebg(self):
        """渲染两层：
        1) 底层画布：整窗壁纸（壁纸模糊 + 轻微压暗），仅窗口边缘露出；
        2) 毛玻璃画布：各面板区域壁纸清晰裁剪 -> 面板模糊 + 随模糊度轻微加深。
        面板上的文字均为画布文本项或上层控件，始终清晰、不受模糊影响。
        取色伪透明不再内嵌于此（独立 _schedule_tint），避免拖动滑块时全量重染。"""
        if not _HAVE_PIL or not self._image_mode:
            return
        cw = self.root.winfo_width()
        ch = self.root.winfo_height()
        if cw <= 10 or ch <= 10:
            return
        try:
            src = self._load_bg_source()
            cover, ox, oy = self._cover_resize(src, cw, ch)
            cover = cover.crop((ox, oy, ox + cw, oy + ch))  # 整窗清晰壁纸
            # 缓存清晰壁纸供取色伪透明复用，尺寸不变则不重算
            if self._cover_cache is None or self._cover_cache.size != cover.size:
                self._cover_cache = cover

            # 1) 底层壁纸
            wp = cover
            if self._image_blur > 0:
                wp = wp.filter(ImageFilter.GaussianBlur(self._image_blur))
            wp = PILImage.eval(wp, lambda v: int(v * 0.88))
            self._bg_photo = ImageTk.PhotoImage(wp)
            if self._bg_canvas is not None and self._bg_canvas.winfo_exists():
                if self._bg_item is None:
                    self._bg_item = self._bg_canvas.create_image(
                        0, 0, image=self._bg_photo, anchor="nw")
                else:
                    self._bg_canvas.itemconfig(self._bg_item, image=self._bg_photo)

            # 2) 毛玻璃面板
            veil = min(0.35, self._panel_blur / 50 * 0.35)
            root_x = self.root.winfo_rootx()
            root_y = self.root.winfo_rooty()
            for c in self._glass_canvases:
                try:
                    if not c.winfo_exists():
                        continue
                    w, h = c.winfo_width(), c.winfo_height()
                    if w < 10 or h < 10:
                        continue
                    x = c.winfo_rootx() - root_x
                    y = c.winfo_rooty() - root_y
                    x = max(0, min(x, cw - 1))
                    y = max(0, min(y, ch - 1))
                    w = min(w, cw - x)
                    h = min(h, ch - y)
                    if w < 10 or h < 10:
                        continue
                    region = cover.crop((x, y, x + w, y + h))
                    if self._panel_blur > 0:
                        region = region.filter(
                            ImageFilter.GaussianBlur(self._panel_blur))
                        if veil > 0:
                            region = PILImage.blend(
                                region,
                                PILImage.new("RGB", region.size, (16, 16, 16)),
                                veil)
                    # 平均色作为画布底色：透明 CTk 子控件会解析为该色，
                    # 视觉上接近重度磨砂，不会突兀
                    avg = region.resize((1, 1), PILImage.LANCZOS).getpixel((0, 0))
                    try:
                        c.configure(bg="#%02x%02x%02x" % avg[:3])
                    except Exception:
                        pass
                    photo = ImageTk.PhotoImage(region)
                    if str(c) in self._glass_photos:
                        self._glass_photos[str(c)] = photo  # 复用引用槽
                    else:
                        self._glass_photos[str(c)] = photo
                    c.delete("glassbg")
                    c.create_image(0, 0, image=photo, anchor="nw",
                                   tags=("glassbg",))
                    c.tag_lower("glassbg")
                except Exception:
                    continue

            # 侧栏版本文字贴底
            if self._ver_item is not None and self.sidebar.winfo_exists():
                try:
                    self.sidebar.coords(self._ver_item, 18,
                                        self.sidebar.winfo_height() - 24)
                except Exception:
                    pass

            # 取色伪透明独立调度（不阻塞、不重复整窗重渲染）
            self._schedule_tint()
        except Exception as e:
            print(f"壁纸渲染异常: {e}")

    # ── 构建 UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        # 主容器
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # ── 侧栏 ──
        self._build_sidebar()

        # ── 内容区 ──
        main = self._new_panel(self.root)
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)
        self.main = main

        self.content = self._new_panel(main)
        self.content.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=0)
        self.content.rowconfigure(1, weight=1)

        # 页面容器（不同模式切换）
        self.page_frame = self._new_panel(self.content)
        self.page_frame.grid(row=0, column=0, sticky="nsew")
        self.page_frame.columnconfigure(0, weight=1)
        self.page_frame.rowconfigure(0, weight=1)

        # 输出区域
        self._build_output()

    def _build_sidebar(self):
        # 图片背景模式：侧栏为毛玻璃画布 + 画布文本项（文字不受模糊影响）
        if self._image_mode and _HAVE_PIL:
            self._build_sidebar_canvas()
            return

        sidebar = ctk.CTkFrame(self.root, fg_color=self._theme.BG_SIDEBAR, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.columnconfigure(0, weight=1)

        # 标题区域
        head = ctk.CTkFrame(sidebar, fg_color=self._theme.BG_SIDEBAR, corner_radius=0)
        self.sidebar = sidebar
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(22, 16))
        title = ctk.CTkLabel(
            head, text="FileEncryptor",
            font=(FONT_FAMILY, 14, "bold"),
            text_color=self._theme.TEXT_LIGHT, anchor="w"
        )
        title.pack(fill="x")
        subtitle = ctk.CTkLabel(
            head, text=tr("app_subtitle"),
            font=(FONT_FAMILY, 9),
            text_color=self._theme.TEXT_MUTED, anchor="w"
        )
        subtitle.pack(fill="x", pady=(2, 0))

        # 导航按钮
        self.nav_btns = {}
        nav_items = [
            ("encrypt",   "\U0001F512  " + tr("nav_encrypt")),
            ("decrypt",   "\U0001F513  " + tr("nav_decrypt")),
            ("batch_enc", "\u25C9  " + tr("nav_batch_enc")),
            ("batch_dec", "\u25CB  " + tr("nav_batch_dec")),
            ("settings",  "\u2699  " + tr("nav_settings")),
        ]

        for i, (mode, label) in enumerate(nav_items, start=1):
            btn = ctk.CTkLabel(
                sidebar, text=label, font=FONT,
                text_color=self._theme.NAV_INACTIVE, cursor="hand2",
                anchor="w",
            )
            btn.grid(row=i, column=0, sticky="ew", padx=18, pady=4)
            btn.bind("<Button-1>", lambda e, m=mode: self._switch_mode(m))
            self.nav_btns[mode] = btn

        # 弹性空间（放在所有按钮之后，即第6行）
        spacer = ctk.CTkFrame(sidebar, fg_color=self._theme.BG_SIDEBAR, corner_radius=0)
        spacer.grid(row=6, column=0, sticky="ew")
        sidebar.rowconfigure(6, weight=1)

        # 底部版本信息
        ver_frame = ctk.CTkFrame(sidebar, fg_color=self._theme.BG_SIDEBAR, corner_radius=0)
        ver_frame.grid(row=10, column=0, sticky="ew")
        ver = ctk.CTkLabel(
            ver_frame, text="v1.4.1 \u00b7 libsodium",
            font=(FONT_FAMILY, 8), text_color=self._theme.VER_TEXT,
            anchor="w", padx=18, pady=12,
        )
        ver.pack(fill="x")

    def _build_sidebar_canvas(self):
        """图片背景模式：侧栏为毛玻璃画布。
        标题/导航/版本均为画布文本项，绘制在模糊背景之上，始终清晰。"""
        sb = tk.Canvas(self.root, width=196, highlightthickness=0, bd=0)
        sb.grid(row=0, column=0, sticky="ns")
        self.sidebar = sb
        self._glass_canvases.append(sb)

        sb.create_text(
            18, 30, text="FileEncryptor", anchor="w",
            font=(FONT_FAMILY, 14, "bold"), fill=self._theme.TEXT_LIGHT)
        sb.create_text(
            18, 50, text=tr("app_subtitle"), anchor="w",
            font=(FONT_FAMILY, 9), fill=self._theme.TEXT_MUTED)

        nav_items = [
            ("encrypt",   "\U0001F512  " + tr("nav_encrypt")),
            ("decrypt",   "\U0001F513  " + tr("nav_decrypt")),
            ("batch_enc", "\u25C9  " + tr("nav_batch_enc")),
            ("batch_dec", "\u25CB  " + tr("nav_batch_dec")),
            ("settings",  "\u2699  " + tr("nav_settings")),
        ]
        self._nav_items = {}
        y = 92
        for mode, label in nav_items:
            tag = f"nav:{mode}"
            item = sb.create_text(
                18, y, text=label, anchor="w",
                font=FONT, fill=self._theme.NAV_INACTIVE, tags=(tag,))
            self._nav_items[mode] = item
            sb.tag_bind(tag, "<Enter>", lambda e, m=mode: self._nav_hover(m, True))
            sb.tag_bind(tag, "<Leave>", lambda e, m=mode: self._nav_hover(m, False))
            sb.tag_bind(tag, "<Button-1>", lambda e, m=mode: self._switch_mode(m))
            y += 34

        self._ver_item = sb.create_text(
            18, 80, text="v2.0.0 \u00b7 libsodium",
            anchor="w", font=(FONT_FAMILY, 8), fill=self._theme.VER_TEXT)
        self._update_nav_canvas()

    def _nav_hover(self, mode, enter):
        """导航项悬停（画布文本项填色）"""
        if mode == self._current_mode:
            return
        try:
            self.sidebar.itemconfig(
                self._nav_items[mode],
                fill=self._theme.NAV_HOVER if enter else self._theme.NAV_INACTIVE)
        except Exception:
            pass

    def _update_nav_canvas(self):
        """导航高亮更新（图片背景模式的画布文本项）"""
        for m, item in self._nav_items.items():
            try:
                fill = self._theme.NAV_ACTIVE if m == self._current_mode else self._theme.NAV_INACTIVE
                self.sidebar.itemconfig(item, fill=fill)
            except Exception:
                pass

    def _build_output(self):
        """输出日志区域（含进度条）"""
        out_frame = self._new_panel(self.content)
        out_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        out_frame.columnconfigure(0, weight=1)
        out_frame.rowconfigure(0, weight=0)
        out_frame.rowconfigure(1, weight=0)
        out_frame.rowconfigure(2, weight=1)
        self.output_region = out_frame

        # 图片模式下小容器透明，透出毛玻璃画布底色（取自壁纸平均色）
        _fg = "transparent" if self._image_mode else self._theme.BG_MAIN

        # 进度条
        prog_frame = ctk.CTkFrame(out_frame, fg_color=_fg, corner_radius=0)
        prog_frame.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        self._progress_label = ctk.CTkLabel(
            prog_frame, text="", font=FONT_SM,
            text_color=self._theme.TEXT_MUTED, anchor="w", width=10,
        )
        self._progress_label.pack(side="left")

        self._progress_bar = ctk.CTkProgressBar(
            prog_frame, width=200, height=6,
            fg_color=self._theme.PROG_TRACK,
            progress_color=self._theme.ACCENT,
        )
        self._progress_bar.pack(side="left", fill="x", expand=True)
        self._progress_bar.set(0)

        self._progress_pct = ctk.CTkLabel(
            prog_frame, text="", font=FONT_SM,
            text_color=self._theme.TEXT_MUTED, anchor="e", width=4,
        )
        self._progress_pct.pack(side="right", padx=(4, 0))

        # 标题行
        head_row = ctk.CTkFrame(out_frame, fg_color=_fg, corner_radius=0)
        head_row.grid(row=1, column=0, sticky="ew")
        ctk.CTkLabel(
            head_row, text="\u25b6 " + tr("log_title"),
            font=FONT_SM, text_color=self._theme.TEXT_MUTED
        ).pack(side="left")

        export_btn = ctk.CTkLabel(
            head_row, text="\u2193 " + tr("export"), font=FONT_SM,
            text_color=self._theme.TEXT_MUTED, cursor="hand2", padx=8,
        )
        export_btn.pack(side="right", padx=(0, 8))
        export_btn.bind("<Button-1>", lambda e: self._export_log())
        export_btn.bind("<Enter>", lambda e: export_btn.configure(text_color=self._theme.ACCENT))
        export_btn.bind("<Leave>", lambda e: export_btn.configure(text_color=self._theme.TEXT_MUTED))

        self.clear_out_btn = ctk.CTkLabel(
            head_row, text="\u00d7 " + tr("clear"), font=FONT_SM,
            text_color=self._theme.TEXT_MUTED, cursor="hand2",
        )
        self.clear_out_btn.pack(side="right")
        self.clear_out_btn.bind("<Button-1>", lambda e: self._clear_output())
        self.clear_out_btn.bind("<Enter>", lambda e: self.clear_out_btn.configure(text_color=self._theme.ERROR))
        self.clear_out_btn.bind("<Leave>", lambda e: self.clear_out_btn.configure(text_color=self._theme.TEXT_MUTED))

        # 日志文本框
        self.output_text = ctk.CTkTextbox(
            out_frame, font=FONT_MONO, text_color="#c0c0c0", fg_color=self._theme.OUT_BG,
            border_width=1, border_color=self._theme.BORDER,
            wrap="word", state="disabled",
            corner_radius=4,
        )
        self.output_text.grid(row=2, column=0, sticky="nsew")

        # 状态栏
        self.status_bar = ctk.CTkLabel(
            out_frame, text=tr("ready"), font=FONT_SM,
            text_color=self._theme.TEXT_MUTED, anchor="w",
        )
        self.status_bar.grid(row=3, column=0, sticky="ew", pady=(4, 0))

    # ── 页面切换 ───────────────────────────────────────────────────────

    def _switch_mode(self, mode):
        self._current_mode = mode

        # 更新导航高亮（图片模式为画布文本项，普通模式为标签）
        if self._image_mode and self._nav_items:
            self._update_nav_canvas()
        else:
            for m, btn in self.nav_btns.items():
                is_active = m == mode
                btn.configure(text_color=self._theme.NAV_ACTIVE if is_active else self._theme.NAV_INACTIVE)
                for seq in ("<Enter>", "<Leave>"):
                    try:
                        btn.unbind(seq)
                    except Exception:
                        pass
                if not is_active:
                    btn.bind("<Enter>", lambda e, b=btn: b.configure(text_color=self._theme.NAV_HOVER))
                    btn.bind("<Leave>", lambda e, b=btn: b.configure(text_color=self._theme.NAV_INACTIVE))

        # 设置页不显示日志/进度条区域，其余页面显示
        if getattr(self, "output_region", None) is not None:
            if mode == "settings":
                self.output_region.grid_remove()
            elif not self.output_region.winfo_ismapped():
                self.output_region.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        # 隐藏所有已创建的页面
        for page in self._pages.values():
            page.pack_forget()

        # 创建页面（如果尚未创建）或显示已缓存的页面
        if mode not in self._pages:
            page = build_page(mode, self, self.page_frame)
            if page is not None:
                self._pages[mode] = page

        self._pages[mode].pack(fill="both", expand=True)
        # 图片模式下，懒加载的新页面画布需要绘制毛玻璃背景
        if self._image_mode:
            self.root.after_idle(self._render_imagebg)

        self._set_status(tr("ready"))

    # ── 执行操作 ───────────────────────────────────────────────────────

    def _log(self, text):
        self.output_text.configure(state="normal")
        self.output_text.insert("end", text + "\n")
        self.output_text.see("end")
        self.output_text.configure(state="disabled")

    def _clear_output(self):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")

    def _export_log(self):
        self.output_text.configure(state="normal")
        log_content = self.output_text.get("1.0", "end").strip()
        self.output_text.configure(state="disabled")

        if not log_content:
            messagebox.showinfo(tr("hint"), tr("msg_log_empty"))
            return

        last_path = self.config.get("paths", "last_export_dir", "")

        file_path = filedialog.asksaveasfilename(
            title=tr("export"),
            defaultextension=".txt",
            initialdir=last_path if last_path else None,
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(log_content)
                export_dir = os.path.dirname(file_path)
                self.config.set("paths", "last_export_dir", export_dir)
                self.config.save()
                self._set_status(f"{tr('msg_log_exported')}: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror(tr("error"), f"{tr('msg_export_fail')}:\n{str(e)}")

    def _set_status(self, text):
        self.status_bar.configure(text=text)

    def _set_busy(self, busy):
        self._running = busy
        self.root.configure(cursor="watch" if busy else "")

    def _reset_progress(self):
        self._progress_bar.set(0)
        self._progress_pct.configure(text="")
        self._progress_label.configure(text="")

    def _set_progress(self, value, label=""):
        self._progress_bar.set(value / 100.0)
        self._progress_pct.configure(text=f"{value}%")
        if label:
            self._progress_label.configure(text=label)

    def _run_async_stream(self, args, desc="", password=None, password2=None,
                          timeout=600, overwrite=None, fallback=None):
        """在后台线程中流式运行并实时显示输出"""
        if self._running:
            self._log(f"[!] {tr('msg_busy')}")
            return

        self._set_busy(True)
        self._reset_progress()
        self._log("─" * 50)
        self._log(f"[>] {desc}")
        self._set_status(tr("running"))

        def run():
            exit_code = -1
            collected = []
            cancelled = False
            try:
                for line_text, progress, err in _engine_service.run(
                    args, password=password, password2=password2,
                    timeout=timeout, overwrite=overwrite, fallback=fallback
                ):
                    if line_text:
                        collected.append(line_text)
                        self.root.after(0, self._log, line_text)

                    if progress:
                        cur, total = progress
                        if total and total > 0:
                            pct = int(cur * 100 / total)
                            pct = max(0, min(100, pct))
                            label = f"{cur / 1048576.0:.1f}/{total / 1048576.0:.1f} MiB"
                            self.root.after(0, self._set_progress, pct, label)

                    if err:
                        if isinstance(err, int):
                            exit_code = err
                        else:
                            collected.append(f"[!] {err}")
                            self.root.after(0, self._log, f"[!] {err}")

                    # 取消后 exit_code 为 -1，不得覆盖为成功
                    if _engine_service.cancelled:
                        cancelled = True

                # 未取消失败（-1）时视为引擎无显式退出码 => 成功
                if exit_code == -1 and not cancelled:
                    exit_code = 0

            except Exception as e:
                exit_code = -1
                self.root.after(0, self._log, f"[!] 异常: {e}")

            self.root.after(0, self._on_stream_result, exit_code, collected, desc)

        threading.Thread(target=run, daemon=True).start()

    def _on_stream_result(self, exit_code, lines, desc):
        self._set_busy(False)

        self._set_progress(100, tr("done"))

        if exit_code == 0:
            self._log(f"[OK] {desc} {tr('done')}")
            self._set_status(tr("done"))
        else:
            self._log(f"[FAIL] {desc} {tr('failed')} (exit={exit_code})")
            self._set_status(tr("failed"))

        self._log("─" * 50)

        # 3 秒后自动清除进度条
        self.root.after(3000, self._reset_progress)

    # ── 加密执行 ───────────────────────────────────────────────────────

    def _show_errors(self, errs):
        """按校验结果展示首条错误（警告用 showerror / 提示用 showwarning）"""
        if not errs:
            return False
        sev, key = errs[0]
        if sev == "error":
            messagebox.showerror(tr("error"), tr(key))
        else:
            messagebox.showwarning(tr("hint"), tr(key))
        return True

    def _do_encrypt(self):
        src = self.enc_file.get().strip()
        pw = self.enc_pw.get()
        pw2 = self.enc_pw2.get()
        out = self.enc_out.get().strip()
        algo = self.enc_algo.get()
        delete = self.enc_del_var.get()

        if self._show_errors(validate_encrypt_inputs(src, pw, pw2)):
            return
        if (dir_err := ensure_output_dir(out)) and self._show_errors([dir_err]):
            return

        args = build_encrypt_args(src, out, algo, delete)

        self._run_async_stream(
            args,
            desc=f"{tr('start_encrypt')}: {os.path.basename(src)}",
            password=pw, password2=pw,
            timeout=600, overwrite="y", fallback="n",
        )

    # ── 解密执行 ───────────────────────────────────────────────────────

    def _do_decrypt(self):
        src = self.dec_file.get().strip()
        pw = self.dec_pw.get()
        out = self.dec_out.get().strip()

        if self._show_errors(validate_decrypt_inputs(src, pw)):
            return
        if (dir_err := ensure_output_dir(out)) and self._show_errors([dir_err]):
            return

        args = build_decrypt_args(src, out)

        self._run_async_stream(
            args,
            desc=f"{tr('start_decrypt')}: {os.path.basename(src)}",
            password=pw, timeout=600, overwrite="y",
        )

    # ── 批量加密 ───────────────────────────────────────────────────────

    def _do_batch_encrypt(self):
        src = self.benc_dir.get().strip()
        pw = self.benc_pw.get()
        pw2 = self.benc_pw2.get()
        out = self.benc_out.get().strip()
        algo = self.benc_algo.get()
        threads = self.benc_threads.get()
        delete = self.benc_del_var.get()

        if self._show_errors(validate_batch_encrypt_inputs(src, pw, pw2)):
            return
        if (dir_err := ensure_output_dir(out)) and self._show_errors([dir_err]):
            return

        args = build_batch_encrypt_args(src, out, algo, threads, delete)

        self._run_async_stream(
            args,
            desc=f"{tr('start_batch_enc')}: {os.path.basename(src)}",
            password=pw, password2=pw,
            timeout=1800, overwrite="y", fallback="n",
        )

    # ── 批量解密 ───────────────────────────────────────────────────────

    def _do_batch_decrypt(self):
        src = self.bdec_dir.get().strip()
        pw = self.bdec_pw.get()
        out = self.bdec_out.get().strip()
        threads = self.bdec_threads.get()

        if self._show_errors(validate_batch_decrypt_inputs(src, pw)):
            return
        if (dir_err := ensure_output_dir(out)) and self._show_errors([dir_err]):
            return

        args = build_batch_decrypt_args(src, out, threads)

        self._run_async_stream(
            args,
            desc=f"{tr('start_batch_dec')}: {os.path.basename(src)}",
            password=pw, timeout=1800, overwrite="y",
        )

    # ── 启动 ──────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


# ── 入口 ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 检查 tkinter 可用性
    try:
        root = tk.Tk()
        root.withdraw()
        root.destroy()
    except Exception as e:
        print(f"[ERROR] tkinter 不可用：{e}")
        print("请确保系统安装了 Python 的 tkinter 支持。")
        print("Windows: 重新安装 Python 时勾选 'tcl/tk and IDLE'")
        input("按 Enter 退出...")
        sys.exit(1)

    app = FileEncryptorGUI()
    app.run()