"""
Simple test for hydrogen lipophilic fix without Unicode.
"""

import sys
import os

# Add the parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def test_hydrogen_lipo():
    """Test hydrogen lipophilic with polar atom exclusion."""
    print("Testing Hydrogen Lipophilic Fix...")
    
    try:
        from src.features.cheminformatics.services.atom_properties import select_atoms_by_property
        from src.core.domain.models.molecule import Molecule
        from src.core.domain.models.atom import Atom
        from src.core.domain.models.bond import BondType
        
        # Create test molecule: CH3-CH2-OH
        molecule = Molecule()
        
        # Create atoms
        c1 = Atom('C')  # Non-polar carbon
        c2 = Atom('C')  # Carbon attached to O
        o = Atom('O')  # Polar oxygen
        h1 = Atom('H')  # H attached to C1 (should be lipophilic)
        h2 = Atom('H')  # H attached to C2 (should NOT be lipophilic)
        h3 = Atom('H')  # H attached to O (should NOT be lipophilic)
        
        # Add atoms
        molecule.add_atom(c1)
        molecule.add_atom(c2)
        molecule.add_atom(o)
        molecule.add_atom(h1)
        molecule.add_atom(h2)
        molecule.add_atom(h3)
        
        # Add bonds
        molecule.add_bond(0, 1, BondType.SINGLE)  # C1-C2
        molecule.add_bond(0, 3, BondType.SINGLE)  # C1-H1
        molecule.add_bond(1, 2, BondType.SINGLE)  # C2-O
        molecule.add_bond(1, 4, BondType.SINGLE)  # C2-H2
        molecule.add_bond(2, 5, BondType.SINGLE)  # O-H3
        
        print(f"   Created molecule with {len(molecule.atoms)} atoms")
        
        # Test selection
        lipo_indices = select_atoms_by_property(molecule, 'lipophilic')
        print(f"   sele('lipo') result: {lipo_indices}")
        
        # Expected: C1 (index 0) should be lipophilic
        # H1 (index 3) attached to C1 should be lipophilic
        # C2 (index 1) attached to O should NOT be lipophilic
        # H2 (index 4) attached to C2 should be lipophilic (C2 is carbon, not polar)
        # H3 (index 5) attached to O should NOT be lipophilic
        # O (index 2) should NOT be lipophilic
        
        expected = {0, 3, 4}  # C1, H1, and H2 should be lipophilic
        print(f"   Expected: {expected}")
        
        if lipo_indices == expected:
            print("   SUCCESS: Corrected hydrogen lipophilic working!")
            print("   - C1 (non-polar carbon): lipophilic")
            print("   - H1 (attached to C1): lipophilic")
            print("   - C2 (attached to O): NOT lipophilic")
            print("   - H2 (attached to C2): lipophilic (C2 is carbon)")
            print("   - H3 (attached to O): NOT lipophilic")
            return True
        else:
            print("   ISSUE: Results don't match expected")
            return False
            
    except Exception as e:
        print(f"   Error: {e}")
        return False

def main():
    success = test_hydrogen_lipo()
    
    print("\n" + "=" * 50)
    print("HYDROGEN LIPOPHILIC TEST RESULT")
    print("=" * 50)
    
    if success:
        print("ENHANCED LIPOPHILIC SELECTION WORKING!")
        print("Carbon and hydrogen attached to polar atoms excluded")
    else:
        print("ISSUES FOUND - Need investigation")

if __name__ == "__main__":
    main()
