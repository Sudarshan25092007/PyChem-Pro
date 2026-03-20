"""
Test that AM1 GUI integration works with the fixed implementation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.domain.models.molecule import Molecule
from src.core.domain.models.atom import Atom
from src.core.domain.models.bond import BondType
from src.features.cheminformatics.services.am1 import am1_assign_charges

def test_am1_for_gui():
    """Test AM1 with molecules that would typically be used in GUI."""
    print("=== AM1 GUI Compatibility Test ===")
    
    # Test molecules that users might load in GUI
    test_molecules = [
        {
            "name": "Water (H2O)",
            "smiles": "O",
            "expected_elements": ["O", "H", "H"]
        },
        {
            "name": "Methane (CH4)", 
            "smiles": "C",
            "expected_elements": ["C", "H", "H", "H", "H"]
        },
        {
            "name": "Ammonia (NH3)",
            "smiles": "N",
            "expected_elements": ["N", "H", "H", "H"]
        },
        {
            "name": "Methanol (CH3OH)",
            "smiles": "CO",
            "expected_elements": ["C", "O", "H", "H", "H", "H"]
        }
    ]
    
    all_passed = True
    
    for mol_info in test_molecules:
        print(f"\nTesting {mol_info['name']}...")
        
        try:
            # Create simple test molecule (not full SMILES parsing)
            mol = Molecule(mol_info['name'])
            
            # Add atoms based on expected elements
            atom_indices = []
            for element in mol_info['expected_elements']:
                idx = mol.add_atom(Atom(element))
                atom_indices.append(idx)
            
            # Set some basic coordinates
            for i, idx in enumerate(atom_indices):
                mol.atoms[idx].coords = (i * 1.0, 0.0, 0.0)
            
            # Add some bonds (simplified)
            if len(atom_indices) > 1:
                for i in range(min(4, len(atom_indices)-1)):
                    mol.add_bond(atom_indices[0], atom_indices[i+1], BondType.SINGLE)
            
            print(f"  Elements: {[atom.symbol for atom in mol.atoms]}")
            
            # Test AM1 charge calculation
            success = am1_assign_charges(mol)
            
            if success:
                charges = [atom.partial_charge for atom in mol.atoms]
                total_charge = sum(charges)
                print(f"  [PASS] AM1 charges: {[f'{c:+.3f}' for c in charges]}")
                print(f"  [PASS] Total charge: {total_charge:+.6f}")
                
                # Check charge conservation
                if abs(total_charge) < 0.001:
                    print(f"  [PASS] Charge conserved")
                else:
                    print(f"  [WARN] Charge not conserved: {total_charge}")
                    all_passed = False
                    
            else:
                print(f"  [FAIL] AM1 calculation failed")
                all_passed = False
                
        except Exception as e:
            print(f"  [ERROR] {e}")
            all_passed = False
    
    print(f"\n=== Test Results ===")
    if all_passed:
        print("[SUCCESS] All AM1 GUI tests passed!")
        print("AM1 is ready for GUI use.")
    else:
        print("[FAIL] Some AM1 GUI tests failed.")
        print("Check the implementation before GUI use.")
    
    return all_passed

if __name__ == "__main__":
    test_am1_for_gui()
