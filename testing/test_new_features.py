"""
Comprehensive test script for all new features implemented in March 2026.

Tests:
1. H-bond donor/acceptor and lipophilic atom definitions
2. GUI color customization 
3. Fixed AM1 and PM3 partial charges
4. Dummy sphere creation
"""

import sys
import os

# Add the parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from src.core.domain.models.molecule import Molecule
from src.core.domain.models.atom import Atom
from src.core.domain.models.bond import BondType

def test_atom_properties():
    """Test H-bond donor/acceptor and lipophilic atom definitions."""
    print("=== Testing Atom Properties ===")
    
    # Create test molecule with various functional groups
    mol = Molecule("test_molecule")
    
    # Add atoms for ethanol (CH3CH2OH)
    atoms = []
    atoms.append(mol.add_atom(Atom('C')))  # Carbon 0
    atoms.append(mol.add_atom(Atom('C')))  # Carbon 1
    atoms.append(mol.add_atom(Atom('O')))  # Oxygen
    atoms.append(mol.add_atom(Atom('H')))  # H1
    atoms.append(mol.add_atom(Atom('H')))  # H2
    atoms.append(mol.add_atom(Atom('H')))  # H3
    atoms.append(mol.add_atom(Atom('H')))  # H4
    atoms.append(mol.add_atom(Atom('H')))  # H5 (hydroxyl)
    
    # Add bonds
    mol.add_bond(atoms[0], atoms[1], BondType.SINGLE)  # C-C
    mol.add_bond(atoms[1], atoms[2], BondType.SINGLE)  # C-O
    mol.add_bond(atoms[0], atoms[3], BondType.SINGLE)  # C-H
    mol.add_bond(atoms[0], atoms[4], BondType.SINGLE)  # C-H
    mol.add_bond(atoms[0], atoms[5], BondType.SINGLE)  # C-H
    mol.add_bond(atoms[1], atoms[6], BondType.SINGLE)  # C-H
    mol.add_bond(atoms[2], atoms[7], BondType.SINGLE)  # O-H (hydroxyl)
    
    # Set some basic coordinates
    for i, atom_idx in enumerate(atoms):
        mol.atoms[atom_idx].coords = (i * 1.0, 0.0, 0.0)
    
    # Test atom property analysis
    from src.features.cheminformatics.services.atom_properties import analyze_molecule_properties
    
    properties = analyze_molecule_properties(mol)
    
    print(f"Total atoms: {properties['total_atoms']}")
    print(f"H-bond donors: {properties['hbond_donors']}")
    print(f"H-bond acceptors: {properties['hbond_acceptors']}")
    print(f"Lipophilic atoms: {properties['lipophilic_atoms']}")
    print(f"Polar atoms: {properties['polar_atoms']}")
    
    # Test selection functions
    from src.features.cheminformatics.services.atom_properties import select_atoms_by_property
    
    donors = select_atoms_by_property(mol, 'donor')
    acceptors = select_atoms_by_property(mol, 'acceptor')
    lipophilic = select_atoms_by_property(mol, 'lipophilic')
    
    print(f"Selected donors: {donors}")
    print(f"Selected acceptors: {acceptors}")
    print(f"Selected lipophilic: {lipophilic}")
    
    # Verify expected results
    expected_donors = 1  # Only the hydroxyl H
    expected_acceptors = 1  # Only the oxygen
    expected_lipophilic = 2  # Two carbons
    
    success = (properties['hbond_donors'] == expected_donors and
              properties['hbond_acceptors'] == expected_acceptors and
              properties['lipophilic_atoms'] == expected_lipophilic)
    
    print(f"Atom properties test: {'PASS' if success else 'FAIL'}")
    return success

def test_color_customization():
    """Test color customization functionality."""
    print("\n=== Testing Color Customization ===")
    
    try:
        from src.features.ui.color_dialog import AtomColorDialog, get_atom_color, get_charge_color
        
        # Test color helper functions
        carbon_color = get_atom_color('C')
        oxygen_color = get_atom_color('O')
        
        print(f"Carbon color: {carbon_color}")
        print(f"Oxygen color: {oxygen_color}")
        
        # Test charge-based colors
        positive_color = get_charge_color(0.5)
        negative_color = get_charge_color(-0.5)
        
        print(f"Positive charge color: {positive_color}")
        print(f"Negative charge color: {negative_color}")
        
        # Test color dialog creation (without showing)
        dialog = AtomColorDialog()
        
        # Test default colors
        default_colors = dialog.get_colors()
        expected_keys = ['atom_c', 'atom_o', 'atom_h', 'atom_selected', 'atom_positive']
        
        has_required_colors = all(key in default_colors for key in expected_keys)
        
        print(f"Color customization test: {'PASS' if has_required_colors else 'FAIL'}")
        return has_required_colors
        
    except Exception as e:
        print(f"Color customization test: FAIL - {e}")
        return False

