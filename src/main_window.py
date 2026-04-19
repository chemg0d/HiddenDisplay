import os
import sys
import time
import datetime

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFileDialog, QSystemTrayIcon, QMenu, QScrollArea, QFrame
)

try:
    from qfluentwidgets import (
        PushButton, PrimaryPushButton, CheckBox, LineEdit, ComboBox,
        TextEdit, CardWidget, TitleLabel, CaptionLabel,
        BodyLabel, StrongBodyLabel, InfoBar, InfoBarPosition,
        setTheme, Theme, ToolButton
    )
    FLUENT_AVAILABLE = True
except ImportError:
    FLUENT_AVAILABLE = False

from src.config import load_config, save_config, BIN_DIR
from src.fps_optimizer import run_all_optimizations, is_admin, create_restore_point
from src.graphics_preset import apply_low_preset, restore_settings
from src.game_launcher import GameLaunchWorker, find_riot_client, emergency_cleanup, is_game_running
from src.stretch import (
    STRETCH_RESOLUTIONS, apply_stretch, revert_stretch, auto_revert_on_exit,
    open_nvidia_control_panel
)

APP_VERSION = "4.0.0"
APP_NAME = "HiddenDisplay"

# ── Translations ──
LANG = {
    'en': {
        'mods': 'Mods',
        'blood': 'Enable Blood & Corpse',
        'vng': 'Remove VNG Logo',
        'play': 'PLAY VALORANT',
        'launching': 'LAUNCHING...',
        'log': 'Log',
        'optimization': 'Optimization',
        'fps': 'FPS Boost',
        'optimize': 'Optimize',
        'gfx': 'Graphics Quality',
        'apply_low': 'Apply Low',
        'restore': 'Restore',
        'game_folder': 'Game Folder',
        'browse': 'Browse',
        'auto_detected': 'Auto-detected',
        'custom_path': 'Custom path set',
        'path_not_found': 'Path not found',
        'fps_confirm': 'This will create a restore point, then apply system optimizations.\n\nContinue?',
        'fps_title': 'FPS Optimization',
        'creating_rp': 'Creating restore point...',
        'applying_opt': 'Applying optimizations...',
        'restart_pc': 'Restart PC for full effect.',
        'results': 'Results',
        'no_mods': 'Launched VALORANT (no mods)',
        'error': 'Error',
        'riot_err': 'Riot Client not found.',
        'blood_err': 'Blood folder not found',
        'paks_err': 'Game Paks folder not found',
        'start_seq': 'Starting launch sequence...',
        'done': 'Done.',
        'developed_by': 'Developed by Chemg0d',
        'minimized': 'Minimized to tray.',
        'stretch': 'True Stretch',
        'resolution': 'Resolution',
        'apply_stretch': 'Apply Stretch',
        'revert_stretch': 'Revert',
        'stretch_hint': 'Modifies game config + sets read-only. Revert to undo.',
        'riot_found': 'Riot Client found',
        'riot_not_found': 'Riot Client not found',
    },
    'vi': {
        'mods': 'Tinh chỉnh',
        'blood': 'Hiển thị Máu & Xác',
        'vng': 'Xóa Logo VNG',
        'play': 'CHƠI VALORANT',
        'launching': 'ĐANG KHỞI ĐỘNG...',
        'log': 'Nhật ký',
        'optimization': 'Tối ưu',
        'fps': 'Tăng FPS',
        'optimize': 'Tối ưu',
        'gfx': 'Chất lượng đồ họa',
        'apply_low': 'Hạ thấp',
        'restore': 'Khôi phục',
        'game_folder': 'Thư mục game',
        'browse': 'Chọn',
        'auto_detected': 'Tự động phát hiện',
        'custom_path': 'Đã đặt đường dẫn',
        'path_not_found': 'Không tìm thấy',
        'fps_confirm': 'Sẽ tạo điểm khôi phục và tối ưu hệ thống.\n\nTiếp tục?',
        'fps_title': 'Tối ưu FPS',
        'creating_rp': 'Đang tạo điểm khôi phục...',
        'applying_opt': 'Đang tối ưu...',
        'restart_pc': 'Khởi động lại máy tính để áp dụng.',
        'results': 'Kết quả',
        'no_mods': 'Đã khởi động VALORANT (không mod)',
        'error': 'Lỗi',
        'riot_err': 'Không tìm thấy Riot Client.',
        'blood_err': 'Không tìm thấy thư mục blood',
        'paks_err': 'Không tìm thấy thư mục game',
        'start_seq': 'Bắt đầu trình khởi động...',
        'done': 'Xong.',
        'developed_by': 'Phát triển bởi Chemg0d',
        'minimized': 'Thu nhỏ xuống khay.',
        'stretch': 'True Stretch',
        'resolution': 'Độ phân giải',
        'apply_stretch': 'Áp dụng Stretch',
        'revert_stretch': 'Hoàn tác',
        'stretch_hint': 'Chỉnh sửa config game + đặt chỉ đọc. Nhấn Hoàn tác để khôi phục.',
        'riot_found': 'Đã tìm thấy Riot Client',
        'riot_not_found': 'Không tìm thấy Riot Client',
    },
}


