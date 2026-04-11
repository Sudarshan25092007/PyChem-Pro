# src/services/forcefield/torsion.py
"""
MMFF94 torsion energy and analytical gradient.
E_torsion = 0.5 * [V1*(1-cos(phi)) + V2*(1-cos(2*phi)) + V3*(1-cos(3*phi))]
"""
import numpy as np
from src.core.domain.models.molecule import Molecule
from src.services.forcefield.parameters import get_torsion_params


class TorsionCalculator:

    def build_torsion_list(self, mol: Molecule) -> list:
        mol.assign_hybridization()
        torsions = []
        for bond in mol.bonds:
            j, k = bond.begin_atom_idx, bond.end_atom_idx
            neighbors_j = [n for n in mol.get_neighbors(j) if n != k]
            neighbors_k = [n for n in mol.get_neighbors(k) if n != j]
            for i in neighbors_j:
                for l in neighbors_k:
                    if i == l:
                        continue
                    V1, V2, V3 = self._lookup_params(mol, i, j, k, l)
                    torsions.append((i, j, k, l, V1, V2, V3))
        return torsions

    def energy(self, coords, torsions):
        total = 0.0
        for i, j, k, l, V1, V2, V3 in torsions:
            phi = self._compute_dihedral(coords[i], coords[j], coords[k], coords[l])
            total += 0.5 * (
                V1 * (1 - np.cos(phi)) +
                V2 * (1 - np.cos(2 * phi)) +
                V3 * (1 - np.cos(3 * phi))
            )
        return total

    def gradient(self, coords, torsions):
        grad = np.zeros_like(coords, dtype=np.float64)
        for i, j, k, l, V1, V2, V3 in torsions:
            phi = self._compute_dihedral(coords[i], coords[j], coords[k], coords[l])
            dE_dphi = 0.5 * (
                V1 * np.sin(phi) +
                2 * V2 * np.sin(2 * phi) +
                3 * V3 * np.sin(3 * phi)
            )
            g_i, g_j, g_k, g_l = self._dihedral_gradient(
                coords[i], coords[j], coords[k], coords[l])
            grad[i] += dE_dphi * g_i
            grad[j] += dE_dphi * g_j
            grad[k] += dE_dphi * g_k
            grad[l] += dE_dphi * g_l
        return grad

    @staticmethod
    def _compute_dihedral(p0, p1, p2, p3):
        b1 = p1 - p0; b2 = p2 - p1; b3 = p3 - p2
        n1 = np.cross(b1, b2); n2 = np.cross(b2, b3)
        n1_norm = np.linalg.norm(n1) + 1e-10
        n2_norm = np.linalg.norm(n2) + 1e-10
        n1 = n1 / n1_norm; n2 = n2 / n2_norm
        m1 = np.cross(n1, b2 / (np.linalg.norm(b2) + 1e-10))
        x = np.dot(n1, n2); y = np.dot(m1, n2)
        return np.arctan2(y, x)

    @staticmethod
    def _dihedral_gradient(p0, p1, p2, p3):
        """
        Analytical gradient of the dihedral angle with respect to each atom.
        Returns (dphi/dp0, dphi/dp1, dphi/dp2, dphi/dp3).

        Uses the Blondel-Karplus formula adapted to the atan2(y, x) convention
        used in _compute_dihedral.
        """
        b1 = p1 - p0
        b2 = p2 - p1
        b3 = p3 - p2
        n1 = np.cross(b1, b2)
        n2 = np.cross(b2, b3)
        n1_sq = np.dot(n1, n1) + 1e-10
        n2_sq = np.dot(n2, n2) + 1e-10
        b2_norm = np.linalg.norm(b2) + 1e-10
        b2_sq = b2_norm * b2_norm

        # dphi/dp0 and dphi/dp3 for atan2 convention
        g0 = (b2_norm / n1_sq) * n1
        g3 = -(b2_norm / n2_sq) * n2

        # dphi/dp1 and dphi/dp2 from conservation (sum of gradients = 0)
        # and the partitioning based on projections
        f1 = np.dot(b1, b2) / b2_sq
        f2 = np.dot(b3, b2) / b2_sq
        g1 = -g0 - f1 * g0 + f2 * g3
        g2 = -(g0 + g1 + g3)

        return g0, g1, g2, g3

    def _lookup_params(self, mol, i, j, k, l):
        sym_i = mol.atoms[i].symbol
        sym_l = mol.atoms[l].symbol
        type_j = f"{mol.atoms[j].symbol}_{mol.atoms[j].hybridization or 'sp3'}"
        type_k = f"{mol.atoms[k].symbol}_{mol.atoms[k].hybridization or 'sp3'}"
        return get_torsion_params(sym_i, type_j, type_k, sym_l)
