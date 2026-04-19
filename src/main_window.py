import os
import sys
import time
import datetime
import threading

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QFont, QColor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFileDialog, QSystemTrayIcon, QMenu, QFrame, QMessageBox,
    QSizePolicy
)

from qfluentwidgets import (
    PushButton, PrimaryPushButton, CheckBox, LineEdit, ComboBox,
    TextEdit, CardWidget, TitleLabel, CaptionLabel,
    BodyLabel, StrongBodyLabel, InfoBar, InfoBarPosition,
    setTheme, Theme
)

from PIL import Image

from src.config import load_config, save_config, BIN_DIR
from src.fps_optimizer import run_all_optimizations, is_admin, create_restore_point
from src.graphics_preset import apply_low_preset, restore_settings
from src.game_launcher import GameLaunchWorker, find_riot_client, emergency_cleanup, is_game_running
from src.stretch import (
    STRETCH_RESOLUTIONS, apply_stretch, revert_stretch, auto_revert_on_exit,
    get_native_resolution, is_resolution_supported, open_nvidia_control_panel
)

APP_VERSION = "4.0.0"
APP_NAME = "HiddenDisplay"

LANG = {
    'en': {
        'mods': 'Mods',
        'blood': 'Enable Blood & Corpse',
        'vng': 'Remove VNG Logo',
        'launch': 'Launch',
        'play': 'PLAY VALORANT',
        'launching': 'LAUNCHING...',
        'riot_found': 'Riot Client found',
        'riot_not_found': 'Riot Client not found — Browse to locate',
        'riot_browse': 'Browse',
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
        'stretch': 'True Stretch',
        'resolution': 'Resolution',
        'apply_stretch': 'Apply Stretch',
        'revert_stretch': 'Revert',
        'stretch_hint': 'Modifies game config + sets read-only. Revert to undo.',
    },
    'vi': {
        'mods': 'Tinh chỉnh',
        'blood': 'Hiển thị Máu & Xác',
        'vng': 'Xóa Logo VNG',
        'launch': 'Khởi động',
        'play': 'CHƠI VALORANT',
        'launching': 'ĐANG KHỞI ĐỘNG...',
        'riot_found': 'Đã tìm thấy Riot Client',
        'riot_not_found': 'Không tìm thấy Riot Client — Nhấn Chọn',
        'riot_browse': 'Chọn',
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
        'stretch': 'True Stretch',
        'resolution': 'Độ phân giải',
        'apply_stretch': 'Áp dụng Stretch',
        'revert_stretch': 'Hoàn tác',
        'stretch_hint': 'Chỉnh sửa config game + đặt chỉ đọc. Nhấn Hoàn tác để khôi phục.',
    },
}


def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR = _get_base_dir()
BLOOD_DIR = os.path.join(BASE_DIR, 'blood')
DEFAULT_PAKS_DIR = r'C:\Riot Games\VALORANT\live\ShooterGame\Content\Paks'


# ═══════════════════════════════════════
#  QThread workers
# ═══════════════════════════════════════
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
            blood_dir=self.blood_dir, paks_dir=self.paks_dir,
            enable_blood=self.enable_blood,
            enable_vng_remove=self.enable_vng,
            custom_riot_path=self.custom_riot_path,
            on_log=lambda msg: self.log_signal.emit(msg),
            on_ok=lambda: self.finished_ok.emit(),
            on_err=lambda err: self.finished_err.emit(err),
        )
        worker._run()


class StretchRevertThread(QThread):
    revert_signal = pyqtSignal()

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


