"""
GPU detection via PowerShell's Get-CimInstance Win32_VideoController.
Classifies the system into: nvidia_only, hybrid, non_nvidia, unknown.
"""
import subprocess


def detect_gpus():
    """Query installed video controllers. Returns dict with flags + names."""
    names = []
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             'Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name'],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        pass

    has_nvidia = any('nvidia' in n.lower() for n in names)
    has_intel = any('intel' in n.lower() for n in names)
    has_amd = any(('amd' in n.lower()) or ('radeon' in n.lower()) for n in names)

    return {
        'names': names,
        'nvidia': has_nvidia,
        'intel': has_intel,
        'amd': has_amd,
    }


def get_gpu_category(gpus):
    """Returns 'nvidia_only', 'hybrid', 'non_nvidia', or 'unknown'."""
    if not gpus['names']:
        return 'unknown'
    if gpus['nvidia'] and (gpus['intel'] or gpus['amd']):
        return 'hybrid'
    if gpus['nvidia']:
        return 'nvidia_only'
    if gpus['intel'] or gpus['amd']:
        return 'non_nvidia'
    return 'unknown'
