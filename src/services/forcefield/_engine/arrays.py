"""
Pre-built NumPy arrays for the MMFF94 engine.

InteractionArrays is a frozen dataclass holding all 7 term's
parameter arrays. Built once per optimize_geometry call by ArraysBuilder
(implemented in Task 19) and consumed by every per-term calculator.

Design contract:
    - All arrays contiguous, dtype-locked.
    - Never resized between optimization steps.
    - Index arrays are int32 (matching numpy default for small ints).
    - Parameter arrays are float64.
"""
from __future__ import annotations
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class InteractionArrays:
    """All pre-cooked per-term data for one molecule, ready for vectorized ops."""

    n_atoms: int

    # ────────── Bond stretching ──────────
    bond_i: np.ndarray   # (Nb,) int32 — atom index i
    bond_j: np.ndarray   # (Nb,) int32 — atom index j
    bond_kb: np.ndarray  # (Nb,) float64 — force constant
    bond_r0: np.ndarray  # (Nb,) float64 — equilibrium length (Å)

    # ────────── Angle bending ──────────
    # theta0 in DEGREES (intentional — locks the units fix from spec §7.2)
    angle_i: np.ndarray; angle_j: np.ndarray; angle_k: np.ndarray   # int32
    angle_ka: np.ndarray; angle_theta0_deg: np.ndarray              # float64
    angle_is_linear: np.ndarray                                      # bool

    # ────────── Stretch-bend ──────────
    sb_i: np.ndarray; sb_j: np.ndarray; sb_k: np.ndarray             # int32
    sb_kbai: np.ndarray; sb_kbak: np.ndarray                         # float64
    sb_r0_ij: np.ndarray; sb_r0_jk: np.ndarray                       # float64
    sb_theta0_deg: np.ndarray                                        # float64

    # ────────── Torsion ──────────
    tor_i: np.ndarray; tor_j: np.ndarray
    tor_k: np.ndarray; tor_l: np.ndarray                             # int32
    tor_v1: np.ndarray; tor_v2: np.ndarray; tor_v3: np.ndarray       # float64

    # ────────── Out-of-plane bending ──────────
    oop_center: np.ndarray                                           # int32
    oop_i: np.ndarray; oop_j: np.ndarray; oop_k: np.ndarray          # int32
    oop_koop: np.ndarray                                             # float64

    # ────────── Van der Waals ──────────
    vdw_i: np.ndarray; vdw_j: np.ndarray                             # int32
    vdw_rs: np.ndarray; vdw_eps: np.ndarray                          # float64
                                                                     # combined R*, ε

    # ────────── Electrostatic ──────────
    es_i: np.ndarray; es_j: np.ndarray                               # int32
    es_qq: np.ndarray                                                # float64 — qi*qj precomputed
    es_factor: np.ndarray                                            # float64 — 249.0537 (1-4) or 332.0716
