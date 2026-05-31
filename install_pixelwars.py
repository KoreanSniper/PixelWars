from __future__ import annotations

import json
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path


RELEASES_URL = "https://api.github.com/repos/KoreanSniper/PixelWars/releases"
INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PixelWars"
TARGET_EXE = INSTALL_DIR / "PixelWars.exe"
VERSION_FILE = INSTALL_DIR / "version.txt"
PRESERVED_DIR_NAMES = ("saves", "territory_images")


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


def fetch_latest_release() -> tuple[str, str, str | None]:
    request = urllib.request.Request(RELEASES_URL, headers={"User-Agent": "PixelWarsInstaller"})
    with urllib.request.urlopen(request) as response:
        releases = json.loads(response.read().decode("utf-8"))
    for release in releases:
        if release.get("draft"):
            continue
        assets = release.get("assets", [])
        sha_url = next((str(asset["browser_download_url"]) for asset in assets if asset.get("name") == "PixelWars.exe.sha256"), None)
        for asset in release.get("assets", []):
            if asset.get("name") == "PixelWars.exe":
                return str(release["tag_name"]), str(asset["browser_download_url"]), sha_url
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def fetch_expected_sha256(url: str | None) -> str | None:
    if not url:
        return None
    request = urllib.request.Request(url, headers={"User-Agent": "PixelWarsInstaller"})
    with urllib.request.urlopen(request) as response:
        text = response.read().decode("utf-8", errors="replace").strip()
    match = re.search(r"\b[a-fA-F0-9]{64}\b", text)
    return match.group(0).lower() if match else None


def validate_install_dir() -> None:
    install = INSTALL_DIR.resolve()
    local_appdata = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))).resolve()
    if install.name != "PixelWars" or local_appdata not in install.parents:
        raise RuntimeError(f"Refusing to modify unexpected install path: {install}")


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


def create_shortcuts(enable_startup: bool = False) -> None:
    user_profile = Path(os.environ.get("USERPROFILE", str(Path.home())))
    appdata = Path(os.environ.get("APPDATA", user_profile / "AppData" / "Roaming"))
    create_shortcut(user_profile / "Desktop" / "PixelWars.lnk")
    if not enable_startup:
        return
    startup = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup.mkdir(parents=True, exist_ok=True)
    create_shortcut(startup / "PixelWars.lnk")


def stop_running_game() -> None:
    subprocess.run(
        ["taskkill", "/f", "/im", "PixelWars.exe", "/t"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def backup_user_data() -> Path | None:
    existing = [INSTALL_DIR / name for name in PRESERVED_DIR_NAMES if (INSTALL_DIR / name).exists()]
    if not existing:
        return None
    backup_root = INSTALL_DIR.with_name(f"PixelWars_user_data_backup_{datetime.now():%Y%m%d_%H%M%S}")
    backup_root.mkdir(parents=True, exist_ok=True)
    for source in existing:
        target = backup_root / source.name
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    return backup_root


def restore_user_data(backup_root: Path | None) -> None:
    if backup_root is None or not backup_root.exists():
        return
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    for item in backup_root.iterdir():
        target = INSTALL_DIR / item.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(item), str(target))
    shutil.rmtree(backup_root, ignore_errors=True)


def reinstall(latest_version: str, download_url: str, sha_url: str | None) -> None:
    validate_install_dir()
    stop_running_game()
    backup_root = backup_user_data()
    try:
        if INSTALL_DIR.exists():
            if INSTALL_DIR.is_dir():
                shutil.rmtree(INSTALL_DIR)
            else:
                INSTALL_DIR.unlink()
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        restore_user_data(backup_root)
        download(download_url, TARGET_EXE)
        expected_sha = fetch_expected_sha256(sha_url)
        if expected_sha:
            actual_sha = sha256_file(TARGET_EXE)
            if actual_sha != expected_sha:
                TARGET_EXE.unlink(missing_ok=True)
                raise RuntimeError("Downloaded PixelWars.exe failed SHA-256 verification.")
        else:
            print("Warning: PixelWars.exe.sha256 was not found; skipping hash verification.")
        VERSION_FILE.write_text(latest_version, encoding="utf-8")
    except Exception:
        restore_user_data(backup_root)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="PixelWars installer/updater")
    parser.add_argument("--startup", action="store_true", help="Register PixelWars in Windows startup.")
    parser.add_argument("--no-launch", action="store_true", help="Do not start PixelWars after install/update.")
    args = parser.parse_args()

    print("PixelWars installer/updater")
    print(f"Install path: {INSTALL_DIR}")
    try:
        latest_version, download_url, sha_url = fetch_latest_release()
        installed_version = read_installed_version()
        print(f"Installed version: {installed_version or 'not installed'}")
        print(f"Latest version:    {latest_version}")
        if is_older(installed_version, latest_version):
            print("Installing latest version...")
            reinstall(latest_version, download_url, sha_url)
        else:
            print("PixelWars is already up to date.")
        create_shortcuts(enable_startup=args.startup)
        print("Desktop shortcut enabled.")
        if args.startup:
            print("Startup shortcut enabled.")
        else:
            print("Startup shortcut skipped. Run with --startup to enable it.")
        if not args.no_launch:
            print("Starting PixelWars...")
            subprocess.Popen([str(TARGET_EXE)], cwd=str(INSTALL_DIR))
    except Exception as exc:
        print(f"Install/update failed: {exc}")
        input("Press Enter to exit...")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
