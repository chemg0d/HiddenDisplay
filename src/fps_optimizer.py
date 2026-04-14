import subprocess
import ctypes
import sys


def is_admin():
    """Check if running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def create_restore_point(name="RestorePointForHiddenDisplay"):
    """Create a Windows System Restore Point before applying optimizations."""
    if not is_admin():
        return False, "Requires administrator privileges to create restore point"
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             f'Checkpoint-Computer -Description "{name}" -RestorePointType "MODIFY_SETTINGS"'],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return True, f"Restore point '{name}' created"
        return False, f"Failed: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, "Restore point creation timed out (may still be in progress)"
    except Exception as e:
        return False, str(e)


def set_ultimate_performance_power_plan():
    """Activate or create the Ultimate Performance power plan."""
    try:
        # Try to activate Ultimate Performance directly
        result = subprocess.run(
            ['powercfg', '/setactive', 'e9a42b02-d5df-448d-aa00-03f14749eb61'],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            # Duplicate the scheme first (unhides it on Win10/11 Home)
            subprocess.run(
                ['powercfg', '/duplicatescheme', 'e9a42b02-d5df-448d-aa00-03f14749eb61'],
                capture_output=True, text=True
            )
            subprocess.run(
                ['powercfg', '/setactive', 'e9a42b02-d5df-448d-aa00-03f14749eb61'],
                capture_output=True, text=True
            )
        return True, "Ultimate Performance power plan activated"
    except Exception as e:
        return False, str(e)


def disable_visual_effects():
    """Set Windows visual effects to Best Performance + reduce menu delay."""
    try:
        import winreg
        # Visual effects to best performance
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects',
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, 'VisualFXSetting', 0, winreg.REG_DWORD, 2)
        winreg.CloseKey(key)

        # Reduce menu show delay
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Control Panel\Desktop',
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, 'MenuShowDelay', 0, winreg.REG_SZ, '0')
        winreg.SetValueEx(key, 'ForegroundLockTimeout', 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)

        # Disable animations
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Control Panel\Desktop\WindowMetrics',
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, 'MinAnimate', 0, winreg.REG_SZ, '0')
        winreg.CloseKey(key)

        # Disable listview alpha select
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced',
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, 'ListviewAlphaSelect', 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)

        return True, "Visual effects set to Best Performance"
    except Exception as e:
        return False, str(e)


def disable_game_dvr_and_bar():
    """Disable Xbox Game Bar, Game DVR, and Game Mode overhead."""
    try:
        import winreg
        # Disable Game Bar
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\GameBar',
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, 'UseNexusForGameBarEnabled', 0, winreg.REG_DWORD, 0)
        winreg.SetValueEx(key, 'AllowAutoGameMode', 0, winreg.REG_DWORD, 0)
        winreg.SetValueEx(key, 'AllowGameMode', 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)

        # Disable Game DVR
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\GameDVR',
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, 'AppCaptureEnabled', 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)

        return True, "Game Bar & DVR disabled"
    except Exception as e:
        return False, str(e)


def disable_nagle_algorithm():
    """Disable Nagle's algorithm for lower network latency (requires admin)."""
    if not is_admin():
        return False, "Requires administrator privileges"
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r'SYSTEM\CurrentControlSet\Services\Tcpip\Parameters',
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, 'TcpAckFrequency', 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, 'TCPNoDelay', 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
        return True, "Nagle's algorithm disabled (lower latency)"
    except Exception as e:
        return False, str(e)


def disable_startup_delay():
    """Remove startup delay for faster boot."""
    try:
        import winreg
        key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize'
        )
        winreg.SetValueEx(key, 'StartupDelayInMSec', 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)
        return True, "Startup delay disabled"
    except Exception as e:
        return False, str(e)


def disable_prefetch_superfetch():
    """Disable Prefetch and Superfetch (requires admin)."""
    if not is_admin():
        return False, "Requires administrator privileges"
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r'SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters',
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, 'EnablePrefetcher', 0, winreg.REG_DWORD, 0)
        winreg.SetValueEx(key, 'EnableSuperfetch', 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)
        return True, "Prefetch & Superfetch disabled"
    except Exception as e:
        return False, str(e)


def optimize_system_responsiveness():
    """Set multimedia system responsiveness to maximum (requires admin)."""
    if not is_admin():
        return False, "Requires administrator privileges"
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile',
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, 'SystemResponsiveness', 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)
        return True, "System responsiveness optimized for gaming"
    except Exception as e:
        return False, str(e)


def disable_fullscreen_optimizations(exe_path):
    """Disable fullscreen optimizations for a specific executable."""
    try:
        import winreg
        key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers'
        )
        winreg.SetValueEx(key, exe_path, 0, winreg.REG_SZ, '~ DISABLEDXMAXIMIZEDWINDOWEDMODE')
        winreg.CloseKey(key)
        return True, "Fullscreen optimizations disabled"
    except Exception as e:
        return False, str(e)


def enable_hardware_gpu_scheduling():
    """Enable hardware-accelerated GPU scheduling (requires admin + restart)."""
    if not is_admin():
        return False, "Requires administrator privileges"
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r'SYSTEM\CurrentControlSet\Control\GraphicsDrivers',
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, 'HwSchMode', 0, winreg.REG_DWORD, 2)
        winreg.CloseKey(key)
        return True, "Hardware GPU scheduling enabled (restart required)"
    except Exception as e:
        return False, str(e)


def set_timer_resolution():
    """Request high timer resolution for smoother frametimes."""
    try:
        ntdll = ctypes.windll.ntdll
        # Set to 0.5ms (5000 * 100ns)
        ntdll.NtSetTimerResolution(5000, True, ctypes.byref(ctypes.c_ulong()))
        return True, "Timer resolution set to 0.5ms"
    except Exception as e:
        return False, str(e)


def clean_temp_files():
    """Clear temporary files to free up space."""
    import os
    import shutil
    temp_dirs = [
        os.environ.get('TEMP', ''),
        os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Temp'),
    ]
    cleared = 0
    for temp_dir in temp_dirs:
        if not temp_dir or not os.path.exists(temp_dir):
            continue
        for item in os.listdir(temp_dir):
            path = os.path.join(temp_dir, item)
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    cleared += 1
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                    cleared += 1
            except (PermissionError, OSError):
                pass
    return True, f"Cleared {cleared} temp items"


def run_all_optimizations(valorant_exe_path=None):
    """Run all FPS optimizations and return results."""
    results = {}
    results['power_plan'] = set_ultimate_performance_power_plan()
    results['visual_effects'] = disable_visual_effects()
    results['game_dvr_bar'] = disable_game_dvr_and_bar()
    results['nagle'] = disable_nagle_algorithm()
    results['startup_delay'] = disable_startup_delay()
    results['prefetch'] = disable_prefetch_superfetch()
    results['responsiveness'] = optimize_system_responsiveness()
    results['timer_resolution'] = set_timer_resolution()
    results['gpu_scheduling'] = enable_hardware_gpu_scheduling()
    results['temp_files'] = clean_temp_files()

    if valorant_exe_path:
        results['fullscreen_opt'] = disable_fullscreen_optimizations(valorant_exe_path)

    return results
