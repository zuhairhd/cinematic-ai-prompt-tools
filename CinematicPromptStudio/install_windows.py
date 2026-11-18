"""Install app files on the requested drive; keep Python's venv on the local disk."""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path(r"Z:\zuhairhd\Backup\prompt")
FILES = ("app.py", "core.py", "choices.py", "requirements.txt", "LEARNING_GUIDE.txt", "README.txt",
         "example_project.json", "install_windows.py", "INSTALL_TO_Z_DRIVE.cmd",
         "START.cmd", "TEST_REPORT.txt", "tests/test_core.py", "tests/test_gui.py", "tests/test_choices.py")


def main():
    if os.name != "nt":
        raise RuntimeError("This installer is for Windows. On Linux/macOS, follow README.txt.")
    if sys.version_info < (3, 10):
        raise RuntimeError("Install Python 3.10 or newer, including Tcl/Tk support.")
    source = Path(__file__).resolve().parent
    target = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else TARGET
    if not Path(target.anchor).exists():
        raise RuntimeError(f"The drive {target.anchor} is not available. Connect the Z: drive and run this installer as your normal Windows user (not Administrator).")
    import tkinter  # Fail early if this Python was installed without Tk.
    target.mkdir(parents=True, exist_ok=True)
    same = source.resolve() == target.resolve()
    if not same:
        backup = target / ("_previous_install_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
        for relative in FILES:
            src, dest = source / relative, target / relative
            if not src.is_file():
                raise RuntimeError(f"Missing {relative}. Extract the complete ZIP before installing.")
            if dest.is_file():
                old = backup / relative
                old.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, old)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    # Network drives are suitable for code/backups, but venv executables work better locally.
    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CinematicPromptStudio"
    venv = local / "venv"
    python = venv / "Scripts" / "python.exe"
    if not python.is_file():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(target / "requirements.txt")], check=True)
    subprocess.run([str(python), "-c", "import tkinter; from PIL import Image, ImageTk"], check=True)
    print(f"\nInstalled successfully in: {target}")
    print("Next time double-click START.cmd in that folder.")
    subprocess.Popen([str(python), str(target / "app.py")], cwd=str(target))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError, ImportError) as exc:
        print(f"\nInstallation could not finish: {exc}", file=sys.stderr)
        raise SystemExit(1)
