#!/usr/bin/env python3
"""
Test PDB loading performance with larger file
"""

import sys
import os
import time

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from src.io.file_reader import read_pdb

def create_large_pdb(num_residues=100):
    """Create a larger PDB file for performance testing"""
    pdb_content = """HEADER    PERFORMANCE TEST PROTEIN
"""
    
    atom_serial = 1
    conect_records = []
    
    for res_seq in range(1, num_residues + 1):
        res_name = "ALA" if res_seq % 2 == 1 else "GLY"
        chain_id = "A"
        
        # Add backbone atoms
        backbone_atoms = ["N", "CA", "C", "O"]
        for atom_name in backbone_atoms:
            x = res_seq * 1.5
            y = atom_serial * 0.1
            z = res_seq * 0.2
            pdb_content += f"ATOM{atom_serial:6d}  {atom_name:<4} {res_name:<3} {chain_id} {res_seq:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           {atom_name[0]:>2}\n"
            atom_serial += 1
        
        # Add side chain atoms for ALA
        if res_name == "ALA":
            x = res_seq * 1.5 + 0.5
            y = atom_serial * 0.1
            z = res_seq * 0.2 + 0.5
            pdb_content += f"ATOM{atom_serial:6d}  CB  {res_name:<3} {chain_id} {res_seq:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C\n"
            
            # Add CONECT records
            if res_seq > 1:
                # Connect to previous residue
                prev_ca = (res_seq - 1) * 4 + 2  # CA of previous residue
                curr_n = (res_seq - 1) * 4 + 5    # N of current residue
                conect_records.append(f"CONECT{prev_ca:6d}{curr_n:6d}\n")
            
            atom_serial += 1
    
    # Add some secondary structure
    pdb_content += "HELIX     1    1 ALA A   1    ALA A  10  1\n"
    pdb_content += "SHEET     1    A1 GLY A  11    GLY A  20\n"
    
    # Add CONECT records
    pdb_content += "".join(conect_records)
    pdb_content += "END\n"
    
    return pdb_content

def test_pdb_performance():
    """Test PDB loading performance"""
    
    print("Testing PDB loading performance...")
    
    # Create test files of different sizes
    sizes = [50, 100, 200, 500]  # Number of residues
    
    for size in sizes:
        print(f"\nTesting {size} residues (~{size*5} atoms):")
        
        # Create test PDB
        pdb_content = create_large_pdb(size)
        test_file = f"test_perf_{size}.pdb"
        
        with open(test_file, 'w') as f:
            f.write(pdb_content)
        
        try:
            # Measure loading time
            start_time = time.time()
            mol = read_pdb(test_file)
            end_time = time.time()
            
            load_time = end_time - start_time
            file_size = os.path.getsize(test_file) / 1024  # KB
            
            print(f"  File size: {file_size:.1f} KB")
            print(f"  Load time: {load_time:.3f} seconds")
            print(f"  Atoms loaded: {len(mol.atoms)}")
            print(f"  Bonds loaded: {len(mol.bonds)}")
            print(f"  Speed: {len(mol.atoms)/load_time:.0f} atoms/second")
            
            # Performance target: should load 500KB file in < 2 seconds
            if file_size >= 500 and load_time < 2.0:
                print("  PASS: Meets performance target")
            elif file_size < 500:
                print("  OK: Smaller file, performance acceptable")
            else:
                print("  WARN: Above performance target")
                
        except Exception as e:
            print(f"  FAIL: {e}")
        
        finally:
            # Clean up
            if os.path.exists(test_file):
                os.remove(test_file)
    
    print("\nPDB performance testing completed!")

if __name__ == "__main__":
    test_pdb_performance()
