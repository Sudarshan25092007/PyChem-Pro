#!/usr/bin/env python3
"""
Test PDB import functionality
"""

import sys
import os

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from src.io.file_reader import read_pdb

def test_pdb_import():
    """Test PDB file import"""
    
    # Create a simple PDB file for testing
    pdb_content = """HEADER    TEST STRUCTURE
ATOM      1  N   ALA A   1      10.000   5.000   0.000  1.00 20.00           N
ATOM      2  CA  ALA A   1      11.000   5.000   0.000  1.00 20.00           C
ATOM      3  C   ALA A   1      11.500   6.000   0.000  1.00 20.00           C
ATOM      4  O   ALA A   1      12.500   6.000   0.000  1.00 20.00           O
ATOM      5  CB  ALA A   1      11.000   4.000   1.000  1.00 20.00           C
CONECT    1    2
CONECT    2    3    5
CONECT    3    4
END
"""
    
    # Write test PDB file
    test_file = "test.pdb"
    with open(test_file, 'w') as f:
        f.write(pdb_content)
    
    try:
        print("Testing PDB import...")
        mol = read_pdb(test_file)
        
        print("PASS Successfully imported PDB:", mol.name)
        print("PASS Atoms:", len(mol.atoms))
        print("PASS Bonds:", len(mol.bonds))
        
        # Check PDB-specific attributes
        for i, atom in enumerate(mol.atoms):
            print(f"  Atom {i}: {atom.symbol} - {atom.pdb_name} in {atom.res_name} chain {atom.chain_id}")
        
        print("PASS PDB import test passed!")
        
    except Exception as e:
        print("FAIL PDB import failed:", e)
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_pdb_import()
