"""
Quick test of AM1 optimization performance.
"""

import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.domain.models.molecule import Molecule
from src.core.domain.models.atom import Atom
from src.core.domain.models.bond import BondType
from src.features.cheminformatics.services.am1 import am1_optimize_geometry

def test_am1_performance():
    """Test AM1 optimization performance improvements."""
    print("=== AM1 Performance Test ===")
    
    # Create water molecule
    mol = Molecule("water")
    o_idx = mol.add_atom(Atom('O'))
    h1_idx = mol.add_atom(Atom('H'))
    h2_idx = mol.add_atom(Atom('H'))
    
    mol.add_bond(o_idx, h1_idx, BondType.SINGLE)
    mol.add_bond(o_idx, h2_idx, BondType.SINGLE)
    
    # Set initial coordinates
    mol.atoms[o_idx].coords = (0.0, 0.0, 0.0)
    mol.atoms[h1_idx].coords = (1.2, 0.0, 0.0)
    mol.atoms[h2_idx].coords = (0.0, 1.2, 0.0)
    
    print("Testing AM1 optimization on water...")
    start_time = time.time()
    success = am1_optimize_geometry(mol, max_steps=10)
    end_time = time.time()
    
    print(f"Completed in {end_time - start_time:.2f} seconds")
    print(f"Success: {success}")
    
    if success:
        r1 = ((mol.atoms[h1_idx].x - mol.atoms[o_idx].x)**2 + 
              (mol.atoms[h1_idx].y - mol.atoms[o_idx].y)**2)**0.5
        r2 = ((mol.atoms[h2_idx].x - mol.atoms[o_idx].x)**2 + 
              (mol.atoms[h2_idx].y - mol.atoms[o_idx].y)**2)**0.5
        print(f"Final O-H distances: {r1:.3f}, {r2:.3f} Å")
        print("[PASS] AM1 optimization working efficiently")
    
    return success

if __name__ == "__main__":
    test_am1_performance()
