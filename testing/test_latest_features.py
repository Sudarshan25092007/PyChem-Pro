"""
Test the latest features: enhanced lipophilic definition, sphere size, and COM/Centroid toggles.
"""

import sys
import os

# Add the parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def test_enhanced_lipophilic_definition():
    """Test enhanced lipophilic atom definition."""
    print("Testing Enhanced Lipophilic Definition...")
    
    try:
        from src.features.cheminformatics.services.atom_properties import AtomPropertyAnalyzer
        from src.core.domain.models.molecule import Molecule
        from src.core.domain.models.atom import Atom
        from src.core.domain.models.bond import Bond
        
        # Create test molecule: C-C-O (ethanol-like)
        molecule = Molecule()
        
        # Add atoms
        c1 = Atom('C')
        c1.position = (0.0, 0.0, 0.0)
        c1.index = 0
        
        c2 = Atom('C')
        c2.position = (1.0, 0.0, 0.0)
        c2.index = 1
        
        o = Atom('O')
        o.position = (2.0, 0.0, 0.0)
        o.index = 2
        
        molecule.atoms = [c1, c2, o]
        
        # Add bonds
        molecule.bonds = [
            Bond(c1, c2, order=1),
            Bond(c2, o, order=1)
        ]
        
        # Create analyzer
        analyzer = AtomPropertyAnalyzer(molecule)
        
        # Test lipophilic detection
        c1_lipophilic = analyzer.is_lipophilic(0)  # C1 (attached to C2 only)
        c2_lipophilic = analyzer.is_lipophilic(1)  # C2 (attached to C1 and O)
        o_lipophilic = analyzer.is_lipophilic(2)    # O (polar)
        
        print(f"   C1 (attached to C only): {c1_lipophilic}")
        print(f"   C2 (attached to O): {c2_lipophilic}")
        print(f"   O (polar): {o_lipophilic}")
        
        # C1 should be lipophilic, C2 should NOT be lipophilic (attached to O)
        if c1_lipophilic and not c2_lipophilic and not o_lipophilic:
            print("   ✅ Enhanced lipophilic definition working correctly")
            return True
        else:
            print("   ❌ Enhanced lipophilic definition failed")
            return False
            
    except Exception as e:
        print(f"   Error: {e}")
        return False

def test_sphere_size_default():
    """Test default sphere size is 60%."""
    print("\nTesting Default Sphere Size...")
    
    try:
        from src.features.visualization_3d.ui.mol_viewer_3d import MolViewer3D
        
        # Create viewer
        viewer = MolViewer3D()
        
        # Check default sphere scale
        default_scale = viewer.sphere_scale
        
        print(f"   Default sphere scale: {default_scale}")
        
        if default_scale == 0.6:
            print("   ✅ Default sphere size set to 60% correctly")
            return True
        else:
            print("   ❌ Default sphere size not 60%")
            return False
            
    except Exception as e:
        print(f"   Error: {e}")
        return False

def test_com_centroid_toggles():
    """Test COM and Centroid toggle functionality."""
    print("\nTesting COM and Centroid Toggles...")
    
    try:
        from src.app.main_window import MainWindow
        from src.core.domain.models.molecule import Molecule
        from src.core.domain.models.atom import Atom
        
        # Create simple test molecule
        molecule = Molecule()
        c = Atom('C')
        c.position = (0.0, 0.0, 0.0)
        c.index = 0
        molecule.atoms = [c]
        
        # Create main window (without showing)
        main_window = MainWindow()
        main_window.molecule = molecule
        
        # Test toggle methods exist
        has_com_toggle = hasattr(main_window, '_toggle_com_sphere')
        has_centroid_toggle = hasattr(main_window, '_toggle_centroid_sphere')
        
        print(f"   COM toggle method exists: {has_com_toggle}")
        print(f"   Centroid toggle method exists: {has_centroid_toggle}")
        
        if has_com_toggle and has_centroid_toggle:
            print("   ✅ COM and Centroid toggle methods available")
            return True
        else:
            print("   ❌ Missing toggle methods")
            return False
            
    except Exception as e:
        print(f"   Error: {e}")
        return False

def test_documentation_updated():
    """Test documentation has been updated."""
    print("\nTesting Documentation Updates...")
    
    try:
        # Check if documentation files exist
        docs_dir = os.path.join(parent_dir, 'docs')
        
        latest_features_doc = os.path.join(docs_dir, 'LATEST_FEATURES_UPDATE.md')
        index_doc = os.path.join(docs_dir, 'DOCUMENTATION_INDEX.md')
        
        latest_exists = os.path.exists(latest_features_doc)
        index_exists = os.path.exists(index_doc)
        
        print(f"   Latest features documentation exists: {latest_exists}")
        print(f"   Documentation index updated: {index_exists}")
        
        if latest_exists and index_exists:
            print("   ✅ Documentation updated correctly")
            return True
        else:
            print("   ❌ Documentation not updated")
            return False
            
    except Exception as e:
        print(f"   Error: {e}")
        return False

def main():
    """Run all latest feature tests."""
    print("SMILES Molecular Toolkit - Latest Features Test")
    print("=" * 60)
    
    tests = [
        ("Enhanced Lipophilic Definition", test_enhanced_lipophilic_definition),
        ("Default Sphere Size", test_sphere_size_default),
        ("COM/Centroid Toggles", test_com_centroid_toggles),
        ("Documentation Updated", test_documentation_updated)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"   ❌ {test_name} failed with exception: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("LATEST FEATURES TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL LATEST FEATURES WORKING!")
        print("✅ Enhanced lipophilic definition working")
        print("✅ Default sphere size set to 60%")
        print("✅ COM and Centroid toggles available")
        print("✅ Documentation updated")
        print("\nAll new features implemented successfully!")
    else:
        print(f"\n❌ {total-passed} feature(s) not working")
    
    return passed == total

if __name__ == "__main__":
    main()
