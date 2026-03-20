"""
Simple test to verify AM1 GUI integration works.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.app.main_window import MainWindow
from PySide6.QtWidgets import QApplication

def test_gui_integration():
    """Test that AM1 options are properly integrated into the GUI."""
    app = QApplication(sys.argv)
    
    # Create main window
    main_window = MainWindow()
    
    # Check that AM1 options are available
    charge_methods = [main_window.chg_combo.itemText(i) for i in range(main_window.chg_combo.count())]
    opt_methods = [main_window.opt_combo.itemText(i) for i in range(main_window.opt_combo.count())]
    
    print("Available charge methods:", charge_methods)
    print("Available optimization methods:", opt_methods)
    
    # Verify AM1 is included
    assert "AM1" in charge_methods, "AM1 not found in charge methods"
    assert "AM1" in opt_methods, "AM1 not found in optimization methods"
    
    print("✓ AM1 successfully integrated into GUI")
    print("✓ Charge methods dropdown includes AM1")
    print("✓ Optimization methods dropdown includes AM1")
    
    # Test setting AM1 as selected method
    main_window.chg_combo.setCurrentText("AM1")
    main_window.opt_combo.setCurrentText("AM1")
    
    assert main_window.chg_combo.currentText() == "AM1", "Failed to set AM1 charge method"
    assert main_window.opt_combo.currentText() == "AM1", "Failed to set AM1 optimization method"
    
    print("✓ AM1 methods can be selected in GUI")
    
    print("\nGUI integration test PASSED!")
    return True

if __name__ == "__main__":
    try:
        test_gui_integration()
    except Exception as e:
        print(f"GUI integration test FAILED: {e}")
        sys.exit(1)
