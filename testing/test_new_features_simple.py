"""
Simple test for new features without GUI dependencies.
"""

import sys
import os

# Add the parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def test_core_functionality():
    """Test core functionality without GUI components."""
    print("SMILES Molecular Toolkit - New Features Test")
    print("=" * 50)
    
    success_count = 0
    total_tests = 4
    
    # Test 1: Atom Properties
    print("\n1. Testing Atom Properties...")
    try:
        from src.core.domain.models.molecule import Molecule
        from src.core.domain.models.atom import Atom
        from src.core.domain.models.bond import BondType
        from src.features.cheminformatics.services.atom_properties import analyze_molecule_properties
        
        # Create test molecule
        mol = Molecule("test")
        c_idx = mol.add_atom(Atom('C'))
        o_idx = mol.add_atom(Atom('O'))
        h_idx = mol.add_atom(Atom('H'))
        
        mol.add_bond(c_idx, o_idx, BondType.SINGLE)
        mol.add_bond(o_idx, h_idx, BondType.SINGLE)
        
        # Set coordinates
        mol.atoms[c_idx].coords = (0.0, 0.0, 0.0)
        mol.atoms[o_idx].coords = (1.0, 0.0, 0.0)
        mol.atoms[h_idx].coords = (2.0, 0.0, 0.0)
        
        properties = analyze_molecule_properties(mol)
        
        if properties['total_atoms'] == 3:
            print("   Atom Properties: PASS")
            success_count += 1
        else:
            print("   Atom Properties: FAIL")
            
    except Exception as e:
        print(f"   Atom Properties: FAIL - {e}")
    
    # Test 2: Charge Scaling
    print("\n2. Testing Charge Scaling...")
    try:
        from src.features.cheminformatics.services.am1 import am1_assign_charges
        from src.features.cheminformatics.services.pm3 import pm3_assign_charges
        
        # Create water molecule
        mol = Molecule("water")
        o_idx = mol.add_atom(Atom('O'))
        h1_idx = mol.add_atom(Atom('H'))
        h2_idx = mol.add_atom(Atom('H'))
        
        mol.add_bond(o_idx, h1_idx, BondType.SINGLE)
        mol.add_bond(o_idx, h2_idx, BondType.SINGLE)
        
        mol.atoms[o_idx].coords = (0.0, 0.0, 0.0)
        mol.atoms[h1_idx].coords = (0.96, 0.0, 0.0)
        mol.atoms[h2_idx].coords = (-0.96, 0.0, 0.0)
        
        # Test AM1
        am1_success = am1_assign_charges(mol)
        
        # Test PM3
        pm3_success = pm3_assign_charges(mol)
        
        if am1_success and pm3_success:
            # Check if charges are reasonable (should be scaled)
            charges = [atom.partial_charge for atom in mol.atoms]
            max_charge = max(abs(c) for c in charges)
            
            if max_charge < 0.6:  # Should be scaled down
                print("   Charge Scaling: PASS")
                success_count += 1
            else:
                print("   Charge Scaling: FAIL - charges not scaled")
        else:
            print("   Charge Scaling: FAIL - calculation failed")
            
    except Exception as e:
        print(f"   Charge Scaling: FAIL - {e}")
    
    # Test 3: Dummy Spheres
    print("\n3. Testing Dummy Spheres...")
    try:
        from src.features.visualization_3d.services.dummy_sphere import DummySphereManager, create_dummy_sphere_at_com
        
        # Create test molecule
        mol = Molecule("sphere_test")
        c1_idx = mol.add_atom(Atom('C'))
        c2_idx = mol.add_atom(Atom('C'))
        
        mol.atoms[c1_idx].coords = (0.0, 0.0, 0.0)
        mol.atoms[c2_idx].coords = (2.0, 0.0, 0.0)
        
        # Test sphere creation
        manager = DummySphereManager(mol)
        com_sphere_id = manager.create_sphere_at_com()
        
        # Test convenience function
        com_id_2 = create_dummy_sphere_at_com(mol)
        
        if com_sphere_id is not None and com_id_2 is not None:
            print("   Dummy Spheres: PASS")
            success_count += 1
        else:
            print("   Dummy Spheres: FAIL")
            
    except Exception as e:
        print(f"   Dummy Spheres: FAIL - {e}")
    
    # Test 4: Color System
    print("\n4. Testing Color System...")
    try:
        from src.shared.ui.theme import COLORS
        from src.features.ui.color_dialog import get_atom_color
        
        # Test color definitions exist
        required_colors = ['atom_c', 'atom_o', 'atom_h', 'atom_selected']
        has_colors = all(color in COLORS for color in required_colors)
        
        # Test color helper function
        carbon_color = get_atom_color('C')
        
        if has_colors and carbon_color.startswith('#'):
            print("   Color System: PASS")
            success_count += 1
        else:
            print("   Color System: FAIL")
            
    except Exception as e:
        print(f"   Color System: FAIL - {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Passed: {success_count}/{total_tests}")
    print(f"Success Rate: {success_count/total_tests*100:.1f}%")
    
    if success_count == total_tests:
        print("\nAll core new features are working correctly!")
    else:
        print(f"\n{total_tests-success_count} feature(s) need attention")
    
    return success_count == total_tests

if __name__ == "__main__":
    test_core_functionality()
