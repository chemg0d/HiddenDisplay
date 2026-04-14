"""
TrueStretch — Custom stretched resolution for VALORANT.
Works by:
  1. Setting NVIDIA scaling to Full-screen via registry (requires admin)
  2. Modifying GameUserSettings.ini for each account
  3. Making config files read-only so game can't overwrite
"""

import os
import glob
import stat
import ctypes
import subprocess


STRETCH_RESOLUTIONS = {
    "1440x1080": {"w": 1440, "h": 1080, "label": "1440 x 1080", "desc": "4:3"},
    "1280x960":  {"w": 1280, "h": 960,  "label": "1280 x 960",  "desc": "4:3"},
    "1024x768":  {"w": 1024, "h": 768,  "label": "1024 x 768",  "desc": "4:3 classic"},
    "custom":    {"w": 0,    "h": 0,    "label": "Custom",       "desc": "Enter your own"},
}


def _get_config_base():
    return os.path.join(os.environ.get('LOCALAPPDATA', ''), 'VALORANT', 'Saved', 'Config')


SKIP_FOLDERS = {'CrashReportClient', 'WindowsClient'}


def _get_account_folders():
    """Find all account folder paths (skip CrashReportClient, WindowsClient, username folders)."""
    base = _get_config_base()
    if not os.path.exists(base):
        return []

    folders = []
    for folder in os.listdir(base):
        if folder in SKIP_FOLDERS:
            continue
        parts = folder.split('-')
        if len(parts) >= 2 and len(parts[1]) > 20:
            continue
        full = os.path.join(base, folder)
        if os.path.isdir(full):
            folders.append(full)
    return folders


def _get_windowsclient_settings():
    """Get the global WindowsClient/GameUserSettings.ini path."""
    base = _get_config_base()
    ini = os.path.join(base, 'WindowsClient', 'GameUserSettings.ini')
    return ini if os.path.exists(ini) else None


def _make_writable(path):
    """Remove read-only flag from a file."""
    if os.path.exists(path):
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)


def _make_readonly(path):
    """Set read-only flag on a file."""
    if os.path.exists(path):
        os.chmod(path, stat.S_IREAD)


def _is_readonly(path):
    """Check if file is read-only."""
    if not os.path.exists(path):
        return False
    return not os.access(path, os.W_OK)


def _backup_file(path):
    """Backup a file if not already backed up."""
    backup = path + '.stretch_backup'
    if not os.path.exists(backup) and os.path.exists(path):
        with open(path, 'r') as f:
            content = f.read()
        with open(backup, 'w') as f:
            f.write(content)


