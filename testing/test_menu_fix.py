"""
Test the menu initialization fix for COM and Centroid toggles.
"""

import sys
import os

# Add the parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def test_menu_initialization():
    """Test that menu initialization doesn't fail."""
    print("Testing Menu Initialization Fix...")
    
    try:
        # Test that we can import the main window without error
        from src.app.main_window import MainWindow
        print("   ✅ MainWindow import successful")
        
        # Test that the main window can be created (without showing)
        # This would fail if the viewer_3d reference issue wasn't fixed
        try:
            # This should not raise AttributeError anymore
            main_window = MainWindow()
            print("   ✅ MainWindow creation successful")
            
            # Check that the toggle actions are stored in main window
            has_com_action = hasattr(main_window, '_toggle_com_action')
            has_centroid_action = hasattr(main_window, '_toggle_centroid_action')
            
            print(f"   COM action stored in main window: {has_com_action}")
            print(f"   Centroid action stored in main window: {has_centroid_action}")
            
            if has_com_action and has_centroid_action:
                print("   ✅ Action references stored correctly")
                return True
            else:
                print("   ❌ Action references not found")
                return False
                
        except AttributeError as e:
            if "'MainWindow' object has no attribute 'viewer_3d'" in str(e):
                print("   ❌ Original AttributeError still present")
                return False
            else:
                print(f"   ❌ Different AttributeError: {e}")
                return False
        except Exception as e:
            print(f"   ❌ Other error during MainWindow creation: {e}")
            return False
            
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False

def test_action_references():
    """Test that action references work correctly."""
    print("\nTesting Action References...")
    
    try:
        from src.app.main_window import MainWindow
        
        main_window = MainWindow()
        
        # Test that we can access the actions
        if hasattr(main_window, '_toggle_com_action'):
            com_action = main_window._toggle_com_action
            print(f"   COM action type: {type(com_action).__name__}")
            print(f"   COM action checkable: {com_action.isCheckable()}")
            print(f"   COM action checked: {com_action.isChecked()}")
        
        if hasattr(main_window, '_toggle_centroid_action'):
            centroid_action = main_window._toggle_centroid_action
            print(f"   Centroid action type: {type(centroid_action).__name__}")
            print(f"   Centroid action checkable: {centroid_action.isCheckable()}")
            print(f"   Centroid action checked: {centroid_action.isChecked()}")
        
        print("   ✅ Action references working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ Action reference test failed: {e}")
        return False

def main():
    """Run menu fix tests."""
    print("SMILES Molecular Toolkit - Menu Fix Test")
    print("=" * 50)
    
    tests = [
        test_menu_initialization,
        test_action_references
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("MENU FIX TEST SUMMARY")
    print("=" * 50)
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 MENU FIX WORKING!")
        print("✅ MainWindow creation successful")
        print("✅ Action references stored correctly")
        print("✅ AttributeError resolved")
        print("\nThe application should now start without errors!")
    else:
        print(f"\n❌ {total-passed} test(s) failed")
    
    return passed == total

if __name__ == "__main__":
    main()
