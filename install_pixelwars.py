from __future__ import annotations

import os
import subprocess
import sys
import urllib.request
from pathlib import Path


VERSION = "v1.0.0-alpha"
DOWNLOAD_URL = f"https://github.com/KoreanSniper/PixelWars/releases/download/{VERSION}/PixelWars.exe"
INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PixelWars"
TARGET_EXE = INSTALL_DIR / "PixelWars.exe"


def download(url: str, target: Path) -> None:
    with urllib.request.urlopen(url) as response, target.open("wb") as output:
        total = int(response.headers.get("Content-Length", "0") or 0)
        done = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            done += len(chunk)
            if total:
                percent = int(done * 100 / total)
                print(f"\rDownloading PixelWars.exe... {percent:3d}%", end="", flush=True)
        print()


def create_shortcut() -> None:
    desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    shortcut = desktop / "PixelWars.lnk"
    script = (
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$shortcut = $shell.CreateShortcut('{shortcut}'); "
        f"$shortcut.TargetPath = '{TARGET_EXE}'; "
        f"$shortcut.WorkingDirectory = '{INSTALL_DIR}'; "
        "$shortcut.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    print("PixelWars alpha 1.0.0 installer")
    print(f"Install path: {INSTALL_DIR}")
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    try:
        download(DOWNLOAD_URL, TARGET_EXE)
    except Exception as exc:
        print(f"Download failed: {exc}")
        input("Press Enter to exit...")
        return 1
    create_shortcut()
    print("Install complete.")
    print("Starting PixelWars...")
    try:
        subprocess.Popen([str(TARGET_EXE)], cwd=str(INSTALL_DIR))
    except Exception as exc:
        print(f"Could not start PixelWars: {exc}")
        input("Press Enter to exit...")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