def _modify_game_settings(ini_path, width, height, log_func=None):
    """
    Modify GameUserSettings.ini (account profile):
    - Resolution to target W x H
    - bShouldLetterbox=False (Fill)
    - LastConfirmedFullscreenMode=0, PreferredFullscreenMode=0
    - FullscreenMode=2 added after HDRDisplayOutputNits
    - Set read-only
    """
    log = log_func or (lambda msg: None)
    _make_writable(ini_path)
    _backup_file(ini_path)

    with open(ini_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    found_fullscreen_mode = False
    found_hdr_line_idx = -1

    for line in lines:
        stripped = line.strip()

        # Resolution
        if stripped.startswith('ResolutionSizeX='):
            new_lines.append(f'ResolutionSizeX={width}\n'); continue
        if stripped.startswith('ResolutionSizeY='):
            new_lines.append(f'ResolutionSizeY={height}\n'); continue
        if stripped.startswith('LastUserConfirmedResolutionSizeX='):
            new_lines.append(f'LastUserConfirmedResolutionSizeX={width}\n'); continue
        if stripped.startswith('LastUserConfirmedResolutionSizeY='):
            new_lines.append(f'LastUserConfirmedResolutionSizeY={height}\n'); continue

        # Fullscreen modes
        if stripped.startswith('FullscreenMode='):
            new_lines.append('FullscreenMode=2\n')
            found_fullscreen_mode = True; continue
        if stripped.startswith('LastConfirmedFullscreenMode='):
            new_lines.append('LastConfirmedFullscreenMode=0\n'); continue
        if stripped.startswith('PreferredFullscreenMode='):
            new_lines.append('PreferredFullscreenMode=0\n'); continue

        # Aspect Ratio = Fill
        if stripped.startswith('bShouldLetterbox='):
            new_lines.append('bShouldLetterbox=False\n'); continue
        if stripped.startswith('bLastConfirmedShouldLetterbox='):
            new_lines.append('bLastConfirmedShouldLetterbox=False\n'); continue

        # Track HDRDisplayOutputNits for inserting FullscreenMode
        if stripped.startswith('HDRDisplayOutputNits='):
            found_hdr_line_idx = len(new_lines)

        new_lines.append(line)

    # Insert FullscreenMode=2 after HDRDisplayOutputNits if not found
    if not found_fullscreen_mode and found_hdr_line_idx >= 0:
        new_lines.insert(found_hdr_line_idx + 1, 'FullscreenMode=2\n')

    with open(ini_path, 'w') as f:
        f.writelines(new_lines)
    # NOTE: Do NOT lock read-only — VALORANT needs to save other settings
    # (like Show Mature Content) to this file. Stretch values are re-applied
    # on every Play VALORANT click instead.
    return True


def _modify_windowsclient_settings(ini_path, width, height, log_func=None):
    """
    Modify WindowsClient/GameUserSettings.ini (global):
    - Same resolution + letterbox + fullscreen changes
    - No FullscreenMode line (not present in this file)
    - Set read-only
    """
    log = log_func or (lambda msg: None)
    _make_writable(ini_path)
    _backup_file(ini_path)

    with open(ini_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        stripped = line.strip()

        if stripped.startswith('ResolutionSizeX='):
            new_lines.append(f'ResolutionSizeX={width}\n'); continue
        if stripped.startswith('ResolutionSizeY='):
            new_lines.append(f'ResolutionSizeY={height}\n'); continue
        if stripped.startswith('LastUserConfirmedResolutionSizeX='):
            new_lines.append(f'LastUserConfirmedResolutionSizeX={width}\n'); continue
        if stripped.startswith('LastUserConfirmedResolutionSizeY='):
            new_lines.append(f'LastUserConfirmedResolutionSizeY={height}\n'); continue
        if stripped.startswith('LastConfirmedFullscreenMode='):
            new_lines.append('LastConfirmedFullscreenMode=0\n'); continue
        if stripped.startswith('PreferredFullscreenMode='):
            new_lines.append('PreferredFullscreenMode=0\n'); continue
        if stripped.startswith('bShouldLetterbox='):
            new_lines.append('bShouldLetterbox=False\n'); continue
        if stripped.startswith('bLastConfirmedShouldLetterbox='):
            new_lines.append('bLastConfirmedShouldLetterbox=False\n'); continue

        new_lines.append(line)

    with open(ini_path, 'w') as f:
        f.writelines(new_lines)
    # NOTE: Do NOT lock read-only — stretch is re-applied on every Play click.
    return True


def _modify_riot_settings(ini_path, log_func=None):
    """
    Modify RiotUserSettings.ini (account/Windows folder):
    - Append graphics quality settings if not present
    - Set read-only
    """
    log = log_func or (lambda msg: None)
    _make_writable(ini_path)
    _backup_file(ini_path)

    RIOT_SETTINGS = {
        'EAresIntSettingName::MaterialQuality': '0',
        'EAresIntSettingName::TextureQuality': '0',
        'EAresIntSettingName::DetailQuality': '0',
        'EAresIntSettingName::UIQuality': '0',
        'EAresIntSettingName::AnisotropicFiltering': '1',
        'EAresIntSettingName::BloomQuality': '0',
        'EAresBoolSettingName::DisableDistortion': 'True',
        'EAresBoolSettingName::LimitFramerateOnBattery': 'False',
        'EAresBoolSettingName::LimitFramerateInMenu': 'False',
        'EAresBoolSettingName::LimitFramerateInBackground': 'False',
        'EAresIntSettingName::NvidiaReflexLowLatencySetting': '2',
    }

    with open(ini_path, 'r') as f:
        content = f.read()

    for key, val in RIOT_SETTINGS.items():
        if key in content:
            # Update existing line
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                if line.startswith(key + '='):
                    new_lines.append(f'{key}={val}')
                else:
                    new_lines.append(line)
            content = '\n'.join(new_lines)
        else:
            # Append
            content = content.rstrip('\n') + f'\n{key}={val}'

    content = content.rstrip('\n') + '\n'

    with open(ini_path, 'w') as f:
        f.write(content)
    # NOTE: Do NOT set RiotUserSettings.ini read-only — VALORANT stores
    # Show Mature Content flag and other user prefs here. Locking it causes
    # the "requires a restart" popup to loop infinitely.
    return True


import ctypes as _ctypes_stretch

class _DEVMODE(_ctypes_stretch.Structure):
    _fields_ = [
        ("dmDeviceName", _ctypes_stretch.c_wchar * 32),
        ("dmSpecVersion", _ctypes_stretch.c_short),
        ("dmDriverVersion", _ctypes_stretch.c_short),
        ("dmSize", _ctypes_stretch.c_ushort),
        ("dmDriverExtra", _ctypes_stretch.c_ushort),
        ("dmFields", _ctypes_stretch.c_uint),
        ("dmPositionX", _ctypes_stretch.c_int),
        ("dmPositionY", _ctypes_stretch.c_int),
        ("dmDisplayOrientation", _ctypes_stretch.c_int),
        ("dmDisplayFixedOutput", _ctypes_stretch.c_int),
        ("dmColor", _ctypes_stretch.c_short),
        ("dmDuplex", _ctypes_stretch.c_short),
        ("dmYResolution", _ctypes_stretch.c_short),
        ("dmTTOption", _ctypes_stretch.c_short),
        ("dmCollate", _ctypes_stretch.c_short),
        ("dmFormName", _ctypes_stretch.c_wchar * 32),
        ("dmLogPixels", _ctypes_stretch.c_short),
        ("dmBitsPerPel", _ctypes_stretch.c_int),
        ("dmPelsWidth", _ctypes_stretch.c_int),
        ("dmPelsHeight", _ctypes_stretch.c_int),
        ("dmDisplayFlags", _ctypes_stretch.c_int),
        ("dmDisplayFrequency", _ctypes_stretch.c_int),
        ("dmICMMethod", _ctypes_stretch.c_int),
        ("dmICMIntent", _ctypes_stretch.c_int),
        ("dmMediaType", _ctypes_stretch.c_int),
        ("dmDitherType", _ctypes_stretch.c_int),
        ("dmReserved1", _ctypes_stretch.c_int),
        ("dmReserved2", _ctypes_stretch.c_int),
        ("dmPanningWidth", _ctypes_stretch.c_int),
        ("dmPanningHeight", _ctypes_stretch.c_int),
    ]

_user32 = _ctypes_stretch.windll.user32


def get_native_resolution():
    """Get current desktop resolution."""
    dm = _DEVMODE()
    dm.dmSize = _ctypes_stretch.sizeof(dm)
    _user32.EnumDisplaySettingsW(None, -1, _ctypes_stretch.byref(dm))
    return dm.dmPelsWidth, dm.dmPelsHeight


def is_resolution_supported(width, height):
    """Check if a resolution is in Windows' supported display mode list."""
    dm = _DEVMODE()
    dm.dmSize = _ctypes_stretch.sizeof(dm)
    i = 0
    while _user32.EnumDisplaySettingsW(None, i, _ctypes_stretch.byref(dm)):
        if dm.dmPelsWidth == width and dm.dmPelsHeight == height:
            return True
        i += 1
    return False


def open_nvidia_control_panel():
    """Open NVIDIA Control Panel. Returns (success, message)."""
    nvcp_paths = [
        r"C:\Program Files\NVIDIA Corporation\Control Panel Client\nvcplui.exe",
        r"C:\Windows\System32\nvcplui.exe",
    ]
    for exe in nvcp_paths:
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe], creationflags=0x08000000)
                return True, "NVIDIA Control Panel opened"
            except Exception:
                continue

    # Try Microsoft Store NVIDIA Control Panel
    try:
        subprocess.Popen(
            ['explorer.exe', 'shell:AppsFolder\\NVIDIACorp.NVIDIAControlPanel_56jybvy8sckqj!NVIDIACorp.NVIDIAControlPanel'],
            creationflags=0x08000000
        )
        return True, "NVIDIA Control Panel opened"
    except Exception:
        pass

    # Fallback to Windows Display Settings
    try:
        os.startfile("ms-settings:display")
        return False, "NVIDIA CP not found. Opened Windows Display Settings."
    except Exception:
        return False, "Could not open display settings"


