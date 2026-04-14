# HiddenDisplay — Engine Documentation

## Tech Stack

- **Language:** Python 3.14
- **GUI Framework:** CustomTkinter (dark theme, native DPI scaling)
- **Threading:** Python threading.Thread + tkinter self.after() for thread-safe UI updates
- **Bundler:** PyInstaller (single-file .exe, all assets embedded)
- **Platform:** Windows 10/11 only

## Dependencies

| Package | Purpose |
|---------|---------|
| customtkinter | GUI framework — dark theme, native DPI scaling, resizable |
| psutil | Process detection (polling for VALORANT-Win64-Shipping.exe) |
| pywin32 | Windows registry manipulation (FPS optimizations) |
| pycaw | Windows Core Audio API (Discord volume — currently unused) |
| comtypes | COM interface support for pycaw |
| Pillow | Icon format conversion during PyInstaller build |
| PyInstaller | Compiles Python + assets into standalone .exe |
| curl (system) | Riot Client local API calls (bundled with Windows 10/11) |

## Project Structure

```
HiddenDisplay/
├── main.py                     # Entry point — launches PyQt5 app
├── build.spec                  # PyInstaller build configuration
├── requirements.txt            # pip dependencies
├── config.json                 # Runtime config (saved next to exe)
│
├── src/
│   ├── main_window.py          # GUI — all UI, translations, event handlers
│   ├── game_launcher.py        # Core engine — launch game + inject mods
│   ├── config.py               # Config load/save, path resolution
│   ├── process_killer.py       # Kill VALORANT/Riot processes
│   ├── fps_optimizer.py        # Windows registry tweaks for FPS
│   ├── graphics_preset.py      # GameUserSettings.ini replacement
│   ├── discord_volume.py       # pycaw Discord volume control (unused)
│   └── pak_manager.py          # Legacy pak manager (replaced by game_launcher)
│
├── bin/
│   ├── icon.ico                # App icon
│   ├── GameUserSettings.ini    # Low-quality graphics preset
│   └── paks/                   # Legacy pak files (unused)
│
├── blood/                      # Blood/corpse mod files
│   ├── MatureData-WindowsClient.pak
│   ├── MatureData-WindowsClient.sig
│   ├── MatureData-WindowsClient.ucas
│   └── MatureData-WindowsClient.utoc
│
├── public/                     # GitHub release folder (closed source)
│   ├── HiddenDisplay.exe
│   ├── blood/
│   ├── README.md
│   └── .gitignore
│
└── docs/
    └── ENGINE.md               # This file
```

## Core Engine — How It Works

### The Problem

VALORANT's Riot Client runs a file integrity check before launching the game. If it detects modified .pak files in `ShooterGame/Content/Paks/`, it triggers a repair and reverts them. So you can't just pre-copy modded files — they'll be deleted before the game starts.

### The Solution — Race Condition Injection

The key insight: the integrity check happens BEFORE `VALORANT-Win64-Shipping.exe` spawns. Once the game process starts, the check has already passed. But the game hasn't loaded pak files yet — it takes time to initialize. This creates a timing window.

### Flow

```
User clicks "PLAY VALORANT"
        │
        ▼
[1] Find RiotClientServices.exe
    Custom path → Registry → RiotClientInstalls.json
      → Running process → Common drive paths
        │
        ▼
[2] Ensure Riot Client is running
    If not running → launch with cmd /c start
    Wait for lockfile at:
      %LOCALAPPDATA%\Riot Games\Riot Client\Config\lockfile
        │
        ▼
[3] Trigger Play via Riot Client Local API
    Read lockfile → format: name:pid:port:password:protocol
    POST https://127.0.0.1:{port}/product-launcher/v1/products/valorant/patchlines/live
    Auth: Basic riot:{password}
    This is equivalent to clicking the Play button in Riot Client UI
        │
        ▼
[4] Poll for game process (every 50ms)
    Loop: psutil.process_iter() looking for
      "VALORANT-Win64-Shipping.exe"
        │
        ▼  (game process detected — integrity check passed)
        │
[5] RACE — inject mods as fast as possible
    ├── Copy blood/*.pak/.sig/.ucas/.utoc → game Paks/
    └── Delete VNGLogo-WindowsClient.pak/.sig/.ucas/.utoc
        │
        ▼  (typically completes in <50ms)
        │
[6] Game engine loads pak files
    Finds our modified blood paks → blood/corpse enabled
    VNG logo files missing → logo skipped
```

