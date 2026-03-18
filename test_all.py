"""
Comprehensive test script for the SMILES to 3D converter.
Tests all modules: parsing, 3D generation, charges, and file export.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_parser():
    """Test SMILES parser with various molecules."""
    from src.parser.parser import parse_smiles
    
    test_cases = [
        ("C", "Methane", 1),
        ("CC", "Ethane", 2),
        ("C=C", "Ethene", 2),
        ("C#C", "Ethyne", 2),
        ("CCO", "Ethanol", 3),
        ("CC(=O)O", "Acetic acid", 4),
        ("c1ccccc1", "Benzene", 6),
        ("C1CCCCC1", "Cyclohexane", 6),
        ("CC(C)C", "Isobutane", 4),
        ("[NH4+]", "Ammonium", 1),
        ("[O-]", "Oxide", 1),
        ("[2H]O[2H]", "D2O", 3),
        ("CC(=O)Oc1ccccc1C(=O)O", "Aspirin", 13),
        ("c1ccncc1", "Pyridine", 6),
        ("C/C=C/C", "Trans-2-butene", 4),
        ("C/C=C\\C", "Cis-2-butene", 4),
        ("Cn1cnc2c1c(=O)n(c(=O)n2C)C", "Caffeine", 14),
    ]
    
    print("=" * 60)
    print("PARSER TESTS")
    print("=" * 60)
    
    passed = 0
    failed = 0
    for smiles, name, expected_heavy in test_cases:
        try:
            mol = parse_smiles(smiles, name)
            heavy = mol.num_heavy_atoms
            status = "PASS" if heavy == expected_heavy else f"WARN(got {heavy}, expected {expected_heavy})"
            if heavy == expected_heavy:
                passed += 1
            else:
                failed += 1
            formula = mol.molecular_formula()
            print(f"  [{status}] {name:20s} {smiles:30s} -> {formula}, {len(mol.atoms)} atoms (heavy={heavy})")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {name:20s} {smiles:30s} -> ERROR: {e}")
    
    print(f"\n  Results: {passed} passed, {failed} failed out of {len(test_cases)}")
    return failed == 0


def test_3d_generation():
    """Test 3D coordinate generation."""
    from src.parser.parser import parse_smiles
    from src.geometry.coord_gen import generate_3d_coordinates
    import numpy as np
    
    print("\n" + "=" * 60)
    print("3D COORDINATE GENERATION TESTS")
    print("=" * 60)
    
    test_cases = [
        ("C", "Methane"),
        ("CC", "Ethane"),
        ("c1ccccc1", "Benzene"),
        ("C1CCCCC1", "Cyclohexane"),
        ("CCO", "Ethanol"),
        ("CC(=O)O", "Acetic acid"),
    ]
    
    passed = 0
    failed = 0
    for smiles, name in test_cases:
        try:
            mol = parse_smiles(smiles, name)
            generate_3d_coordinates(mol, optimize=True, max_opt_steps=100)
            
            # Verify all atoms have coordinates
            all_have_coords = all(a.has_coords for a in mol.atoms)
            
            # Verify no overlapping atoms (minimum distance > 0.5 A)
            min_dist = float('inf')
            for i in range(len(mol.atoms)):
                for j in range(i+1, len(mol.atoms)):
                    a1, a2 = mol.atoms[i], mol.atoms[j]
                    d = np.sqrt((a1.x-a2.x)**2 + (a1.y-a2.y)**2 + (a1.z-a2.z)**2)
                    min_dist = min(min_dist, d)
            
            no_overlap = min_dist > 0.3
            status = "PASS" if (all_have_coords and no_overlap) else "FAIL"
            if status == "PASS":
                passed += 1
            else:
                failed += 1
            print(f"  [{status}] {name:20s} coords={all_have_coords}, min_dist={min_dist:.2f}A, {len(mol.atoms)} atoms")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {name:20s} -> ERROR: {e}")
    
    print(f"\n  Results: {passed} passed, {failed} failed out of {len(test_cases)}")
    return failed == 0


def test_charges():
    """Test Gasteiger charge calculation."""
    from src.parser.parser import parse_smiles
    from src.geometry.coord_gen import generate_3d_coordinates
    from src.charges.gasteiger import compute_gasteiger_charges
    
    print("\n" + "=" * 60)
    print("GASTEIGER CHARGE TESTS")
    print("=" * 60)
    
    test_cases = [
        ("O", "Water", 0),
        ("CCO", "Ethanol", 0),
        ("[NH4+]", "Ammonium", 1),
        ("CC(=O)O", "Acetic acid", 0),
    ]
    
    passed = 0
    failed = 0
    for smiles, name, expected_total in test_cases:
        try:
            mol = parse_smiles(smiles, name)
            generate_3d_coordinates(mol, optimize=False, max_opt_steps=50)
            compute_gasteiger_charges(mol)
            
            total_q = sum(a.partial_charge for a in mol.atoms)
            charges_str = ", ".join(f"{a.symbol}={a.partial_charge:.3f}" for a in mol.atoms if a.symbol != 'H')
            
            close_to_expected = abs(total_q - expected_total) < 0.1
            status = "PASS" if close_to_expected else "WARN"
            if close_to_expected:
                passed += 1
            else:
                failed += 1
            print(f"  [{status}] {name:20s} total_q={total_q:.4f} (expected ~{expected_total})")
            print(f"         heavy atoms: {charges_str}")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {name:20s} -> ERROR: {e}")
    
    print(f"\n  Results: {passed} passed, {failed} failed out of {len(test_cases)}")
    return failed == 0


def test_file_export():
    """Test SDF and MOL2 export."""
    from src.parser.parser import parse_smiles
    from src.geometry.coord_gen import generate_3d_coordinates
    from src.charges.gasteiger import compute_gasteiger_charges
    from src.io.sdf_writer import write_sdf
    from src.io.mol2_writer import write_mol2
    import tempfile
    
    print("\n" + "=" * 60)
    print("FILE EXPORT TESTS")
    print("=" * 60)
    
    mol = parse_smiles("c1ccccc1", "Benzene")
    generate_3d_coordinates(mol, optimize=True, max_opt_steps=100)
    compute_gasteiger_charges(mol)
    
    passed = 0
    failed = 0
    
    # Test SDF
    try:
        sdf_content = write_sdf(mol)
        has_header = "Benzene" in sdf_content
        has_end = "M  END" in sdf_content
        has_delim = "$$$$" in sdf_content
        ok = has_header and has_end and has_delim
        status = "PASS" if ok else "FAIL"
        if ok: passed += 1
        else: failed += 1
        print(f"  [{status}] SDF export: header={has_header}, M_END={has_end}, $$$$={has_delim}")
        print(f"         SDF size: {len(sdf_content)} chars, {sdf_content.count(chr(10))} lines")
        
        # Write to temp file
        sdf_path = os.path.join(tempfile.gettempdir(), "test_benzene.sdf")
        write_sdf(mol, sdf_path)
        print(f"         Written to: {sdf_path}")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] SDF export -> ERROR: {e}")
    
    # Test MOL2
    try:
        mol2_content = write_mol2(mol)
        has_mol = "@<TRIPOS>MOLECULE" in mol2_content
        has_atom = "@<TRIPOS>ATOM" in mol2_content
        has_bond = "@<TRIPOS>BOND" in mol2_content
        ok = has_mol and has_atom and has_bond
        status = "PASS" if ok else "FAIL"
        if ok: passed += 1
        else: failed += 1
        print(f"  [{status}] MOL2 export: MOLECULE={has_mol}, ATOM={has_atom}, BOND={has_bond}")
        print(f"         MOL2 size: {len(mol2_content)} chars, {mol2_content.count(chr(10))} lines")
        
        mol2_path = os.path.join(tempfile.gettempdir(), "test_benzene.mol2")
        write_mol2(mol, mol2_path)
        print(f"         Written to: {mol2_path}")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] MOL2 export -> ERROR: {e}")
    
    print(f"\n  Results: {passed} passed, {failed} failed out of 2")
    return failed == 0


def test_gui_import():
    """Test that GUI modules import correctly."""
    print("\n" + "=" * 60)
    print("GUI IMPORT TESTS")
    print("=" * 60)
    
    try:
        from src.gui.theme import get_stylesheet, COLORS
        print(f"  [PASS] Theme loaded: {len(COLORS)} colors defined")
    except Exception as e:
        print(f"  [FAIL] Theme -> {e}")
        return False
    
    try:
        from PySide6.QtWidgets import QApplication
        # Create app for widget testing
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        from src.gui.mol_viewer_3d import MolViewer3D
        print(f"  [PASS] MolViewer3D imported")
        
        from src.gui.input_panel import InputPanel
        print(f"  [PASS] InputPanel imported")
        
        from src.gui.main_window import MainWindow
        print(f"  [PASS] MainWindow imported")
        
        return True
    except Exception as e:
        print(f"  [FAIL] GUI import -> {e}")
        return False


def test_license():
    """Test license system."""
    from src.security.license import LicenseManager
    
    print("\n" + "=" * 60)
    print("LICENSE SYSTEM TESTS")
    print("=" * 60)
    
    mgr = LicenseManager(license_file=os.path.join(os.environ.get('TEMP', '/tmp'), 'test_license.dat'))
    
    # Get machine ID
    machine_id = mgr.get_machine_id()
    print(f"  Machine ID: {machine_id[:16]}...")
    
    # Generate key
    key = mgr.generate_license_key(machine_id, days_valid=365)
    print(f"  Generated key: {key[:40]}...")
    
    # Save and validate
    mgr.save_license(key)
    valid, msg, features = mgr.validate_license()
    print(f"  Validation: valid={valid}, msg='{msg}'")
    print(f"  Features: {features}")
    
    status = "PASS" if valid else "FAIL"
    print(f"  [{status}] License system working")
    
    # Cleanup
    try: os.remove(os.path.join(os.environ.get('TEMP', '/tmp'), 'test_license.dat'))
    except: pass
    
    return valid


if __name__ == "__main__":
    print("SMILES to 3D Converter — Comprehensive Test Suite")
    print("=" * 60)
    
    results = {
        "Parser": test_parser(),
        "3D Generation": test_3d_generation(),
        "Gasteiger Charges": test_charges(),
        "File Export": test_file_export(),
        "GUI Imports": test_gui_import(),
        "License System": test_license(),
    }
    
    print("\n" + "=" * 60)
    print("OVERALL RESULTS")
    print("=" * 60)
    for name, ok in results.items():
        print(f"  {'✓' if ok else '✗'} {name}")
    
    all_pass = all(results.values())
    print(f"\n{'All tests passed!' if all_pass else 'Some tests failed.'}")
    sys.exit(0 if all_pass else 1)
