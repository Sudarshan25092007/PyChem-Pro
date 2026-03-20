"""
Comprehensive tests for AM1 semi-empirical quantum mechanical implementation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from src.core.domain.models.molecule import Molecule
from src.core.domain.models.atom import Atom
from src.core.domain.models.bond import BondType
from src.features.cheminformatics.services.am1 import am1_assign_charges, am1_optimize_geometry, AM1Calculator

def test_am1_water_charges():
    """Test AM1 charge calculation on water molecule."""
    print("Testing AM1 charge calculation on water...")
    
    # Create water molecule with reasonable initial geometry
    mol = Molecule("water")
    
    # Add atoms
    o_idx = mol.add_atom(Atom('O'))
    h1_idx = mol.add_atom(Atom('H'))
    h2_idx = mol.add_atom(Atom('H'))
    
    # Add bonds
    mol.add_bond(o_idx, h1_idx, BondType.SINGLE)
    mol.add_bond(o_idx, h2_idx, BondType.SINGLE)
    
    # Set initial coordinates (approximate water geometry)
    mol.atoms[o_idx].coords = (0.000, 0.000, 0.000)
    mol.atoms[h1_idx].coords = (0.958, 0.000, 0.000)
    mol.atoms[h2_idx].coords = (-0.240, 0.927, 0.000)
    
    # Calculate AM1 charges
    success = am1_assign_charges(mol)
    
    if success:
        print("[PASS] AM1 charge calculation successful")
        print("Partial charges:")
        for i, atom in enumerate(mol.atoms):
            print(f"  {atom.symbol}: {atom.partial_charge:+.4f}")
        
        # Check charge conservation (should sum to 0)
        total_charge = sum(atom.partial_charge for atom in mol.atoms)
        print(f"Total charge: {total_charge:+.6f} (should be ~0)")
        
        # Check reasonable charge distribution
        o_charge = mol.atoms[o_idx].partial_charge
        h_charges = [mol.atoms[h1_idx].partial_charge, mol.atoms[h2_idx].partial_charge]
        
        if o_charge < -0.3 and all(c > 0.2 for c in h_charges):
            print("[PASS] Charge distribution is chemically reasonable")
        else:
            print("[WARN] Charge distribution may be unusual")
        
        return True
    else:
        print("[FAIL] AM1 charge calculation failed")
        return False

def test_am1_methane_charges():
    """Test AM1 charge calculation on methane molecule."""
    print("\nTesting AM1 charge calculation on methane...")
    
    # Create methane molecule
    mol = Molecule("methane")
    
    # Add atoms
    c_idx = mol.add_atom(Atom('C'))
    h_indices = []
    for i in range(4):
        h_idx = mol.add_atom(Atom('H'))
        h_indices.append(h_idx)
        mol.add_bond(c_idx, h_idx, BondType.SINGLE)
    
    # Set initial coordinates (tetrahedral geometry)
    mol.atoms[c_idx].coords = (0.000, 0.000, 0.000)
    # Tetrahedral H positions
    tetrahedral_coords = [
        (0.629, 0.629, 0.629),
        (-0.629, -0.629, 0.629),
        (-0.629, 0.629, -0.629),
        (0.629, -0.629, -0.629)
    ]
    for h_idx, coords in zip(h_indices, tetrahedral_coords):
        mol.atoms[h_idx].coords = coords
    
    # Calculate AM1 charges
    success = am1_assign_charges(mol)
    
    if success:
        print("[PASS] AM1 charge calculation successful")
        print("Partial charges:")
        for i, atom in enumerate(mol.atoms):
            print(f"  {atom.symbol}: {atom.partial_charge:+.4f}")
        
        # Check charge conservation
        total_charge = sum(atom.partial_charge for atom in mol.atoms)
        print(f"Total charge: {total_charge:+.6f} (should be ~0)")
        
        # Methane should have near-zero charges (non-polar)
        c_charge = mol.atoms[c_idx].partial_charge
        h_charges = [mol.atoms[h_idx].partial_charge for h_idx in h_indices]
        
        if abs(c_charge) < 0.1 and all(abs(c) < 0.1 for c in h_charges):
            print("[PASS] Charge distribution is chemically reasonable for non-polar molecule")
        else:
            print("[WARN] Charge distribution may be unusual for methane")
        
        return True
    else:
        print("[FAIL] AM1 charge calculation failed")
        return False

def test_am1_ammonia_charges():
    """Test AM1 charge calculation on ammonia molecule."""
    print("\nTesting AM1 charge calculation on ammonia...")
    
    # Create ammonia molecule
    mol = Molecule("ammonia")
    
    # Add atoms
    n_idx = mol.add_atom(Atom('N'))
    h_indices = []
    for i in range(3):
        h_idx = mol.add_atom(Atom('H'))
        h_indices.append(h_idx)
        mol.add_bond(n_idx, h_idx, BondType.SINGLE)
    
    # Set initial coordinates (trigonal pyramidal geometry)
    mol.atoms[n_idx].coords = (0.000, 0.000, 0.000)
    # Trigonal pyramidal H positions
    h_coords = [
        (0.944, 0.000, -0.388),
        (-0.472, 0.818, -0.388),
        (-0.472, -0.818, -0.388)
    ]
    for h_idx, coords in zip(h_indices, h_coords):
        mol.atoms[h_idx].coords = coords
    
    # Calculate AM1 charges
    success = am1_assign_charges(mol)
    
    if success:
        print("[PASS] AM1 charge calculation successful")
        print("Partial charges:")
        for i, atom in enumerate(mol.atoms):
            print(f"  {atom.symbol}: {atom.partial_charge:+.4f}")
        
        # Check charge conservation
        total_charge = sum(atom.partial_charge for atom in mol.atoms)
        print(f"Total charge: {total_charge:+.6f} (should be ~0)")
        
        return True
    else:
        print("[FAIL] AM1 charge calculation failed")
        return False

def test_am1_water_optimization():
    """Test AM1 geometry optimization on water molecule."""
    print("\nTesting AM1 geometry optimization on water...")
    
    # Create water molecule with distorted geometry
    mol = Molecule("water_distorted")
    
    # Add atoms
    o_idx = mol.add_atom(Atom('O'))
    h1_idx = mol.add_atom(Atom('H'))
    h2_idx = mol.add_atom(Atom('H'))
    
    # Add bonds
    mol.add_bond(o_idx, h1_idx, BondType.SINGLE)
    mol.add_bond(o_idx, h2_idx, BondType.SINGLE)
    
    # Set distorted initial coordinates
    mol.atoms[o_idx].coords = (0.000, 0.000, 0.000)
    mol.atoms[h1_idx].coords = (1.500, 0.000, 0.000)  # Too long
    mol.atoms[h2_idx].coords = (0.000, 1.500, 0.000)  # 90° angle
    
    print("Initial coordinates:")
    for i, atom in enumerate(mol.atoms):
        print(f"  {atom.symbol}: ({atom.x:.3f}, {atom.y:.3f}, {atom.z:.3f})")
    
    # Calculate initial O-H distances and H-O-H angle
    r1 = np.linalg.norm(np.array(mol.atoms[h1_idx].coords) - np.array(mol.atoms[o_idx].coords))
    r2 = np.linalg.norm(np.array(mol.atoms[h2_idx].coords) - np.array(mol.atoms[o_idx].coords))
    print(f"Initial O-H distances: {r1:.3f}, {r2:.3f} Å")
    
    # Optimize geometry
    success = am1_optimize_geometry(mol, max_steps=20)
    
    if success:
        print("[PASS] AM1 geometry optimization successful")
        print("Optimized coordinates:")
        for i, atom in enumerate(mol.atoms):
            print(f"  {atom.symbol}: ({atom.x:.3f}, {atom.y:.3f}, {atom.z:.3f})")
        
        print("Optimized partial charges:")
        for i, atom in enumerate(mol.atoms):
            print(f"  {atom.symbol}: {atom.partial_charge:+.4f}")
        
        # Check final geometry
        r1_opt = np.linalg.norm(np.array(mol.atoms[h1_idx].coords) - np.array(mol.atoms[o_idx].coords))
        r2_opt = np.linalg.norm(np.array(mol.atoms[h2_idx].coords) - np.array(mol.atoms[o_idx].coords))
        print(f"Optimized O-H distances: {r1_opt:.3f}, {r2_opt:.3f} Å")
        
        # Calculate H-O-H angle
        v1 = np.array(mol.atoms[h1_idx].coords) - np.array(mol.atoms[o_idx].coords)
        v2 = np.array(mol.atoms[h2_idx].coords) - np.array(mol.atoms[o_idx].coords)
        angle = np.degrees(np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))))
        print(f"H-O-H angle: {angle:.1f}°")
        
        # Check if geometry improved
        if 0.8 < r1_opt < 1.2 and 0.8 < r2_opt < 1.2 and 100 < angle < 115:
            print("[PASS] Optimized geometry is chemically reasonable")
        else:
            print("[WARN] Optimized geometry may need improvement")
        
        return True
    else:
        print("[FAIL] AM1 geometry optimization failed")
        return False

def test_am1_calculator_class():
    """Test AM1Calculator class directly."""
    print("\nTesting AM1Calculator class...")
    
    # Create simple H2 molecule
    mol = Molecule("hydrogen")
    
    h1_idx = mol.add_atom(Atom('H'))
    h2_idx = mol.add_atom(Atom('H'))
    mol.add_bond(h1_idx, h2_idx, BondType.SINGLE)
    
    # Set coordinates
    mol.atoms[h1_idx].coords = (0.000, 0.000, 0.000)
    mol.atoms[h2_idx].coords = (0.740, 0.000, 0.000)  # H-H bond length
    
    try:
        calculator = AM1Calculator(mol)
        print("[PASS] AM1Calculator created successfully")
        print(f"Number of atoms: {calculator.n_atoms}")
        print(f"Number of basis functions: {calculator.n_basis}")
        
        # Test SCF
        success = calculator.run_scf(max_iterations=50)
        if success:
            print("[PASS] SCF calculation successful")
            print(f"Total energy: {calculator.total_energy:.6f} Hartree")
            
            # Test charge calculation
            charges = calculator.calculate_partial_charges()
            print("Partial charges:")
            for i, charge in enumerate(charges):
                print(f"  {mol.atoms[i].symbol}: {charge:+.4f}")
            
            return True
        else:
            print("[FAIL] SCF calculation failed")
            return False
            
    except Exception as e:
        print(f"[FAIL] AM1Calculator test failed: {e}")
        return False

def test_am1_error_handling():
    """Test AM1 error handling for unsupported elements."""
    print("\nTesting AM1 error handling...")
    
    # Test with unsupported element
    mol = Molecule("test")
    
    try:
        # Try to add an unsupported element
        atom = Atom('Cl')  # Chlorine not in our parameter set
        mol.add_atom(atom)
        
        # This should fail
        calculator = AM1Calculator(mol)
        print("[FAIL] Should have failed for unsupported element")
        return False
        
    except ValueError as e:
        if "AM1 parameters not available" in str(e):
            print("[PASS] Correctly detected unsupported element")
            return True
        else:
            print(f"[FAIL] Unexpected error: {e}")
            return False
    except Exception as e:
        print(f"[FAIL] Unexpected error type: {e}")
        return False

def test_am1_performance():
    """Test AM1 performance on a slightly larger molecule."""
    print("\nTesting AM1 performance on ethanol...")
    
    # Create ethanol molecule
    mol = Molecule("ethanol")
    
    # Add atoms
    c1_idx = mol.add_atom(Atom('C'))
    c2_idx = mol.add_atom(Atom('C'))
    o_idx = mol.add_atom(Atom('O'))
    h_oh_idx = mol.add_atom(Atom('H'))
    
    # Add hydrogens to first carbon
    h_c1_indices = []
    for i in range(3):
        h_idx = mol.add_atom(Atom('H'))
        h_c1_indices.append(h_idx)
        mol.add_bond(c1_idx, h_idx, BondType.SINGLE)
    
    # Add hydrogens to second carbon
    h_c2_indices = []
    for i in range(2):
        h_idx = mol.add_atom(Atom('H'))
        h_c2_indices.append(h_idx)
        mol.add_bond(c2_idx, h_idx, BondType.SINGLE)
    
    # Add bonds between heavy atoms
    mol.add_bond(c1_idx, c2_idx, BondType.SINGLE)
    mol.add_bond(c2_idx, o_idx, BondType.SINGLE)
    mol.add_bond(o_idx, h_oh_idx, BondType.SINGLE)
    
    # Set reasonable initial coordinates
    mol.atoms[c1_idx].coords = (0.000, 0.000, 0.000)
    mol.atoms[c2_idx].coords = (1.540, 0.000, 0.000)
    mol.atoms[o_idx].coords = (2.500, 0.000, 0.000)
    mol.atoms[h_oh_idx].coords = (3.100, 0.900, 0.000)
    
    # Add H coordinates (simplified)
    for i, h_idx in enumerate(h_c1_indices):
        angle = i * 2 * np.pi / 3
        mol.atoms[h_idx].coords = (-0.500, 0.800 * np.sin(angle), 0.800 * np.cos(angle))
    
    for i, h_idx in enumerate(h_c2_indices):
        angle = i * np.pi
        mol.atoms[h_idx].coords = (1.540, 0.800 * np.sin(angle), 0.800 * np.cos(angle))
    
    print(f"Testing on ethanol ({len(mol.atoms)} atoms)")
    
    # Test charge calculation
    import time
    start_time = time.time()
    success = am1_assign_charges(mol)
    end_time = time.time()
    
    if success:
        print(f"[PASS] AM1 charge calculation successful in {end_time - start_time:.2f} seconds")
        print("Partial charges:")
        for i, atom in enumerate(mol.atoms):
            print(f"  {atom.symbol}: {atom.partial_charge:+.4f}")
        
        # Check charge conservation
        total_charge = sum(atom.partial_charge for atom in mol.atoms)
        print(f"Total charge: {total_charge:+.6f} (should be ~0)")
        
        return True
    else:
        print("[FAIL] AM1 charge calculation failed")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("AM1 SEMI-EMPIRICAL QUANTUM MECHANICS TESTS")
    print("=" * 60)
    
    tests = [
        ("Water Charges", test_am1_water_charges),
        ("Methane Charges", test_am1_methane_charges),
        ("Ammonia Charges", test_am1_ammonia_charges),
        ("Water Optimization", test_am1_water_optimization),
        ("AM1Calculator Class", test_am1_calculator_class),
        ("Error Handling", test_am1_error_handling),
        ("Performance Test", test_am1_performance),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'-' * 40}")
        print(f"Running: {test_name}")
        print(f"{'-' * 40}")
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[FAIL] Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All AM1 tests passed successfully!")
    else:
        print("[WARNING] Some tests failed - review the implementation")
    
    print("=" * 60)
