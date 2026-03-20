"""
Test the lipophilic selection to debug why carbon attached to polar atoms is still being selected.
"""

import sys
import os

# Add the parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def test_lipophilic_selection():
    """Test lipophilic selection with a molecule that has carbon attached to polar atoms."""
    print("Testing Lipophilic Selection...")
    
    try:
        from src.features.cheminformatics.services.atom_properties import AtomPropertyAnalyzer, select_atoms_by_property
        from src.core.domain.models.molecule import Molecule
        from src.core.domain.models.atom import Atom
        from src.core.domain.models.bond import Bond
        
        # Create test molecule: CH3-CH2-OH (ethanol-like)
        molecule = Molecule()
        
        # Create atoms first
        c1 = Atom('C')
        c2 = Atom('C')  # This carbon is attached to O, should NOT be lipophilic
        o = Atom('O')  # Polar atom
        h1 = Atom('H')  # Hydrogen on C1, should be lipophilic
        
        # Add atoms using molecule's add_atom method to initialize adjacency properly
        c1_idx = molecule.add_atom(c1)
        c2_idx = molecule.add_atom(c2)
        o_idx = molecule.add_atom(o)
        h1_idx = molecule.add_atom(h1)
        
        # Set positions after adding
        c1.x, c1.y, c1.z = 0.0, 0.0, 0.0
        c2.x, c2.y, c2.z = 1.0, 0.0, 0.0
        o.x, o.y, o.z = 2.0, 0.0, 0.0
        h1.x, h1.y, h1.z = -0.5, 0.5, 0.0
        
        # Add bonds using molecule's add_bond method to build adjacency properly
        from src.core.domain.models.bond import BondType
        bond1_idx = molecule.add_bond(0, 1, BondType.SINGLE)  # C1-C2
        bond2_idx = molecule.add_bond(1, 2, BondType.SINGLE)  # C2-O
        bond3_idx = molecule.add_bond(0, 3, BondType.SINGLE)  # C1-H1
        
        print(f"   Created molecule with {len(molecule.atoms)} atoms")
        print(f"   Bonds: {len(molecule.bonds)}")
        
        # Test individual atom lipophilic status
        analyzer = AtomPropertyAnalyzer(molecule)
        
        print("\n   Individual atom lipophilic tests:")
        for i, atom in enumerate(molecule.atoms):
            is_lipo = analyzer.is_lipophilic(i)
            neighbors = molecule.get_neighbors(i)
            neighbor_symbols = [molecule.atoms[n].symbol for n in neighbors]
            print(f"   Atom {i} ({atom.symbol}): lipophilic={is_lipo}, neighbors={neighbor_symbols}")
        
        # Test selection using the same method as sele('lipo')
        lipo_indices = select_atoms_by_property(molecule, 'lipophilic')
        print(f"\n   sele('lipo') result: {lipo_indices}")
        
        # Expected: C1 and H1 should be lipophilic, C2 should NOT be lipophilic (attached to O)
        expected_lipo = {0, 3}  # C1 and H1
        if lipo_indices == expected_lipo:
            print("   ✅ Lipophilic selection working correctly!")
            return True
        else:
            print(f"   ❌ Lipophilic selection incorrect!")
            print(f"   Expected: {expected_lipo}")
            print(f"   Got: {lipo_indices}")
            
            # Debug: Check if adjacency is working
            print("\n   Debugging adjacency:")
            for i in range(len(molecule.atoms)):
                neighbors = molecule.get_neighbors(i)
                print(f"   Atom {i} neighbors: {neighbors}")
            
            return False
            
    except Exception as e:
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run lipophilic selection test."""
    print("SMILES Molecular Toolkit - Lipophilic Selection Debug")
    print("=" * 60)
    
    success = test_lipophilic_selection()
    
    print("\n" + "=" * 60)
    print("LIPOPHILIC SELECTION TEST RESULT")
    print("=" * 60)
    
    if success:
        print("🎉 LIPOPHILIC SELECTION WORKING!")
        print("✅ Carbon attached to polar atoms correctly excluded")
        print("✅ sele('lipo') command should work correctly")
    else:
        print("❌ LIPOPHILIC SELECTION ISSUE FOUND")
        print("❌ Carbon attached to polar atoms still being selected")
        print("❌ Need further investigation")

if __name__ == "__main__":
    main()