### File: `src/game_launcher.py`

This is the core engine. Key components:

**`GameLaunchWorker(QThread)`** — background thread that:
1. Finds `RiotClientServices.exe` (custom path → registry → installs JSON → running process → common paths)
2. If Riot Client not running → starts it with `cmd /c start` (de-elevates from admin)
3. Waits for lockfile to appear (up to 30 seconds)
4. Reads port + auth token from lockfile
5. Calls Riot Client's local HTTPS API to trigger Play (same as clicking Play button)
6. Polls every 50ms for `VALORANT-Win64-Shipping.exe`
7. On detection: copies blood files + deletes VNG files using `shutil.copy2` and `os.remove`
8. Emits Qt signals: `log(str)`, `finished_ok()`, `finished_err(str)`

**Riot Client Local API:** Riot Client runs a local HTTPS server on a random port. The port and auth token are stored in a lockfile at `%LOCALAPPDATA%\Riot Games\Riot Client\Config\lockfile`. Format: `name:pid:port:password:protocol`. We read it and POST to the product-launcher endpoint — equivalent to clicking the Play button in the UI.

**API readiness check:** After starting Riot Client, the lockfile appears before the API is actually responsive. We ping `GET /riotclient/region-locale` every 1s (up to 20s) to confirm the API is ready before calling the launch endpoint. This prevents the first-run issue where the launch API was called too early and silently failed.

**Threading model:** Uses Python's `threading.Thread` with daemon=True. UI updates are dispatched via `self.after(0, callback)` — tkinter's thread-safe mechanism. Previous PyQt5 QThread + pyqtSignal approach was incompatible with CustomTkinter's mainloop (signals were silently lost without a Qt event loop).

**Why curl?** The API uses a self-signed SSL certificate. Python's urllib requires SSL context workarounds that can be flaky. `curl -sk` handles this reliably and is bundled with Windows 10/11. Falls back to urllib if curl is unavailable.

**Why always kill + restart?** When Riot Client is already running, its session state is unpredictable — the launch API may succeed but not actually start the game. A fresh start guarantees a clean state. The kill→start→wait→launch cycle takes ~5-8 seconds.

**Why 50ms polling?** The window between process spawn and pak file loading is small. 50ms gives us ~20 checks per second — fast enough to catch the process within 1-2 frames of it appearing.

**Why `cmd /c start`?** If the tool runs as admin (for FPS optimizations), launching Riot Client directly would also run it as admin, which Riot/Vanguard may reject. `cmd /c start` de-elevates the child process.

**Helper functions:**
- `find_riot_client(custom_path)` — 5-method detection: custom path → registry → RiotClientInstalls.json → running process → common drive paths
- `_read_lockfile()` — parses lockfile format `name:pid:port:password:protocol`, returns `(port, password)`
- `_riot_api_launch(port, password, log_func)` — POST to launch endpoint via curl (primary) or urllib (fallback), with logging
- `_riot_api_ping(port, password)` — GET region-locale to check if API is responsive
- `_is_riot_client_running()` — quick psutil check for RiotClientServices.exe
- `_kill_riot_client()` — kills all Riot processes + deletes stale lockfile

### File: `src/main_window.py`

The GUI built with CustomTkinter. Key architectural decisions:

**CustomTkinter over PyQt5:** Switched from PyQt5 to CustomTkinter to fix DPI scaling issues — text was clipped in GroupBox widgets at 125%/150% Windows scaling. CustomTkinter uses native DPI handling and renders correctly at any scale.

**Translations:** All UI strings are in a `LANG` dict with `'en'` and `'vi'` keys (Vietnamese with diacritics). `self.t('key')` returns the current language string. Language switch is instant — `_refresh_texts()` updates all widget labels via `.configure(text=...)` without rebuilding the UI.

