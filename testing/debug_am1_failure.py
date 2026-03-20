"""
Debug script to identify why AM1 charge calculation is failing.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.domain.models.molecule import Molecule
from src.core.domain.models.atom import Atom
from src.core.domain.models.bond import BondType
from src.features.cheminformatics.services.am1 import am1_assign_charges

def debug_am1_failure():
    """Debug AM1 failure by testing with a simple molecule."""
    print("=== AM1 Debug Script ===")
    
    # Test 1: Simple H2 molecule (should work)
    print("\n1. Testing H2 molecule...")
    try:
        mol_h2 = Molecule("h2")
        h1_idx = mol_h2.add_atom(Atom('H'))
        h2_idx = mol_h2.add_atom(Atom('H'))
        mol_h2.add_bond(h1_idx, h2_idx, BondType.SINGLE)
        
        # Set coordinates
        mol_h2.atoms[h1_idx].coords = (0.0, 0.0, 0.0)
        mol_h2.atoms[h2_idx].coords = (0.74, 0.0, 0.0)
        
        print(f"   H2 atoms: {[atom.symbol for atom in mol_h2.atoms]}")
        print(f"   H2 coordinates: {[(atom.x, atom.y, atom.z) for atom in mol_h2.atoms]}")
        
        success = am1_assign_charges(mol_h2)
        print(f"   H2 AM1 success: {success}")
        if success:
            print(f"   H2 charges: {[atom.partial_charge for atom in mol_h2.atoms]}")
        
    except Exception as e:
        print(f"   H2 failed: {e}")
    
    # Test 2: Water molecule (should work)
    print("\n2. Testing H2O molecule...")
    try:
        mol_h2o = Molecule("water")
        o_idx = mol_h2o.add_atom(Atom('O'))
        h1_idx = mol_h2o.add_atom(Atom('H'))
        h2_idx = mol_h2o.add_atom(Atom('H'))
        
        mol_h2o.add_bond(o_idx, h1_idx, BondType.SINGLE)
        mol_h2o.add_bond(o_idx, h2_idx, BondType.SINGLE)
        
        # Set coordinates
        mol_h2o.atoms[o_idx].coords = (0.0, 0.0, 0.0)
        mol_h2o.atoms[h1_idx].coords = (0.958, 0.0, 0.0)
        mol_h2o.atoms[h2_idx].coords = (-0.240, 0.927, 0.0)
        
        print(f"   H2O atoms: {[atom.symbol for atom in mol_h2o.atoms]}")
        
        success = am1_assign_charges(mol_h2o)
        print(f"   H2O AM1 success: {success}")
        if success:
            print(f"   H2O charges: {[atom.partial_charge for atom in mol_h2o.atoms]}")
        
    except Exception as e:
        print(f"   H2O failed: {e}")
    
    # Test 3: Check supported elements
    print("\n3. Checking supported elements...")
    from src.features.cheminformatics.services.am1 import AM1_PARAMETERS
    print(f"   Supported elements: {list(AM1_PARAMETERS.keys())}")
    
    # Test 4: Try a molecule with unsupported element
    print("\n4. Testing molecule with Cl (unsupported)...")
    try:
        mol_cl = Molecule("cl_test")
        cl_idx = mol_cl.add_atom(Atom('Cl'))
        mol_cl.atoms[cl_idx].coords = (0.0, 0.0, 0.0)
        
        print(f"   Cl molecule atoms: {[atom.symbol for atom in mol_cl.atoms]}")
        
        success = am1_assign_charges(mol_cl)
        print(f"   Cl AM1 success: {success}")
        
    except Exception as e:
        print(f"   Cl failed (expected): {e}")
    
    print("\n=== Debug Complete ===")
    print("If H2 and H2O work but your molecule fails,")
    print("the issue is likely unsupported elements in your molecule.")

if __name__ == "__main__":
    debug_am1_failure()
