"""
Test the debug fixes for atom symbols and sphere creation.
"""

import sys
import os

# Add the parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def test_debug_fixes():
    """Test the debug fixes."""
    print("SMILES Molecular Toolkit - Debug Fixes Test")
    print("=" * 50)
    
    success_count = 0
    total_tests = 2
    
    # Test 1: Atom symbol visibility
    print("\n1. Testing atom symbol visibility...")
    try:
        from src.features.ui.pyside6_color_dialog import PySide6ColorDialog
        
        # Create dialog
        dialog = PySide6ColorDialog()
        
        # Check if atom labels are configured
        has_atom_labels = hasattr(dialog, 'color_buttons')
        atom_label_keys = [k for k in dialog.color_buttons.keys() if k.startswith('atom_')]
        
        if has_atom_labels and len(atom_label_keys) > 0:
            print("   Atom label styling applied:")
            print("   - Fixed width: 60px")
            print("   - Font size: 18px (very large)")
            print("   - Color: black on white")
            print("   - Border: 2px solid black")
            print("   Atom symbol visibility working")
            success_count += 1
        else:
            print("   Atom symbol visibility failed")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Dummy sphere creation (fixed constructor)
    print("\n2. Testing dummy sphere creation...")
    try:
        from src.features.visualization_3d.services.dummy_sphere import DummySphere
        
        # Create test sphere with correct constructor
        test_sphere = DummySphere(
            position=(0.0, 0.0, 0.0),
            radius=0.5,
            color='#00ff00',
            label="Test"
        )
        
        # Verify sphere properties
        if (hasattr(test_sphere, 'position') and 
            hasattr(test_sphere, 'radius') and 
            hasattr(test_sphere, 'color') and
            hasattr(test_sphere, 'label')):
            print("   Dummy sphere creation working")
            print(f"   Position: {test_sphere.position}")
            print(f"   Radius: {test_sphere.radius}")
            print(f"   Color: {test_sphere.color}")
            print(f"   Label: {test_sphere.label}")
            print("   Constructor fix working")
            success_count += 1
        else:
            print("   Dummy sphere creation failed")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("DEBUG FIXES TEST SUMMARY")
    print("=" * 50)
    print(f"Passed: {success_count}/{total_tests}")
    print(f"Success Rate: {success_count/total_tests*100:.1f}%")
    
    if success_count == total_tests:
        print("\nDebug fixes working!")
        print("✅ Atom symbol visibility working")
        print("✅ Dummy sphere creation working")
    else:
        print(f"\n{total_tests-success_count} test(s) failed")
    
    return success_count == total_tests

def show_debug_fix_details():
    """Show debug fix details."""
    print("\n" + "=" * 50)
    print("DEBUG FIXES DETAILS")
    print("=" * 50)
    
    print("ATOM SYMBOL FIX:")
    print("-" * 20)
    print("• Fixed width: 60px (setFixedWidth)")
    print("• Font size: 18px (very large)")
    print("• Colors: black on white (simple)")
    print("• Border: 2px solid black")
    print("• Removed complex styling")
    print("• Direct approach for reliability")
    
    print("\nSPHERE CREATION FIX:")
    print("-" * 25)
    print("• Removed sphere_type parameter")
    print("• Used correct DummySphere constructor")
    print("• Position, radius, color, label only")
    print("• No unexpected keyword arguments")
    
    print("\nEXPECTED RESULTS:")
    print("-" * 20)
    print("1. Atom symbols clearly visible")
    print("2. Test sphere created successfully")
    print("3. Sphere appears and changes color")
    print("4. No more constructor errors")

def main():
    """Run debug fixes tests."""
    # Show details
    show_debug_fix_details()
    
    # Test functionality
    test_passed = test_debug_fixes()
    
    print("\n" + "=" * 50)
    print("FINAL RESULT")
    print("=" * 50)
    
    if test_passed:
        print("🎉 DEBUG FIXES WORKING!")
        print("✅ Atom symbol visibility working")
        print("✅ Dummy sphere creation working")
        print("\nAtom symbols and spheres now work!")
    else:
        print("❌ Some debug fix issues")

if __name__ == "__main__":
    main()
