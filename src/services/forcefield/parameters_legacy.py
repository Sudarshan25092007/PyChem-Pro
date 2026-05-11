# src/services/forcefield/parameters.py
"""
MMFF94 parameter tables — consolidated empirical data.

All parameters in one file for easy reference and modification.
"""

# ─── Bond Stretching ───────────────────────────────────────────
# Key: (symbol1, symbol2, bond_order) -> (r0_angstrom, kb_force_constant)
MMFF94_BOND = {
    ('C', 'C', 1): (1.52, 4.4),
    ('C', 'C', 2): (1.33, 9.6),
    ('C', 'C', 3): (1.20, 15.0),
    ('C', 'C', 1.5): (1.39, 7.0),
    ('C', 'N', 1): (1.47, 4.2),
    ('C', 'N', 2): (1.27, 9.0),
    ('C', 'N', 1.5): (1.34, 6.5),
    ('C', 'O', 1): (1.43, 5.0),
    ('C', 'O', 2): (1.22, 11.5),
    ('C', 'O', 1.5): (1.30, 8.0),
    ('C', 'S', 1): (1.82, 3.2),
    ('C', 'S', 2): (1.60, 7.5),
    ('C', 'F', 1): (1.35, 5.5),
    ('C', 'Cl', 1): (1.77, 3.0),
    ('C', 'Br', 1): (1.94, 2.5),
    ('C', 'I', 1): (2.14, 2.0),
    ('C', 'H', 1): (1.09, 4.8),
    ('C', 'P', 1): (1.85, 3.0),
    ('N', 'N', 1): (1.45, 3.8),
    ('N', 'N', 2): (1.25, 9.5),
    ('N', 'O', 1): (1.40, 4.0),
    ('N', 'O', 2): (1.21, 11.0),
    ('N', 'H', 1): (1.01, 6.0),
    ('N', 'S', 1): (1.75, 3.5),
    ('O', 'O', 1): (1.48, 3.0),
    ('O', 'H', 1): (0.96, 7.2),
    ('O', 'P', 1): (1.63, 4.5),
    ('O', 'P', 2): (1.48, 9.0),
    ('O', 'S', 1): (1.70, 4.0),
    ('O', 'S', 2): (1.43, 10.0),
    ('S', 'S', 1): (2.05, 2.8),
    ('S', 'H', 1): (1.34, 4.0),
    ('P', 'H', 1): (1.42, 3.5),
    ('P', 'P', 1): (2.21, 2.0),
    # Added Halogens and common organic bonds
    ('N', 'O', 1.5): (1.23, 9.0), # Nitro group N=O
    ('C', 'N', 3): (1.16, 14.0),  # Nitrile C#N
    ('S', 'O', 2): (1.43, 10.0),  # Sulfone S=O
    ('P', 'O', 2): (1.48, 9.0),   # Phosphine oxide P=O
}

