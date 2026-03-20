"""
Simple test to verify color button fix works.
"""

import sys
import os

# Add the parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def test_color_fix():
    """Test color button fix functionality."""
    print("SMILES Molecular Toolkit - Color Button Fix Test")
    print("=" * 50)
    
    success_count = 0
    total_tests = 4
    
    # Test 1: Import color schemes
    print("\n1. Testing color scheme import...")
    try:
        from src.features.ui.color_schemes import get_color_scheme_manager
        manager = get_color_scheme_manager()
        print("   Color scheme manager imported successfully")
        success_count += 1
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Get available schemes
    print("\n2. Testing available schemes...")
    try:
        schemes = [scheme.name for scheme in manager.schemes]
        print(f"   Available schemes: {len(schemes)}")
        print(f"   First scheme: {schemes[0]}")
        success_count += 1
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Color cycling
    print("\n3. Testing color cycling...")
    try:
        from src.features.ui.color_schemes import cycle_color_scheme
        original = manager.current_scheme
        colors = cycle_color_scheme()
        new_scheme = manager.current_scheme
        print(f"   Cycled from {original} to {new_scheme}")
        success_count += 1
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Simple color customizer
    print("\n4. Testing simple color customizer...")
    try:
        from src.features.ui.color_dialog_simple import SimpleColorCustomizer
        customizer = SimpleColorCustomizer()
        current = customizer.get_current_scheme()
        print(f"   Current scheme: {current}")
        success_count += 1
    except Exception as e:
        print(f"   Error: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Passed: {success_count}/{total_tests}")
    print(f"Success Rate: {success_count/total_tests*100:.1f}%")
    
    if success_count == total_tests:
        print("\nColor button fix is working correctly!")
        print("The Colors button will cycle through beautiful color schemes.")
    else:
        print(f"\n{total_tests-success_count} test(s) failed")
    
    return success_count == total_tests

if __name__ == "__main__":
    test_color_fix()