def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR = _get_base_dir()
BLOOD_DIR = os.path.join(BASE_DIR, 'blood')
DEFAULT_PAKS_DIR = r'C:\Riot Games\VALORANT\live\ShooterGame\Content\Paks'


# ── Launch Worker (QThread) ──
class LaunchThread(QThread):
    log_signal = pyqtSignal(str)
    finished_ok = pyqtSignal()
    finished_err = pyqtSignal(str)

    def __init__(self, blood_dir, paks_dir, enable_blood, enable_vng,
                 custom_riot_path, parent=None):
        super().__init__(parent)
        self.blood_dir = blood_dir
        self.paks_dir = paks_dir
        self.enable_blood = enable_blood
        self.enable_vng = enable_vng
        self.custom_riot_path = custom_riot_path

    def run(self):
        worker = GameLaunchWorker(
            blood_dir=self.blood_dir,
            paks_dir=self.paks_dir,
            enable_blood=self.enable_blood,
            enable_vng_remove=self.enable_vng,
            custom_riot_path=self.custom_riot_path,
            on_log=lambda msg: self.log_signal.emit(msg),
            on_ok=lambda: self.finished_ok.emit(),
            on_err=lambda err: self.finished_err.emit(err),
        )
        worker._run()


# ── Stretch Revert Watcher (QThread) ──
class StretchRevertThread(QThread):
    revert_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        for _ in range(150):
            if is_game_running():
                break
            time.sleep(2)
        else:
            return
        while is_game_running():
            time.sleep(2)
        self.revert_signal.emit()


# ── Section Card ──
class SectionCard(CardWidget if FLUENT_AVAILABLE else QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 14, 16, 14)
        self._layout.setSpacing(8)

        if FLUENT_AVAILABLE:
            self._title = StrongBodyLabel(title, self)
        else:
            self._title = QLabel(title, self)
            f = QFont("Segoe UI", 11)
            f.setBold(True)
            self._title.setFont(f)
        self._layout.addWidget(self._title)
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(6)
        self._layout.addLayout(self.content_layout)

    def set_title(self, text):
        self._title.setText(text)