# ─── Angle Bending ─────────────────────────────────────────────
# Key: (sym_i, sym_center, sym_k, hybridization) -> (theta0_deg, ka)
MMFF94_ANGLE = {
    ('C', 'C', 'C', 'sp3'): (109.5, 0.7),
    ('C', 'C', 'H', 'sp3'): (109.5, 0.5),
    ('H', 'C', 'H', 'sp3'): (109.5, 0.4),
    ('C', 'C', 'O', 'sp3'): (109.5, 0.8),
    ('C', 'C', 'N', 'sp3'): (109.5, 0.8),
    ('O', 'C', 'H', 'sp3'): (109.5, 0.6),
    ('N', 'C', 'H', 'sp3'): (109.5, 0.6),
    ('O', 'C', 'O', 'sp3'): (109.5, 0.9),
    ('N', 'C', 'N', 'sp3'): (109.5, 0.8),
    ('C', 'C', 'S', 'sp3'): (109.5, 0.6),
    ('C', 'C', 'F', 'sp3'): (109.5, 0.7),
    ('C', 'C', 'Cl', 'sp3'): (109.5, 0.6),
    ('F', 'C', 'H', 'sp3'): (109.5, 0.6),
    ('Cl', 'C', 'H', 'sp3'): (109.5, 0.5),
    ('S', 'C', 'H', 'sp3'): (109.5, 0.5),
    ('C', 'C', 'C', 'sp2'): (120.0, 0.9),
    ('C', 'C', 'H', 'sp2'): (120.0, 0.5),
    ('C', 'C', 'O', 'sp2'): (120.0, 1.0),
    ('C', 'C', 'N', 'sp2'): (120.0, 0.9),
    ('O', 'C', 'O', 'sp2'): (126.0, 1.2),
    ('O', 'C', 'H', 'sp2'): (120.0, 0.6),
    ('N', 'C', 'H', 'sp2'): (120.0, 0.6),
    ('N', 'C', 'O', 'sp2'): (120.0, 1.0),
    ('H', 'C', 'H', 'sp2'): (120.0, 0.4),
    ('C', 'C', 'C', 'sp'): (180.0, 1.2),
    ('C', 'C', 'H', 'sp'): (180.0, 0.6),
    ('C', 'C', 'N', 'sp'): (180.0, 1.0),
    ('C', 'N', 'C', 'sp3'): (109.5, 0.7),
    ('C', 'N', 'H', 'sp3'): (109.5, 0.6),
    ('H', 'N', 'H', 'sp3'): (106.0, 0.5),
    ('C', 'N', 'C', 'sp2'): (120.0, 0.9),
    ('C', 'N', 'H', 'sp2'): (120.0, 0.6),
    ('O', 'N', 'O', 'sp2'): (125.0, 1.1),
    ('C', 'O', 'H', 'sp3'): (104.5, 0.8),
    ('C', 'O', 'C', 'sp3'): (112.0, 0.8),
    ('H', 'O', 'H', 'sp3'): (104.5, 0.7),
    ('C', 'O', 'P', 'sp3'): (120.0, 0.7),
    ('C', 'S', 'C', 'sp3'): (99.0, 0.6),
    ('C', 'S', 'H', 'sp3'): (96.0, 0.5),
    ('H', 'S', 'H', 'sp3'): (92.0, 0.4),
    ('O', 'P', 'O', 'sp3'): (109.5, 0.8),
    ('C', 'P', 'C', 'sp3'): (109.5, 0.6),
    # Added parameters
    ('C', 'N', 'O', 'sp2'): (120.0, 1.0),
    ('O', 'N', 'O', 'sp2'): (120.0, 1.2),
    ('C', 'C', 'Cl', 'sp2'): (120.0, 0.7),
    ('C', 'C', 'F', 'sp2'): (120.0, 0.8),
}

# ─── Torsion/Dihedral ─────────────────────────────────────────
# Key: (sym_i, type_j, type_k, sym_l) -> (V1, V2, V3)
MMFF94_TORSION = {
    ('*', 'C_sp3', 'C_sp3', '*'): (0.0, 0.0, 0.3),
    ('H', 'C_sp3', 'C_sp3', 'H'): (0.0, 0.0, 0.24),
    ('C', 'C_sp3', 'C_sp3', 'C'): (0.2, 0.3, 0.4),
    ('C', 'C_sp3', 'C_sp3', 'H'): (0.0, 0.0, 0.3),
    ('O', 'C_sp3', 'C_sp3', 'O'): (0.0, 1.0, 0.0),
    ('O', 'C_sp3', 'C_sp3', 'H'): (0.0, 0.0, 0.4),
    ('N', 'C_sp3', 'C_sp3', 'H'): (0.0, 0.0, 0.35),
    ('N', 'C_sp3', 'C_sp3', 'N'): (0.0, 0.8, 0.0),
    ('*', 'C_sp3', 'C_sp2', '*'): (0.0, 0.0, 0.0),
    ('H', 'C_sp3', 'C_sp2', '*'): (0.0, 0.0, 0.1),
    ('*', 'C_sp2', 'C_sp2', '*'): (0.0, 10.0, 0.0),
    ('*', 'C_sp2', 'N_sp2', '*'): (0.0, 8.0, 0.0),
    ('*', 'N_sp2', 'C_sp2', '*'): (0.0, 8.0, 0.0),
    ('C', 'C_sp3', 'O_sp3', 'H'): (0.0, 0.0, 0.5),
    ('C', 'C_sp3', 'O_sp3', 'C'): (0.0, 0.0, 0.6),
    ('H', 'C_sp3', 'O_sp3', 'H'): (0.0, 0.0, 0.4),
    ('H', 'C_sp3', 'O_sp3', 'C'): (0.0, 0.0, 0.4),
    ('C', 'C_sp3', 'N_sp3', 'H'): (0.0, 0.0, 0.3),
    ('H', 'C_sp3', 'S_sp3', 'H'): (0.0, 0.0, 0.25),
    ('C', 'C_sp3', 'N_sp3', 'C'): (0.0, 0.0, 0.5),
    ('*', 'C_sp3', 'S_sp3', '*'): (0.0, 0.0, 0.3),
    ('H', 'C_sp3', 'S_sp3', 'H'): (0.0, 0.0, 0.25),
    # Aromatic ring torsions
    ('*', 'C_aro', 'C_aro', '*'): (0.0, 10.0, 0.0),
    ('*', 'C_aro', 'N_aro', '*'): (0.0, 10.0, 0.0),
    ('*', 'N_aro', 'N_aro', '*'): (0.0, 10.0, 0.0),
}

