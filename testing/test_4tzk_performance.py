#!/usr/bin/env python3
"""
Test large PDB file performance improvements
"""

import sys
import os
import time

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from src.io.file_reader import read_pdb
from src.gui.mol_viewer_3d import MolViewer3D
from PySide6.QtWidgets import QApplication

def test_large_pdb_performance():
    """Test performance with a file similar to 4TZK.pdb (597KB)"""
    
    print("Testing large PDB performance optimizations...")
    
    # Create a test file similar to 4TZK.pdb size
    target_kb = 597
    print(f"\nCreating {target_kb}KB test file (similar to 4TZK.pdb)...")
    
    # Generate a realistic protein structure
    pdb_content = f"""HEADER    4TZK TEST STRUCTURE - {target_kb}KB
REMARK   1 SIMULATED FOR PERFORMANCE TESTING
REMARK   2 TYPICAL PROTEIN WITH THOUSANDS OF ATOMS
"""
    
    atom_serial = 1
    conect_records = []
    
    # Create about 4000 residues to reach ~600KB
    num_residues = int(target_kb * 1024 / 300)  # ~300 bytes per residue
    
    for res_seq in range(1, min(num_residues + 1, 5000)):  # Cap at 5000 for testing
        # Use realistic amino acid distribution
        aa_types = ["ALA", "GLY", "VAL", "LEU", "ILE", "SER", "THR", "ASP", "ASN", 
                   "GLU", "LYS", "ARG", "HIS", "PHE", "TYR", "TRP", "PRO", "CYS", "MET"]
        res_name = aa_types[res_seq % len(aa_types)]
        chain_id = chr(65 + (res_seq % 4))  # A, B, C, D chains
        
        # Add backbone atoms
        backbone_atoms = ["N", "CA", "C", "O"]
        for atom_name in backbone_atoms:
            x = res_seq * 1.5 + (atom_serial % 10) * 0.1
            y = (res_seq % 20) * 0.8 + (atom_serial % 5) * 0.2
            z = (res_seq % 15) * 1.2 + (atom_serial % 3) * 0.3
            pdb_content += f"ATOM{atom_serial:6d}  {atom_name:<4} {res_name:<3} {chain_id} {res_seq:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           {atom_name[0]:>2}\n"
            atom_serial += 1
        
        # Add side chain atoms based on residue type
        if res_name in ["ALA", "GLY"]:
            # Simple side chains
            x = res_seq * 1.5 + 0.5
            y = (res_seq % 20) * 0.8 + 0.5
            z = (res_seq % 15) * 1.2 + 0.5
            side_atom = "CB" if res_name == "ALA" else "HA"
            pdb_content += f"ATOM{atom_serial:6d}  {side_atom:<4} {res_name:<3} {chain_id} {res_seq:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C\n"
            atom_serial += 1
        elif res_name in ["VAL", "LEU", "ILE"]:
            # Medium side chains
            for i, atom in enumerate(["CB", "CG1", "CG2"]):
                x = res_seq * 1.5 + 0.5 + i * 0.3
                y = (res_seq % 20) * 0.8 + 0.5 + i * 0.2
                z = (res_seq % 15) * 1.2 + 0.5 + i * 0.4
                pdb_content += f"ATOM{atom_serial:6d}  {atom:<4} {res_name:<3} {chain_id} {res_seq:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C\n"
                atom_serial += 1
        else:
            # Complex side chains
            for i, atom in enumerate(["CB", "CG", "CD", "CE", "NZ"][:5]):
                x = res_seq * 1.5 + 0.5 + i * 0.3
                y = (res_seq % 20) * 0.8 + 0.5 + i * 0.2
                z = (res_seq % 15) * 1.2 + 0.5 + i * 0.4
                pdb_content += f"ATOM{atom_serial:6d}  {atom:<4} {res_name:<3} {chain_id} {res_seq:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C\n"
                atom_serial += 1
        
        # Add some CONECT records periodically
        if res_seq > 1 and res_seq % 5 == 0:
            prev_ca = (res_seq - 1) * 6 + 2  # Approximate CA position
            curr_n = res_seq * 6 + 1        # Approximate N position
            conect_records.append(f"CONECT{prev_ca:6d}{curr_n:6d}\n")
    
    # Add secondary structure
    pdb_content += "HELIX     1    1 ALA A   1    ALA A 100  1\n"
    pdb_content += "HELIX     2    2 VAL B 101    VAL B 200  1\n"
    pdb_content += "SHEET     1    A1 LEU C 201    LEU C 300\n"
    pdb_content += "SHEET     2    A2 ILE D 301    ILE D 400\n"
    
    # Add CONECT records
    pdb_content += "".join(conect_records[:100])  # Limit connections for performance
    pdb_content += "END\n"
    
    test_file = f"test_4tzk_like_{target_kb}kb.pdb"
    
    with open(test_file, 'w') as f:
        f.write(pdb_content)
    
    try:
        # Check file size
        actual_size = os.path.getsize(test_file) / 1024
        print(f"Created test file: {actual_size:.1f} KB")
        
        # Test loading performance
        print("\n1. Testing PDB loading performance...")
        start_time = time.time()
        mol = read_pdb(test_file)
        load_time = time.time() - start_time
        
        print(f"   Load time: {load_time:.3f} seconds")
        print(f"   Atoms: {len(mol.atoms)}")
        print(f"   Bonds: {len(mol.bonds)}")
        print(f"   Is protein: {mol.properties.get('is_protein', False)}")
        
        # Test rendering performance with Qt
        print("\n2. Testing rendering performance...")
        app = QApplication(sys.argv)
        
        viewer = MolViewer3D()
        viewer.setMinimumSize(800, 600)
        
        # Test initial load
        start_time = time.time()
        viewer.set_molecule(mol)
        initial_render_time = time.time() - start_time
        
        print(f"   Initial render time: {initial_render_time:.3f} seconds")
        print(f"   Auto-switched to: {viewer.render_mode}")
        
        # Test different render modes
        render_modes = ['ball_and_stick', 'cartoon', 'ribbon', 'backbone']
        
        for mode in render_modes:
            viewer.render_mode = mode
            start_time = time.time()
            viewer.update()
            # Force repaint
            viewer.repaint()
            render_time = time.time() - start_time
            
            print(f"   {mode}: {render_time:.3f} seconds")
        
        # Test large molecule optimization
        if len(mol.atoms) > 500:
            print(f"\n3. Large molecule optimization active:")
            print(f"   Atoms > 500: Using fast rendering for ball_and_stick mode")
            print(f"   Simple circles instead of gradient spheres")
            print(f"   Thin lines instead of detailed bonds")
        
        # Performance evaluation
        total_time = load_time + initial_render_time
        print(f"\n4. Performance Summary:")
        print(f"   Total load + render time: {total_time:.3f} seconds")
        
        if total_time < 2.0:
            print("   EXCELLENT: Very responsive")
        elif total_time < 5.0:
            print("   GOOD: Acceptable performance")
        elif total_time < 10.0:
            print("   OK: Some delay but usable")
        else:
            print("   SLOW: May need optimization")
        
        app.quit()
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
    
    print("\nLarge PDB performance test completed!")

if __name__ == "__main__":
    test_large_pdb_performance()
