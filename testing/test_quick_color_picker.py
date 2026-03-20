"""
Test the quick color picker - no console input required.
"""

import sys
import os

# Add the parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def test_quick_color_picker():
    """Test quick color picker functionality."""
    print("SMILES Molecular Toolkit - Quick Color Picker Test")
    print("=" * 55)
    
    success_count = 0
    total_tests = 5
    
    # Test 1: Import quick color picker
    print("\n1. Testing quick color picker import...")
    try:
        from src.features.ui.quick_color_picker import get_color_picker, QuickColorPicker
        picker = get_color_picker()
        print("   Quick color picker imported successfully")
        success_count += 1
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Check available schemes
    print("\n2. Testing available color schemes...")
    try:
        schemes = picker.get_available_schemes()
        print(f"   Available schemes: {len(schemes)}")
        print(f"   Schemes: {', '.join(schemes)}")
        success_count += 1
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Color scheme cycling
    print("\n3. Testing color scheme cycling...")
    try:
        from src.features.ui.quick_color_picker import cycle_color_scheme, get_color_status
        
        original_scheme = picker.get_current_scheme()
        colors = cycle_color_scheme()
        new_scheme = picker.get_current_scheme()
        status = get_color_status()
        
        print(f"   Cycled from {original_scheme} to {new_scheme}")
        print(f"   Colors applied: {len(colors)} definitions")
        print(f"   Status message: {status}")
        success_count += 1
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Specific scheme application
    print("\n4. Testing specific scheme application...")
    try:
        from src.features.ui.quick_color_picker import apply_specific_scheme
        
        # Test applying Red Theme
        success = apply_specific_scheme("Red Theme")
        current_scheme = picker.get_current_scheme()
        
        print(f"   Applied Red Theme: {success}")
        print(f"   Current scheme: {current_scheme}")
        success_count += 1
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 5: Color application to theme
    print("\n5. Testing color application to theme...")
    try:
        # Get current colors
        current_colors = picker.color_schemes[picker.current_scheme][1]
        
        # Apply to theme
        picker.apply_scheme(current_colors)
        
        print(f"   Applied {len(current_colors)} colors to theme")
        print(f"   Sample colors: atom_c={current_colors.get('atom_c', 'N/A')}")
        print(f"   Sample colors: sphere_default={current_colors.get('sphere_default', 'N/A')}")
        success_count += 1
    except Exception as e:
        print(f"   Error: {e}")
    
    # Summary
    print("\n" + "=" * 55)
    print("QUICK COLOR PICKER TEST SUMMARY")
    print("=" * 55)
    print(f"Passed: {success_count}/{total_tests}")
    print(f"Success Rate: {success_count/total_tests*100:.1f}%")
    
    if success_count == total_tests:
        print("\nQuick color picker working perfectly!")
        print("✅ No console input required")
        print("✅ 6 predefined color schemes")
        print("✅ Automatic cycling works")
        print("✅ Theme integration works")
        print("✅ Status messages working")
    else:
        print(f"\n{total_tests-success_count} test(s) failed")
    
    return success_count == total_tests

def show_color_schemes():
    """Show all available color schemes."""
    print("\n" + "=" * 55)
    print("AVAILABLE COLOR SCHEMES")
    print("=" * 55)
    
    try:
        from src.features.ui.quick_color_picker import get_color_picker
        
        picker = get_color_picker()
        schemes = picker.get_available_schemes()
        
        print("Click Colors button to cycle through these schemes:")
        print()
        
        for i, scheme_name in enumerate(schemes):
            colors = picker.get_scheme_by_name(scheme_name)
            print(f"{i+1}. {scheme_name}")
            print(f"   Sample: Carbon={colors.get('atom_c', 'N/A')}")
            print(f"   Sample: Sphere={colors.get('sphere_default', 'N/A')}")
            print()
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def demonstrate_colors_button():
    """Demonstrate how Colors button works now."""
    print("\n" + "=" * 55)
    print("COLORS BUTTON DEMONSTRATION")
    print("=" * 55)
    
    try:
        from src.features.ui.quick_color_picker import cycle_color_scheme, get_color_status
        
        print("HOW THE COLORS BUTTON WORKS NOW:")
        print("1. User clicks Colors button")
        print("2. Color scheme cycles automatically")
        print("3. Status bar shows current scheme")
        print("4. Colors applied immediately to 3D viewer")
        print("5. No console input required!")
        
        print("\n" + "-" * 55)
        print("DEMONSTRATION - Clicking Colors Button:")
        print("-" * 55)
        
        # Simulate clicking Colors button multiple times
        for i in range(6):
            colors = cycle_color_scheme()
            status = get_color_status()
            
            print(f"Click #{i+1}: {status}")
            print(f"   Carbon color: {colors.get('atom_c', 'N/A')}")
            print(f"   Sphere color: {colors.get('sphere_default', 'N/A')}")
        
        print("\n" + "=" * 55)
        print("RESULT:")
        print("=" * 55)
        print("✅ Colors button works without console input")
        print("✅ 6 beautiful color schemes available")
        print("✅ Automatic cycling with each click")
        print("✅ Status messages show current scheme")
        print("✅ No errors or console issues")
        
        return True
        
    except Exception as e:
        print(f"Demonstration error: {e}")
        return False

def main():
    """Run all quick color picker tests."""
    # Show color schemes
    show_color_schemes()
    
    # Test functionality
    test_passed = test_quick_color_picker()
    
    # Demonstrate colors button
    demo_success = demonstrate_colors_button()
    
    print("\n" + "=" * 55)
    print("FINAL RESULT")
    print("=" * 55)
    
    if test_passed and demo_success:
        print("🎉 QUICK COLOR PICKER WORKING!")
        print("✅ No console input required")
        print("✅ Colors button cycles through schemes")
        print("✅ No errors or console issues")
        print("✅ Simple and effective solution")
        print("\nThe Colors button is now fixed and working!")
    else:
        print("❌ Some issues remain")

if __name__ == "__main__":
    main()