# ─── Out-of-Plane Bending ──────────────────────────────────────
# Key: (sym_center, sym_i, sym_j, sym_k) -> koop
MMFF94_OOP = {
    ('C', 'C', 'C', 'C'): 0.05,
    ('C', 'C', 'C', 'H'): 0.04,
    ('C', 'C', 'H', 'H'): 0.03,
    ('N', 'C', 'C', 'C'): 0.05,
    ('C', 'N', 'C', 'C'): 0.04,
    ('C', 'C', 'C', 'N'): 0.05,
}

# ─── Van der Waals ─────────────────────────────────────────────
MMFF94_VDW = {
    'H': (1.20, 0.020), 'C': (1.70, 0.107), 'N': (1.55, 0.069),
    'O': (1.52, 0.060), 'F': (1.47, 0.050), 'S': (1.80, 0.250),
    'P': (1.80, 0.200), 'Cl': (1.75, 0.227), 'Br': (1.85, 0.320),
    'I': (1.98, 0.400), 'Si': (2.10, 0.310), 'B': (1.65, 0.085),
    'Se': (1.90, 0.291),
}

# ─── Bond Charge Increments ───────────────────────────────────
MMFF94_BCI = {
    ('C', 'C'): 0.0, ('C', 'H'): -0.06, ('H', 'C'): 0.06,
    ('C', 'O'): 0.15, ('O', 'C'): -0.15, ('C', 'N'): 0.10,
    ('N', 'C'): -0.10, ('C', 'S'): 0.05, ('S', 'C'): -0.05,
    ('C', 'F'): 0.20, ('F', 'C'): -0.20, ('C', 'Cl'): 0.15,
    ('Cl', 'C'): -0.15, ('C', 'Br'): 0.12, ('Br', 'C'): -0.12,
    ('C', 'I'): 0.10, ('I', 'C'): -0.10, ('O', 'H'): -0.25,
    ('H', 'O'): 0.25, ('N', 'H'): -0.20, ('H', 'N'): 0.20,
    ('S', 'H'): -0.10, ('H', 'S'): 0.10, ('N', 'O'): 0.12,
    ('O', 'N'): -0.12, ('N', 'N'): 0.0, ('O', 'O'): 0.0,
    ('S', 'S'): 0.0, ('H', 'H'): 0.0,
}

# ─── Lookup Functions ──────────────────────────────────────────

def get_bond_params(sym1, sym2, order):
    key = (sym1, sym2, order)
    if key in MMFF94_BOND: return MMFF94_BOND[key]
    rev_key = (sym2, sym1, order)
    if rev_key in MMFF94_BOND: return MMFF94_BOND[rev_key]
    return (1.50, 4.0)

def get_angle_params(sym_i, sym_center, sym_k, hyb):
    key = (sym_i, sym_center, sym_k, hyb)
    if key in MMFF94_ANGLE: return MMFF94_ANGLE[key]
    rev_key = (sym_k, sym_center, sym_i, hyb)
    if rev_key in MMFF94_ANGLE: return MMFF94_ANGLE[rev_key]
    defaults = {'sp3': (109.5, 0.5), 'sp2': (120.0, 0.7), 'sp': (180.0, 1.0)}
    return defaults.get(hyb, (109.5, 0.5))

def get_torsion_params(sym_i, type_j, type_k, sym_l):
    for key in [
        (sym_i, type_j, type_k, sym_l),
        (sym_l, type_k, type_j, sym_i),
        ('*', type_j, type_k, '*'),
        ('*', type_k, type_j, '*'),
    ]:
        if key in MMFF94_TORSION: return MMFF94_TORSION[key]
    if 'sp2' in type_j or 'sp2' in type_k: return (0.0, 1.0, 0.0)
    return (0.0, 0.0, 0.2)

def get_vdw_params(symbol):
    return MMFF94_VDW.get(symbol, (1.70, 0.10))

def get_bci_charge(sym1, sym2):
    pair = (sym1, sym2)
    if pair in MMFF94_BCI: return MMFF94_BCI[pair]
    rev_pair = (sym2, sym1)
    if rev_pair in MMFF94_BCI: return -MMFF94_BCI[rev_pair]
    return 0.0

def get_oop_params(sym_center, neighbors):
    """Find OOP force constant."""
    # Heuristic fallback for missing parameters
    return 0.05