# ═══════════════════════════════════════
#  Main Window — Horizontal layout
# ═══════════════════════════════════════
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

        setTheme(Theme.DARK)
        self._build_ui()
        self._setup_tray()

    def t(self, key):
        return LANG.get(self.lang, LANG['en']).get(key, key)

    # ─────────────────────────────────────
    #  UI
    # ─────────────────────────────────────
    def _build_ui(self):
        self.setWindowTitle(APP_NAME)
        self.resize(960, 560)
        self.setMinimumSize(860, 480)

        icon_path = os.path.join(BIN_DIR, 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 16)
        root.setSpacing(12)

        # ── Header row ──
        header = QHBoxLayout()
        title = TitleLabel(APP_NAME)
        header.addWidget(title)
        self.dev_label = CaptionLabel(f"v{APP_VERSION}  ·  {self.t('developed_by')}")
        header.addWidget(self.dev_label)
        header.addStretch()

        self.lang_combo = ComboBox()
        self.lang_combo.addItems(["EN", "VI"])
        self.lang_combo.setCurrentText("VI" if self.lang == 'vi' else "EN")
        self.lang_combo.setFixedWidth(70)
        self.lang_combo.currentTextChanged.connect(self._change_language)
        header.addWidget(self.lang_combo)
        root.addLayout(header)

        # ── Two columns ──
        columns = QHBoxLayout()
        columns.setSpacing(16)

        # ═══ LEFT COLUMN ═══
        left = QVBoxLayout()
        left.setSpacing(12)

        # Game Folder
        folder_card = CardWidget()
        fc = QVBoxLayout(folder_card)
        fc.setContentsMargins(16, 12, 16, 12)
        fc.setSpacing(8)
        self.folder_title = StrongBodyLabel(self.t('game_folder'))
        fc.addWidget(self.folder_title)

        fr = QHBoxLayout()
        self.path_entry = LineEdit()
        self.path_entry.setPlaceholderText(r"C:\Riot Games\VALORANT")
        saved = self.config.get('game_path', '')
        if saved:
            self.path_entry.setText(saved)
        fr.addWidget(self.path_entry)
        self.browse_btn = PushButton(self.t('browse'))
        self.browse_btn.setFixedWidth(72)
        self.browse_btn.clicked.connect(self._browse_folder)
        fr.addWidget(self.browse_btn)
        fc.addLayout(fr)
        self.path_status = CaptionLabel("")
        fc.addWidget(self.path_status)
        self._update_path_status()
        left.addWidget(folder_card)

        # Mods
        mods_card = CardWidget()
        mc = QVBoxLayout(mods_card)
        mc.setContentsMargins(16, 12, 16, 12)
        mc.setSpacing(6)
        self.mods_title = StrongBodyLabel(self.t('mods'))
        mc.addWidget(self.mods_title)
        self.chk_blood = CheckBox(self.t('blood'))
        if self.config.get('enable_blood', True):
            self.chk_blood.setChecked(True)
        mc.addWidget(self.chk_blood)
        self.chk_vng = CheckBox(self.t('vng'))
        if self.config.get('enable_vng_remove', True):
            self.chk_vng.setChecked(True)
        mc.addWidget(self.chk_vng)
        left.addWidget(mods_card)

        # Launch
        launch_card = CardWidget()
        lc = QVBoxLayout(launch_card)
        lc.setContentsMargins(16, 12, 16, 12)
        lc.setSpacing(8)
        self.launch_title = StrongBodyLabel(self.t('launch'))
        lc.addWidget(self.launch_title)

        self.launch_btn = PrimaryPushButton(self.t('play'))
        self.launch_btn.setFixedHeight(44)
        f = self.launch_btn.font()
        f.setPointSize(13)
        f.setBold(True)
        self.launch_btn.setFont(f)
        self.launch_btn.clicked.connect(self._launch_game)
        lc.addWidget(self.launch_btn)

        rr = QHBoxLayout()
        custom_riot = self.config.get('riot_client_path', '')
        riot = find_riot_client(custom_riot)
        self.riot_label = CaptionLabel(
            self.t('riot_found') if riot else self.t('riot_not_found'))
        self.riot_label.setStyleSheet(
            f"color: {'#22c55e' if riot else '#ef4444'};")
        rr.addWidget(self.riot_label)
        rr.addStretch()
        self.riot_browse_btn = PushButton(self.t('riot_browse'))
        self.riot_browse_btn.setFixedWidth(64)
        self.riot_browse_btn.clicked.connect(self._browse_riot_client)
        rr.addWidget(self.riot_browse_btn)
        lc.addLayout(rr)
        left.addWidget(launch_card)

        left.addStretch()
        columns.addLayout(left, 1)

        # ═══ RIGHT COLUMN ═══
        right = QVBoxLayout()
        right.setSpacing(12)

        # Optimization
        opt_card = CardWidget()
        oc = QVBoxLayout(opt_card)
        oc.setContentsMargins(16, 12, 16, 12)
        oc.setSpacing(8)
        self.opt_title = StrongBodyLabel(self.t('optimization'))
        oc.addWidget(self.opt_title)

        frow = QHBoxLayout()
        self.fps_label = BodyLabel(self.t('fps'))
        frow.addWidget(self.fps_label)
        frow.addStretch()
        self.opt_btn = PushButton(self.t('optimize'))
        self.opt_btn.setFixedWidth(90)
        self.opt_btn.clicked.connect(self._optimize_fps)
        frow.addWidget(self.opt_btn)
        oc.addLayout(frow)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        oc.addWidget(sep)

        grow = QHBoxLayout()
        self.gfx_label = BodyLabel(self.t('gfx'))
        grow.addWidget(self.gfx_label)
        grow.addStretch()
        self.apply_gfx_btn = PushButton(self.t('apply_low'))
        self.apply_gfx_btn.setFixedWidth(90)
        self.apply_gfx_btn.clicked.connect(self._apply_graphics)
        grow.addWidget(self.apply_gfx_btn)
        self.restore_gfx_btn = PushButton(self.t('restore'))
        self.restore_gfx_btn.setFixedWidth(90)
        self.restore_gfx_btn.clicked.connect(self._restore_graphics)
        grow.addWidget(self.restore_gfx_btn)
        oc.addLayout(grow)
        right.addWidget(opt_card)

        # Stretch
        stretch_card = CardWidget()
        sc = QVBoxLayout(stretch_card)
        sc.setContentsMargins(16, 12, 16, 12)
        sc.setSpacing(8)
        self.stretch_title = StrongBodyLabel(self.t('stretch'))
        sc.addWidget(self.stretch_title)

        resrow = QHBoxLayout()
        self.res_label = BodyLabel(self.t('resolution'))
        resrow.addWidget(self.res_label)
        resrow.addStretch()
        self.link_btn = PushButton("🔗")
        self.link_btn.setFixedSize(30, 30)
        self.link_btn.setToolTip("Link stretch to Play")
        self.link_btn.clicked.connect(self._toggle_stretch_link)
        resrow.addWidget(self.link_btn)
        self._res_options = self._build_res_options()
        self.res_combo = ComboBox()
        self.res_combo.addItems(self._res_options)
        self.res_combo.setFixedWidth(200)
        self.res_combo.currentTextChanged.connect(self._on_res_change)
        resrow.addWidget(self.res_combo)
        sc.addLayout(resrow)

        # Restore last res
        last_res = self.config.get('last_resolution', '')
        init_opt = self._res_options[0] if self._res_options else ""
        if last_res == 'custom':
            init_opt = "Custom"
        elif last_res:
            for o in self._res_options:
                if last_res in o:
                    init_opt = o
                    break
        self.res_combo.setCurrentText(init_opt)

        # Custom resolution
        self.custom_res_widget = QWidget()
        cr = QHBoxLayout(self.custom_res_widget)
        cr.setContentsMargins(0, 0, 0, 0)
        cr.addWidget(BodyLabel("W × H:"))
        self.custom_w_entry = LineEdit()
        self.custom_w_entry.setPlaceholderText("1440")
        self.custom_w_entry.setFixedWidth(70)
        cw = self.config.get('custom_width', '')
        if cw:
            self.custom_w_entry.setText(str(cw))
        cr.addWidget(self.custom_w_entry)
        cr.addWidget(BodyLabel("×"))
        self.custom_h_entry = LineEdit()
        self.custom_h_entry.setPlaceholderText("1080")
        self.custom_h_entry.setFixedWidth(70)
        ch = self.config.get('custom_height', '')
        if ch:
            self.custom_h_entry.setText(str(ch))
        cr.addWidget(self.custom_h_entry)
        self.save_custom_btn = PushButton("Save")
        self.save_custom_btn.setFixedWidth(56)
        self.save_custom_btn.clicked.connect(self._save_custom_resolution)
        cr.addWidget(self.save_custom_btn)
        cr.addStretch()
        self.custom_res_widget.setVisible(last_res == 'custom')
        sc.addWidget(self.custom_res_widget)

        srow = QHBoxLayout()
        self.stretch_btn = PushButton(self.t('apply_stretch'))
        self.stretch_btn.clicked.connect(self._apply_stretch)
        srow.addWidget(self.stretch_btn)
        self.revert_btn = PushButton(self.t('revert_stretch'))
        self.revert_btn.setFixedWidth(90)
        self.revert_btn.clicked.connect(self._revert_stretch)
        srow.addWidget(self.revert_btn)
        sc.addLayout(srow)
        self.stretch_hint_label = CaptionLabel(self.t('stretch_hint'))
        sc.addWidget(self.stretch_hint_label)
        right.addWidget(stretch_card)

        # Log
        log_card = CardWidget()
        lgc = QVBoxLayout(log_card)
        lgc.setContentsMargins(16, 12, 16, 12)
        lgc.setSpacing(6)
        self.log_title = StrongBodyLabel(self.t('log'))
        lgc.addWidget(self.log_title)
        self.log_box = TextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(80)
        lgc.addWidget(self.log_box)
        right.addWidget(log_card, 1)  # stretches to fill

        columns.addLayout(right, 1)
        root.addLayout(columns, 1)

    # ─────────────────────────────────────
    #  Tray
    # ─────────────────────────────────────
    def _setup_tray(self):
        icon_path = os.path.join(BIN_DIR, 'icon.ico')
        icon = QIcon(icon_path) if os.path.exists(icon_path) else \
            self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
        self.tray_icon = QSystemTrayIcon(icon, self)
        menu = QMenu()
        menu.addAction("Show HiddenDisplay").triggered.connect(self._show_from_tray)
        menu.addAction("Quit").triggered.connect(self._quit_from_tray)
        self.tray_icon.setContextMenu(menu)
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
            emergency_cleanup(self._get_paks_dir())
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

    # ─────────────────────────────────────
    #  Language
    # ─────────────────────────────────────
    def _change_language(self, choice):
        self.lang = 'vi' if choice == 'VI' else 'en'
        self.config['language'] = self.lang
        save_config(self.config)
        self._refresh_texts()

    def _refresh_texts(self):
        self.dev_label.setText(f"v{APP_VERSION}  ·  {self.t('developed_by')}")
        self.folder_title.setText(self.t('game_folder'))
        self.browse_btn.setText(self.t('browse'))
        self.mods_title.setText(self.t('mods'))
        self.chk_blood.setText(self.t('blood'))
        self.chk_vng.setText(self.t('vng'))
        self.launch_title.setText(self.t('launch'))
        self.launch_btn.setText(self.t('play'))
        self.riot_browse_btn.setText(self.t('riot_browse'))
        self.log_title.setText(self.t('log'))
        self.opt_title.setText(self.t('optimization'))
        self.fps_label.setText(self.t('fps'))
        self.opt_btn.setText(self.t('optimize'))
        self.gfx_label.setText(self.t('gfx'))
        self.apply_gfx_btn.setText(self.t('apply_low'))
        self.restore_gfx_btn.setText(self.t('restore'))
        self.stretch_title.setText(self.t('stretch'))
        self.res_label.setText(self.t('resolution'))
        self.stretch_btn.setText(self.t('apply_stretch'))
        self.revert_btn.setText(self.t('revert_stretch'))
        self.stretch_hint_label.setText(self.t('stretch_hint'))
        custom_riot = self.config.get('riot_client_path', '')
        riot = find_riot_client(custom_riot)
        self.riot_label.setText(
            self.t('riot_found') if riot else self.t('riot_not_found'))
        self.riot_label.setStyleSheet(
            f"color: {'#22c55e' if riot else '#ef4444'};")
        self._update_path_status()

    # ─────────────────────────────────────
    #  Game Folder
    # ─────────────────────────────────────
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
        path = QFileDialog.getExistingDirectory(
            self, "Select VALORANT Folder", r"C:\Riot Games")
        if path:
            self.path_entry.setText(path)
            self.config['game_path'] = path
            save_config(self.config)
            self._update_path_status()

    def _browse_riot_client(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select RiotClientServices.exe",
            r"C:\Riot Games\Riot Client",
            "Executable (RiotClientServices.exe);;All Files (*.*)")
        if path and os.path.exists(path):
            self.config['riot_client_path'] = path
            save_config(self.config)
            self.riot_label.setText(self.t('riot_found'))
            self.riot_label.setStyleSheet("color: #22c55e;")

    def _update_path_status(self):
        custom = self.path_entry.text().strip()
        if custom:
            paks = self._resolve_paks_dir(custom)
            if paks:
                self.path_status.setText(f"{self.t('custom_path')}: {custom}")
                self.path_status.setStyleSheet("color: #22c55e;")
                self.config['game_path'] = custom
                save_config(self.config)
                return
            self.path_status.setText(f"{self.t('path_not_found')}: {custom}")
            self.path_status.setStyleSheet("color: #ef4444;")
            return
        if os.path.exists(DEFAULT_PAKS_DIR):
            self.path_status.setText(
                f"{self.t('auto_detected')}: C:\\Riot Games\\VALORANT")
            self.path_status.setStyleSheet("color: #22c55e;")
        else:
            self.path_status.setText(self.t('path_not_found'))
            self.path_status.setStyleSheet("color: #ef4444;")

    # ─────────────────────────────────────
    #  Log
    # ─────────────────────────────────────
    def _log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{ts}] {msg}")

    # ─────────────────────────────────────
    #  Launch
    # ─────────────────────────────────────
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
                    f'cmd /c start "" "{riot_exe}" '
                    '--launch-product=valorant --launch-patchline=live',
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
        if not self.stretch_active:
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
        InfoBar.error(
            title=self.t('error'), content=msg,
            orient=Qt.Orientation.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=5000, parent=self)

    def _show_info(self, title, msg):
        InfoBar.success(
            title=title, content=msg,
            orient=Qt.Orientation.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=5000, parent=self)

    def _ask_yes_no(self, title, msg):
        r = QMessageBox.question(
            self, title, msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return r == QMessageBox.StandardButton.Yes

    # ─────────────────────────────────────
    #  Optimization
    # ─────────────────────────────────────
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
                paks_dir, '..', '..', 'Binaries', 'Win64',
                'VALORANT-Win64-Shipping.exe'))
            if os.path.exists(exe):
                exe_path = exe
        results = run_all_optimizations(exe_path)
        ok_count = sum(1 for ok, _ in results.values() if ok)
        details = [f"  [{'OK' if ok else 'FAIL'}] {n}: {m}"
                   for n, (ok, m) in results.items()]
        self._show_info(self.t('results'),
            f"{ok_count}/{len(results)} applied:\n" +
            "\n".join(details) + f"\n\n{self.t('restart_pc')}")

    def _apply_graphics(self):
        ok, msg = apply_low_preset(os.path.join(BIN_DIR, 'GameUserSettings.ini'))
        self._show_info(self.t('gfx'), msg) if ok else self._show_error(msg)

    def _restore_graphics(self):
        ok, msg = restore_settings()
        self._show_info(self.t('gfx'), msg) if ok else self._show_error(msg)

    # ─────────────────────────────────────
    #  Stretch
    # ─────────────────────────────────────
    def _build_res_options(self):
        opts = []
        for k, v in STRETCH_RESOLUTIONS.items():
            opts.append("Custom" if k == 'custom'
                        else f"{v['label']}  —  {v['desc']}")
        return opts

    def _toggle_stretch_link(self):
        self.stretch_linked = not self.stretch_linked
        self._log("Stretch linked — applies on Play"
                  if self.stretch_linked else "Stretch unlinked")

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
            w, h = int(self.custom_w_entry.text()), int(self.custom_h_entry.text())
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
        dlg = QDialog(self)
        dlg.setWindowTitle("One-Time Setup Required")
        dlg.setFixedSize(520, 420)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(12)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.addWidget(TitleLabel("Custom Resolution Setup"))
        sub = CaptionLabel(f"Resolution {width}x{height} not in display mode list")
        sub.setStyleSheet("color: #ef4444;")
        lay.addWidget(sub)
        lay.addWidget(BodyLabel(
            "One-time setup in NVIDIA Control Panel:\n\n"
            "1. Click \"Open NVIDIA CP\" below\n"
            "2. Go to:  Display  >  Change Resolution\n"
            "3. Click \"Customize...\"\n"
            "4. Check \"Enable resolutions not exposed by the display\"\n"
            "5. Click \"Create Custom Resolution\"\n"
            f"6. Set Horizontal pixels: {width}\n"
            f"7. Set Vertical lines: {height}\n"
            "8. Click Test, then OK\n"
            "9. Come back and click Apply Stretch again"))
        br = QHBoxLayout()
        ob = PrimaryPushButton("Open NVIDIA CP")
        ob.clicked.connect(lambda: (self._log(open_nvidia_control_panel()[1]), dlg.close()))
        br.addWidget(ob)
        cb = PushButton("Close")
        cb.clicked.connect(dlg.close)
        br.addWidget(cb)
        lay.addLayout(br)
        dlg.exec()

    def _revert_stretch(self):
        self._log("Reverting stretch...")
        ok = revert_stretch(self.native_w, self.native_h, self._log)
        if ok:
            self.stretch_active = False
            self._log("Reverted — restart VALORANT for changes")
        else:
            self._log("Nothing to revert")