**Game path resolution:** `_resolve_paks_dir(base_path)` tries both `base_path/live/ShooterGame/Content/Paks` and `base_path/ShooterGame/Content/Paks`, so users can point to either `C:\Riot Games\VALORANT` or `C:\Riot Games\VALORANT\live`.

**Riot Client path:** Browse button lets users manually locate `RiotClientServices.exe` if auto-detection fails (non-standard install drives). Saved to config as `riot_client_path`.

**Thread-safe UI updates:** Worker callbacks use `self.after(0, self._log, msg)` to dispatch UI updates from the background thread to tkinter's main thread. Direct widget access from threads would cause crashes.

**Button state feedback:** Optimization buttons start gray and turn blue on success via `_set_btn_blue()` / `_set_btn_gray()` which call `.configure(fg_color=...)` on the CTkButton.

### File: `src/fps_optimizer.py`

Windows system tweaks via registry (`winreg`) and subprocess (`powercfg`, `powershell`):

| Optimization | Method | Requires Admin |
|-------------|--------|---------------|
| Ultimate Performance power plan | `powercfg /setactive` + `/duplicatescheme` | No |
| Disable visual effects | Registry: `VisualFXSetting = 2` | No |
| Reduce menu delay | Registry: `MenuShowDelay = 0` | No |
| Disable Game Bar + DVR | Registry: `UseNexusForGameBarEnabled = 0` | No |
| Disable Nagle's algorithm | Registry: `TCPNoDelay = 1` | Yes |
| Disable Prefetch/Superfetch | Registry: `EnablePrefetcher = 0` | Yes |
| System responsiveness | Registry: `SystemResponsiveness = 0` | Yes |
| Hardware GPU scheduling | Registry: `HwSchMode = 2` | Yes |
| Timer resolution | `ntdll.NtSetTimerResolution(5000)` | No |
| Fullscreen optimizations | Registry: AppCompat flag per exe | No |
| Clean temp files | `os.remove` / `shutil.rmtree` on TEMP dirs | No |
| Restore point | `powershell Checkpoint-Computer` | Yes |

### File: `src/graphics_preset.py`

Replaces `GameUserSettings.ini` for ALL VALORANT accounts:
- Globs `%LOCALAPPDATA%\VALORANT\Saved\Config\*\Windows\GameUserSettings.ini`
- Backs up each to `.hd_backup`
- Copies `bin/GameUserSettings.ini` (720p, all quality = 0) over each one

### File: `src/config.py`

**Path handling for PyInstaller:**
- `sys._MEIPASS` — temp extraction dir (bundled assets: bin/, blood/)
- `os.path.dirname(sys.executable)` — dir where .exe lives (config.json goes here so it persists)

```python
config.json = next to exe (persists)
bin/, blood/ = inside _MEIPASS (temp, bundled in exe)
```

## Build Process

```bash
cd C:\Users\chemg0d\Desktop\HiddenDisplay
C:\Users\chemg0d\AppData\Local\Programs\Python\Python314\Scripts\pyinstaller.exe build.spec --clean --noconfirm
```

`build.spec` bundles:
- `bin/` → icon, GameUserSettings.ini, legacy paks
- `blood/` → blood mod pak files

Output: `dist/HiddenDisplay.exe` (~42 MB single file)

## Config Schema

```json
{
  "game_path": "",
  "enable_blood": true,
  "enable_vng_remove": true,
  "minimize_to_tray": true,
  "language": "en"
}
```

## Key Design Decisions

1. **Single .exe** — no installer, no dependencies, no Python needed. PyInstaller bundles everything including blood pak files.

2. **Race injection over pre-modification** — the original VrC-Support tool had timing issues with Riot's integrity check. Our approach waits for the game process to spawn, guaranteeing the check has passed.

3. **50ms polling** — aggressive but necessary. The window between process spawn and pak loading is narrow. CPU cost is negligible (one `psutil.process_iter()` call every 50ms).

4. **No Firebase/cloud** — the original VrC-Support used Firebase for user accounts. We removed this entirely — the tool is fully offline.

5. **Closed source release** — only the compiled .exe and blood asset files go to GitHub. Source code stays private.