# ── Main Window ──
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.lang = self.config.get('language', 'en')
        self.launch_thread = None
        self.stretch_active = False
        self.stretch_linked = False
        self.native_w, self.native_h = 0, 0
        self.tray_icon = None

        if FLUENT_AVAILABLE:
            setTheme(Theme.DARK)

        self._build_ui()
        self._setup_tray()

    def t(self, key):
        return LANG.get(self.lang, LANG['en']).get(key, key)

    # ── UI Build ──
    def _build_ui(self):
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(900, 520)
        self.resize(960, 520)

        self.setStyleSheet("""
            QFrame#separator { max-height: 1px; }
        """)

        icon_path = os.path.join(BIN_DIR, 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # ════════════════ ROOT: 2-column horizontal layout ════════════════
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ═══════════ LEFT PANEL (no scroll — fits at minimum size) ═══════════
        left_scroll = QScrollArea(self)
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        left_widget = QWidget()
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(20, 16, 12, 16)
        left.setSpacing(8)

        # ── Header ──
        header = QHBoxLayout()
        if FLUENT_AVAILABLE:
            title_lbl = TitleLabel(APP_NAME, self)
        else:
            title_lbl = QLabel(APP_NAME, self)
            title_lbl.setFont(QFont("Segoe UI Semibold", 20, QFont.Weight.Bold))
        header.addWidget(title_lbl)
        header.addStretch()
        self.lang_combo = ComboBox(self) if FLUENT_AVAILABLE else self._make_combo()
        self.lang_combo.addItems(["EN", "VI"])
        self.lang_combo.setCurrentText("VI" if self.lang == 'vi' else "EN")
        self.lang_combo.setFixedWidth(68)
        self.lang_combo.currentTextChanged.connect(self._change_language)
        header.addWidget(self.lang_combo)
        left.addLayout(header)

        if FLUENT_AVAILABLE:
            self.dev_label = CaptionLabel(self.t('developed_by'), self)
        else:
            self.dev_label = QLabel(self.t('developed_by'), self)
            self.dev_label.setStyleSheet("color: #777; font-size: 11px;")
        left.addWidget(self.dev_label)

        # ── Mods ──
        self.mods_card = SectionCard(self.t('mods'), self)
        self.chk_blood = CheckBox(self.t('blood'), self) if FLUENT_AVAILABLE else self._make_checkbox(self.t('blood'))
        if self.config.get('enable_blood', True):
            self.chk_blood.setChecked(True)
        self.mods_card.content_layout.addWidget(self.chk_blood)
        self.chk_vng = CheckBox(self.t('vng'), self) if FLUENT_AVAILABLE else self._make_checkbox(self.t('vng'))
        if self.config.get('enable_vng_remove', True):
            self.chk_vng.setChecked(True)
        self.mods_card.content_layout.addWidget(self.chk_vng)
        left.addWidget(self.mods_card)

        # ── Optimization ──
        self.opt_card = SectionCard(self.t('optimization'), self)
        fps_row = QHBoxLayout()
        self.fps_label = BodyLabel(self.t('fps'), self) if FLUENT_AVAILABLE else QLabel(self.t('fps'), self)
        fps_row.addWidget(self.fps_label)
        fps_row.addStretch()
        self.opt_btn = PushButton(self.t('optimize'), self) if FLUENT_AVAILABLE else self._make_button(self.t('optimize'))
        self.opt_btn.setFixedWidth(90)
        self.opt_btn.clicked.connect(self._optimize_fps)
        fps_row.addWidget(self.opt_btn)
        self.opt_card.content_layout.addLayout(fps_row)

        gfx_row = QHBoxLayout()
        self.gfx_label = BodyLabel(self.t('gfx'), self) if FLUENT_AVAILABLE else QLabel(self.t('gfx'), self)
        gfx_row.addWidget(self.gfx_label)
        gfx_row.addStretch()
        self.apply_gfx_btn = PushButton(self.t('apply_low'), self) if FLUENT_AVAILABLE else self._make_button(self.t('apply_low'))
        self.apply_gfx_btn.setFixedWidth(90)
        self.apply_gfx_btn.clicked.connect(self._apply_graphics)
        gfx_row.addWidget(self.apply_gfx_btn)
        self.restore_gfx_btn = PushButton(self.t('restore'), self) if FLUENT_AVAILABLE else self._make_button(self.t('restore'))
        self.restore_gfx_btn.setFixedWidth(90)
        self.restore_gfx_btn.clicked.connect(self._restore_graphics)
        gfx_row.addWidget(self.restore_gfx_btn)
        self.opt_card.content_layout.addLayout(gfx_row)
        left.addWidget(self.opt_card)

        # ── Stretch ──
        self.stretch_card = SectionCard(self.t('stretch'), self)
        res_row = QHBoxLayout()
        self.res_label = BodyLabel(self.t('resolution'), self) if FLUENT_AVAILABLE else QLabel(self.t('resolution'), self)
        res_row.addWidget(self.res_label)
        res_row.addStretch()

        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
        self._icon_link = QIcon(os.path.join(assets_dir, 'link.svg'))
        self._icon_linkoff = QIcon(os.path.join(assets_dir, 'linkoff.svg'))

        if FLUENT_AVAILABLE:
            self.link_btn = ToolButton(self._icon_linkoff, self)
        else:
            from PyQt6.QtWidgets import QToolButton
            self.link_btn = QToolButton(self)
            self.link_btn.setIcon(self._icon_linkoff)
        self.link_btn.setIconSize(QSize(18, 18))
        self.link_btn.setFixedSize(32, 32)
        self.link_btn.setCheckable(True)
        self.link_btn.clicked.connect(self._toggle_stretch_link)
        res_row.addWidget(self.link_btn)

        self._res_options = self._build_res_options()
        self.res_combo = ComboBox(self) if FLUENT_AVAILABLE else self._make_combo()
        self.res_combo.addItems(self._res_options)
        self.res_combo.setFixedWidth(200)
        self.res_combo.currentTextChanged.connect(self._on_res_change)
        res_row.addWidget(self.res_combo)
        self.stretch_card.content_layout.addLayout(res_row)

        # Restore last resolution
        last_res = self.config.get('last_resolution', '')
        initial_option = self._res_options[0] if self._res_options else ""
        if last_res == 'custom':
            initial_option = "Custom"
        elif last_res:
            for opt in self._res_options:
                if last_res in opt:
                    initial_option = opt
                    break
        self.res_combo.setCurrentText(initial_option)

        # Custom resolution
        self.custom_res_widget = QWidget(self)
        cl = QHBoxLayout(self.custom_res_widget)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(QLabel("W × H:", self))
        self.custom_w_entry = LineEdit(self) if FLUENT_AVAILABLE else self._make_line_edit()
        self.custom_w_entry.setPlaceholderText("1440")
        self.custom_w_entry.setFixedWidth(70)
        sw = self.config.get('custom_width', '')
        if sw:
            self.custom_w_entry.setText(str(sw))
        cl.addWidget(self.custom_w_entry)
        cl.addWidget(QLabel("×", self))
        self.custom_h_entry = LineEdit(self) if FLUENT_AVAILABLE else self._make_line_edit()
        self.custom_h_entry.setPlaceholderText("1080")
        self.custom_h_entry.setFixedWidth(70)
        sh = self.config.get('custom_height', '')
        if sh:
            self.custom_h_entry.setText(str(sh))
        cl.addWidget(self.custom_h_entry)
        self.save_custom_btn = PushButton("Save", self) if FLUENT_AVAILABLE else self._make_button("Save")
        self.save_custom_btn.setFixedWidth(55)
        self.save_custom_btn.clicked.connect(self._save_custom_resolution)
        cl.addWidget(self.save_custom_btn)
        cl.addStretch()
        self.custom_res_widget.setVisible(last_res == 'custom')
        self.stretch_card.content_layout.addWidget(self.custom_res_widget)

        stretch_btns = QHBoxLayout()
        self.stretch_btn = PushButton(self.t('apply_stretch'), self) if FLUENT_AVAILABLE else self._make_button(self.t('apply_stretch'))
        self.stretch_btn.clicked.connect(self._apply_stretch)
        stretch_btns.addWidget(self.stretch_btn)
        self.revert_btn = PushButton(self.t('revert_stretch'), self) if FLUENT_AVAILABLE else self._make_button(self.t('revert_stretch'))
        self.revert_btn.setFixedWidth(90)
        self.revert_btn.clicked.connect(self._revert_stretch)
        stretch_btns.addWidget(self.revert_btn)
        self.stretch_card.content_layout.addLayout(stretch_btns)

        self.stretch_hint_label = QLabel(self.t('stretch_hint'), self)
        self.stretch_hint_label.setStyleSheet("color: #666; font-size: 10px;")
        self.stretch_card.content_layout.addWidget(self.stretch_hint_label)
        left.addWidget(self.stretch_card)

        left.addStretch()
        left_scroll.setWidget(left_widget)

        # ═══════════ RIGHT PANEL (Log on top, Play at bottom) ═══════════
        right_widget = QWidget(self)
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(16, 16, 20, 16)
        right.setSpacing(10)

        # Log (top of right panel, fills available space)
        if FLUENT_AVAILABLE:
            log_title = StrongBodyLabel(self.t('log'), self)
        else:
            log_title = QLabel(self.t('log'), self)
            lf = QFont("Segoe UI", 11)
            lf.setBold(True)
            log_title.setFont(lf)
        log_title.setStyleSheet("")
        self.log_title_label = log_title
        right.addWidget(log_title)

        if FLUENT_AVAILABLE:
            self.log_box = TextEdit(self)
        else:
            from PyQt6.QtWidgets import QTextEdit
            self.log_box = QTextEdit(self)
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("""
            QTextEdit, TextEdit {
                border: 1px solid palette(mid);
                border-radius: 4px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 11px;
                padding: 4px;
            }
        """)
        right.addWidget(self.log_box, 1)

        # ── Game Folder (right panel, on top) ──
        self.folder_card = SectionCard(self.t('game_folder'), self)
        folder_row = QHBoxLayout()
        self.path_entry = LineEdit(self) if FLUENT_AVAILABLE else self._make_line_edit()
        self.path_entry.setPlaceholderText(r"C:\Riot Games\VALORANT")
        saved_path = self.config.get('game_path', '')
        if saved_path:
            self.path_entry.setText(saved_path)
        folder_row.addWidget(self.path_entry)
        self.browse_btn = PushButton(self.t('browse'), self) if FLUENT_AVAILABLE else self._make_button(self.t('browse'))
        self.browse_btn.setFixedWidth(72)
        self.browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(self.browse_btn)
        self.folder_card.content_layout.addLayout(folder_row)
        self.path_status = QLabel("", self)
        self.path_status.setStyleSheet("font-size: 11px;")
        self.folder_card.content_layout.addWidget(self.path_status)
        self._update_path_status()
        right.addWidget(self.folder_card)

        # Play button — big and at the bottom
        self.launch_btn = PrimaryPushButton(self.t('play'), self) if FLUENT_AVAILABLE else self._make_button(self.t('play'))
        self.launch_btn.setFixedHeight(52)
        f = self.launch_btn.font()
        f.setPointSize(15)
        f.setBold(True)
        self.launch_btn.setFont(f)
        self.launch_btn.clicked.connect(self._launch_game)
        right.addWidget(self.launch_btn)

        # ════════════════ Assemble ════════════════
        root.addWidget(left_scroll, 1)
        root.addWidget(right_widget, 1)

    # ── Tray ──
    def _setup_tray(self):
        icon_path = os.path.join(BIN_DIR, 'icon.ico')
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
        self.tray_icon = QSystemTrayIcon(icon, self)
        tray_menu = QMenu()
        tray_menu.addAction("Show HiddenDisplay").triggered.connect(self._show_from_tray)
        tray_menu.addAction("Quit").triggered.connect(self._quit_from_tray)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit_from_tray(self):
        try:
            paks_dir = self._get_paks_dir()
            emergency_cleanup(paks_dir)
        except Exception:
            pass
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

    # ── Language ──
    def _change_language(self, choice):
        self.lang = 'vi' if choice == 'VI' else 'en'
        self.config['language'] = self.lang
        save_config(self.config)
        self._refresh_texts()

    def _refresh_texts(self):
        self.dev_label.setText(self.t('developed_by'))
        self.folder_card.set_title(self.t('game_folder'))
        self.browse_btn.setText(self.t('browse'))
        self.mods_card.set_title(self.t('mods'))
        self.chk_blood.setText(self.t('blood'))
        self.chk_vng.setText(self.t('vng'))
        self.launch_btn.setText(self.t('play'))
        self.log_title_label.setText(self.t('log'))
        self.opt_card.set_title(self.t('optimization'))
        self.fps_label.setText(self.t('fps'))
        self.opt_btn.setText(self.t('optimize'))
        self.gfx_label.setText(self.t('gfx'))
        self.apply_gfx_btn.setText(self.t('apply_low'))
        self.restore_gfx_btn.setText(self.t('restore'))
        self.stretch_card.set_title(self.t('stretch'))
        self.res_label.setText(self.t('resolution'))
        self.stretch_btn.setText(self.t('apply_stretch'))
        self.revert_btn.setText(self.t('revert_stretch'))
        self.stretch_hint_label.setText(self.t('stretch_hint'))
        self._update_path_status()

    # ── Game Folder ──
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

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select VALORANT Folder", r"C:\Riot Games")
        if path:
            self.path_entry.setText(path)
            self.config['game_path'] = path
            save_config(self.config)
            self._update_path_status()

    def _update_path_status(self):
        custom = self.path_entry.text().strip()
        if custom:
            paks = self._resolve_paks_dir(custom)
            if paks:
                self.path_status.setText(f"{self.t('custom_path')}: {custom}")
                self.path_status.setStyleSheet("color: #22c55e; font-size: 11px;")
                self.config['game_path'] = custom
                save_config(self.config)
                return
            else:
                self.path_status.setText(f"{self.t('path_not_found')}: {custom}")
                self.path_status.setStyleSheet("color: #ef4444; font-size: 11px;")
                return
        if os.path.exists(DEFAULT_PAKS_DIR):
            self.path_status.setText(f"{self.t('auto_detected')}: C:\\Riot Games\\VALORANT")
            self.path_status.setStyleSheet("color: #22c55e; font-size: 11px;")
        else:
            self.path_status.setText(self.t('path_not_found'))
            self.path_status.setStyleSheet("color: #ef4444; font-size: 11px;")

    # ── Log ──
    def _log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{ts}] {msg}")

    # ── Launch ──
    def _launch_game(self):
        self.config['enable_blood'] = self.chk_blood.isChecked()
        self.config['enable_vng_remove'] = self.chk_vng.isChecked()
        save_config(self.config)

        if self.stretch_linked:
            res_key = self._get_selected_resolution_key()
            cw, ch = 0, 0
            if res_key == 'custom':
                try:
                    cw = int(self.config.get('custom_width', '0'))
                    ch = int(self.config.get('custom_height', '0'))
                except ValueError:
                    pass
            self._log(f"Applying stretch ({res_key})...")
            try:
                ok, nw, nh = apply_stretch(res_key, self._log, cw, ch)
                if ok and ok != "needs_custom_res":
                    self.native_w, self.native_h = nw, nh
                    self.stretch_active = True
                    self.config['last_resolution'] = res_key
                    save_config(self.config)
            except Exception as e:
                self._log(f"Stretch error: {e}")

        paks_dir = self._get_paks_dir()
        custom_riot = self.config.get('riot_client_path', '')

        if not self.chk_blood.isChecked() and not self.chk_vng.isChecked():
            import subprocess
            riot_exe = find_riot_client(custom_riot)
            if riot_exe:
                subprocess.Popen(
                    f'cmd /c start "" "{riot_exe}" --launch-product=valorant --launch-patchline=live',
                    shell=True, creationflags=0x08000000)
                self._log(self.t('no_mods'))
                if self.stretch_linked and self.stretch_active:
                    self._start_stretch_revert_watcher()
            else:
                self._show_error(self.t('riot_err'))
            return

        if self.chk_blood.isChecked() and not os.path.exists(BLOOD_DIR):
            self._show_error(f"{self.t('blood_err')}:\n{BLOOD_DIR}")
            return
        if not paks_dir:
            self._show_error(self.t('paks_err'))
            return

        self.launch_btn.setEnabled(False)
        self.launch_btn.setText(self.t('launching'))
        self._log(self.t('start_seq'))

        self.launch_thread = LaunchThread(
            blood_dir=BLOOD_DIR, paks_dir=paks_dir,
            enable_blood=self.chk_blood.isChecked(),
            enable_vng=self.chk_vng.isChecked(),
            custom_riot_path=custom_riot, parent=self)
        self.launch_thread.log_signal.connect(self._log)
        self.launch_thread.finished_ok.connect(self._on_launch_ok)
        self.launch_thread.finished_err.connect(self._on_launch_err)
        self.launch_thread.start()

        if self.stretch_linked and self.stretch_active:
            self._start_stretch_revert_watcher()

    def _start_stretch_revert_watcher(self):
        self._revert_thread = StretchRevertThread(self)
        self._revert_thread.revert_signal.connect(self._auto_revert_stretch)
        self._revert_thread.start()

    def _auto_revert_stretch(self):
        if not self.stretch_active and not self.config.get('last_resolution'):
            return
        self._log("Game closed — restoring desktop resolution...")
        try:
            auto_revert_on_exit(self.native_w, self.native_h, self._log)
        except Exception as e:
            self._log(f"Revert error: {e}")
        self._log("Desktop restored.")

    def _on_launch_ok(self):
        self.launch_btn.setEnabled(True)
        self.launch_btn.setText(self.t('play'))
        self._log(self.t('done'))

    def _on_launch_err(self, err):
        self.launch_btn.setEnabled(True)
        self.launch_btn.setText(self.t('play'))
        self._log(f"ERROR: {err}")

    def _show_error(self, msg):
        if FLUENT_AVAILABLE:
            InfoBar.error(
                title=self.t('error'), content=msg,
                orient=Qt.Orientation.Horizontal,
                isClosable=True, position=InfoBarPosition.TOP,
                duration=5000, parent=self)
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.t('error'), msg)

    def _show_info(self, title, msg):
        if FLUENT_AVAILABLE:
            InfoBar.success(
                title=title, content=msg,
                orient=Qt.Orientation.Horizontal,
                isClosable=True, position=InfoBarPosition.TOP,
                duration=5000, parent=self)
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, title, msg)

    def _ask_yes_no(self, title, msg):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, title, msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return reply == QMessageBox.StandardButton.Yes

    # ── Optimization ──
    def _optimize_fps(self):
        if not self._ask_yes_no(self.t('fps_title'), self.t('fps_confirm')):
            return
        self._log(self.t('creating_rp'))
        create_restore_point()
        self._log(self.t('applying_opt'))
        paks_dir = self._get_paks_dir()
        exe_path = None
        if paks_dir:
            exe = os.path.normpath(os.path.join(
                paks_dir, '..', '..', 'Binaries', 'Win64', 'VALORANT-Win64-Shipping.exe'))
            if os.path.exists(exe):
                exe_path = exe
        results = run_all_optimizations(exe_path)
        ok_count = sum(1 for ok, _ in results.values() if ok)
        details = [f"  [{'OK' if ok else 'FAIL'}] {n}: {m}" for n, (ok, m) in results.items()]
        self._show_info(self.t('results'),
            f"{ok_count}/{len(results)} applied:\n\n" + "\n".join(details) + f"\n\n{self.t('restart_pc')}")

    def _apply_graphics(self):
        ok, msg = apply_low_preset(os.path.join(BIN_DIR, 'GameUserSettings.ini'))
        self._show_info(self.t('gfx'), msg) if ok else self._show_error(msg)

    def _restore_graphics(self):
        ok, msg = restore_settings()
        self._show_info(self.t('gfx'), msg) if ok else self._show_error(msg)

    # ── Stretch ──
    def _build_res_options(self):
        options = []
        for k, v in STRETCH_RESOLUTIONS.items():
            if k == 'custom':
                options.append("Custom")
            else:
                options.append(f"{v['label']}  —  {v['desc']}")
        return options

    def _toggle_stretch_link(self):
        self.stretch_linked = self.link_btn.isChecked()
        if self.stretch_linked:
            self.link_btn.setIcon(self._icon_link)
            self._log("Stretch linked — will apply when you press Play")
        else:
            self.link_btn.setIcon(self._icon_linkoff)
            self._log("Stretch unlinked")

    def _on_res_change(self, choice):
        self.custom_res_widget.setVisible(choice == "Custom")

    def _get_selected_resolution_key(self):
        selected = self.res_combo.currentText()
        if selected == "Custom":
            return "custom"
        for k, v in STRETCH_RESOLUTIONS.items():
            if k != 'custom' and v['label'] in selected:
                return k
        return list(STRETCH_RESOLUTIONS.keys())[0]

    def _apply_stretch(self):
        res_key = self._get_selected_resolution_key()
        cw, ch = 0, 0
        if res_key == "custom":
            try:
                cw = int(self.custom_w_entry.text())
                ch = int(self.custom_h_entry.text())
            except ValueError:
                self._log("Invalid custom resolution"); return
            if cw < 640 or ch < 480:
                self._log("Resolution too small (min 640x480)"); return
            self._log(f"Applying custom stretch: {cw}x{ch}")
        else:
            self._log(f"Applying stretch: {res_key}")

        ok, nw, nh = apply_stretch(res_key, self._log, cw, ch)
        if ok == "needs_custom_res":
            tw = cw if res_key == "custom" else STRETCH_RESOLUTIONS[res_key]['w']
            th = ch if res_key == "custom" else STRETCH_RESOLUTIONS[res_key]['h']
            self._show_nvidia_tutorial(tw, th)
            return
        if ok:
            self.native_w, self.native_h = nw, nh
            self.stretch_active = True
            self.config['last_resolution'] = res_key
            if res_key == 'custom':
                self.config['custom_width'] = str(cw)
                self.config['custom_height'] = str(ch)
            save_config(self.config)
            self._log("Restart VALORANT for changes to take effect")
        else:
            self._log("Stretch failed")

    def _save_custom_resolution(self):
        try:
            w = int(self.custom_w_entry.text())
            h = int(self.custom_h_entry.text())
        except ValueError:
            self._log("Invalid — enter numbers only"); return
        if w < 640 or h < 480:
            self._log("Too small (min 640x480)"); return
        self.config['custom_width'] = str(w)
        self.config['custom_height'] = str(h)
        save_config(self.config)
        self._log(f"Saved custom: {w}x{h}")

    def _show_nvidia_tutorial(self, width, height):
        from PyQt6.QtWidgets import QDialog
        dialog = QDialog(self)
        dialog.setWindowTitle("One-Time Setup Required")
        dialog.setFixedSize(520, 400)
        dialog.setStyleSheet("background-color: #202020; color: #e0e0e0;")
        layout = QVBoxLayout(dialog)
        title = QLabel("Custom Resolution Setup", dialog)
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        subtitle = QLabel(f"Resolution {width}x{height} not in your display mode list", dialog)
        subtitle.setStyleSheet("color: #ef4444;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        steps = (
            "One-time setup in NVIDIA Control Panel:\n\n"
            "1. Click \"Open NVIDIA CP\" below\n"
            "2. Go to:  Display  >  Change Resolution\n"
            "3. Click \"Customize...\" button\n"
            "4. Check \"Enable resolutions not exposed by the display\"\n"
            "5. Click \"Create Custom Resolution\"\n"
            f"6. Set Horizontal pixels: {width}\n"
            f"7. Set Vertical lines: {height}\n"
            "8. Click Test, then OK to save\n"
            "9. Come back and click Apply Stretch again"
        )
        layout.addWidget(QLabel(steps, dialog))
        btn_row = QHBoxLayout()
        open_btn = PrimaryPushButton("Open NVIDIA CP", dialog) if FLUENT_AVAILABLE else self._make_button("Open NVIDIA CP")
        open_btn.clicked.connect(lambda: (open_nvidia_control_panel(), dialog.close()))
        btn_row.addWidget(open_btn)
        close_btn = PushButton("Close", dialog) if FLUENT_AVAILABLE else self._make_button("Close")
        close_btn.clicked.connect(dialog.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        dialog.exec()

    def _revert_stretch(self):
        self._log("Reverting stretch...")
        ok = revert_stretch(self.native_w, self.native_h, self._log)
        if ok:
            self.stretch_active = False
            self._log("Reverted — restart VALORANT for changes")
        else:
            self._log("Nothing to revert")

    # ── Fallback widget factories ──
    def _make_button(self, text):
        from PyQt6.QtWidgets import QPushButton
        btn = QPushButton(text, self)
        return btn

    def _make_combo(self):
        from PyQt6.QtWidgets import QComboBox
        return QComboBox(self)

    def _make_line_edit(self):
        from PyQt6.QtWidgets import QLineEdit
        return QLineEdit(self)

    def _make_checkbox(self, text):
        from PyQt6.QtWidgets import QCheckBox
        return QCheckBox(text, self)
