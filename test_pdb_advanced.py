#!/usr/bin/env python3
"""
Test PDB import through main window functionality
"""

import sys
import os

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from src.io.file_reader import read_pdb

def create_test_pdb():
    """Create a test PDB file"""
    pdb_content = """HEADER    PROTEIN TEST
ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00 20.00           N
ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00 20.00           C
ATOM      3  C   ALA A   1       2.016   1.424   0.000  1.00 20.00           C
ATOM      4  O   ALA A   1       3.204   1.424   0.000  1.00 20.00           O
ATOM      5  CB  ALA A   1       1.937  -0.944   1.258  1.00 20.00           C
ATOM      6  N   GLY A   2       2.016   2.864   0.000  1.00 20.00           N
ATOM      7  CA  GLY A   2       3.474   2.864   0.000  1.00 20.00           C
ATOM      8  C   GLY A   2       4.032   4.288   0.000  1.00 20.00           C
HELIX     1    1 ALA A   1    ALA A   1  1
SHEET     1    A1 GLY A   2    GLY A   2
CONECT    1    2
CONECT    2    3    5
CONECT    3    4    6
CONECT    6    7
CONECT    7    8
END
"""
    
    with open("test_protein.pdb", 'w') as f:
        f.write(pdb_content)
    return "test_protein.pdb"

def test_pdb_features():
    """Test PDB import with protein features"""
    
    test_file = create_test_pdb()
    
    try:
        print("Testing PDB import with protein features...")
        mol = read_pdb(test_file)
        
        print("PASS Successfully imported PDB:", mol.name)
        print("PASS Atoms:", len(mol.atoms))
        print("PASS Bonds:", len(mol.bonds))
        print("PASS Is protein:", mol.properties.get('is_protein', False))
        
        # Test PDB-specific attributes
        print("\nPDB atom information:")
        for i, atom in enumerate(mol.atoms):
            info = f"  {i}: {atom.symbol} ({atom.pdb_name}) in {atom.res_name}{atom.res_seq} chain {atom.chain_id}"
            if atom.ss_type:
                ss_map = {'H': 'Helix', 'E': 'Sheet', 'C': 'Coil'}
                info += f" [{ss_map.get(atom.ss_type, 'Unknown')}]"
            if atom.b_factor:
                info += f" B-factor: {atom.b_factor:.1f}"
            print(info)
        
        # Test secondary structure ranges
        if 'helix_ranges' in mol.properties:
            print("\nHelix ranges:", mol.properties['helix_ranges'])
        if 'sheet_ranges' in mol.properties:
            print("Sheet ranges:", mol.properties['sheet_ranges'])
        
        print("\nPASS PDB protein import test completed successfully!")
        
    except Exception as e:
        print("FAIL PDB import failed:", e)
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_pdb_features()
