#!/usr/bin/env python3
"""
Simple test script to demonstrate SMILES to 3D conversion
"""

import sys
import os

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from src.parser import parse_smiles
from src.geometry import generate_3d_coordinates
from src.charges import compute_gasteiger_charges

def test_smiles_conversion():
    """Test basic SMILES to 3D conversion"""
    
    # Test molecules
    test_smiles = [
        "C",           # Methane
        "CC",          # Ethane  
        "CCO",         # Ethanol
        "c1ccccc1",    # Benzene
        "CC(=O)O",     # Acetic acid
        "C1=CC=CC=C1", # Benzene (alternative)
    ]
    
    print("SMILES to 3D Conversion Test")
    print("=" * 40)
    
    for i, smiles in enumerate(test_smiles, 1):
        try:
            print(f"\n{i}. SMILES: {smiles}")
            
            # Parse SMILES
            mol = parse_smiles(smiles)
            print(f"   Parsed: {mol.molecular_formula()} - {len(mol.atoms)} atoms, {len(mol.bonds)} bonds")
            
            # Generate 3D coordinates
            generate_3d_coordinates(mol, optimize=True, max_opt_steps=100)
            print(f"   3D coordinates generated")
            
            # Compute charges
            compute_gasteiger_charges(mol)
            print(f"   Gasteiger charges computed")
            
            # Show some atom info
            heavy_atoms = [a for a in mol.atoms if a.symbol != 'H']
            print(f"   Heavy atoms: {', '.join(f'{a.symbol}({a.partial_charge:+.3f})' for a in heavy_atoms[:3])}")
            
        except Exception as e:
            print(f"   ERROR: {e}")
    
    print(f"\nTest completed successfully!")

if __name__ == "__main__":
    test_smiles_conversion()
