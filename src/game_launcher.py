import os
import time
import json
import shutil
import ssl
import psutil
import subprocess
import urllib.request
import base64
import threading


GAME_PROCESS = 'VALORANT-Win64-Shipping.exe'

RIOT_CLIENT_PATHS = [
    r'C:\Riot Games\Riot Client\RiotClientServices.exe',
    r'D:\Riot Games\Riot Client\RiotClientServices.exe',
    r'E:\Riot Games\Riot Client\RiotClientServices.exe',
    r'F:\Riot Games\Riot Client\RiotClientServices.exe',
    r'C:\Program Files\Riot Games\Riot Client\RiotClientServices.exe',
    r'D:\Program Files\Riot Games\Riot Client\RiotClientServices.exe',
    r'C:\Program Files (x86)\Riot Games\Riot Client\RiotClientServices.exe',
    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Riot Games', 'Riot Client', 'RiotClientServices.exe'),
]

LOCKFILE_PATH = os.path.join(
    os.environ.get('LOCALAPPDATA', ''), 'Riot Games', 'Riot Client', 'Config', 'lockfile'
)

BLOOD_FILES = [
    'MatureData-WindowsClient.pak',
    'MatureData-WindowsClient.sig',
    'MatureData-WindowsClient.ucas',
    'MatureData-WindowsClient.utoc',
]

VNG_FILES = [
    'VNGLogo-WindowsClient.pak',
    'VNGLogo-WindowsClient.sig',
    'VNGLogo-WindowsClient.ucas',
    'VNGLogo-WindowsClient.utoc',
]


def _get_backup_dir():
    """Get the backup directory for originals (next to exe or project root)."""
    import sys
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, '.originals_backup')


def _cleanup_watcher(paks_dir, backup_dir, injected_blood, deleted_vng, log_func=None):
    """
    Runs in background after injection. Waits for VALORANT to exit, then
    restores all original files so the game folder is clean (no ban risk).
    """
    log = log_func or (lambda msg: None)

    # Wait for game to exit — poll every 2s
    while is_game_running():
        time.sleep(2)

    log("VALORANT closed — restoring original files...")

    restored = 0
    removed = 0

    # Remove our injected blood files (or restore originals if they existed)
    for fname in injected_blood:
        game_path = os.path.join(paks_dir, fname)
        backup_path = os.path.join(backup_dir, fname)
        try:
            if os.path.exists(backup_path):
                # Original existed — restore it
                shutil.copy2(backup_path, game_path)
                os.remove(backup_path)
                restored += 1
            elif os.path.exists(game_path):
                # No original existed — remove our injected file to keep Paks clean
                os.remove(game_path)
                removed += 1
        except Exception as e:
            log(f"  Error restoring {fname}: {e}")

    # Restore deleted VNG files
    for fname in deleted_vng:
        game_path = os.path.join(paks_dir, fname)
        backup_path = os.path.join(backup_dir, fname)
        try:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, game_path)
                os.remove(backup_path)
                restored += 1
        except Exception as e:
            log(f"  Error restoring {fname}: {e}")

    log(f"Cleanup done — {restored} restored, {removed} removed")

    # Clean up empty backup dir
    try:
        if os.path.exists(backup_dir) and not os.listdir(backup_dir):
            os.rmdir(backup_dir)
    except OSError:
        pass


def emergency_cleanup(paks_dir=None):
    """
    Emergency restore on HD exit if game is still running and mods are injected.
    Called from main_window on app close.
    """
    backup_dir = _get_backup_dir()
    if not os.path.exists(backup_dir):
        return

    if not paks_dir:
        paks_dir = r'C:\Riot Games\VALORANT\live\ShooterGame\Content\Paks'

    if not os.path.exists(paks_dir):
        return

    try:
        for fname in os.listdir(backup_dir):
            backup_path = os.path.join(backup_dir, fname)
            game_path = os.path.join(paks_dir, fname)
            try:
                shutil.copy2(backup_path, game_path)
                os.remove(backup_path)
            except Exception:
                pass

        # Remove any blood files we injected that didn't have backups
        for fname in BLOOD_FILES:
            game_path = os.path.join(paks_dir, fname)
            if os.path.exists(game_path) and not os.path.exists(os.path.join(backup_dir, fname)):
                try:
                    os.remove(game_path)
                except Exception:
                    pass

        if os.path.exists(backup_dir) and not os.listdir(backup_dir):
            os.rmdir(backup_dir)
    except Exception:
        pass


