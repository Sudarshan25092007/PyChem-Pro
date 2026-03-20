#!/usr/bin/env python3
"""
Test PDB loading performance with 500KB file
"""

import sys
import os
import time

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from src.io.file_reader import read_pdb

def create_large_pdb_kb(target_kb=500):
    """Create a PDB file of approximately target KB size"""
    # Each residue is roughly 4 lines * ~80 chars = ~320 chars
    # To get 500KB, we need about 500*1024/320 ≈ 1600 residues
    num_residues = int(target_kb * 1024 / 320)
    
    pdb_content = f"""HEADER    LARGE PROTEIN TEST - TARGET {target_kb}KB
REMARK   1 GENERATED FOR PERFORMANCE TESTING
"""
    
    atom_serial = 1
    conect_records = []
    
    for res_seq in range(1, num_residues + 1):
        # Alternate between different residue types
        residue_types = ["ALA", "GLY", "VAL", "LEU", "ILE", "SER", "THR", "ASP", "ASN", "GLU"]
        res_name = residue_types[res_seq % len(residue_types)]
        chain_id = chr(65 + (res_seq % 4))  # A, B, C, D chains
        
        # Add backbone atoms
        backbone_atoms = ["N", "CA", "C", "O"]
        for atom_name in backbone_atoms:
            x = res_seq * 1.5 + (atom_serial % 10) * 0.1
            y = (res_seq % 20) * 0.8 + (atom_serial % 5) * 0.2
            z = (res_seq % 15) * 1.2 + (atom_serial % 3) * 0.3
            pdb_content += f"ATOM{atom_serial:6d}  {atom_name:<4} {res_name:<3} {chain_id} {res_seq:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           {atom_name[0]:>2}\n"
            atom_serial += 1
        
        # Add side chain atoms (varying complexity)
        if res_name == "ALA":
            x = res_seq * 1.5 + 0.5
            y = (res_seq % 20) * 0.8 + 0.5
            z = (res_seq % 15) * 1.2 + 0.5
            pdb_content += f"ATOM{atom_serial:6d}  CB  {res_name:<3} {chain_id} {res_seq:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C\n"
            atom_serial += 1
        elif res_name == "VAL":
            x = res_seq * 1.5 + 0.5
            y = (res_seq % 20) * 0.8 + 0.5
            z = (res_seq % 15) * 1.2 + 0.5
            pdb_content += f"ATOM{atom_serial:6d}  CB  {res_name:<3} {chain_id} {res_seq:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C\n"
            atom_serial += 1
            x = res_seq * 1.5 + 1.0
            pdb_content += f"ATOM{atom_serial:6d}  CG1 {res_name:<3} {chain_id} {res_seq:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C\n"
            atom_serial += 1
            x = res_seq * 1.5 + 0.0
            pdb_content += f"ATOM{atom_serial:6d}  CG2 {res_name:<3} {chain_id} {res_seq:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C\n"
            atom_serial += 1
        
        # Add some CONECT records for connectivity
        if res_seq > 1 and res_seq % 10 == 0:
            prev_ca = (res_seq - 1) * 5 + 2  # Approximate CA position
            curr_n = res_seq * 5 + 1        # Approximate N position
            conect_records.append(f"CONECT{prev_ca:6d}{curr_n:6d}\n")
    
    # Add secondary structure annotations
    pdb_content += "HELIX     1    1 ALA A   1    ALA A  50  1\n"
    pdb_content += "HELIX     2    2 VAL B  51    VAL B 100  1\n"
    pdb_content += "SHEET     1    A1 LEU C 101    LEU C 150\n"
    pdb_content += "SHEET     2    A2 ILE D 151    ILE D 200\n"
    
    # Add CONECT records
    pdb_content += "".join(conect_records)
    pdb_content += "END\n"
    
    return pdb_content

def test_large_pdb_performance():
    """Test PDB loading performance with 500KB file"""
    
    print("Testing PDB loading performance with 500KB file...")
    
    # Create 500KB test file
    target_kb = 500
    print(f"\nCreating {target_kb}KB test file...")
    
    pdb_content = create_large_pdb_kb(target_kb)
    test_file = f"test_large_{target_kb}kb.pdb"
    
    with open(test_file, 'w') as f:
        f.write(pdb_content)
    
    try:
        # Check actual file size
        actual_size = os.path.getsize(test_file) / 1024
        print(f"Actual file size: {actual_size:.1f} KB")
        
        # Measure loading time
        print("Loading file...")
        start_time = time.time()
        mol = read_pdb(test_file)
        end_time = time.time()
        
        load_time = end_time - start_time
        
        print(f"\nResults:")
        print(f"  File size: {actual_size:.1f} KB")
        print(f"  Load time: {load_time:.3f} seconds")
        print(f"  Atoms loaded: {len(mol.atoms)}")
        print(f"  Bonds loaded: {len(mol.bonds)}")
        
        if load_time > 0:
            print(f"  Speed: {len(mol.atoms)/load_time:.0f} atoms/second")
            print(f"  Rate: {actual_size/load_time:.0f} KB/second")
        
        # Performance evaluation
        if load_time < 2.0:
            print("  EXCELLENT: Loads in under 2 seconds")
        elif load_time < 5.0:
            print("  GOOD: Loads in under 5 seconds")
        elif load_time < 10.0:
            print("  ACCEPTABLE: Loads in under 10 seconds")
        else:
            print("  SLOW: Takes more than 10 seconds")
        
        # Test memory efficiency
        import psutil
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Load again to test memory usage
        mol2 = read_pdb(test_file)
        
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = memory_after - memory_before
        
        print(f"  Memory used: {memory_used:.1f} MB")
        print(f"  Memory per atom: {memory_used*1024/len(mol.atoms):.2f} KB/atom")
        
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
    
    print("\nLarge PDB performance testing completed!")

if __name__ == "__main__":
    test_large_pdb_performance()
