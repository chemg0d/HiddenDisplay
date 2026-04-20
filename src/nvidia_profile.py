"""
Applies NVIDIA driver settings to the VALORANT profile via a patched
nvidiaProfileInspector.exe that finds the correct profile by executable
(handles both _GLOBAL_DRIVER_PROFILE and existing Valorant profiles).
"""
import os
import sys
import subprocess


# Setting IDs from NPI's NvApiDriverSettings.h
SETTING_AA_TRANSPARENCY_SS = 0x10D48A85  # Antialiasing - Transparency Supersampling
SETTING_AUTO_LOD_BIAS      = 0x00638E8F  # Driver Controlled LOD Bias (must be OFF for manual)
SETTING_LOD_BIAS           = 0x00738E8F  # Texture filtering - LOD Bias

# Values
AA_MODE_REPLAY_MODE_ALL = 0x00000008
AUTO_LOD_BIAS_OFF       = 0x00000000

LOD_PRESETS = {
    'low':       0x00000008,  # +1 in NPI display
    'medium':    0x00000010,  # +2
    'high':      0x00000018,  # +3
    'valocraft': 0x00000036,  # custom ValoCraft value
}

VALORANT_EXE = "VALORANT-Win64-Shipping.exe"
VALORANT_FALLBACK_PROFILE = "Valorant"


def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_npi_exe():
    return os.path.join(_get_base_dir(), 'bin', 'npi', 'nvidiaProfileInspector.exe')


def apply_valorant_profile(lod_key: str):
    """Apply NVIDIA settings to VALORANT profile. Returns (ok, message).

    Uses the patched NPI CLI:
        nvidiaProfileInspector.exe -applyExe <exe> <fallbackProfile> <id>=<val> ...

    This finds the profile currently owning VALORANT-Win64-Shipping.exe and
    applies settings to it. If the exe is in _GLOBAL_DRIVER_PROFILE only,
    a new "Valorant" profile is created and the exe is added to it.
    """
    lod_key = lod_key.lower()
    if lod_key not in LOD_PRESETS:
        return False, f"Unknown preset: {lod_key}"

    npi_exe = _get_npi_exe()
    if not os.path.exists(npi_exe):
        return False, f"NPI not found: {npi_exe}"

    lod_value = LOD_PRESETS[lod_key]
    cmd = [
        npi_exe,
        '-applyExe', VALORANT_EXE, VALORANT_FALLBACK_PROFILE,
        f'0x{SETTING_AA_TRANSPARENCY_SS:08X}=0x{AA_MODE_REPLAY_MODE_ALL:08X}',
        f'0x{SETTING_AUTO_LOD_BIAS:08X}=0x{AUTO_LOD_BIAS_OFF:08X}',
        f'0x{SETTING_LOD_BIAS:08X}=0x{lod_value:08X}',
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            profile_info = result.stdout.strip() or f"profile for {VALORANT_EXE}"
            return True, f"Applied NVIDIA profile ({lod_key}) — {profile_info}"
        err = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        return False, f"NPI failed: {err}"
    except subprocess.TimeoutExpired:
        return False, "NPI timed out"
    except Exception as e:
        return False, f"NPI error: {e}"