def find_riot_client(custom_path=None):
    """Find RiotClientServices.exe."""
    if custom_path and os.path.exists(custom_path):
        return custom_path

    try:
        import winreg
        for reg_path in (
            r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Riot Game valorant.live',
            r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Riot Game league_of_legends.live',
            r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Riot Game valorant.live',
        ):
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                install_loc, _ = winreg.QueryValueEx(key, 'InstallLocation')
                winreg.CloseKey(key)
                riot_dir = os.path.join(os.path.dirname(os.path.dirname(install_loc)),
                                        'Riot Client', 'RiotClientServices.exe')
                if os.path.exists(riot_dir):
                    return riot_dir
            except OSError:
                pass
    except ImportError:
        pass

    try:
        installs_json = os.path.join(os.environ.get('PROGRAMDATA', ''), 'Riot Games', 'RiotClientInstalls.json')
        if os.path.exists(installs_json):
            with open(installs_json, 'r') as f:
                data = json.load(f)
            for key, val in data.items():
                if isinstance(val, str) and val.endswith('.exe') and os.path.exists(val):
                    return val
                if isinstance(val, dict):
                    for v in val.values():
                        if isinstance(v, str) and 'RiotClientServices' in v and os.path.exists(v):
                            return v
    except Exception:
        pass

    for proc in psutil.process_iter(['name', 'exe']):
        try:
            if proc.info['name'] == 'RiotClientServices.exe' and proc.info['exe']:
                return proc.info['exe']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    for path in RIOT_CLIENT_PATHS:
        if os.path.exists(path):
            return path

    return None


def _read_lockfile():
    if not os.path.exists(LOCKFILE_PATH):
        return None, None
    try:
        with open(LOCKFILE_PATH, 'r') as f:
            content = f.read().strip()
        parts = content.split(':')
        if len(parts) >= 5:
            return int(parts[2]), parts[3]
    except Exception:
        pass
    return None, None


def _riot_api_launch(port, password, log_func=None):
    """Call Riot Client local API to launch VALORANT."""
    url = f"https://127.0.0.1:{port}/product-launcher/v1/products/valorant/patchlines/live"

    try:
        result = subprocess.run(
            ['curl', '-sk', '-u', f'riot:{password}', '-X', 'POST', url],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000
        )
        if log_func:
            log_func(f"API response: {result.stdout.strip()}")
        return len(result.stdout.strip()) > 0 and result.returncode == 0
    except FileNotFoundError:
        pass
    except Exception as e:
        if log_func:
            log_func(f"curl failed: {e}")

    # Fallback: urllib
    auth = base64.b64encode(f"riot:{password}".encode()).decode()
    req = urllib.request.Request(url, method='POST')
    req.add_header('Authorization', f'Basic {auth}')
    req.add_header('Content-Type', 'application/json')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        resp = urllib.request.urlopen(req, data=b'', context=ctx, timeout=10)
        body = resp.read().decode()
        if log_func:
            log_func(f"API response: {resp.status} {body}")
        return True
    except urllib.error.HTTPError as e:
        if log_func:
            log_func(f"API error: {e.code}")
        return False
    except Exception as e:
        if log_func:
            log_func(f"API exception: {e}")
        return False


def _riot_api_ping(port, password):
    """Check if Riot Client API is responsive."""
    url = f"https://127.0.0.1:{port}/riotclient/region-locale"
    try:
        result = subprocess.run(
            ['curl', '-sk', '-u', f'riot:{password}', url],
            capture_output=True, text=True, timeout=3,
            creationflags=0x08000000
        )
        return result.returncode == 0 and len(result.stdout.strip()) > 2
    except Exception:
        return False


def _is_riot_client_running():
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] == 'RiotClientServices.exe':
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def is_game_running():
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] == GAME_PROCESS:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


