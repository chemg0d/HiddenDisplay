import sys
import os
import ctypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


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


def main():
    if not is_admin():
        run_as_admin()
        return

    from src.main_window import MainWindow
    app = MainWindow()
    app.mainloop()


if __name__ == '__main__':
    main()
