#!/usr/bin/env python3
"""
Test with the actual 4TZK.pdb file
"""

import sys
import os
import time

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

def test_actual_4tzk():
    """Test with the actual 4TZK.pdb file"""
    
    pdb_file = r"D:\Badar_Sir\4TZK.pdb"
    
    if not os.path.exists(pdb_file):
        print(f"File not found: {pdb_file}")
        print("Please make sure the file exists at the specified location.")
        return
    
    print("Testing with actual 4TZK.pdb file...")
    
    # Check file size
    file_size = os.path.getsize(pdb_file) / 1024
    print(f"File size: {file_size:.1f} KB")
    
    try:
        from src.io.file_reader import read_pdb
        from src.gui.mol_viewer_3d import MolViewer3D
        from PySide6.QtWidgets import QApplication
        
        # Test loading performance
        print("\n1. Loading PDB file...")
        start_time = time.time()
        mol = read_pdb(pdb_file)
        load_time = time.time() - start_time
        
        print(f"   Load time: {load_time:.3f} seconds")
        print(f"   Atoms: {len(mol.atoms)}")
        print(f"   Bonds: {len(mol.bonds)}")
        print(f"   Is protein: {mol.properties.get('is_protein', False)}")
        
        # Test rendering performance
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
        
        print("\n3. Render mode performance:")
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
            print(f"\n4. Large molecule optimization:")
            print(f"   Atoms ({len(mol.atoms)}) > 500: Fast rendering enabled")
            print(f"   Ball_and_stick mode uses simple circles and thin lines")
            print(f"   Protein modes (cartoon/ribbon/backbone) are always fast")
        
        # Performance evaluation
        total_time = load_time + initial_render_time
        print(f"\n5. Performance Summary:")
        print(f"   Load time: {load_time:.3f} seconds")
        print(f"   Initial render: {initial_render_time:.3f} seconds")
        print(f"   Total time: {total_time:.3f} seconds")
        
        if total_time < 2.0:
            print("   EXCELLENT: Very responsive")
        elif total_time < 5.0:
            print("   GOOD: Acceptable performance")
        elif total_time < 10.0:
            print("   OK: Some delay but usable")
        else:
            print("   SLOW: May need further optimization")
        
        # Recommendations
        print("\n6. Recommendations:")
        if len(mol.atoms) > 1000:
            print("   - Use Cartoon or Ribbon mode for best performance")
            print("   - Ball_and_stick mode uses simplified rendering")
            print("   - Consider hiding side chains for faster interaction")
        
        app.quit()
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n4TZK.pdb test completed!")

if __name__ == "__main__":
    test_actual_4tzk()
