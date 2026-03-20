"""
Simple AM1 test to debug issues.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from src.core.domain.models.molecule import Molecule
from src.core.domain.models.atom import Atom
from src.core.domain.models.bond import BondType
from src.features.cheminformatics.services.am1 import am1_assign_charges

def test_simple_h2():
    """Test AM1 on simple H2 molecule."""
    print("Testing AM1 on H2 molecule...")
    
    # Create H2 molecule
    mol = Molecule("h2")
    
    h1_idx = mol.add_atom(Atom('H'))
    h2_idx = mol.add_atom(Atom('H'))
    mol.add_bond(h1_idx, h2_idx, BondType.SINGLE)
    
    # Set coordinates
    mol.atoms[h1_idx].coords = (0.0, 0.0, 0.0)
    mol.atoms[h2_idx].coords = (0.74, 0.0, 0.0)
    
    print("Initial coordinates:")
    for atom in mol.atoms:
        print(f"  {atom.symbol}: ({atom.x:.3f}, {atom.y:.3f}, {atom.z:.3f})")
    
    # Calculate charges
    success = am1_assign_charges(mol)
    
    if success:
        print("SUCCESS!")
        print("Partial charges:")
        for atom in mol.atoms:
            print(f"  {atom.symbol}: {atom.partial_charge:+.4f}")
        
        total_charge = sum(atom.partial_charge for atom in mol.atoms)
        print(f"Total charge: {total_charge:+.6f}")
    else:
        print("FAILED!")
    
    return success

if __name__ == "__main__":
    test_simple_h2()
