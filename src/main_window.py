import os
import sys
import time
import datetime
import threading
import customtkinter as ctk

from PIL import Image

try:
    import pystray
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

from src.config import load_config, save_config, BIN_DIR
from src.game_launcher import GameLaunchWorker, find_riot_client, emergency_cleanup, is_game_running
from src.stretch import (
    STRETCH_RESOLUTIONS, apply_stretch, revert_stretch, auto_revert_on_exit,
    get_native_resolution, is_resolution_supported, open_nvidia_control_panel
)
from src.nvidia_profile import apply_valorant_profile
from src.gpu_detect import detect_gpus, get_gpu_category

APP_VERSION = "4.0.0"
APP_NAME = "HiddenDisplay"


def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR = _get_base_dir()
BLOOD_DIR = os.path.join(BASE_DIR, 'blood')
DEFAULT_PAKS_DIR = r'C:\Riot Games\VALORANT\live\ShooterGame\Content\Paks'

# Colors
BLUE = "#3b82f6"
BLUE_HOVER = "#60a5fa"
GRAY_BTN = "#2a2a2a"
GRAY_HOVER = "#3a3a3a"
RED = "#ef4444"
GREEN = "#22c55e"
YELLOW = "#eab308"
DIM = "#666666"

# ── Translations ──
LANG = {
    'en': {
        'mods': 'MODS',
        'blood': 'Show Mature Content',
        'vng': 'Remove VNG Logo',
        'launch': 'LAUNCH',
        'play': 'PLAY VALORANT',
        'launching': 'LAUNCHING...',
        'riot_found': 'Riot Client found',
        'riot_not_found': 'Riot Client not found — click Browse to locate',
        'riot_browse': 'Browse',
        'log': 'LOG',
        'game_folder': 'GAME FOLDER',
        'browse': 'Browse',
        'auto_detected': 'Auto-detected',
        'custom_path': 'Custom path set',
        'path_not_found': 'Path not found',
        'no_mods': 'Launched VALORANT (no mods)',
        'error': 'Error',
        'riot_err': 'Riot Client not found.',
        'blood_err': 'Blood folder not found',
        'paks_err': 'Game Paks folder not found',
        'start_seq': 'Starting launch sequence...',
        'done': 'Done.',
        'developed_by': 'Developed by Chemg0d',
        'minimized': 'Minimized to tray.',
        'stretch': 'TRUE STRETCH',
        'resolution': 'Resolution',
        'apply_stretch': 'Apply Stretch',
        'revert_stretch': 'Revert',
        'stretch_hint': 'Modifies game config + sets read-only. Revert to undo.',
        'other': 'OTHER',
        'lod_preset': 'Graphic setting',
        'apply_nvidia': 'Apply',
        'nvidia_hint': 'Applies to VALORANT profile: Transparency Supersampling + LOD Bias.',
        'gpu_no_nvidia_title': 'NVIDIA GPU Required',
        'gpu_no_nvidia_msg': ('This tool only supports True Stretch and graphics-quality '
                              'features on NVIDIA GPUs. Your system uses:\n\n{names}\n\n'
                              'Those sections have been disabled.'),
        'gpu_hybrid_title': 'Hybrid GPU Detected',
        'gpu_hybrid_msg': ('Your device is running both GPUs:\n\n{names}\n\n'
                           'Please switch to dGPU mode, or disable the Intel/AMD GPU '
                           'in Device Manager > Display adapters, otherwise True Stretch '
                           'and NVIDIA profile changes may not apply correctly.'),
        'gpu_picker_title': 'GPU Mode',
        'gpu_picker_subtitle': 'Detected GPU(s):',
        'gpu_mode_auto': 'Auto-detect',
        'gpu_mode_nvidia_only': 'NVIDIA only',
        'gpu_mode_hybrid': 'Hybrid (NVIDIA + Intel/AMD)',
        'gpu_mode_non_nvidia': 'Non-NVIDIA (Intel/AMD only)',
        'gpu_picker_apply': 'Apply',
        'gpu_picker_cancel': 'Cancel',
        'gpu_picker_note': 'Manual override applies on next app start.',
        'risk_blood': 'Ban risk: Very Low — file added/restored, no modifications to existing game files',
        'risk_vng': 'Ban risk: Low — temporarily deletes logo file, auto-restored on game exit',
        'risk_stretch': 'Ban risk: None — only modifies user config files',
        'risk_nvidia': 'Ban risk: None — modifies NVIDIA driver settings only',
        'welcome_title': 'Welcome to HiddenDisplay',
        'welcome_thanks': 'Thank you for using our app!',
        'welcome_body': ('We know some users may worry about ban risk when using this tool. '
                         'That\'s why every feature now shows its own ban-risk label — '
                         'please review them and use with confidence.'),
        'welcome_follow': 'Follow us:',
        'welcome_close': 'Got it',
        'warning': 'USE AT YOUR OWN RISK',
        'disclaimer': 'We take no responsibility for anything that happens to your account while using this tool.',
    },
    'vi': {
        'mods': 'TINH CHỈNH',
        'blood': 'Nội dung dành cho người lớn',
        'vng': 'Xóa Logo VNG',
        'launch': 'KHỞI ĐỘNG',
        'play': 'CHƠI VALORANT',
        'launching': 'ĐANG KHỞI ĐỘNG...',
        'riot_found': 'Đã tìm thấy Riot Client',
        'riot_not_found': 'Không tìm thấy Riot Client — nhấn Chọn để tìm',
        'riot_browse': 'Chọn',
        'log': 'NHẬT KÝ',
        'game_folder': 'THƯ MỤC GAME',
        'browse': 'Chọn',
        'auto_detected': 'Tự động phát hiện',
        'custom_path': 'Đã đặt đường dẫn',
        'path_not_found': 'Không tìm thấy',
        'no_mods': 'Đã khởi động VALORANT (không mod)',
        'error': 'Lỗi',
        'riot_err': 'Không tìm thấy Riot Client.',
        'blood_err': 'Không tìm thấy thư mục blood',
        'paks_err': 'Không tìm thấy thư mục game',
        'start_seq': 'Bắt đầu trình khởi động...',
        'done': 'Xong.',
        'developed_by': 'Phát triển bởi Chemg0d',
        'minimized': 'Thu nhỏ xuống khay.',
        'stretch': 'TRUE STRETCH',
        'resolution': 'Độ phân giải',
        'apply_stretch': 'Áp dụng Stretch',
        'revert_stretch': 'Hoàn tác',
        'stretch_hint': 'Chỉnh sửa config game + đặt chỉ đọc. Nhấn Hoàn tác để khôi phục.',
        'other': 'KHÁC',
        'lod_preset': 'Graphic setting',
        'apply_nvidia': 'Áp dụng',
        'nvidia_hint': 'Áp dụng cho profile VALORANT: Transparency Supersampling + LOD Bias.',
        'gpu_no_nvidia_title': 'Yêu cầu GPU NVIDIA',
        'gpu_no_nvidia_msg': ('Công cụ chỉ hỗ trợ True Stretch và chỉnh chất lượng đồ họa '
                              'trên GPU NVIDIA. Hệ thống của bạn đang dùng:\n\n{names}\n\n'
                              'Các mục đó đã bị vô hiệu hóa.'),
        'gpu_hybrid_title': 'Phát hiện GPU Hybrid',
        'gpu_hybrid_msg': ('Thiết bị của bạn đang chạy cả hai GPU:\n\n{names}\n\n'
                           'Vui lòng chuyển sang chế độ dGPU, hoặc tắt GPU Intel/AMD '
                           'trong Device Manager > Display adapters, nếu không True Stretch '
                           'và thay đổi NVIDIA profile có thể không áp dụng đúng.'),
        'gpu_picker_title': 'Chế độ GPU',
        'gpu_picker_subtitle': 'GPU đã phát hiện:',
        'gpu_mode_auto': 'Tự động phát hiện',
        'gpu_mode_nvidia_only': 'Chỉ NVIDIA',
        'gpu_mode_hybrid': 'Hybrid (NVIDIA + Intel/AMD)',
        'gpu_mode_non_nvidia': 'Không phải NVIDIA (Intel/AMD)',
        'gpu_picker_apply': 'Áp dụng',
        'gpu_picker_cancel': 'Hủy',
        'gpu_picker_note': 'Ghi đè thủ công sẽ có hiệu lực khi khởi động lại.',
        'risk_blood': 'Rủi ro ban: Rất thấp — chỉ thêm file, không chỉnh sửa file gốc của game',
        'risk_vng': 'Rủi ro ban: Thấp — tạm xóa file logo, tự khôi phục khi thoát game',
        'risk_stretch': 'Rủi ro ban: Không — chỉ chỉnh file config của người dùng',
        'risk_nvidia': 'Rủi ro ban: Không — chỉ chỉnh NVIDIA driver settings',
        'welcome_title': 'Chào mừng đến HiddenDisplay',
        'welcome_thanks': 'Cảm ơn bạn đã sử dụng ứng dụng của chúng tôi!',
        'welcome_body': ('Chúng tôi biết một số bạn có thể lo ngại về rủi ro ban khi dùng tool. '
                         'Vì vậy chúng tôi đã thêm nhãn rủi ro ban cho từng tính năng — '
                         'bạn hãy kiểm tra và sử dụng với sự yên tâm.'),
        'welcome_follow': 'Theo dõi chúng tôi:',
        'welcome_close': 'Đã hiểu',
        'warning': 'TỰ CHỊU RỦI RO KHI SỬ DỤNG',
        'disclaimer': 'Chúng tôi không chịu trách nhiệm với những gì xảy ra với tài khoản của bạn khi sử dụng.',
    },
}


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.lang = self.config.get('language', 'en')
        self.launch_worker = None
        self.stretch_active = False
        self.stretch_linked = False
        self.other_linked = False
        self.native_w, self.native_h = 0, 0
        self.tray_icon = None
        self._build_ui()
        # X button → hide to tray instead of closing
        self.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        # Setup tray icon in background thread
        if TRAY_AVAILABLE:
            threading.Thread(target=self._setup_tray, daemon=True).start()
        # First-run welcome popup
        self.after(200, self._maybe_show_welcome)
        # GPU detection + conditional disable/notify (runs after window is visible)
        self.after(500, self._apply_gpu_policy)

    def _setup_tray(self):
        """Create system tray icon with Show/Quit menu."""
        try:
            icon_path = os.path.join(BIN_DIR, 'icon.ico')
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
            else:
                # Fallback: small blue square
                image = Image.new('RGB', (64, 64), color='#3b82f6')

            menu = pystray.Menu(
                pystray.MenuItem("Show HiddenDisplay", self._show_from_tray, default=True),
                pystray.MenuItem("Quit", self._quit_from_tray),
            )
            self.tray_icon = pystray.Icon("HiddenDisplay", image, "HiddenDisplay", menu)
            self.tray_icon.run()
        except Exception:
            pass

    def _hide_to_tray(self):
        """Hide window to system tray instead of closing."""
        if TRAY_AVAILABLE and self.tray_icon:
            self.withdraw()
        else:
            # No tray available — just minimize
            self.iconify()

    def _show_from_tray(self, icon=None, item=None):
        """Restore window from tray."""
        self.after(0, self._do_show)

    def _do_show(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _quit_from_tray(self, icon=None, item=None):
        """Quit properly from tray menu — runs full cleanup."""
        self.after(0, self._real_quit)

    def _real_quit(self):
        """Actual quit — runs emergency cleanup + destroys window."""
        try:
            paks_dir = self._get_paks_dir()
            emergency_cleanup(paks_dir)
        except Exception:
            pass
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.destroy()

    def t(self, key):
        return LANG.get(self.lang, LANG['en']).get(key, key)

    def _apply_gpu_policy(self):
        """Detect GPU(s) and enable/disable stretch + other, show notifications.
        Manual override from config.gpu_override takes precedence over auto-detection."""
        self._detected_gpus = detect_gpus()
        override = self.config.get('gpu_override', 'auto')
        if override in ('nvidia_only', 'hybrid', 'non_nvidia'):
            category = override
            self._log(f"GPU mode (manual): {category}")
        else:
            category = get_gpu_category(self._detected_gpus)
        gpus = self._detected_gpus
        names_str = "\n".join("  - " + n for n in gpus['names']) or "  (none detected)"

        if category == 'non_nvidia':
            # Disable stretch and other sections entirely
            for widget in (self.stretch_btn, self.revert_btn, self.res_menu,
                           self.link_btn, self.custom_w_entry, self.custom_h_entry,
                           self.save_custom_btn,
                           self.apply_nvidia_btn, self.lod_menu, self.other_link_btn):
                try:
                    widget.configure(state="disabled")
                except Exception:
                    pass
            self._log(f"Non-NVIDIA GPU detected: {', '.join(gpus['names'])}")
            if not self.config.get('gpu_notif_no_nvidia_shown', False):
                self._show_info(self.t('gpu_no_nvidia_title'),
                                self.t('gpu_no_nvidia_msg').format(names=names_str))
                self.config['gpu_notif_no_nvidia_shown'] = True
                save_config(self.config)

        elif category == 'hybrid':
            self._log(f"Hybrid GPU setup: {', '.join(gpus['names'])}")
            if not self.config.get('gpu_notif_hybrid_shown', False):
                self._show_info(self.t('gpu_hybrid_title'),
                                self.t('gpu_hybrid_msg').format(names=names_str))
                self.config['gpu_notif_hybrid_shown'] = True
                save_config(self.config)

        elif category == 'nvidia_only':
            self._log(f"NVIDIA GPU detected: {', '.join(gpus['names'])}")

    def _maybe_show_welcome(self):
        """Show one-time welcome popup on first run."""
        if self.config.get('welcome_shown', False):
            return
        self._show_welcome_popup()
        self.config['welcome_shown'] = True
        save_config(self.config)

    def _show_welcome_popup(self):
        """Welcome popup shown in both EN and VI simultaneously."""
        import webbrowser

        en = LANG['en']
        vi = LANG['vi']

        popup = ctk.CTkToplevel(self)
        popup.title("Welcome / Chào mừng")
        popup.geometry("560x620")
        popup.configure(fg_color="#0d0d0d")
        popup.transient(self)
        popup.grab_set()
        popup.resizable(False, False)

        title = ctk.CTkLabel(popup, text=f"{en['welcome_title']}  /  {vi['welcome_title']}",
                              font=ctk.CTkFont(family="Segoe UI Semibold", size=16, weight="bold"),
                              text_color="#ffffff")
        title.pack(pady=(18, 4))

        warning = ctk.CTkLabel(popup,
                                text=f"{en['warning']}  /  {vi['warning']}",
                                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                                text_color=RED)
        warning.pack(pady=(0, 10))

        # English block
        en_thanks = ctk.CTkLabel(popup, text="[EN] " + en['welcome_thanks'],
                                  font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                  text_color=BLUE)
        en_thanks.pack(pady=(4, 2))
        en_body = ctk.CTkLabel(popup, text=en['welcome_body'],
                                font=ctk.CTkFont(family="Segoe UI", size=11),
                                text_color="#bbbbbb", justify="left", wraplength=500)
        en_body.pack(padx=24, pady=(0, 10))

        sep1 = ctk.CTkFrame(popup, fg_color="#2a2a2a", height=1)
        sep1.pack(fill="x", padx=24, pady=2)

        # Vietnamese block
        vi_thanks = ctk.CTkLabel(popup, text="[VI] " + vi['welcome_thanks'],
                                  font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                  text_color=BLUE)
        vi_thanks.pack(pady=(8, 2))
        vi_body = ctk.CTkLabel(popup, text=vi['welcome_body'],
                                font=ctk.CTkFont(family="Segoe UI", size=11),
                                text_color="#bbbbbb", justify="left", wraplength=500)
        vi_body.pack(padx=24, pady=(0, 12))

        sep2 = ctk.CTkFrame(popup, fg_color="#2a2a2a", height=1)
        sep2.pack(fill="x", padx=24, pady=4)

        follow = ctk.CTkLabel(popup,
                               text=f"{en['welcome_follow']}  /  {vi['welcome_follow']}",
                               font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                               text_color="#ffffff")
        follow.pack(pady=(8, 4))

        links = [
            ("Discord",  "https://discord.com/invite/qyazsuHkk5"),
            ("YouTube",  "https://www.youtube.com/@Longl%C3%A0Chem?sub_confirmation=1"),
            ("TikTok",   "https://www.tiktok.com/@longtenlalongchem"),
            ("TikTok 2", "https://www.tiktok.com/@longlachem"),
        ]
        for name, url in links:
            link = ctk.CTkLabel(popup, text=f"  {name}:  {url}",
                                 font=ctk.CTkFont(family="Segoe UI", size=10, underline=True),
                                 text_color=BLUE, cursor="hand2")
            link.pack(anchor="w", padx=30, pady=1)
            link.bind("<Button-1>", lambda _e, u=url: webbrowser.open(u))

        close_btn = ctk.CTkButton(popup,
                                    text=f"{en['welcome_close']}  /  {vi['welcome_close']}",
                                    width=180, height=34,
                                    fg_color=BLUE, hover_color=BLUE_HOVER,
                                    font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                    command=popup.destroy)
        close_btn.pack(pady=(14, 16))

    def _open_gpu_picker(self):
        """Popup dialog to manually choose GPU mode."""
        popup = ctk.CTkToplevel(self)
        popup.title(self.t('gpu_picker_title'))
        popup.geometry("440x360")
        popup.configure(fg_color="#0d0d0d")
        popup.transient(self)
        popup.grab_set()
        popup.resizable(False, False)

        title = ctk.CTkLabel(popup, text=self.t('gpu_picker_title'),
                              font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                              text_color="#ffffff")
        title.pack(pady=(20, 4))

        detected = getattr(self, '_detected_gpus', None) or detect_gpus()
        names_str = "\n".join(detected['names']) or "(none detected)"
        subtitle = ctk.CTkLabel(popup, text=self.t('gpu_picker_subtitle'),
                                 font=ctk.CTkFont(family="Segoe UI", size=10),
                                 text_color=DIM)
        subtitle.pack(pady=(6, 0))
        names_label = ctk.CTkLabel(popup, text=names_str,
                                    font=ctk.CTkFont(family="Segoe UI", size=11),
                                    text_color="#bbbbbb", justify="left")
        names_label.pack(pady=(0, 10))

        import tkinter as tk
        mode_var = tk.StringVar(value=self.config.get('gpu_override', 'auto'))

        options = [
            ('auto',         self.t('gpu_mode_auto')),
            ('nvidia_only',  self.t('gpu_mode_nvidia_only')),
            ('hybrid',       self.t('gpu_mode_hybrid')),
            ('non_nvidia',   self.t('gpu_mode_non_nvidia')),
        ]
        for val, label in options:
            rb = ctk.CTkRadioButton(popup, text=label, variable=mode_var, value=val,
                                     font=ctk.CTkFont(family="Segoe UI", size=11),
                                     fg_color=BLUE, hover_color=BLUE_HOVER)
            rb.pack(anchor="w", padx=40, pady=2)

        note = ctk.CTkLabel(popup, text=self.t('gpu_picker_note'),
                             font=ctk.CTkFont(family="Segoe UI", size=9),
                             text_color=DIM)
        note.pack(pady=(10, 6))

        btn_row = ctk.CTkFrame(popup, fg_color="transparent")
        btn_row.pack(pady=(0, 16))

        def apply_choice():
            self.config['gpu_override'] = mode_var.get()
            save_config(self.config)
            self._log(f"GPU override saved: {mode_var.get()}")
            popup.destroy()

        apply_btn = ctk.CTkButton(btn_row, text=self.t('gpu_picker_apply'),
                                   width=100, height=32,
                                   fg_color=BLUE, hover_color=BLUE_HOVER,
                                   font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                   command=apply_choice)
        apply_btn.pack(side="left", padx=6)

        cancel_btn = ctk.CTkButton(btn_row, text=self.t('gpu_picker_cancel'),
                                    width=100, height=32,
                                    fg_color=GRAY_BTN, hover_color=GRAY_HOVER,
                                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                    command=popup.destroy)
        cancel_btn.pack(side="left", padx=6)

    def _resolve_paks_dir(self, base_path):
        for sub in ('live/ShooterGame/Content/Paks', 'ShooterGame/Content/Paks'):
            p = os.path.join(base_path, sub)
            if os.path.exists(p):
                return p
        return None

    def _get_paks_dir(self):
        custom = self.config.get('game_path', '')
        if custom and os.path.exists(custom):
            paks = self._resolve_paks_dir(custom)
            if paks:
                return paks
        if os.path.exists(DEFAULT_PAKS_DIR):
            return DEFAULT_PAKS_DIR
        return None

    def _build_ui(self):
        # Window config
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title(APP_NAME)
        self.geometry("520x820")
        self.minsize(480, 700)
        self.configure(fg_color="#0d0d0d")

        icon_path = os.path.join(BIN_DIR, 'icon.ico')
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # Scrollable frame for content
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#0d0d0d", scrollbar_button_color="#2a2a2a")
        self.scroll.pack(fill="both", expand=True, padx=0, pady=0)
        container = self.scroll

        # ── Header ──
        header_frame = ctk.CTkFrame(container, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(16, 0))

        # Spacer left
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=0)
        header_frame.grid_columnconfigure(2, weight=0)
        header_frame.grid_columnconfigure(3, weight=0)

        title = ctk.CTkLabel(header_frame, text=APP_NAME,
                              font=ctk.CTkFont(family="Segoe UI Semibold", size=24, weight="bold"))
        title.grid(row=0, column=0, sticky="w")

        self.gpu_btn = ctk.CTkButton(
            header_frame, text="GPU", width=50, height=28,
            fg_color=GRAY_BTN, hover_color=GRAY_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._open_gpu_picker
        )
        self.gpu_btn.grid(row=0, column=1, sticky="e", padx=(0, 6))

        self.lang_menu = ctk.CTkOptionMenu(
            header_frame, values=["EN", "VI"],
            width=60, height=28,
            fg_color=GRAY_BTN, button_color=GRAY_BTN,
            button_hover_color=GRAY_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._change_language
        )
        self.lang_menu.set("VI" if self.lang == 'vi' else "EN")
        self.lang_menu.grid(row=0, column=3, sticky="e")

        self.dev_label = ctk.CTkLabel(container, text=self.t('developed_by'),
                                       text_color=DIM, font=ctk.CTkFont(family="Segoe UI", size=11))
        self.dev_label.pack(padx=20, anchor="w", pady=(0, 2))

        self.warning_label = ctk.CTkLabel(container, text="⚠  " + self.t('warning'),
                                           text_color=RED,
                                           font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"))
        self.warning_label.pack(padx=20, anchor="w", pady=(0, 8))

        # ── Game Folder ──
        self.folder_label = ctk.CTkLabel(container, text=self.t('game_folder'),
                                          font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.folder_label.pack(padx=20, anchor="w", pady=(8, 4))

        folder_frame = ctk.CTkFrame(container, fg_color="#1a1a1a", corner_radius=8)
        folder_frame.pack(fill="x", padx=20, pady=(0, 2))

        self.path_entry = ctk.CTkEntry(folder_frame, placeholder_text=r"C:\Riot Games\VALORANT",
                                        border_width=0, fg_color="#111111", height=36)
        saved_path = self.config.get('game_path', '')
        if saved_path:
            self.path_entry.insert(0, saved_path)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)

        self.browse_btn = ctk.CTkButton(folder_frame, text=self.t('browse'), width=70, height=32,
                                         fg_color=GRAY_BTN, hover_color=GRAY_HOVER,
                                         font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                         command=self._browse_folder)
        self.browse_btn.pack(side="right", padx=(0, 8), pady=8)

        self.path_status = ctk.CTkLabel(container, text="", font=ctk.CTkFont(family="Segoe UI", size=10))
        self.path_status.pack(padx=24, anchor="w", pady=(0, 6))
        self._update_path_status()

        # ── Mods ──
        self.mods_label = ctk.CTkLabel(container, text=self.t('mods'),
                                        font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.mods_label.pack(padx=20, anchor="w", pady=(8, 4))

        mods_frame = ctk.CTkFrame(container, fg_color="#1a1a1a", corner_radius=8)
        mods_frame.pack(fill="x", padx=20, pady=(0, 6))

        self.chk_blood = ctk.CTkCheckBox(mods_frame, text=self.t('blood'),
                                          font=ctk.CTkFont(family="Segoe UI", size=13),
                                          checkbox_width=22, checkbox_height=22, corner_radius=4,
                                          fg_color=BLUE, hover_color=BLUE_HOVER)
        if self.config.get('enable_blood', True):
            self.chk_blood.select()
        self.chk_blood.pack(padx=16, pady=(12, 0), anchor="w")

        self.risk_blood_label = ctk.CTkLabel(mods_frame, text=self.t('risk_blood'),
                                              font=ctk.CTkFont(family="Segoe UI", size=9),
                                              text_color=GREEN)
        self.risk_blood_label.pack(padx=42, pady=(0, 6), anchor="w")

        self.chk_vng = ctk.CTkCheckBox(mods_frame, text=self.t('vng'),
                                        font=ctk.CTkFont(family="Segoe UI", size=13),
                                        checkbox_width=22, checkbox_height=22, corner_radius=4,
                                        fg_color=BLUE, hover_color=BLUE_HOVER)
        if self.config.get('enable_vng_remove', True):
            self.chk_vng.select()
        self.chk_vng.pack(padx=16, pady=(4, 0), anchor="w")

        self.risk_vng_label = ctk.CTkLabel(mods_frame, text=self.t('risk_vng'),
                                            font=ctk.CTkFont(family="Segoe UI", size=9),
                                            text_color=YELLOW)
        self.risk_vng_label.pack(padx=42, pady=(0, 12), anchor="w")

        # ── Launch ──
        self.launch_label = ctk.CTkLabel(container, text=self.t('launch'),
                                          font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.launch_label.pack(padx=20, anchor="w", pady=(8, 4))

        launch_frame = ctk.CTkFrame(container, fg_color="#1a1a1a", corner_radius=8)
        launch_frame.pack(fill="x", padx=20, pady=(0, 2))

        self.launch_btn = ctk.CTkButton(launch_frame, text=self.t('play'), height=48,
                                         font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                                         fg_color=BLUE, hover_color=BLUE_HOVER,
                                         corner_radius=8,
                                         command=self._launch_game)
        self.launch_btn.pack(fill="x", padx=12, pady=(12, 6))

        riot_row = ctk.CTkFrame(launch_frame, fg_color="transparent")
        riot_row.pack(fill="x", padx=12, pady=(0, 10))

        custom_riot = self.config.get('riot_client_path', '')
        riot = find_riot_client(custom_riot)
        self.riot_label = ctk.CTkLabel(riot_row,
                                        text=self.t('riot_found') if riot else self.t('riot_not_found'),
                                        text_color=GREEN if riot else RED,
                                        font=ctk.CTkFont(family="Segoe UI", size=10))
        self.riot_label.pack(side="left")

        self.riot_browse_btn = ctk.CTkButton(riot_row, text=self.t('riot_browse'),
                                              width=60, height=26,
                                              fg_color=GRAY_BTN, hover_color=GRAY_HOVER,
                                              font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                                              command=self._browse_riot_client)
        self.riot_browse_btn.pack(side="right")

        # ── Log ──
        self.log_label = ctk.CTkLabel(container, text=self.t('log'),
                                       font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.log_label.pack(padx=20, anchor="w", pady=(8, 4))

        self.log_box = ctk.CTkTextbox(container, height=100, fg_color="#0a0a0a",
                                       border_width=1, border_color="#2a2a2a",
                                       corner_radius=8,
                                       font=ctk.CTkFont(family="Consolas", size=11),
                                       text_color="#888888", state="disabled")
        self.log_box.pack(fill="x", padx=20, pady=(0, 6))

        # ── True Stretch ──
        self.stretch_label = ctk.CTkLabel(container, text=self.t('stretch'),
                                           font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.stretch_label.pack(padx=20, anchor="w", pady=(8, 4))

        stretch_frame = ctk.CTkFrame(container, fg_color="#1a1a1a", corner_radius=8)
        stretch_frame.pack(fill="x", padx=20, pady=(0, 6))

        # Resolution selector
        res_row = ctk.CTkFrame(stretch_frame, fg_color="transparent")
        res_row.pack(fill="x", padx=12, pady=(12, 6))

        self.res_label = ctk.CTkLabel(res_row, text=self.t('resolution'),
                                       font=ctk.CTkFont(family="Segoe UI", size=12))
        self.res_label.pack(side="left")

        self._res_options = self._build_res_options()

        self.res_menu = ctk.CTkOptionMenu(
            res_row, values=self._res_options, width=240, height=30,
            fg_color=GRAY_BTN, button_color=GRAY_BTN, button_hover_color=GRAY_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._on_res_change)
        self.res_menu.pack(side="right")

        # Link icon — toggles whether stretch is applied when pressing Play
        link_icon_path = os.path.join(BIN_DIR, 'link.png')
        self._link_img = ctk.CTkImage(
            light_image=Image.open(link_icon_path),
            dark_image=Image.open(link_icon_path),
            size=(16, 16))
        self.link_btn = ctk.CTkButton(
            res_row, image=self._link_img, text="",
            width=30, height=30,
            fg_color=GRAY_BTN, hover_color=GRAY_HOVER,
            corner_radius=6,
            command=self._toggle_stretch_link)
        self.link_btn.pack(side="right", padx=(0, 6))
        # Restore last used resolution
        last_res = self.config.get('last_resolution', '')
        initial_option = self._res_options[0]
        if last_res == 'custom':
            initial_option = "Custom"
        elif last_res:
            for opt in self._res_options:
                if last_res in opt:
                    initial_option = opt
                    break
        self.res_menu.set(initial_option)

        # Custom resolution input (hidden by default)
        self.custom_res_frame = ctk.CTkFrame(stretch_frame, fg_color="transparent")

        custom_label = ctk.CTkLabel(self.custom_res_frame, text="W x H:",
                                     font=ctk.CTkFont(family="Segoe UI", size=11))
        custom_label.pack(side="left", padx=(0, 6))

        self.custom_w_entry = ctk.CTkEntry(self.custom_res_frame, width=70, height=28,
                                            placeholder_text="1440", border_width=0,
                                            fg_color="#111111",
                                            font=ctk.CTkFont(family="Segoe UI", size=11))
        saved_w = self.config.get('custom_width', '')
        if saved_w:
            self.custom_w_entry.insert(0, str(saved_w))
        self.custom_w_entry.pack(side="left", padx=(0, 4))

        ctk.CTkLabel(self.custom_res_frame, text="x",
                      font=ctk.CTkFont(family="Segoe UI", size=11)).pack(side="left", padx=2)

        self.custom_h_entry = ctk.CTkEntry(self.custom_res_frame, width=70, height=28,
                                            placeholder_text="1080", border_width=0,
                                            fg_color="#111111",
                                            font=ctk.CTkFont(family="Segoe UI", size=11))
        saved_h = self.config.get('custom_height', '')
        if saved_h:
            self.custom_h_entry.insert(0, str(saved_h))
        self.custom_h_entry.pack(side="left", padx=(4, 0))

        # Save custom resolution button
        self.save_custom_btn = ctk.CTkButton(self.custom_res_frame, text="Save",
                                              width=50, height=28,
                                              fg_color=GRAY_BTN, hover_color=GRAY_HOVER,
                                              font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                                              command=self._save_custom_resolution)
        self.save_custom_btn.pack(side="left", padx=(6, 0))

        # Show custom frame if last resolution was custom
        if last_res == 'custom':
            self.custom_res_frame.pack(fill="x", padx=12, pady=(0, 4))

        # Buttons row
        btn_row = ctk.CTkFrame(stretch_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(4, 6))

        self.stretch_btn = ctk.CTkButton(btn_row, text=self.t('apply_stretch'), height=34,
                                          fg_color=GRAY_BTN, hover_color=GRAY_HOVER,
                                          font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                          command=self._apply_stretch)
        self.stretch_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.revert_btn = ctk.CTkButton(btn_row, text=self.t('revert_stretch'), height=34,
                                         fg_color=GRAY_BTN, hover_color=GRAY_HOVER,
                                         font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                         command=self._revert_stretch, width=90)
        self.revert_btn.pack(side="right")

        self.stretch_hint_label = ctk.CTkLabel(stretch_frame,
                                     text=self.t('stretch_hint'),
                                     font=ctk.CTkFont(family="Segoe UI", size=9),
                                     text_color=DIM)
        self.stretch_hint_label.pack(padx=12, anchor="w", pady=(0, 2))

        self.risk_stretch_label = ctk.CTkLabel(stretch_frame,
                                                text=self.t('risk_stretch'),
                                                font=ctk.CTkFont(family="Segoe UI", size=9),
                                                text_color=GREEN)
        self.risk_stretch_label.pack(padx=12, anchor="w", pady=(0, 8))

        # ── Other (NVIDIA Profile) ──
        self.nvidia_label = ctk.CTkLabel(container, text=self.t('other'),
                                          font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.nvidia_label.pack(padx=20, anchor="w", pady=(8, 4))

        nvidia_frame = ctk.CTkFrame(container, fg_color="#1a1a1a", corner_radius=8)
        nvidia_frame.pack(fill="x", padx=20, pady=(0, 6))

        nvidia_row = ctk.CTkFrame(nvidia_frame, fg_color="transparent")
        nvidia_row.pack(fill="x", padx=12, pady=(12, 6))

        self.lod_label = ctk.CTkLabel(nvidia_row, text=self.t('lod_preset'),
                                       font=ctk.CTkFont(family="Segoe UI", size=12))
        self.lod_label.pack(side="left")

        self.apply_nvidia_btn = ctk.CTkButton(nvidia_row, text=self.t('apply_nvidia'),
                                               width=90, height=30,
                                               fg_color=GRAY_BTN, hover_color=GRAY_HOVER,
                                               font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                               command=self._apply_nvidia_profile)
        self.apply_nvidia_btn.pack(side="right")

        self._lod_options = ["Low", "Medium", "High", "ValoCraft :)"]
        self.lod_menu = ctk.CTkOptionMenu(
            nvidia_row, values=self._lod_options, width=150, height=30,
            fg_color=GRAY_BTN, button_color=GRAY_BTN, button_hover_color=GRAY_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=11))
        self.lod_menu.set("Low")
        self.lod_menu.pack(side="right", padx=(0, 6))

        # Link icon — toggles whether NVIDIA profile is applied when pressing Play
        self.other_link_btn = ctk.CTkButton(
            nvidia_row, image=self._link_img, text="",
            width=30, height=30,
            fg_color=GRAY_BTN, hover_color=GRAY_HOVER,
            corner_radius=6,
            command=self._toggle_other_link)
        self.other_link_btn.pack(side="right", padx=(0, 6))

        self.nvidia_hint_label = ctk.CTkLabel(nvidia_frame,
                                    text=self.t('nvidia_hint'),
                                    font=ctk.CTkFont(family="Segoe UI", size=9),
                                    text_color=DIM)
        self.nvidia_hint_label.pack(padx=12, anchor="w", pady=(0, 2))

        self.risk_nvidia_label = ctk.CTkLabel(nvidia_frame,
                                               text=self.t('risk_nvidia'),
                                               font=ctk.CTkFont(family="Segoe UI", size=9),
                                               text_color=GREEN)
        self.risk_nvidia_label.pack(padx=12, anchor="w", pady=(0, 8))

        # Disclaimer at bottom (follows current language)
        self.disclaimer_label = ctk.CTkLabel(container, text=self.t('disclaimer'),
                                              font=ctk.CTkFont(family="Segoe UI", size=10, slant="italic"),
                                              text_color=DIM, wraplength=460, justify="center")
        self.disclaimer_label.pack(padx=20, pady=(12, 14))

    # ── Language ──
    def _change_language(self, choice):
        self.lang = 'vi' if choice == 'VI' else 'en'
        self.config['language'] = self.lang
        save_config(self.config)
        self._refresh_texts()

    def _refresh_texts(self):
        self.dev_label.configure(text=self.t('developed_by'))
        self.warning_label.configure(text="⚠  " + self.t('warning'))
        self.disclaimer_label.configure(text=self.t('disclaimer'))
        self.folder_label.configure(text=self.t('game_folder'))
        self.browse_btn.configure(text=self.t('browse'))
        self.mods_label.configure(text=self.t('mods'))
        self.chk_blood.configure(text=self.t('blood'))
        self.chk_vng.configure(text=self.t('vng'))
        self.risk_blood_label.configure(text=self.t('risk_blood'))
        self.risk_vng_label.configure(text=self.t('risk_vng'))
        self.launch_label.configure(text=self.t('launch'))
        self.launch_btn.configure(text=self.t('play'))
        self.riot_browse_btn.configure(text=self.t('riot_browse'))
        self.log_label.configure(text=self.t('log'))
        custom_riot = self.config.get('riot_client_path', '')
        riot = find_riot_client(custom_riot)
        self.riot_label.configure(
            text=self.t('riot_found') if riot else self.t('riot_not_found'),
            text_color=GREEN if riot else RED)
        self._update_path_status()
        # Stretch
        self.stretch_label.configure(text=self.t('stretch'))
        self.res_label.configure(text=self.t('resolution'))
        self.stretch_btn.configure(text=self.t('apply_stretch'))
        self.revert_btn.configure(text=self.t('revert_stretch'))
        self._res_options = self._build_res_options()
        self.res_menu.configure(values=self._res_options)
        self.res_menu.set(self._res_options[0])
        # Stretch hint + risk
        self.stretch_hint_label.configure(text=self.t('stretch_hint'))
        self.risk_stretch_label.configure(text=self.t('risk_stretch'))
        # Other (NVIDIA Profile)
        self.nvidia_label.configure(text=self.t('other'))
        self.lod_label.configure(text=self.t('lod_preset'))
        self.apply_nvidia_btn.configure(text=self.t('apply_nvidia'))
        self.nvidia_hint_label.configure(text=self.t('nvidia_hint'))
        self.risk_nvidia_label.configure(text=self.t('risk_nvidia'))

    # ── Game Folder ──
    def _browse_folder(self):
        path = ctk.filedialog.askdirectory(title="Select VALORANT Folder",
                                            initialdir=r"C:\Riot Games")
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)
            self.config['game_path'] = path
            save_config(self.config)
            self._update_path_status()

    def _browse_riot_client(self):
        path = ctk.filedialog.askopenfilename(
            title="Select RiotClientServices.exe",
            initialdir=r"C:\Riot Games\Riot Client",
            filetypes=[("Executable", "RiotClientServices.exe"), ("All Files", "*.*")])
        if path and os.path.exists(path):
            self.config['riot_client_path'] = path
            save_config(self.config)
            self.riot_label.configure(text=self.t('riot_found'), text_color=GREEN)

    def _update_path_status(self):
        custom = self.path_entry.get().strip()
        if custom:
            paks = self._resolve_paks_dir(custom)
            if paks:
                self.path_status.configure(
                    text=f"{self.t('custom_path')}: {custom}", text_color=GREEN)
                self.config['game_path'] = custom
                save_config(self.config)
                return
            else:
                self.path_status.configure(
                    text=f"{self.t('path_not_found')}: {custom}", text_color=RED)
                return
        if os.path.exists(DEFAULT_PAKS_DIR):
            self.path_status.configure(
                text=f"{self.t('auto_detected')}: C:\\Riot Games\\VALORANT", text_color=GREEN)
        else:
            self.path_status.configure(text=self.t('path_not_found'), text_color=RED)

    # ── Log ──
    def _log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{ts}] {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # ── Launch ──
    def _launch_game(self):
        self.config['enable_blood'] = self.chk_blood.get() == 1
        self.config['enable_vng_remove'] = self.chk_vng.get() == 1
        save_config(self.config)

        # Apply stretch only if user linked stretch to Play
        if self.stretch_linked:
            res_key = self._get_selected_resolution_key()
            custom_w, custom_h = 0, 0
            if res_key == 'custom':
                try:
                    custom_w = int(self.config.get('custom_width', '0'))
                    custom_h = int(self.config.get('custom_height', '0'))
                except ValueError:
                    pass
            self._log(f"Applying stretch ({res_key})...")
            try:
                ok, nw, nh = apply_stretch(res_key, self._log, custom_w, custom_h)
                if ok and ok != "needs_custom_res":
                    self.native_w, self.native_h = nw, nh
                    self.stretch_active = True
                    self.config['last_resolution'] = res_key
                    save_config(self.config)
            except Exception as e:
                self._log(f"Stretch error: {e}")

        # Apply NVIDIA profile only if user linked Other to Play
        if self.other_linked:
            label_to_key = {
                "Low": "low", "Medium": "medium",
                "High": "high", "ValoCraft :)": "valocraft",
            }
            selected = self.lod_menu.get()
            lod_key = label_to_key.get(selected, "low")
            self._log(f"Applying NVIDIA profile ({selected})...")
            try:
                ok, msg = apply_valorant_profile(lod_key)
                self._log(msg)
            except Exception as e:
                self._log(f"NVIDIA profile error: {e}")

        paks_dir = self._get_paks_dir()
        custom_riot = self.config.get('riot_client_path', '')

        if not self.chk_blood.get() and not self.chk_vng.get():
            import subprocess
            riot_exe = find_riot_client(custom_riot)
            if riot_exe:
                subprocess.Popen(
                    f'cmd /c start "" "{riot_exe}" --launch-product=valorant --launch-patchline=live',
                    shell=True, creationflags=0x08000000)
                self._log(self.t('no_mods'))
                # Spawn stretch revert watcher if stretch was linked
                if self.stretch_linked and self.stretch_active:
                    revert_thread = threading.Thread(
                        target=self._stretch_revert_watcher,
                        daemon=True
                    )
                    revert_thread.start()
            else:
                self._show_error(self.t('riot_err'))
            return

        if self.chk_blood.get() and not os.path.exists(BLOOD_DIR):
            self._show_error(f"{self.t('blood_err')}:\n{BLOOD_DIR}")
            return
        if not paks_dir:
            self._show_error(self.t('paks_err'))
            return

        self.launch_btn.configure(state="disabled", text=self.t('launching'))
        self._log(self.t('start_seq'))

        self.launch_worker = GameLaunchWorker(
            blood_dir=BLOOD_DIR, paks_dir=paks_dir,
            enable_blood=self.chk_blood.get() == 1,
            enable_vng_remove=self.chk_vng.get() == 1,
            custom_riot_path=custom_riot,
            on_log=lambda msg: self.after(0, self._log, msg),
            on_ok=lambda: self.after(0, self._on_launch_ok),
            on_err=lambda err: self.after(0, self._on_launch_err, err))
        self.launch_worker.start()

        # Spawn stretch revert watcher if stretch was linked and applied
        if self.stretch_linked and self.stretch_active:
            revert_thread = threading.Thread(
                target=self._stretch_revert_watcher,
                daemon=True
            )
            revert_thread.start()

    def _stretch_revert_watcher(self):
        """Wait for game to start then exit, then auto-revert stretch settings."""
        # Wait for game to actually start (up to 5 min)
        for _ in range(150):
            if is_game_running():
                break
            time.sleep(2)
        else:
            return  # game never started, abort watcher

        # Wait for game to exit
        while is_game_running():
            time.sleep(2)

        # Game closed — revert stretch
        self.after(0, self._auto_revert_stretch)

    def _auto_revert_stretch(self):
        """Lightweight auto-revert after game exit. Runs on UI thread.
        Only restores desktop resolution — does NOT touch config files,
        so any in-game changes (like Show Mature Content) are preserved."""
        if not self.stretch_active and not self.config.get('last_resolution'):
            return
        self._log("Game closed — restoring desktop resolution...")
        try:
            auto_revert_on_exit(self.native_w, self.native_h, self._log)
        except Exception as e:
            self._log(f"Revert error: {e}")
        self._log("Desktop restored. Config preserved so game settings persist.")

    def _on_launch_ok(self):
        self.launch_btn.configure(state="normal", text=self.t('play'))
        self._log(self.t('done'))

    def _on_launch_err(self, err):
        self.launch_btn.configure(state="normal", text=self.t('play'))
        self._log(f"ERROR: {err}")

    def _show_error(self, msg):
        from tkinter import messagebox
        messagebox.showerror(self.t('error'), msg)

    def _show_info(self, title, msg):
        from tkinter import messagebox
        messagebox.showinfo(title, msg)

    def _ask_yes_no(self, title, msg):
        from tkinter import messagebox
        return messagebox.askyesno(title, msg)

    # ── Button colors ──
    def _set_btn_blue(self, btn):
        btn.configure(fg_color=BLUE, hover_color=BLUE_HOVER)

    def _set_btn_gray(self, btn):
        btn.configure(fg_color=GRAY_BTN, hover_color=GRAY_HOVER)

    # ── True Stretch ──
    def _build_res_options(self):
        """Build resolution dropdown options."""
        options = []
        for k, v in STRETCH_RESOLUTIONS.items():
            if k == 'custom':
                options.append("Custom")
            else:
                options.append(f"{v['label']}  —  {v['desc']}")
        return options

    def _toggle_stretch_link(self):
        """Toggle whether stretch is linked to Play button."""
        self.stretch_linked = not self.stretch_linked
        if self.stretch_linked:
            self.link_btn.configure(fg_color=BLUE, hover_color=BLUE_HOVER)
            self._log("Stretch linked — will apply when you press Play")
        else:
            self.link_btn.configure(fg_color=GRAY_BTN, hover_color=GRAY_HOVER)
            self._log("Stretch unlinked — Play will only apply mods")

    def _toggle_other_link(self):
        """Toggle whether NVIDIA profile is linked to Play button."""
        self.other_linked = not self.other_linked
        if self.other_linked:
            self.other_link_btn.configure(fg_color=BLUE, hover_color=BLUE_HOVER)
            self._log("NVIDIA profile linked — will apply when you press Play")
        else:
            self.other_link_btn.configure(fg_color=GRAY_BTN, hover_color=GRAY_HOVER)
            self._log("NVIDIA profile unlinked — Play will skip it")

    def _on_res_change(self, choice):
        """Show/hide custom resolution input based on dropdown selection."""
        if choice == "Custom":
            self.custom_res_frame.pack(fill="x", padx=12, pady=(0, 4))
        else:
            self.custom_res_frame.pack_forget()

    def _get_selected_resolution_key(self):
        """Map dropdown selection back to resolution key."""
        selected = self.res_menu.get()
        if selected == "Custom":
            return "custom"
        for k, v in STRETCH_RESOLUTIONS.items():
            if k != 'custom' and v['label'] in selected:
                return k
        return list(STRETCH_RESOLUTIONS.keys())[0]

    def _apply_stretch(self):
        res_key = self._get_selected_resolution_key()
        custom_w, custom_h = 0, 0

        if res_key == "custom":
            try:
                custom_w = int(self.custom_w_entry.get())
                custom_h = int(self.custom_h_entry.get())
            except ValueError:
                self._log("Invalid custom resolution — enter numbers only")
                return
            if custom_w < 640 or custom_h < 480:
                self._log("Resolution too small (min 640x480)")
                return
            self._log(f"Applying custom stretch: {custom_w}x{custom_h}")
        else:
            self._log(f"Applying stretch: {res_key}")

        ok, nw, nh = apply_stretch(res_key, self._log, custom_w, custom_h)

        # Resolution not in NVIDIA's mode list — show tutorial popup
        if ok == "needs_custom_res":
            target_w = custom_w if res_key == "custom" else STRETCH_RESOLUTIONS[res_key]['w']
            target_h = custom_h if res_key == "custom" else STRETCH_RESOLUTIONS[res_key]['h']
            self._show_nvidia_tutorial(target_w, target_h)
            return

        if ok:
            self.native_w, self.native_h = nw, nh
            self.stretch_active = True
            self._set_btn_blue(self.stretch_btn)
            # Save last used resolution + custom values
            self.config['last_resolution'] = res_key
            if res_key == 'custom':
                self.config['custom_width'] = str(custom_w)
                self.config['custom_height'] = str(custom_h)
            save_config(self.config)
            self._log("Restart VALORANT for changes to take effect")
        else:
            self._log("Stretch failed")

    def _save_custom_resolution(self):
        """Save custom resolution to config without applying."""
        try:
            w = int(self.custom_w_entry.get())
            h = int(self.custom_h_entry.get())
        except ValueError:
            self._log("Invalid — enter numbers only")
            return
        if w < 640 or h < 480:
            self._log("Too small (min 640x480)")
            return
        self.config['custom_width'] = str(w)
        self.config['custom_height'] = str(h)
        save_config(self.config)
        self._log(f"Saved custom: {w}x{h}")
        self._set_btn_blue(self.save_custom_btn)
        self.after(1200, lambda: self._set_btn_gray(self.save_custom_btn))

    def _show_nvidia_tutorial(self, width, height):
        """Popup tutorial for adding a custom resolution in NVIDIA Control Panel."""
        popup = ctk.CTkToplevel(self)
        popup.title("One-Time Setup Required")
        popup.geometry("520x400")
        popup.configure(fg_color="#0d0d0d")
        popup.transient(self)
        popup.grab_set()
        popup.resizable(False, False)

        title = ctk.CTkLabel(popup, text="Custom Resolution Setup",
                              font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                              text_color="#ffffff")
        title.pack(pady=(20, 6))

        subtitle = ctk.CTkLabel(popup,
                                 text=f"Resolution {width}x{height} not in your display mode list",
                                 font=ctk.CTkFont(family="Segoe UI", size=11),
                                 text_color=RED)
        subtitle.pack(pady=(0, 10))

        steps = (
            "One-time setup in NVIDIA Control Panel:\n\n"
            "1. Click \"Open NVIDIA CP\" below\n"
            "2. Go to:  Display  >  Change Resolution\n"
            "3. Click the \"Customize...\" button\n"
            "4. Check \"Enable resolutions not exposed by the display\"\n"
            "5. Click \"Create Custom Resolution\"\n"
            f"6. Set Horizontal pixels: {width}\n"
            f"7. Set Vertical lines: {height}\n"
            "8. Click Test, then OK to save\n"
            "9. Come back and click Apply Stretch again"
        )

        steps_label = ctk.CTkLabel(popup, text=steps,
                                    font=ctk.CTkFont(family="Segoe UI", size=11),
                                    text_color="#bbbbbb", justify="left")
        steps_label.pack(padx=24, pady=(0, 12))

        btn_row = ctk.CTkFrame(popup, fg_color="transparent")
        btn_row.pack(pady=(0, 20))

        open_btn = ctk.CTkButton(btn_row, text="Open NVIDIA CP", width=150, height=36,
                                  fg_color=BLUE, hover_color=BLUE_HOVER,
                                  font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                  command=lambda: self._open_nvcp_and_log(popup))
        open_btn.pack(side="left", padx=6)

        close_btn = ctk.CTkButton(btn_row, text="Close", width=100, height=36,
                                   fg_color=GRAY_BTN, hover_color=GRAY_HOVER,
                                   font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                   command=popup.destroy)
        close_btn.pack(side="left", padx=6)

    def _open_nvcp_and_log(self, popup):
        ok, msg = open_nvidia_control_panel()
        self._log(msg)
        if popup:
            popup.destroy()

    # ── NVIDIA Profile ──
    def _apply_nvidia_profile(self):
        """Apply NVIDIA settings to VALORANT profile via NPI."""
        label_to_key = {
            "Low": "low",
            "Medium": "medium",
            "High": "high",
            "ValoCraft :)": "valocraft",
        }
        selected = self.lod_menu.get()
        lod_key = label_to_key.get(selected, "low")
        self._log(f"Applying NVIDIA profile ({selected})...")
        ok, msg = apply_valorant_profile(lod_key)
        self._log(msg)
        if ok:
            self._set_btn_blue(self.apply_nvidia_btn)
            self.after(1500, lambda: self._set_btn_gray(self.apply_nvidia_btn))

    def _revert_stretch(self):
        self._log("Reverting stretch...")
        ok = revert_stretch(self.native_w, self.native_h, self._log)
        if ok:
            self.stretch_active = False
            self._set_btn_gray(self.stretch_btn)
            self._log("Reverted — restart VALORANT for changes")
        else:
            self._log("Nothing to revert")
