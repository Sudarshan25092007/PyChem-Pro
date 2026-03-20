"""
Test PM3 integration and compare with AM1.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.domain.models.molecule import Molecule
from src.core.domain.models.atom import Atom
from src.core.domain.models.bond import BondType
from src.features.cheminformatics.services.pm3 import pm3_assign_charges
from src.features.cheminformatics.services.am1 import am1_assign_charges

def test_pm3_vs_am1():
    """Test PM3 vs AM1 on common molecules."""
    print("=== PM3 vs AM1 Comparison Test ===")
    
    # Test molecules
    test_molecules = [
        {
            "name": "Water (H2O)",
            "elements": ["O", "H", "H"],
            "bonds": [(0, 1), (0, 2)]
        },
        {
            "name": "Methane (CH4)",
            "elements": ["C", "H", "H", "H", "H"],
            "bonds": [(0, 1), (0, 2), (0, 3), (0, 4)]
        },
        {
            "name": "Ammonia (NH3)",
            "elements": ["N", "H", "H", "H"],
            "bonds": [(0, 1), (0, 2), (0, 3)]
        },
        {
            "name": "Methanol (CH3OH)",
            "elements": ["C", "O", "H", "H", "H", "H"],
            "bonds": [(0, 1), (0, 2), (0, 3), (0, 4), (1, 5)]
        }
    ]
    
    all_passed = True
    
    for mol_info in test_molecules:
        print(f"\n--- Testing {mol_info['name']} ---")
        
        # Create molecule
        mol = Molecule(mol_info['name'])
        atom_indices = []
        
        # Add atoms
        for element in mol_info['elements']:
            idx = mol.add_atom(Atom(element))
            atom_indices.append(idx)
        
        # Set basic coordinates
        for i, idx in enumerate(atom_indices):
            mol.atoms[idx].coords = (i * 1.0, 0.0, 0.0)
        
        # Add bonds
        for i, j in mol_info['bonds']:
            mol.add_bond(atom_indices[i], atom_indices[j], BondType.SINGLE)
        
        print(f"Elements: {[atom.symbol for atom in mol.atoms]}")
        
        # Test AM1
        print("\nAM1 Results:")
        try:
            mol_am1 = mol  # Copy for AM1
            success_am1 = am1_assign_charges(mol_am1)
            if success_am1:
                charges_am1 = [atom.partial_charge for atom in mol_am1.atoms]
                total_am1 = sum(charges_am1)
                print(f"  Charges: {[f'{c:+.3f}' for c in charges_am1]}")
                print(f"  Total: {total_am1:+.6f}")
                print(f"  Status: SUCCESS")
            else:
                print(f"  Status: FAILED")
                all_passed = False
        except Exception as e:
            print(f"  Status: ERROR - {e}")
            all_passed = False
        
        # Test PM3
        print("\nPM3 Results:")
        try:
            mol_pm3 = mol  # Copy for PM3
            success_pm3 = pm3_assign_charges(mol_pm3)
            if success_pm3:
                charges_pm3 = [atom.partial_charge for atom in mol_pm3.atoms]
                total_pm3 = sum(charges_pm3)
                print(f"  Charges: {[f'{c:+.3f}' for c in charges_pm3]}")
                print(f"  Total: {total_pm3:+.6f}")
                print(f"  Status: SUCCESS")
            else:
                print(f"  Status: FAILED")
                all_passed = False
        except Exception as e:
            print(f"  Status: ERROR - {e}")
            all_passed = False
        
        # Compare results if both succeeded
        if success_am1 and success_pm3:
            diff = [abs(a - p) for a, p in zip(charges_am1, charges_pm3)]
            max_diff = max(diff)
            print(f"\nComparison:")
            print(f"  Max charge difference: {max_diff:.3f}")
            if max_diff < 0.1:
                print(f"  Methods are similar (diff < 0.1)")
            else:
                print(f"  Methods show significant differences (diff >= 0.1)")
    
    print(f"\n=== Test Results ===")
    if all_passed:
        print("[SUCCESS] All PM3 tests passed!")
        print("PM3 is ready for GUI use alongside AM1.")
    else:
        print("[FAIL] Some PM3 tests failed.")
        print("Check the implementation before GUI use.")
    
    return all_passed

if __name__ == "__main__":
    test_pm3_vs_am1()