class GameLaunchWorker:
    """
    Launches VALORANT via Riot Client local API, then injects pak mods.
    Uses plain threading + callbacks (compatible with CustomTkinter).
    """

    def __init__(self, blood_dir, paks_dir, enable_blood=True, enable_vng_remove=True,
                 custom_riot_path=None, on_log=None, on_ok=None, on_err=None):
        self.blood_dir = blood_dir
        self.paks_dir = paks_dir
        self.enable_blood = enable_blood
        self.enable_vng_remove = enable_vng_remove
        self.custom_riot_path = custom_riot_path
        self.on_log = on_log or (lambda msg: None)
        self.on_ok = on_ok or (lambda: None)
        self.on_err = on_err or (lambda msg: None)
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _log(self, msg):
        self.on_log(msg)

    def _kill_riot_client(self):
        riot_names = (
            'RiotClientServices.exe', 'Riot Client.exe',
            'RiotClientCrashHandler.exe', 'RiotClientUx.exe', 'RiotClientUxRender.exe',
        )
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] in riot_names:
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(1.5)
        if os.path.exists(LOCKFILE_PATH):
            try:
                os.remove(LOCKFILE_PATH)
            except OSError:
                pass

    def _start_riot_client(self, riot_exe):
        self._log("Starting Riot Client...")
        try:
            subprocess.Popen(
                f'cmd /c start "" "{riot_exe}" --launch-product=valorant --launch-patchline=live',
                shell=True, creationflags=0x08000000
            )
        except Exception as e:
            self.on_err(f"Failed to start Riot Client: {e}")
            return False

        # Wait for lockfile
        self._log("Waiting for Riot Client...")
        for _ in range(60):
            if os.path.exists(LOCKFILE_PATH) and _is_riot_client_running():
                break
            time.sleep(0.25)
        else:
            self.on_err("Riot Client did not start in time.")
            return False

        # Wait until API is responsive
        port, password = _read_lockfile()
        if not port:
            return False

        self._log("Waiting for Riot Client to be ready...")
        for i in range(20):
            if _riot_api_ping(port, password):
                self._log("Riot Client ready.")
                return True
            time.sleep(1)

        return True

    def _run(self):
        # Step 1: Find Riot Client
        riot_exe = find_riot_client(self.custom_riot_path)
        if not riot_exe:
            self.on_err("Riot Client not found.")
            return

        self._log(f"Riot Client: {riot_exe}")

        # Step 2: Kill existing Riot Client for clean state
        if _is_riot_client_running():
            self._log("Closing Riot Client...")
            self._kill_riot_client()

        # Step 3: Start fresh
        if not self._start_riot_client(riot_exe):
            return

        # Step 4: Trigger Play via API
        port, password = _read_lockfile()
        api_success = False
        if port and password:
            self._log("Triggering Play...")
            for attempt in range(3):
                api_success = _riot_api_launch(port, password, self._log)
                if api_success:
                    break
                time.sleep(1)

        if api_success:
            self._log("Play triggered — waiting for game...")
        else:
            self._log("API failed — please click Play manually")

        # Step 5: Poll for game process
        timeout = 300
        start = time.time()
        while time.time() - start < timeout:
            if is_game_running():
                self._log("VALORANT DETECTED — injecting mods!")
                break
            time.sleep(0.05)
        else:
            self.on_err("Timeout: VALORANT did not start within 5 minutes.")
            return

        # Step 6: Backup originals + inject mods
        backup_dir = _get_backup_dir()
        os.makedirs(backup_dir, exist_ok=True)

        t0 = time.perf_counter()
        errors = []
        injected_blood = []  # track what we copied to clean up later
        deleted_vng = []     # track what we deleted to restore later

        if self.enable_blood:
            for fname in BLOOD_FILES:
                src = os.path.join(self.blood_dir, fname)
                dst = os.path.join(self.paks_dir, fname)
                if os.path.exists(src):
                    try:
                        # Backup original if it exists
                        if os.path.exists(dst):
                            shutil.copy2(dst, os.path.join(backup_dir, fname))
                        shutil.copy2(src, dst)
                        injected_blood.append(fname)
                    except Exception as e:
                        errors.append(f"Copy {fname}: {e}")

        if self.enable_vng_remove:
            for fname in VNG_FILES:
                fpath = os.path.join(self.paks_dir, fname)
                if os.path.exists(fpath):
                    try:
                        # Backup the file we're about to delete
                        shutil.copy2(fpath, os.path.join(backup_dir, fname))
                        os.remove(fpath)
                        deleted_vng.append(fname)
                    except Exception as e:
                        errors.append(f"Delete {fname}: {e}")

        elapsed_ms = (time.perf_counter() - t0) * 1000

        if errors:
            self._log(f"Mods applied in {elapsed_ms:.0f}ms with errors:")
            for err in errors:
                self._log(f"  - {err}")
        else:
            self._log(f"Mods applied in {elapsed_ms:.0f}ms — SUCCESS!")

        # Step 7: Start cleanup watcher (runs until game exits)
        self._log("Cleanup watcher active — files will be restored on game close")
        cleanup_thread = threading.Thread(
            target=_cleanup_watcher,
            args=(self.paks_dir, backup_dir, injected_blood, deleted_vng, self._log),
            daemon=True
        )
        cleanup_thread.start()

        self.on_ok()