def _set_desktop_resolution(width, height):
    """Change Windows desktop resolution via Win32 API."""
    dm = _DEVMODE()
    dm.dmSize = _ctypes_stretch.sizeof(dm)
    _user32.EnumDisplaySettingsW(None, -1, _ctypes_stretch.byref(dm))
    dm.dmPelsWidth = width
    dm.dmPelsHeight = height
    dm.dmFields = 0x80000 | 0x100000  # DM_PELSWIDTH | DM_PELSHEIGHT

    test = _user32.ChangeDisplaySettingsExW(None, _ctypes_stretch.byref(dm), None, 0x02, None)
    if test != 0:
        return False, f"Resolution {width}x{height} not supported by display"

    result = _user32.ChangeDisplaySettingsExW(None, _ctypes_stretch.byref(dm), None, 0x01, None)
    if result == 0:
        return True, f"Desktop resolution set to {width}x{height}"
    return False, f"Failed to set resolution (error {result})"


def _restore_desktop_resolution(native_w, native_h):
    """Restore native desktop resolution."""
    return _set_desktop_resolution(native_w, native_h)


def _is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def _restart_display_driver():
    """Restart display adapter to force NVIDIA to reload registry settings."""
    import time
    try:
        # Disable all display adapters
        subprocess.run(
            ['powershell', '-Command',
             "Get-PnpDevice -Class Display | Where-Object { $_.Status -eq 'OK' } | "
             "Disable-PnpDevice -Confirm:$false -ErrorAction SilentlyContinue"],
            capture_output=True, timeout=10, creationflags=0x08000000
        )
        time.sleep(2)
        # Re-enable all display adapters
        subprocess.run(
            ['powershell', '-Command',
             "Get-PnpDevice -Class Display | Where-Object { $_.Status -ne 'OK' } | "
             "Enable-PnpDevice -Confirm:$false -ErrorAction SilentlyContinue"],
            capture_output=True, timeout=10, creationflags=0x08000000
        )
        time.sleep(2)
    except Exception:
        pass


