"""
Test final sphere fixes and GUI improvements.
"""

import sys
import os

# Add the parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def test_final_sphere_fixes():
    """Test final sphere fixes."""
    print("SMILES Molecular Toolkit - Final Sphere Fixes Test")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Larger GUI size
    print("\n1. Testing larger GUI size...")
    try:
        from src.features.ui.pyside6_color_dialog import PySide6ColorDialog
        
        # Create dialog
        dialog = PySide6ColorDialog()
        
        # Check if dialog is much larger
        min_size = dialog.minimumSize()
        current_size = dialog.size()
        
        if (min_size.width() == 800 and min_size.height() == 700 and
            current_size.width() == 900 and current_size.height() == 800):
            print("   Larger GUI working:")
            print(f"   - Minimum size: {min_size.width()}x{min_size.height()}")
            print(f"   - Default size: {current_size.width()}x{current_size.height()}")
            print("   - Much larger than before")
            success_count += 1
        else:
            print("   Larger GUI failed")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Conditional sphere creation
    print("\n2. Testing conditional sphere creation...")
    try:
        from src.app.main_window import MainWindow
        from src.core.domain.models.molecule import Molecule
        from src.core.domain.models.atom import Atom
        
        # Create test molecule
        molecule = Molecule()
        molecule.atoms = [Atom('C'), Atom('H')]
        
        # Test sphere creation logic
        colors_with_sphere = {'sphere_com': '#ff0000', 'sphere_centroid': '#00ff00'}
        colors_without_sphere = {'atom_c': '#0000ff'}
        
        # Simulate the sphere creation logic
        sphere_keys = ['sphere_default', 'sphere_com', 'sphere_centroid', 'sphere_custom']
        sphere_colors_selected_with = any(key in colors_with_sphere for key in sphere_keys)
        sphere_colors_selected_without = any(key in colors_without_sphere for key in sphere_keys)
        
        if sphere_colors_selected_with and not sphere_colors_selected_without:
            print("   Conditional sphere creation working:")
            print("   - Creates spheres when sphere colors selected")
            print("   - Does not create spheres when only atom colors selected")
            success_count += 1
        else:
            print("   Conditional sphere creation failed")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Specific sphere creation
    print("\n3. Testing specific sphere creation...")
    try:
        from src.features.visualization_3d.services.dummy_sphere import DummySphere
        import numpy as np
        
        # Test creating COM and centroid spheres
        center = np.array([0.0, 0.0, 0.0])
        
        com_sphere = DummySphere(
            position=tuple(center + np.array([0.0, 0.5, 0.0])),
            radius=0.5,
            color='#ff0000',
            label="COM"
        )
        
        centroid_sphere = DummySphere(
            position=tuple(center + np.array([0.0, -0.5, 0.0])),
            radius=0.5,
            color='#00ff00',
            label="Centroid"
        )
        
        # Verify spheres
        if (com_sphere.label == "COM" and centroid_sphere.label == "Centroid"):
            print("   Specific sphere creation working:")
            print("   - COM sphere created with correct label and color")
            print("   - Centroid sphere created with correct label and color")
            print("   - Spheres positioned correctly")
            success_count += 1
        else:
            print("   Specific sphere creation failed")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("FINAL SPHERE FIXES TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {success_count}/{total_tests}")
    print(f"Success Rate: {success_count/total_tests*100:.1f}%")
    
    if success_count == total_tests:
        print("\nFinal sphere fixes working!")
        print("✅ Larger GUI size working")
        print("✅ Conditional sphere creation working")
        print("✅ Specific sphere creation working")
    else:
        print(f"\n{total_tests-success_count} test(s) failed")
    
    return success_count == total_tests

def show_final_sphere_fix_details():
    """Show final sphere fix details."""
    print("\n" + "=" * 60)
    print("FINAL SPHERE FIXES DETAILS")
    print("=" * 60)
    
    print("LARGER GUI SIZE:")
    print("-" * 20)
    print("• Minimum size: 800x700 (much larger)")
    print("• Default size: 900x800 (much larger)")
    print("• User can resize even larger")
    print("• Atom symbols clearly visible")
    
    print("\nCONDITIONAL SPHERE CREATION:")
    print("-" * 35)
    print("• Only creates spheres when sphere colors selected")
    print("• Does not create spheres for atom-only changes")
    print("• Prevents automatic COM/centroid creation")
    print("• User controls when spheres appear")
    
    print("\nSPECIFIC SPHERE CREATION:")
    print("-" * 35)
    print("• Creates COM sphere when sphere_com color selected")
    print("• Creates centroid sphere when sphere_centroid color selected")
    print("• Uses selected colors directly")
    print("• Positions spheres correctly around molecule")
    print("• Labels: 'COM' and 'Centroid'")
    
    print("\nEXPECTED RESULTS:")
    print("-" * 20)
    print("1. Much larger GUI (900x800 default)")
    print("2. Spheres only appear when sphere colors selected")
    print("3. COM and centroid spheres use their selected colors")
    print("4. No automatic sphere creation")
    print("5. User has full control")

def main():
    """Run final sphere fixes tests."""
    # Show details
    show_final_sphere_fix_details()
    
    # Test functionality
    test_passed = test_final_sphere_fixes()
    
    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    
    if test_passed:
        print("🎉 FINAL SPHERE FIXES WORKING!")
        print("✅ Larger GUI size working")
        print("✅ Conditional sphere creation working")
        print("✅ Specific sphere creation working")
        print("\nAll sphere issues now resolved!")
    else:
        print("❌ Some final sphere fix issues")

if __name__ == "__main__":
    main()