def test_charge_scaling():
    """Test AM1 and PM3 charge scaling."""
    print("\n=== Testing Charge Scaling ===")
    
    # Create simple water molecule
    mol = Molecule("water")
    o_idx = mol.add_atom(Atom('O'))
    h1_idx = mol.add_atom(Atom('H'))
    h2_idx = mol.add_atom(Atom('H'))
    
    mol.add_bond(o_idx, h1_idx, BondType.SINGLE)
    mol.add_bond(o_idx, h2_idx, BondType.SINGLE)
    
    # Set coordinates
    mol.atoms[o_idx].coords = (0.0, 0.0, 0.0)
    mol.atoms[h1_idx].coords = (0.96, 0.0, 0.0)
    mol.atoms[h2_idx].coords = (-0.96, 0.0, 0.0)
    
    # Test AM1 charges
    try:
        from src.features.cheminformatics.services.am1 import am1_assign_charges
        
        success_am1 = am1_assign_charges(mol)
        if success_am1:
            charges = [atom.partial_charge for atom in mol.atoms]
            total_charge = sum(charges)
            max_charge = max(abs(c) for c in charges)
            
            print(f"AM1 charges: {[f'{c:+.3f}' for c in charges]}")
            print(f"Total charge: {total_charge:+.6f}")
            print(f"Max charge magnitude: {max_charge:.3f}")
            
            # Check if charges are reasonable
            reasonable = (max_charge < 0.6 and abs(total_charge) < 0.01)
            print(f"AM1 charge scaling: {'PASS' if reasonable else 'FAIL'}")
            am1_success = reasonable
        else:
            print("AM1 charge scaling: FAIL - calculation failed")
            am1_success = False
            
    except Exception as e:
        print(f"AM1 charge scaling: FAIL - {e}")
        am1_success = False
    
    # Test PM3 charges
    try:
        from src.features.cheminformatics.services.pm3 import pm3_assign_charges
        
        success_pm3 = pm3_assign_charges(mol)
        if success_pm3:
            charges = [atom.partial_charge for atom in mol.atoms]
            total_charge = sum(charges)
            max_charge = max(abs(c) for c in charges)
            
            print(f"PM3 charges: {[f'{c:+.3f}' for c in charges]}")
            print(f"Total charge: {total_charge:+.6f}")
            print(f"Max charge magnitude: {max_charge:.3f}")
            
            # Check if charges are reasonable
            reasonable = (max_charge < 0.7 and abs(total_charge) < 0.01)
            print(f"PM3 charge scaling: {'PASS' if reasonable else 'FAIL'}")
            pm3_success = reasonable
        else:
            print("PM3 charge scaling: FAIL - calculation failed")
            pm3_success = False
            
    except Exception as e:
        print(f"PM3 charge scaling: FAIL - {e}")
        pm3_success = False
    
    return am1_success and pm3_success

def test_dummy_spheres():
    """Test dummy sphere creation."""
    print("\n=== Testing Dummy Spheres ===")
    
    # Create test molecule
    mol = Molecule("test_molecule")
    
    # Add atoms in a tetrahedral arrangement
    positions = [
        (1.0, 1.0, 1.0),
        (-1.0, -1.0, 1.0),
        (-1.0, 1.0, -1.0),
        (1.0, -1.0, -1.0)
    ]
    
    atom_indices = []
    for pos in positions:
        idx = mol.add_atom(Atom('C'))
        mol.atoms[idx].coords = pos
        atom_indices.append(idx)
    
    try:
        from src.features.visualization_3d.services.dummy_sphere import (
            DummySphereManager, create_dummy_sphere_at_com, create_dummy_sphere_at_position
        )
        
        # Test sphere manager
        manager = DummySphereManager(mol)
        
        # Test COM sphere creation
        com_sphere_id = manager.create_sphere_at_com(radius=0.5, color='#ff00ff', label='COM')
        
        # Test centroid sphere creation
        centroid_sphere_id = manager.create_sphere_at_centroid(radius=0.4, color='#00ff00', label='Centroid')
        
        # Test custom position sphere
        custom_sphere_id = manager.create_sphere_at_position(
            (0.0, 0.0, 0.0), radius=0.3, color='#ffff00', label='Center'
        )
        
        # Test atom group center sphere
        group_sphere_id = manager.create_sphere_at_atom_center(
            atom_indices[:2], radius=0.35, color='#00ffff', label='Atom Group'
        )
        
        # Test sphere management
        all_spheres = manager.get_all_spheres()
        sphere_summary = manager.get_sphere_summary()
        
        print(f"Total spheres created: {len(all_spheres)}")
        print(f"Sphere summary: {sphere_summary['total_spheres']} spheres")
        
        # Test calculations
        com = manager.calculate_center_of_mass()
        centroid = manager.calculate_geometric_centroid()
        atom_center = manager.calculate_atom_center(atom_indices[:2])
        
        print(f"Center of mass: {com}")
        print(f"Geometric centroid: {centroid}")
        print(f"Atom group center: {atom_center}")
        
        # Test sphere removal
        removed = manager.remove_sphere(custom_sphere_id)
        print(f"Sphere removal test: {'PASS' if removed else 'FAIL'}")
        
        # Test convenience functions
        com_id_2 = create_dummy_sphere_at_com(mol, radius=0.6)
        custom_id_2 = create_dummy_sphere_at_position(mol, (2.0, 2.0, 2.0), radius=0.4)
        
        print(f"Convenience COM sphere ID: {com_id_2}")
        print(f"Convenience custom sphere ID: {custom_id_2}")
        
        # Verify all spheres are valid
        spheres_valid = len(all_spheres) >= 4  # At least 4 spheres should exist
        calculations_valid = len(com) == 3 and len(centroid) == 3
        
        print(f"Dummy spheres test: {'PASS' if spheres_valid and calculations_valid else 'FAIL'}")
        return spheres_valid and calculations_valid
        
    except Exception as e:
        print(f"Dummy spheres test: FAIL - {e}")
        return False

