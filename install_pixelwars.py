from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path


RELEASES_URL = "https://api.github.com/repos/KoreanSniper/PixelWars/releases"
INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PixelWars"
TARGET_EXE = INSTALL_DIR / "PixelWars.exe"
VERSION_FILE = INSTALL_DIR / "version.txt"


def version_key(version: str) -> tuple[int, int, int, int]:
    cleaned = version.strip().lower().removeprefix("v")
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", cleaned)
    if not match:
        return (0, 0, 0, 0)
    major, minor, patch = (int(part) for part in match.groups())
    stage = 0 if any(label in cleaned for label in ("alpha", "beta", "rc")) else 1
    return major, minor, patch, stage


def is_older(installed: str | None, latest: str) -> bool:
    if not installed:
        return True
    return version_key(installed) < version_key(latest)


def read_installed_version() -> str | None:
    if not VERSION_FILE.exists() or not TARGET_EXE.exists():
        return None
    return VERSION_FILE.read_text(encoding="utf-8", errors="ignore").strip() or None


def fetch_latest_release() -> tuple[str, str]:
    request = urllib.request.Request(RELEASES_URL, headers={"User-Agent": "PixelWarsInstaller"})
    with urllib.request.urlopen(request) as response:
        releases = json.loads(response.read().decode("utf-8"))
    for release in releases:
        if release.get("draft"):
            continue
        for asset in release.get("assets", []):
            if asset.get("name") == "PixelWars.exe":
                return str(release["tag_name"]), str(asset["browser_download_url"])
    raise RuntimeError("No release asset named PixelWars.exe was found.")


def download(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "PixelWarsInstaller"})
    with urllib.request.urlopen(request) as response, target.open("wb") as output:
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


def ps_quote(path: Path) -> str:
    return str(path).replace("'", "''")


def create_shortcut(shortcut: Path) -> None:
    script = (
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$shortcut = $shell.CreateShortcut('{ps_quote(shortcut)}'); "
        f"$shortcut.TargetPath = '{ps_quote(TARGET_EXE)}'; "
        f"$shortcut.WorkingDirectory = '{ps_quote(INSTALL_DIR)}'; "
        "$shortcut.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def create_shortcuts() -> None:
    user_profile = Path(os.environ.get("USERPROFILE", str(Path.home())))
    appdata = Path(os.environ.get("APPDATA", user_profile / "AppData" / "Roaming"))
    create_shortcut(user_profile / "Desktop" / "PixelWars.lnk")
    startup = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup.mkdir(parents=True, exist_ok=True)
    create_shortcut(startup / "PixelWars.lnk")


def reinstall(latest_version: str, download_url: str) -> None:
    if INSTALL_DIR.exists():
        shutil.rmtree(INSTALL_DIR)
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    download(download_url, TARGET_EXE)
    VERSION_FILE.write_text(latest_version, encoding="utf-8")


def main() -> int:
    print("PixelWars installer/updater")
    print(f"Install path: {INSTALL_DIR}")
    try:
        latest_version, download_url = fetch_latest_release()
        installed_version = read_installed_version()
        print(f"Installed version: {installed_version or 'not installed'}")
        print(f"Latest version:    {latest_version}")
        if is_older(installed_version, latest_version):
            print("Installing latest version...")
            reinstall(latest_version, download_url)
        else:
            print("PixelWars is already up to date.")
        create_shortcuts()
        print("Startup shortcut enabled.")
        print("Starting PixelWars...")
        subprocess.Popen([str(TARGET_EXE)], cwd=str(INSTALL_DIR))
    except Exception as exc:
        print(f"Install/update failed: {exc}")
        input("Press Enter to exit...")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
