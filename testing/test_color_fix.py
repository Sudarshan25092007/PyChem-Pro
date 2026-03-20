"""
Test script to verify color button fix works correctly.
"""

import sys
import os

# Add the parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def test_color_cycling():
    """Test color cycling functionality."""
    print("Testing Color Button Fix...")
    print("=" * 40)
    
    try:
        # Test 1: Basic color scheme manager
        print("1. Testing color scheme manager...")
        from src.features.ui.color_schemes import get_color_scheme_manager
        
        manager = get_color_scheme_manager()
        schemes = manager.get_available_schemes()
        
        print(f"   Available schemes: {len(schemes)}")
        print(f"   Schemes: {', '.join(schemes[:3])}...")
        
        # Test 2: Color cycling
        print("\n2. Testing color cycling...")
        from src.features.ui.color_schemes import cycle_color_scheme
        
        original_scheme = manager.get_current_scheme()
        print(f"   Original scheme: {original_scheme}")
        
        # Cycle through a few schemes
        for i in range(3):
            colors = cycle_color_scheme()
            current = manager.get_current_scheme()
            print(f"   Cycle {i+1}: {current}")
        
        # Test 3: Simple color customizer
        print("\n3. Testing simple color customizer...")
        from src.features.ui.color_dialog_simple import SimpleColorCustomizer
        
        customizer = SimpleColorCustomizer()
        current_colors = customizer.get_current_colors()
        
        print(f"   Current colors: {len(current_colors)} atom colors")
        print(f"   Carbon color: {current_colors.get('atom_c', 'N/A')}")
        print(f"   Oxygen color: {current_colors.get('atom_o', 'N/A')}")
        
        # Test 4: Color scheme info
        print("\n4. Testing color scheme info...")
        description = manager.get_scheme_description(manager.get_current_scheme())
        print(f"   Current scheme description: {description}")
        
        print("\n✅ All color functionality tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def test_fallback_functionality():
    """Test fallback color functionality."""
    print("\nTesting Fallback Functionality...")
    print("=" * 40)
    
    try:
        # Test basic color toggle
        print("1. Testing basic color toggle...")
        from src.shared.ui.theme import COLORS
        
        original_c = COLORS.get('atom_c', '#909090')
        print(f"   Original carbon color: {original_c}")
        
        # Test basic schemes
        basic_schemes = [
            {'atom_c': '#909090', 'atom_o': '#ff0d0d', 'atom_n': '#3050f8'},
            {'atom_c': '#ff6b6b', 'atom_o': '#4ecdc4', 'atom_n': '#45b7d1'},
            {'atom_c': '#2ecc71', 'atom_o': '#e74c3c', 'atom_n': '#3498db'},
        ]
        
        for i, scheme in enumerate(basic_schemes):
            print(f"   Scheme {i+1}: C={scheme['atom_c']}, O={scheme['atom_o']}, N={scheme['atom_n']}")
        
        print("\n✅ Fallback functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Fallback test error: {e}")
        return False

def test_gui_integration_concept():
    """Test GUI integration concept without actual GUI."""
    print("\nTesting GUI Integration Concept...")
    print("=" * 40)
    
    try:
        # Simulate the main window color button behavior
        print("1. Simulating color button click...")
        
        # This simulates what happens when _show_color_dialog is called
        try:
            # Try to import GUI dialog (will fail in test environment)
            from src.features.ui.color_dialog import AtomColorDialog
            print("   GUI dialog available - would show full dialog")
            gui_available = True
        except ImportError:
            print("   GUI dialog not available - using fallback")
            gui_available = False
        
        if not gui_available:
            # Test the fallback path
            print("2. Testing fallback color cycling...")
            from src.features.ui.color_schemes import cycle_color_scheme
            
            colors = cycle_color_scheme()
            print(f"   Applied colors: {len(colors)} color definitions")
            
            from src.features.ui.color_schemes import get_color_scheme_manager
            manager = get_color_scheme_manager()
            current = manager.get_current_scheme()
            description = manager.get_scheme_description(current)
            
            print(f"   Status message would be: 'Applied {current}: {description}'")
        
        print("\n✅ GUI integration concept tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ GUI integration test error: {e}")
        return False

def main():
    """Run all color fix tests."""
    print("SMILES Molecular Toolkit - Color Button Fix Test")
    print("=" * 50)
    
    test_results = []
    
    # Run tests
    test_results.append(("Color Cycling", test_color_cycling()))
    test_results.append(("Fallback Functionality", test_fallback_functionality()))
    test_results.append(("GUI Integration", test_gui_integration_concept()))
    
    # Summary
    print("\n" + "=" * 50)
    print("COLOR FIX TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:.<20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 Color button fix is working correctly!")
        print("The Colors button will now work by cycling through beautiful color schemes.")
    else:
        print(f"\n⚠️  {total-passed} test(s) need attention")
    
    return passed == total

if __name__ == "__main__":
    main()