def set_nvidia_scaling_fullscreen(log_func=None):
    """
    Set NVIDIA scaling to Full-screen (value=3) via registry.
    Registry: HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Configuration\...\Scaling
    Values: 1=Aspect ratio, 2=No scaling, 3=Full-screen, 4=Integer scaling
    """
    log = log_func or (lambda msg: None)
    if not _is_admin():
        log("NVIDIA scaling: needs admin — skipping")
        return False

    try:
        ps_script = r"""
$configPath = 'HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Configuration'
$found = 0
Get-ChildItem $configPath -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    $props = $_ | Get-ItemProperty -ErrorAction SilentlyContinue
    if ($props.PSObject.Properties.Name -contains 'Scaling') {
        Set-ItemProperty -Path $_.PSPath -Name 'Scaling' -Value 3 -ErrorAction SilentlyContinue
        $found++
    }
}
Write-Output $found
"""
        result = subprocess.run(
            ['powershell', '-Command', ps_script],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000
        )
        count = result.stdout.strip()
        if count and int(count) > 0:
            log(f"NVIDIA scaling set to Full-screen ({count} display(s))")
            return True
        log("No NVIDIA scaling keys found")
        return False
    except Exception as e:
        log(f"NVIDIA scaling error: {e}")
        return False


def apply_stretch(resolution_key, log_func=None, custom_w=0, custom_h=0):
    """
    Apply stretched resolution:
    1. Save native resolution
    2. Change Windows desktop resolution
    3. Modify GameUserSettings.ini for each account
    4. Make config files read-only
    Returns (success, native_w, native_h) for revert.
    """
    log = log_func or (lambda msg: None)

    if resolution_key == "custom":
        if custom_w <= 0 or custom_h <= 0:
            log("Invalid custom resolution")
            return False, 0, 0
        target_w, target_h = custom_w, custom_h
    else:
        res = STRETCH_RESOLUTIONS.get(resolution_key)
        if not res:
            log(f"Unknown resolution: {resolution_key}")
            return False, 0, 0
        target_w, target_h = res['w'], res['h']

    native_w, native_h = get_native_resolution()
    log(f"Native: {native_w}x{native_h} -> Target: {target_w}x{target_h}")

    # Check if resolution is supported by the display
    if not is_resolution_supported(target_w, target_h):
        log(f"Resolution {target_w}x{target_h} not in display mode list.")
        log("You need to add it in NVIDIA Control Panel first.")
        return "needs_custom_res", native_w, native_h

    # Step 1: Set NVIDIA scaling to Full-screen via registry
    if _is_admin():
        set_nvidia_scaling_fullscreen(log)
    else:
        log("Not admin - NVIDIA scaling skipped")

    # Step 2: Change Windows desktop resolution
    log("Changing desktop resolution...")
    ok, msg = _set_desktop_resolution(target_w, target_h)
    log(f"  {msg}")

    # Step 3: Modify all account GameUserSettings.ini
    account_folders = _get_account_folders()
    if not account_folders:
        log("No VALORANT account configs found. Launch the game at least once.")
        return ok, native_w, native_h

    log(f"Found {len(account_folders)} account(s)")
    applied = 0
    for folder in account_folders:
        folder_name = os.path.basename(folder)
        log(f"  Account: {folder_name}")

        # Modify WindowsClient/GameUserSettings.ini
        game_ini = os.path.join(folder, 'WindowsClient', 'GameUserSettings.ini')
        if os.path.exists(game_ini):
            try:
                _modify_game_settings(game_ini, target_w, target_h, log)
                applied += 1
            except Exception as e:
                log(f"    GameUserSettings error: {e}")

        # Modify Windows/RiotUserSettings.ini
        riot_ini = os.path.join(folder, 'Windows', 'RiotUserSettings.ini')
        if os.path.exists(riot_ini):
            try:
                _modify_riot_settings(riot_ini, log)
            except Exception as e:
                log(f"    RiotUserSettings error: {e}")

    # Step 4: Modify global WindowsClient/GameUserSettings.ini
    wc_ini = _get_windowsclient_settings()
    if wc_ini:
        log("  Global WindowsClient config")
        try:
            _modify_windowsclient_settings(wc_ini, target_w, target_h, log)
        except Exception as e:
            log(f"    Error: {e}")

    if applied > 0:
        log(f"Applied {target_w}x{target_h} to {applied} account(s) + global config")
        log("All config files set to read-only")
        return True, native_w, native_h

    return False, native_w, native_h


