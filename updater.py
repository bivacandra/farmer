"""
Auto-Updater module for Tantra Online Farmer Macro.
Checks GitHub Releases for new versions, downloads TantraFarmer.exe,
and seamlessly applies updates on Windows.
"""

import os
import sys
import json
import re
import urllib.request
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Callable, Tuple

GITHUB_REPO = "bivacandra/farmer"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def parse_version(ver_str: str) -> Tuple[int, ...]:
    """Extracts integer tuple from version string like 'v1.0.5' -> (1, 0, 5)."""
    parts = re.findall(r"\d+", ver_str)
    return tuple(int(p) for p in parts) if parts else (0,)


def check_for_updates(current_version: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    """
    Checks GitHub Releases API for a newer version.
    Returns update info dict if a newer version is available, else None.
    """
    try:
        req = urllib.request.Request(
            LATEST_RELEASE_API,
            headers={"User-Agent": "TantraFarmer-AutoUpdater", "Accept": "application/vnd.github.v3+json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode("utf-8"))

        latest_tag = data.get("tag_name", "").strip()
        if not latest_tag:
            return None

        current_tuple = parse_version(current_version)
        latest_tuple = parse_version(latest_tag)

        if latest_tuple <= current_tuple:
            return None

        # Locate TantraFarmer.exe asset
        download_url = None
        asset_size = 0
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if name.lower() == "tantrafarmer.exe":
                download_url = asset.get("browser_download_url")
                asset_size = asset.get("size", 0)
                break

        # Fallback if TantraFarmer.exe directly not found (e.g. only zip present)
        if not download_url:
            for asset in data.get("assets", []):
                if asset.get("name", "").lower().endswith(".exe"):
                    download_url = asset.get("browser_download_url")
                    asset_size = asset.get("size", 0)
                    break

        if not download_url:
            return None

        return {
            "current_version": current_version,
            "latest_version": latest_tag,
            "release_name": data.get("name", latest_tag),
            "release_notes": data.get("body", ""),
            "download_url": download_url,
            "asset_size": asset_size,
            "html_url": data.get("html_url", "")
        }
    except Exception as e:
        print(f"[Updater] Error checking for updates: {e}")
        return None


def download_update(
    download_url: str,
    target_dir: Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    cancel_flag: Optional[Callable[[], bool]] = None
) -> Path:
    """
    Downloads the new executable into target_dir/TantraFarmer_update.exe.
    Calls progress_callback(downloaded_bytes, total_bytes) periodically.
    """
    target_file = target_dir / "TantraFarmer_update.exe"
    if target_file.exists():
        try:
            target_file.unlink()
        except Exception:
            pass

    req = urllib.request.Request(
        download_url,
        headers={"User-Agent": "TantraFarmer-AutoUpdater"}
    )

    with urllib.request.urlopen(req, timeout=30.0) as resp:
        total_size = int(resp.headers.get("content-length", 0))
        downloaded = 0
        chunk_size = 64 * 1024  # 64 KB

        with open(target_file, "wb") as f:
            while True:
                if cancel_flag and cancel_flag():
                    f.close()
                    try:
                        target_file.unlink()
                    except Exception:
                        pass
                    raise InterruptedError("Unduhan dibatalkan oleh pengguna.")

                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total_size)

    return target_file


def apply_update_and_restart(update_file: Path) -> None:
    """
    Replaces the current executable with the new one and restarts the application.
    Uses a temporary Windows batch file to handle process release and replacement.
    """
    if getattr(sys, "frozen", False):
        target_exe = Path(sys.executable).resolve()
    else:
        # Running in dev mode (python gui.py)
        # In dev mode, we just simulate or launch target if exists
        target_exe = update_file.parent / "TantraFarmer.exe"
        if not target_exe.exists():
            print(f"[Updater] Dev mode: update downloaded at {update_file}")
            return

    bat_file = update_file.parent / "updater.bat"
    
    bat_content = f"""@echo off
setlocal
echo Menyiapkan pembaruan Tantra Farmer Macro...
timeout /t 1 /nobreak > nul

:RETRY
move /y "{update_file.name}" "{target_exe.name}" > nul 2>&1
if exist "{update_file.name}" (
    timeout /t 1 /nobreak > nul
    goto RETRY
)

start "" "{target_exe.name}"
del "%~f0"
exit
"""
    try:
        with open(bat_file, "w", encoding="ascii") as f:
            f.write(bat_content)

        if sys.platform == "win32":
            # DETACHED_PROCESS = 0x00000008, CREATE_NO_WINDOW = 0x08000000
            flags = 0x00000008 | 0x08000000
            subprocess.Popen(
                ["cmd.exe", "/c", str(bat_file.name)],
                cwd=str(update_file.parent),
                creationflags=flags,
                close_fds=True
            )
        else:
            # Fallback for testing on Linux
            subprocess.Popen(
                ["sh", "-c", f"sleep 1 && mv '{update_file}' '{target_exe}'"],
                cwd=str(update_file.parent)
            )

        # Terminate current app cleanly
        os._exit(0)
    except Exception as e:
        print(f"[Updater] Gagal menjalankan skrip pembaruan: {e}")
        raise e
