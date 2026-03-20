#!/usr/bin/env python3
"""
Debug cartoon rendering issue
"""

import sys
import os

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

def debug_cartoon():
    """Debug why cartoon isn't working"""
    
    pdb_file = r"D:\Badar_Sir\4TZK.pdb"
    
    if not os.path.exists(pdb_file):
        print(f"File not found: {pdb_file}")
        return
    
    print("Debugging cartoon rendering...")
    
    try:
        from src.io.file_reader import read_pdb
        from src.gui.main_window import MainWindow
        from PySide6.QtWidgets import QApplication
        
        # Load molecule
        mol = read_pdb(pdb_file)
        print(f"Loaded: {len(mol.atoms)} atoms")
        
        # Create application
        app = QApplication(sys.argv)
        main_window = MainWindow()
        main_window._set_molecule(mol)
        
        # Check render mode
        print(f"Current render mode: {main_window.viewer_3d.render_mode}")
        
        # Force cartoon mode
        main_window.viewer_3d.render_mode = 'cartoon'
        print(f"Set render mode to: {main_window.viewer_3d.render_mode}")
        
        # Check if molecule is protein
        is_protein = mol.properties.get('is_protein', False)
        print(f"Is protein: {is_protein}")
        
        # Get residues
        residues = main_window.viewer_3d._group_residues()
        print(f"Residues found: {len(residues)}")
        
        # Show window for manual inspection
        main_window.show()
        print("Window displayed - check cartoon rendering manually")
        
        app.exec()
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nDebug completed!")

if __name__ == "__main__":
    debug_cartoon()
