"""
Build Script — Compile the application using Nuitka for distribution.

Generates a standalone native binary that is very hard to reverse-engineer.
Supports Windows, Linux, and macOS from a single codebase.

Usage:
    python build.py [--onefile] [--icon icon.ico]
"""

import os
import sys
import platform
import subprocess


def build(onefile=True, icon=None):
    """
    Build the application using Nuitka.

    Args:
        onefile: If True, create single executable (default)
        icon: Path to icon file (.ico for Windows, .icns for macOS)
    """
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--enable-plugin=pyside6",
        "--enable-plugin=numpy",
        "--remove-output",
        "--assume-yes-for-downloading",
        "--output-dir=dist",
        "--company-name=SMILES3D",
        "--product-name=SMILES to 3D Converter",
        "--file-version=1.0.0",
        "--product-version=1.0.0",
        "--file-description=SMILES to 3D Molecular Structure Converter",
    ]

    if onefile:
        cmd.append("--onefile")

    # Platform-specific options
    system = platform.system()
    if system == "Windows":
        cmd.append("--windows-console-mode=disable")
        if icon:
            cmd.append(f"--windows-icon-from-ico={icon}")
    elif system == "Darwin":  # macOS
        cmd.append("--macos-create-app-bundle")
        if icon:
            cmd.append(f"--macos-app-icon={icon}")
    elif system == "Linux":
        if icon:
            cmd.append(f"--linux-icon={icon}")

    # Include all source packages
    cmd.extend([
        "--include-package=src",
        "--include-package=src.core",
        "--include-package=src.parser",
        "--include-package=src.geometry",
        "--include-package=src.charges",
        "--include-package=src.io",
        "--include-package=src.gui",
        "--include-package=src.security",
    ])

    # Main script
    cmd.append("main.py")

    print("=" * 60)
    print("Building SMILES to 3D Converter")
    print(f"Platform: {system} ({platform.machine()})")
    print(f"Mode: {'Single file' if onefile else 'Standalone directory'}")
    print("=" * 60)
    print(f"\nCommand: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))

    if result.returncode == 0:
        print("\n✓ Build successful! Output in ./dist/")
    else:
        print(f"\n✗ Build failed with code {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build SMILES to 3D Converter")
    parser.add_argument("--onefile", action="store_true", default=True,
                        help="Create single executable")
    parser.add_argument("--dir", action="store_true",
                        help="Create standalone directory instead of single file")
    parser.add_argument("--icon", type=str, help="Path to icon file")
    args = parser.parse_args()

    build(onefile=not args.dir, icon=args.icon)
