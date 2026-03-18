"""Quick test of core logic (no Qt required)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("SMILES-to-3D Core Tests (no Qt)")
print("=" * 50)

# 1. Formula tests
from src.parser.parser import parse_smiles
formulas = [
    ("C", "CH4"), ("CC", "C2H6"), ("C=C", "C2H4"), ("C#C", "C2H2"),
    ("CCO", "C2H6O"), ("c1ccccc1", "C6H6"), ("CC(=O)O", "C2H4O2"),
    ("CC(=O)Oc1ccccc1C(=O)O", "C9H8O4"),
]
print("\n--- Formula Tests ---")
for smi, expected in formulas:
    mol = parse_smiles(smi)
    got = mol.molecular_formula()
    ok = "PASS" if got == expected else "FAIL"
    print(f"  [{ok}] {smi:30s} -> {got:12s} (expected {expected})")

# 2. 3D generation
from src.geometry.coord_gen import generate_3d_coordinates
import numpy as np
print("\n--- 3D Generation Tests ---")
for smi, name in [("C","Methane"),("CC","Ethane"),("c1ccccc1","Benzene"),("CCO","Ethanol")]:
    mol = parse_smiles(smi, name)
    generate_3d_coordinates(mol, optimize=True, max_opt_steps=100)
    all_ok = all(a.has_coords for a in mol.atoms)
    dists = []
    for i in range(len(mol.atoms)):
        for j in range(i+1, len(mol.atoms)):
            a1,a2 = mol.atoms[i], mol.atoms[j]
            d = np.sqrt((a1.x-a2.x)**2+(a1.y-a2.y)**2+(a1.z-a2.z)**2)
            dists.append(d)
    md = min(dists) if dists else 0
    ok = "PASS" if all_ok and md > 0.3 else "FAIL"
    print(f"  [{ok}] {name:15s} atoms={len(mol.atoms):3d} min_dist={md:.2f}A")

# 3. Gasteiger charges
from src.charges.gasteiger import compute_gasteiger_charges
print("\n--- Gasteiger Charge Tests ---")
for smi, name, expected_total in [("O","Water",0), ("CCO","Ethanol",0), ("[NH4+]","Ammonium",1)]:
    mol = parse_smiles(smi, name)
    generate_3d_coordinates(mol, optimize=False, max_opt_steps=50)
    compute_gasteiger_charges(mol)
    total = sum(a.partial_charge for a in mol.atoms)
    heavy = [f"{a.symbol}={a.partial_charge:.4f}" for a in mol.atoms if a.symbol != 'H']
    ok = "PASS" if abs(total - expected_total) < 0.1 else "WARN"
    print(f"  [{ok}] {name:15s} sum_q={total:.4f} heavy: {', '.join(heavy)}")

# 4. File export
from src.io.sdf_writer import write_sdf
from src.io.mol2_writer import write_mol2
print("\n--- File Export Tests ---")
mol = parse_smiles("c1ccccc1", "Benzene")
generate_3d_coordinates(mol, optimize=True, max_opt_steps=100)
compute_gasteiger_charges(mol)

sdf = write_sdf(mol)
ok1 = "M  END" in sdf and "$$$$" in sdf
print(f"  [{'PASS' if ok1 else 'FAIL'}] SDF: {len(sdf)} chars, has M_END={ok1}")

mol2 = write_mol2(mol)
ok2 = "@<TRIPOS>ATOM" in mol2 and "@<TRIPOS>BOND" in mol2
print(f"  [{'PASS' if ok2 else 'FAIL'}] MOL2: {len(mol2)} chars, has sections={ok2}")

# 5. License
from src.security.license import LicenseManager
print("\n--- License Test ---")
mgr = LicenseManager(license_file=os.path.join(os.environ.get('TEMP','/tmp'), 'test_lic.dat'))
key = mgr.generate_and_save(365)
valid, msg, feats = mgr.validate_license()
print(f"  [{'PASS' if valid else 'FAIL'}] {msg}")
try: os.remove(os.path.join(os.environ.get('TEMP','/tmp'), 'test_lic.dat'))
except: pass

print("\n" + "=" * 50)
print("All core tests completed!")
