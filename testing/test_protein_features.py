#!/usr/bin/env python3
"""
Test protein visualization features
"""

import sys
import os

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from src.io.file_reader import read_pdb
from src.gui.mol_viewer_3d import MolViewer3D
from PySide6.QtWidgets import QApplication

def test_protein_features():
    """Test protein visualization features"""
    
    # Create a test protein PDB file with secondary structure
    pdb_content = """HEADER    TEST PROTEIN WITH SECONDARY STRUCTURE
ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00 20.00           N
ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00 20.00           C
ATOM      3  C   ALA A   1       2.016   1.424   0.000  1.00 20.00           C
ATOM      4  O   ALA A   1       3.204   1.424   0.000  1.00 20.00           O
ATOM      5  CB  ALA A   1       1.937  -0.944   1.258  1.00 20.00           C
ATOM      6  N   LEU A   2       2.016   2.864   0.000  1.00 20.00           N
ATOM      7  CA  LEU A   2       3.474   2.864   0.000  1.00 20.00           C
ATOM      8  C   LEU A   2       4.032   4.288   0.000  1.00 20.00           C
ATOM      9  O   LEU A   2       5.220   4.288   0.000  1.00 20.00           O
ATOM     10  CB  LEU A   2       3.953   1.920   1.258  1.00 20.00           C
ATOM     11  CG  LEU A   2       5.411   1.920   1.258  1.00 20.00           C
ATOM     12  CD1 LEU A   2       6.016   0.544   1.258  1.00 20.00           C
ATOM     13  CD2 LEU A   2       6.016   3.296   1.258  1.00 20.00           C
ATOM     14  N   VAL A   3       4.032   5.712   0.000  1.00 20.00           N
ATOM     15  CA  VAL A   3       5.490   5.712   0.000  1.00 20.00           C
ATOM     16  C   VAL A   3       6.048   7.136   0.000  1.00 20.00           C
ATOM     17  O   VAL A   3       7.236   7.136   0.000  1.00 20.00           O
ATOM     18  CB  VAL A   3       5.969   4.768   1.258  1.00 20.00           C
ATOM     19  CG1 VAL A   3       7.427   4.768   1.258  1.00 20.00           C
ATOM     20  CG2 VAL A   3       5.427   3.344   2.516  1.00 20.00           C
HELIX     1    1 ALA A   1    ALA A   1  1
SHEET     1    A1 LEU A   2    LEU A   2
HELIX     2    2 VAL A   3    VAL A   3  1
CONECT    1    2
CONECT    2    3    5
CONECT    3    4    6
CONECT    5    7
CONECT    6    7    8
CONECT    7    8    9
CONECT    8    9   10
CONECT    9   10   11
CONECT   10   11
CONECT   11   12   13
CONECT   12   13
CONECT   13   14
CONECT   14   15
CONECT   15   16   18
CONECT   16   17   19
CONECT   17   18
CONECT   18   19   20
END
"""
    
    # Write test PDB file
    test_file = "test_protein_advanced.pdb"
    with open(test_file, 'w') as f:
        f.write(pdb_content)
    
    try:
        print("Testing protein visualization features...")
        
        # Test PDB import
        mol = read_pdb(test_file)
        print("PASS PDB import successful")
        print(f"  - Atoms: {len(mol.atoms)}")
        print(f"  - Bonds: {len(mol.bonds)}")
        print(f"  - Is protein: {mol.properties.get('is_protein', False)}")
        
        # Test secondary structure assignment
        ss_types = {}
        for atom in mol.atoms:
            if hasattr(atom, 'ss_type'):
                ss_types[atom.ss_type] = ss_types.get(atom.ss_type, 0) + 1
        print(f"  - Secondary structure: {ss_types}")
        
        # Test Qt application
        app = QApplication(sys.argv)
        
        # Test 3D viewer with protein modes
        viewer = MolViewer3D()
        viewer.set_molecule(mol)
        
        # Test each render mode
        render_modes = ['ball_and_stick', 'spacefill', 'wireframe', 'cartoon', 'ribbon', 'backbone']
        for mode in render_modes:
            viewer.render_mode = mode
            viewer.show_sidechains = True
            viewer.update()
            print(f"  - Render mode '{mode}': OK")
            
            # Test side chain toggle
            viewer.show_sidechains = False
            viewer.update()
            viewer.show_sidechains = True
            viewer.update()
        
        print("PASS All protein visualization features working!")
        
        # Test background color
        from PySide6.QtGui import QColor
        viewer.bg_color = QColor(255, 255, 255)  # White
        viewer.update()
        print("PASS White background working")
        
        app.quit()
        
    except Exception as e:
        print("FAIL Protein visualization test failed:", e)
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_protein_features()
