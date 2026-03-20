"""
Test the enhanced lipophilic selection with hydrogen polar atom exclusion.
"""

import sys
import os

# Add the parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def test_hydrogen_lipophilic_fix():
    """Test hydrogen lipophilic selection with polar atom exclusion."""
    print("Testing Enhanced Hydrogen Lipophilic Selection...")
    
    try:
        from src.features.cheminformatics.services.atom_properties import AtomPropertyAnalyzer, select_atoms_by_property
        from src.core.domain.models.molecule import Molecule
        from src.core.domain.models.atom import Atom
        from src.core.domain.models.bond import BondType
        
        # Create test molecule with various H environments
        molecule = Molecule()
        
        # Create atoms
        c1 = Atom('C')  # Non-polar carbon
        c2 = Atom('C')  # Carbon attached to O
        o = Atom('O')  # Polar oxygen
        n = Atom('N')  # Polar nitrogen
        h1 = Atom('H')  # H attached to C (should be lipophilic)
        h2 = Atom('H')  # H attached to C2 (should NOT be lipophilic - C2 attached to O)
        h3 = Atom('H')  # H attached to O (should NOT be lipophilic)
        h4 = Atom('H')  # H attached to N (should NOT be lipophilic)
        
        # Add atoms to molecule
        molecule.add_atom(c1)
        molecule.add_atom(c2)
        molecule.add_atom(o)
        molecule.add_atom(n)
        molecule.add_atom(h1)
        molecule.add_atom(h2)
        molecule.add_atom(h3)
        molecule.add_atom(h4)
        
        # Add bonds: C1-H1, C1-C2, C2-O, C2-H2, O-H3, N-H4
        molecule.add_bond(0, 1, BondType.SINGLE)  # C1-C2
        molecule.add_bond(0, 4, BondType.SINGLE)  # C1-H1
        molecule.add_bond(1, 2, BondType.SINGLE)  # C2-O
        molecule.add_bond(1, 5, BondType.SINGLE)  # C2-H2
        molecule.add_bond(2, 6, BondType.SINGLE)  # O-H3
        molecule.add_bond(3, 7, BondType.SINGLE)  # N-H4
        
        print(f"   Created molecule with {len(molecule.atoms)} atoms")
        print(f"   Bonds: {len(molecule.bonds)}")
        
        # Test individual atom lipophilic status
        analyzer = AtomPropertyAnalyzer(molecule)
        
        print("\n   Individual atom lipophilic tests:")
        expected_results = {
            0: True,   # C1 (attached to C2, H1) - should be lipophilic
            1: False,  # C2 (attached to C1, O, H2) - should NOT be lipophilic (attached to O)
            2: False,  # O (polar) - should NOT be lipophilic
            3: False,  # N (polar) - should NOT be lipophilic
            4: True,   # H1 (attached to C1) - should be lipophilic
            5: False,  # H2 (attached to C2) - should NOT be lipophilic (C2 attached to O)
            6: False,  # H3 (attached to O) - should NOT be lipophilic
            7: False,  # H4 (attached to N) - should NOT be lipophilic
        }
        
        all_correct = True
        for i, atom in enumerate(molecule.atoms):
            is_lipo = analyzer.is_lipophilic(i)
            neighbors = molecule.get_neighbors(i)
            neighbor_symbols = [molecule.atoms[n].symbol for n in neighbors]
            expected = expected_results[i]
            status = "✅" if is_lipo == expected else "❌"
            print(f"   {status} Atom {i} ({atom.symbol}): lipophilic={is_lipo}, expected={expected}, neighbors={neighbor_symbols}")
            if is_lipo != expected:
                all_correct = False
        
        # Test selection using sele('lipo')
        lipo_indices = select_atoms_by_property(molecule, 'lipophilic')
        expected_lipo = {0, 4}  # Only C1 and H1 should be lipophilic
        
        print(f"\n   sele('lipo') result: {lipo_indices}")
        print(f"   Expected result: {expected_lipo}")
        
        if lipo_indices == expected_lipo and all_correct:
            print("   ✅ Enhanced hydrogen lipophilic selection working correctly!")
            return True
        else:
            print("   ❌ Enhanced hydrogen lipophilic selection has issues")
            return False
            
    except Exception as e:
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run enhanced hydrogen lipophilic test."""
    print("SMILES Molecular Toolkit - Enhanced Hydrogen Lipophilic Test")
    print("=" * 70)
    
    success = test_hydrogen_lipophilic_fix()
    
    print("\n" + "=" * 70)
    print("ENHANCED HYDROGEN LIPOPHILIC TEST RESULT")
    print("=" * 70)
    
    if success:
        print("🎉 ENHANCED HYDROGEN LIPOPHILIC SELECTION WORKING!")
        print("✅ Carbon attached to polar atoms correctly excluded")
        print("✅ Hydrogen attached to polar atoms correctly excluded")
        print("✅ sele('lipo') command works with enhanced accuracy")
        print("\nEnhanced chemical accuracy achieved!")
    else:
        print("❌ ENHANCED HYDROGEN LIPOPHILIC SELECTION ISSUES")
        print("❌ Need further investigation")

if __name__ == "__main__":
    main()
