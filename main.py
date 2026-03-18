"""
SMILES to 3D Molecular Structure Converter
═══════════════════════════════════════════

Main entry point. Initializes the application, checks license,
and launches the GUI.
"""

import sys
import os


def main():
    """Application entry point."""
    # Ensure the src package is importable
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFont, QIcon
    from PySide6.QtCore import Qt

    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("SMILES to 3D Converter")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("SMILES3D")

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # License check
    from src.core.security.license import LicenseManager
    license_mgr = LicenseManager()
    is_valid, message, features = license_mgr.validate_license()

    if not is_valid:
        # Auto-generate a development license (for first run)
        # In production, this would show a license activation dialog
        license_mgr.generate_and_save(days_valid=3650)
        is_valid, message, features = license_mgr.validate_license()

    # Launch main window
    from src.app.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