def _restore_file(path):
    """Restore a file from .stretch_backup and remove backup."""
    backup = path + '.stretch_backup'
    if os.path.exists(backup):
        _make_writable(path)
        with open(backup, 'r') as f:
            content = f.read()
        with open(path, 'w') as f:
            f.write(content)
        os.remove(backup)
        return True
    _make_writable(path)
    return False


def auto_revert_on_exit(native_w=0, native_h=0, log_func=None):
    """
    LIGHTWEIGHT auto-revert after game exit.
    Only restores desktop resolution — does NOT touch config files.
    This preserves any user changes made in-game (like Show Mature Content)
    that VALORANT may have written to config files during the session.

    Config files retain stretch values but since desktop is native,
    the stretch is visually disabled until next HD Play click.
    """
    log = log_func or (lambda msg: None)
    if native_w > 0 and native_h > 0:
        log(f"Restoring desktop to {native_w}x{native_h}...")
        ok, msg = _restore_desktop_resolution(native_w, native_h)
        log(f"  {msg}")
    return True


def revert_stretch(native_w=0, native_h=0, log_func=None):
    """
    FULL revert — used by manual "Revert" button in UI.
    1. Restore native desktop resolution
    2. Restore all config files from backups
    3. Remove read-only flags
    """
    log = log_func or (lambda msg: None)

    # Step 1: Restore desktop resolution
    if native_w > 0 and native_h > 0:
        log(f"Restoring desktop to {native_w}x{native_h}...")
        ok, msg = _restore_desktop_resolution(native_w, native_h)
        log(f"  {msg}")

    # Step 2: Restore all account configs
    reverted = 0
    for folder in _get_account_folders():
        folder_name = os.path.basename(folder)

        game_ini = os.path.join(folder, 'WindowsClient', 'GameUserSettings.ini')
        if os.path.exists(game_ini) and _restore_file(game_ini):
            log(f"  Restored: {folder_name}/GameUserSettings")
            reverted += 1

        riot_ini = os.path.join(folder, 'Windows', 'RiotUserSettings.ini')
        if os.path.exists(riot_ini) and _restore_file(riot_ini):
            log(f"  Restored: {folder_name}/RiotUserSettings")

    # Step 3: Restore global WindowsClient config
    wc_ini = _get_windowsclient_settings()
    if wc_ini and _restore_file(wc_ini):
        log("  Restored: WindowsClient/GameUserSettings")
        reverted += 1

    log(f"Reverted {reverted} config(s)")
    return True
