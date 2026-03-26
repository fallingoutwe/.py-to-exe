#!/usr/bin/env python3
"""Build a Windows executable from a Python script with optional icon selection.

This utility wraps PyInstaller and provides both:
1) a small Tkinter GUI file picker
2) command-line arguments for automation

Examples:
    python py_to_exe_with_icon.py
    python py_to_exe_with_icon.py --script app.py --icon logo.png --name MyApp
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


IMAGE_EXTENSIONS = {".ico", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}


def ensure_pyinstaller_installed() -> None:
    if shutil.which("pyinstaller"):
        return

    print("PyInstaller was not found in PATH.")
    print("Install it with: pip install pyinstaller")
    raise SystemExit(1)


def convert_image_to_ico(icon_path: Path) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    """Return an .ico path. Convert if the selected image is not already .ico."""
    if icon_path.suffix.lower() == ".ico":
        return icon_path, None

    try:
        from PIL import Image  # type: ignore
    except Exception as exc:
        print("Selected icon is not .ico and Pillow is not available to convert it.")
        print("Install Pillow with: pip install pillow")
        raise SystemExit(1) from exc

    temp_dir = tempfile.TemporaryDirectory(prefix="py2exe_icon_")
    output_ico = Path(temp_dir.name) / f"{icon_path.stem}.ico"

    image = Image.open(icon_path)
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    image.save(output_ico, format="ICO")
    return output_ico, temp_dir


def choose_files_with_gui() -> tuple[Path, Path | None, str | None]:
    try:
        import tkinter as tk
        from tkinter import filedialog, simpledialog
    except Exception as exc:
        print("Tkinter is not available. Use command-line arguments instead.")
        raise SystemExit(1) from exc

    root = tk.Tk()
    root.withdraw()
    root.update()

    script_path = filedialog.askopenfilename(
        title="Select Python script",
        filetypes=[("Python files", "*.py")],
    )
    if not script_path:
        raise SystemExit("No script selected. Aborting.")

    icon_path = filedialog.askopenfilename(
        title="Select executable icon/image (optional)",
        filetypes=[("Image files", "*.ico *.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp"), ("All files", "*.*")],
    )

    name = simpledialog.askstring(
        "Executable name",
        "Enter executable name (leave blank to use script filename):",
    )

    root.destroy()

    return Path(script_path), (Path(icon_path) if icon_path else None), (name.strip() if name else None)


def build_executable(script_path: Path, icon_path: Path | None, name: str | None, onefile: bool, windowed: bool) -> int:
    if not script_path.exists() or script_path.suffix.lower() != ".py":
        print(f"Invalid Python script: {script_path}")
        return 1

    ensure_pyinstaller_installed()

    exe_name = name or script_path.stem

    converted_temp_dir: tempfile.TemporaryDirectory[str] | None = None
    icon_to_use: Path | None = None

    if icon_path:
        if not icon_path.exists() or icon_path.suffix.lower() not in IMAGE_EXTENSIONS:
            print(f"Invalid icon/image file: {icon_path}")
            return 1
        icon_to_use, converted_temp_dir = convert_image_to_ico(icon_path)

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--name",
        exe_name,
    ]

    if onefile:
        cmd.append("--onefile")
    if windowed:
        cmd.append("--windowed")
    if icon_to_use:
        cmd.extend(["--icon", str(icon_to_use)])

    cmd.append(str(script_path))

    print("Running:", " ".join(cmd))

    try:
        process = subprocess.run(cmd, check=False)
        if process.returncode == 0:
            dist_path = Path("dist") / exe_name
            if os.name == "nt":
                dist_path = dist_path.with_suffix(".exe")
            print(f"\nBuild complete. Output is in: {dist_path}")
        return process.returncode
    finally:
        if converted_temp_dir is not None:
            converted_temp_dir.cleanup()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Python script into an executable with optional icon/image selection."
    )
    parser.add_argument("--script", type=Path, help="Path to the Python script (*.py)")
    parser.add_argument("--icon", type=Path, help="Path to icon/image (*.ico, *.png, *.jpg, ...)")
    parser.add_argument("--name", type=str, help="Executable name")
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Build in one-folder mode (default is one-file mode)",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Keep a console window (default is windowed mode)",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Disable GUI picker; requires --script",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.no_gui or args.script:
        if not args.script:
            print("--script is required when using --no-gui")
            return 1
        script_path = args.script
        icon_path = args.icon
        name = args.name
    else:
        script_path, icon_path, name = choose_files_with_gui()
        if args.icon:
            icon_path = args.icon
        if args.name:
            name = args.name

    onefile = not args.onedir
    windowed = not args.console

    return build_executable(
        script_path=script_path,
        icon_path=icon_path,
        name=name,
        onefile=onefile,
        windowed=windowed,
    )


if __name__ == "__main__":
    sys.exit(main())
