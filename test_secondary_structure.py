#!/usr/bin/env python3
"""
Test secondary structure detection
"""

import sys
import os

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

def test_secondary_structure():
    """Test secondary structure detection"""
    
    pdb_file = r"D:\Badar_Sir\4TZK.pdb"
    
    if not os.path.exists(pdb_file):
        print(f"File not found: {pdb_file}")
        return
    
    print("Testing secondary structure detection...")
    
    try:
        from src.io.file_reader import read_pdb
        
        # Load molecule
        mol = read_pdb(pdb_file)
        print(f"Loaded: {len(mol.atoms)} atoms")
        
        # Check secondary structure ranges
        helix_ranges = mol.properties.get('helix_ranges', [])
        sheet_ranges = mol.properties.get('sheet_ranges', [])
        
        print(f"Helix ranges: {len(helix_ranges)}")
        for i, (chain, start, end) in enumerate(helix_ranges):
            print(f"  Helix {i+1}: Chain {chain}, Res {start}-{end}")
        
        print(f"Sheet ranges: {len(sheet_ranges)}")
        for i, (chain, start, end) in enumerate(sheet_ranges):
            print(f"  Sheet {i+1}: Chain {chain}, Res {start}-{end}")
        
        # Count secondary structure types
        ss_counts = {'H': 0, 'E': 0, 'C': 0}
        for atom in mol.atoms:
            if hasattr(atom, 'ss_type'):
                ss_counts[atom.ss_type] = ss_counts.get(atom.ss_type, 0) + 1
        
        print(f"Secondary structure counts:")
        print(f"  Helices (H): {ss_counts['H']}")
        print(f"  Sheets (E): {ss_counts['E']}")
        print(f"  Coils (C): {ss_counts['C']}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_secondary_structure()
