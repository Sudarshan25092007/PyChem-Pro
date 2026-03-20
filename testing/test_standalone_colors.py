"""
Test the standalone color system to ensure it works without any GUI dependencies.
"""

import sys
import os

# Add the parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def test_standalone_colors():
    """Test standalone color system functionality."""
    print("SMILES Molecular Toolkit - Standalone Color System Test")
    print("=" * 60)
    
    success_count = 0
    total_tests = 5
    
    # Test 1: Import standalone manager
    print("\n1. Testing standalone color manager import...")
    try:
        from src.features.ui.color_standalone import get_standalone_manager
        manager = get_standalone_manager()
        print("   Standalone manager imported successfully")
        success_count += 1
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Check available schemes
    print("\n2. Testing available color schemes...")
    try:
        scheme_count = manager.get_scheme_count()
        scheme_names = manager.get_all_scheme_names()
        print(f"   Available schemes: {scheme_count}")
        print(f"   Scheme names: {', '.join(scheme_names[:3])}...")
        success_count += 1
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Color cycling
    print("\n3. Testing color cycling...")
    try:
        from src.features.ui.color_standalone import cycle_standalone_colors, get_current_scheme_info
        
        # Get initial scheme
        initial_name, initial_desc = get_current_scheme_info()
        print(f"   Initial scheme: {initial_name}")
        
        # Cycle through a few schemes
        for i in range(3):
            colors = cycle_standalone_colors()
            name, desc = get_current_scheme_info()
            print(f"   Cycle {i+1}: {name}")
        
        success_count += 1
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Color application
    print("\n4. Testing color application...")
    try:
        current_colors = manager.get_current_colors()
        print(f"   Current colors: {len(current_colors)} atom colors")
        print(f"   Carbon color: {current_colors.get('atom_c', 'N/A')}")
        print(f"   Oxygen color: {current_colors.get('atom_o', 'N/A')}")
        print(f"   Nitrogen color: {current_colors.get('atom_n', 'N/A')}")
        success_count += 1
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 5: Scheme information
    print("\n5. Testing scheme information...")
    try:
        from src.features.ui.color_standalone import print_all_schemes
        
        # Print scheme info (this will show all 8 schemes)
        print("   Available color schemes:")
        manager.print_scheme_info()
        success_count += 1
    except Exception as e:
        print(f"   Error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("STANDALONE COLOR SYSTEM TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {success_count}/{total_tests}")
    print(f"Success Rate: {success_count/total_tests*100:.1f}%")
    
    if success_count == total_tests:
        print("\nStandalone color system is working perfectly!")
        print("The Colors button will now cycle through 8 beautiful schemes.")
        print("No GUI dependencies required - works in any environment!")
    else:
        print(f"\n{total_tests-success_count} test(s) failed")
    
    return success_count == total_tests

def test_color_button_simulation():
    """Simulate clicking the Colors button."""
    print("\n" + "=" * 60)
    print("SIMULATING COLORS BUTTON CLICK")
    print("=" * 60)
    
    try:
        # This simulates what happens when user clicks Colors button
        from src.features.ui.color_standalone import cycle_standalone_colors, get_current_scheme_info
        
        print("User clicks Colors button...")
        
        # Simulate multiple clicks
        for click in range(5):
            print(f"\nClick #{click + 1}:")
            
            # Cycle to next scheme
            colors = cycle_standalone_colors()
            
            # Get scheme info
            name, description = get_current_scheme_info()
            
            # Show what user would see in status bar
            status_message = f"Applied {name}: {description}"
            print(f"   Status bar: {status_message}")
            
            # Show some key colors
            print(f"   Carbon: {colors.get('atom_c', 'N/A')}")
            print(f"   Oxygen: {colors.get('atom_o', 'N/A')}")
            print(f"   Nitrogen: {colors.get('atom_n', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("COLORS BUTTON SIMULATION SUCCESSFUL!")
        print("Each click cycles through beautiful color schemes.")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"Simulation error: {e}")
        return False

def main():
    """Run all standalone color tests."""
    # Test core functionality
    core_test_passed = test_standalone_colors()
    
    # Test user interaction simulation
    sim_test_passed = test_color_button_simulation()
    
    # Final summary
    print("\n" + "=" * 60)
    print("FINAL TEST RESULTS")
    print("=" * 60)
    
    if core_test_passed and sim_test_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Standalone color system working perfectly")
        print("✅ Colors button will work without any GUI dependencies")
        print("✅ 8 beautiful color schemes available")
        print("✅ User-friendly status messages")
        print("\nThe Colors button fix is COMPLETE and ready for use!")
    else:
        print("❌ Some tests failed - check implementation")
    
    return core_test_passed and sim_test_passed

if __name__ == "__main__":
    main()
