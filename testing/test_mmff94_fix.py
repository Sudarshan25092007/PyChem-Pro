"""
Test MMFF94 optimization fix for get_bond() error.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.domain.models.molecule import Molecule
from src.core.domain.models.atom import Atom
from src.core.domain.models.bond import BondType
from src.features.cheminformatics.services.mmff94 import mmff94_optimize_geometry, mmff94_assign_charges

def test_mmff94_water():
    """Test MMFF94 optimization on water molecule."""
    print("Testing MMFF94 on water molecule...")
    
    # Create water molecule
    mol = Molecule("water")
    
    # Add atoms
    o_idx = mol.add_atom(Atom('O'))
    h1_idx = mol.add_atom(Atom('H'))
    h2_idx = mol.add_atom(Atom('H'))
    
    # Set initial coordinates
    mol.atoms[o_idx].coords = (0.0, 0.0, 0.0)
    mol.atoms[h1_idx].coords = (1.0, 0.0, 0.0)
    mol.atoms[h2_idx].coords = (-0.5, 0.866, 0.0)
    
    # Add bonds
    mol.add_bond(o_idx, h1_idx, BondType.SINGLE)
    mol.add_bond(o_idx, h2_idx, BondType.SINGLE)
    
    # Assign charges
    success = mmff94_assign_charges(mol)
    print(f"Charge assignment: {'SUCCESS' if success else 'FAILED'}")
    
    # Optimize geometry
    success = mmff94_optimize_geometry(mol)
    print(f"Geometry optimization: {'SUCCESS' if success else 'FAILED'}")
    
    # Print final coordinates
    print("Final coordinates:")
    for i, atom in enumerate(mol.atoms):
        print(f"  {atom.symbol}: ({atom.x:.3f}, {atom.y:.3f}, {atom.z:.3f})")
    
    return success

def test_mmff94_methane():
    """Test MMFF94 optimization on methane molecule."""
    print("\nTesting MMFF94 on methane molecule...")
    
    # Create methane molecule
    mol = Molecule("methane")
    
    # Add atoms
    c_idx = mol.add_atom(Atom('C'))
    h_indices = []
    for i in range(4):
        h_idx = mol.add_atom(Atom('H'))
        h_indices.append(h_idx)
        mol.add_bond(c_idx, h_idx, BondType.SINGLE)
    
    # Set initial coordinates
    mol.atoms[c_idx].coords = (0.0, 0.0, 0.0)
    for i, h_idx in enumerate(h_indices):
        mol.atoms[h_idx].coords = (1.0, 0.0, 0.0)
    
    # Assign charges
    success = mmff94_assign_charges(mol)
    print(f"Charge assignment: {'SUCCESS' if success else 'FAILED'}")
    
    # Optimize geometry
    success = mmff94_optimize_geometry(mol)
    print(f"Geometry optimization: {'SUCCESS' if success else 'FAILED'}")
    
    # Print final coordinates
    print("Final coordinates:")
    for i, atom in enumerate(mol.atoms):
        print(f"  {atom.symbol}: ({atom.x:.3f}, {atom.y:.3f}, {atom.z:.3f})")
    
    return success

def test_mmff94_ethanol():
    """Test MMFF94 optimization on ethanol molecule."""
    print("\nTesting MMFF94 on ethanol molecule...")
    
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
    
    # Set initial coordinates
    mol.atoms[c1_idx].coords = (0.0, 0.0, 0.0)
    mol.atoms[c2_idx].coords = (1.5, 0.0, 0.0)
    mol.atoms[o_idx].coords = (2.5, 0.0, 0.0)
    mol.atoms[h_oh_idx].coords = (3.0, 0.0, 0.0)
    
    for h_idx in h_c1_indices:
        mol.atoms[h_idx].coords = (0.0, 0.0, 0.0)
    for h_idx in h_c2_indices:
        mol.atoms[h_idx].coords = (0.0, 0.0, 0.0)
    
    # Assign charges
    success = mmff94_assign_charges(mol)
    print(f"Charge assignment: {'SUCCESS' if success else 'FAILED'}")
    
    # Optimize geometry
    success = mmff94_optimize_geometry(mol)
    print(f"Geometry optimization: {'SUCCESS' if success else 'FAILED'}")
    
    # Print final coordinates
    print("Final coordinates:")
    for i, atom in enumerate(mol.atoms):
        print(f"  {atom.symbol}: ({atom.x:.3f}, {atom.y:.3f}, {atom.z:.3f})")
    
    return success

if __name__ == "__main__":
    print("=" * 50)
    print("MMFF94 OPTIMIZATION FIX TEST")
    print("=" * 50)
    
    try:
        water_success = test_mmff94_water()
        methane_success = test_mmff94_methane()
        ethanol_success = test_mmff94_ethanol()
        
        print("\n" + "=" * 50)
        print("SUMMARY:")
        print(f"Water: {'PASS' if water_success else 'FAIL'}")
        print(f"Methane: {'PASS' if methane_success else 'FAIL'}")
        print(f"Ethanol: {'PASS' if ethanol_success else 'FAIL'}")
        
        if all([water_success, methane_success, ethanol_success]):
            print("All tests PASSED! MMFF94 fix is working correctly.")
        else:
            print("Some tests FAILED. There may be remaining issues.")
        
    except Exception as e:
        print(f"ERROR during testing: {e}")
        import traceback
        traceback.print_exc()
