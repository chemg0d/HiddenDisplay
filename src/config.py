import json
import os
import sys
import glob


def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_config_dir():
    """Config file goes next to the exe (not in temp), so it persists."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CONFIG_FILE = os.path.join(_get_config_dir(), 'config.json')
BIN_DIR = os.path.join(_get_base_dir(), 'bin')

DEFAULT_CONFIG = {
    'game_path': '',
    'riot_client_path': '',
    'enable_blood': True,
    'enable_vng_remove': True,
    'minimize_to_tray': True,
    'language': 'en',
    'custom_width': '',
    'custom_height': '',
    'last_resolution': '',
    'gpu_notif_no_nvidia_shown': False,
    'gpu_notif_hybrid_shown': False,
    'gpu_override': 'auto',
    'welcome_shown': False,
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except (json.JSONDecodeError, IOError):
            pass
    # First run — create config.json immediately with defaults
    config = DEFAULT_CONFIG.copy()
    save_config(config)
    return config


def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def detect_valorant_path():
    """Try to auto-detect VALORANT installation path."""
    common_paths = [
        r'C:\Riot Games\VALORANT\live',
        r'D:\Riot Games\VALORANT\live',
        r'E:\Riot Games\VALORANT\live',
        r'F:\Riot Games\VALORANT\live',
        r'C:\Program Files\Riot Games\VALORANT\live',
        r'D:\Program Files\Riot Games\VALORANT\live',
        r'C:\Program Files (x86)\Riot Games\VALORANT\live',
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path

    # Check registry for Riot Client install path
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Riot Game valorant.live')
        install_location, _ = winreg.QueryValueEx(key, 'InstallLocation')
        winreg.CloseKey(key)
        if os.path.exists(install_location):
            return install_location
    except (OSError, ImportError):
        pass

    return ''


def get_paks_dir(valorant_path):
    """Get the Paks directory inside the VALORANT installation."""
    paks = os.path.join(valorant_path, 'ShooterGame', 'Content', 'Paks')
    if os.path.exists(paks):
        return paks
    return None
