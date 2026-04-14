import os
import glob
import shutil


def find_all_game_settings_paths():
    """Find ALL VALORANT GameUserSettings.ini paths (all accounts)."""
    local_appdata = os.environ.get('LOCALAPPDATA', '')
    if not local_appdata:
        return []

    base = os.path.join(local_appdata, 'VALORANT', 'Saved', 'Config')
    if not os.path.exists(base):
        return []

    pattern = os.path.join(base, '*', 'Windows', 'GameUserSettings.ini')
    return glob.glob(pattern)


def find_game_settings_path():
    """Find first VALORANT GameUserSettings.ini (for backwards compat)."""
    paths = find_all_game_settings_paths()
    return paths[0] if paths else None


def backup_settings_file(settings_path):
    """Backup a single GameUserSettings.ini."""
    backup_path = settings_path + '.hd_backup'
    if not os.path.exists(backup_path):
        shutil.copy2(settings_path, backup_path)
    return backup_path


def apply_low_preset(preset_file):
    """Replace GameUserSettings.ini with low-quality preset for ALL accounts."""
    paths = find_all_game_settings_paths()
    if not paths:
        return False, "Could not find any GameUserSettings.ini. Launch VALORANT at least once first."

    if not os.path.exists(preset_file):
        return False, f"Preset file not found: {preset_file}"

    applied = 0
    for settings_path in paths:
        backup_settings_file(settings_path)
        shutil.copy2(preset_file, settings_path)
        applied += 1

    return True, f"Low graphics preset applied to {applied} account(s)"


def restore_settings():
    """Restore original GameUserSettings.ini for ALL accounts from backups."""
    paths = find_all_game_settings_paths()
    if not paths:
        return False, "Could not find any GameUserSettings.ini"

    restored = 0
    no_backup = 0
    for settings_path in paths:
        backup_path = settings_path + '.hd_backup'
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, settings_path)
            restored += 1
        else:
            no_backup += 1

    if restored == 0:
        return False, "No backups found. Cannot restore."
    msg = f"Restored {restored} account(s)"
    if no_backup:
        msg += f" ({no_backup} had no backup)"
    return True, msg