def test_integration():
    """Test integration of all new features."""
    print("\n=== Testing Feature Integration ===")
    
    try:
        # Create a molecule for integration testing
        mol = Molecule("integration_test")
        
        # Add atoms for a small organic molecule
        c_idx = mol.add_atom(Atom('C'))
        o_idx = mol.add_atom(Atom('O'))
        h1_idx = mol.add_atom(Atom('H'))
        h2_idx = mol.add_atom(Atom('H'))
        n_idx = mol.add_atom(Atom('N'))
        
        # Add bonds
        mol.add_bond(c_idx, o_idx, BondType.SINGLE)
        mol.add_bond(c_idx, h1_idx, BondType.SINGLE)
        mol.add_bond(c_idx, h2_idx, BondType.SINGLE)
        mol.add_bond(o_idx, n_idx, BondType.SINGLE)
        
        # Set coordinates
        mol.atoms[c_idx].coords = (0.0, 0.0, 0.0)
        mol.atoms[o_idx].coords = (1.2, 0.0, 0.0)
        mol.atoms[h1_idx].coords = (-0.6, 1.0, 0.0)
        mol.atoms[h2_idx].coords = (-0.6, -1.0, 0.0)
        mol.atoms[n_idx].coords = (2.0, 0.0, 0.0)
        
        # Test all features together
        # 1. Atom properties
        from src.features.cheminformatics.services.atom_properties import analyze_molecule_properties
        properties = analyze_molecule_properties(mol)
        
        # 2. AM1 charges with scaling
        from src.features.cheminformatics.services.am1 import am1_assign_charges
        am1_success = am1_assign_charges(mol)
        
        # 3. PM3 charges with scaling
        from src.features.cheminformatics.services.pm3 import pm3_assign_charges
        pm3_success = pm3_assign_charges(mol)
        
        # 4. Dummy spheres
        from src.features.visualization_3d.services.dummy_sphere import create_dummy_sphere_at_com
        sphere_id = create_dummy_sphere_at_com(mol)
        
        # 5. Color customization
        from src.features.ui.color_dialog import get_atom_color
        carbon_color = get_atom_color('C')
        
        # Verify integration success
        integration_success = (
            properties['total_atoms'] == 5 and
            am1_success and pm3_success and
            sphere_id is not None and
            carbon_color.startswith('#')
        )
        
        print(f"Integration test: {'PASS' if integration_success else 'FAIL'}")
        print(f"Atoms: {properties['total_atoms']}")
        print(f"AM1 success: {am1_success}")
        print(f"PM3 success: {pm3_success}")
        print(f"Sphere created: {sphere_id is not None}")
        print(f"Color system working: {carbon_color.startswith('#')}")
        
        return integration_success
        
    except Exception as e:
        print(f"Integration test: FAIL - {e}")
        return False

def main():
    """Run all tests for new features."""
    print("SMILES Molecular Toolkit - New Features Test Suite")
    print("=" * 50)
    
    # Run all tests
    test_results = []
    
    test_results.append(("Atom Properties", test_atom_properties()))
    test_results.append(("Color Customization", test_color_customization()))
    test_results.append(("Charge Scaling", test_charge_scaling()))
    test_results.append(("Dummy Spheres", test_dummy_spheres()))
    test_results.append(("Integration", test_integration()))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
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
        print("\n🎉 All new features are working correctly!")
    else:
        print(f"\n⚠️  {total-passed} feature(s) need attention")
    
    return passed == total

if __name__ == "__main__":
    main()
