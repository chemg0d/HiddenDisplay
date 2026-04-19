import sys
import os
import ctypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MUTEX_NAME = "Global\\HiddenDisplay_SingleInstance"


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    """Re-launch this script as administrator."""
    if getattr(sys, 'frozen', False):
        exe = sys.executable
    else:
        exe = sys.executable
        # When running as python script, pass the script path
        params = f'"{os.path.abspath(__file__)}"'
        ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
        sys.exit(0)

    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, "", None, 1)
    sys.exit(0)


def acquire_single_instance():
    """Create a named mutex to ensure only one instance runs at a time."""
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, MUTEX_NAME)
    last_error = ctypes.windll.kernel32.GetLastError()
    # ERROR_ALREADY_EXISTS = 183
    if last_error == 183:
        ctypes.windll.kernel32.CloseHandle(mutex)
        return None
    return mutex


def main():
    if not is_admin():
        run_as_admin()
        return

    mutex = acquire_single_instance()
    if mutex is None:
        # Another instance is already running
        ctypes.windll.user32.MessageBoxW(
            None, "HiddenDisplay is already running in the tray.",
            "HiddenDisplay", 0x40)
        sys.exit(0)

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    # Enable high DPI scaling
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    from src.main_window import MainWindow
    window = MainWindow()
    window.show()
    exit_code = app.exec()

    # Release mutex on exit
    ctypes.windll.kernel32.ReleaseMutex(mutex)
    ctypes.windll.kernel32.CloseHandle(mutex)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
