"""
Test AM1 GUI integration by checking file contents.
"""

import os

def test_gui_integration():
    """Test that AM1 options are properly integrated into the GUI by checking file contents."""
    
    main_window_path = "src/app/main_window.py"
    
    if not os.path.exists(main_window_path):
        print(f"ERROR: {main_window_path} not found")
        return False
    
    with open(main_window_path, 'r') as f:
        content = f.read()
    
    # Check for AM1 in charge methods
    if 'self.chg_combo.addItems(["Gasteiger", "MMFF94", "AM1"])' in content:
        print("[PASS] AM1 added to charge methods dropdown")
    else:
        print("[FAIL] AM1 not found in charge methods dropdown")
        return False
    
    # Check for AM1 in optimization methods
    if 'self.opt_combo.addItems(["MMFF94", "AM1"])' in content:
        print("[PASS] AM1 added to optimization methods dropdown")
    else:
        print("[FAIL] AM1 not found in optimization methods dropdown")
        return False
    
    # Check for AM1 charge calculation handling
    if 'if "AM1" in method:' in content and 'am1_assign_charges' in content:
        print("[PASS] AM1 charge calculation handling added")
    else:
        print("[FAIL] AM1 charge calculation handling not found")
        return False
    
    # Check for AM1 optimization handling
    if 'am1_optimize_geometry' in content:
        print("[PASS] AM1 geometry optimization handling added")
    else:
        print("[FAIL] AM1 geometry optimization handling not found")
        return False
    
    # Check for status messages
    if 'Computing AM1 charges...' in content and 'Optimizing geometry (AM1)...' in content:
        print("[PASS] AM1 status messages added")
    else:
        print("[FAIL] AM1 status messages not found")
        return False
    
    print("\nGUI integration test PASSED!")
    print("All AM1 features have been successfully integrated into the GUI.")
    return True

if __name__ == "__main__":
    try:
        success = test_gui_integration()
        if not success:
            exit(1)
    except Exception as e:
        print(f"GUI integration test FAILED: {e}")
        exit(1)
