# src/services/forcefield/angle_bending.py
"""
MMFF94 angle bending energy and analytical gradient.
E_angle = 0.021914 * ka * (theta - theta0)^2 * [1 + cb * (theta - theta0)]
where cb = -0.007 (cubic stretch correction)
"""
import math
import numpy as np
from src.core.domain.models.molecule import Molecule
from src.services.forcefield.parameters import get_angle_params

class AngleBendingCalculator:
    CB = -0.007

    def build_angle_list(self, mol: Molecule) -> list:
        mol.assign_hybridization()
        angles = []
        for atom in mol.atoms:
            neighbors = mol.get_neighbors(atom.index)
            if len(neighbors) < 2:
                continue
            hyb = atom.hybridization or 'sp3'
            for a in range(len(neighbors)):
                for b in range(a + 1, len(neighbors)):
                    i, k = neighbors[a], neighbors[b]
                    sym_i = mol.atoms[i].symbol
                    sym_k = mol.atoms[k].symbol
                    params = get_angle_params(sym_i, atom.symbol, sym_k, hyb)
                    # Ensure valid parameters
                    if params is None or not isinstance(params, (list, tuple)) or len(params) != 2:
                        theta0_deg, ka = 109.5, 0.5  # Default sp3 values
                    else:
                        theta0_deg, ka = params
                        try:
                            theta0_deg = float(theta0_deg) if theta0_deg is not None else 109.5
                            ka = float(ka) if ka is not None else 0.5
                        except (TypeError, ValueError):
                            theta0_deg, ka = 109.5, 0.5
                    angles.append((i, atom.index, k, math.radians(theta0_deg), ka))
        return angles

    def energy(self, coords, angles):
        total = 0.0
        for i, j, k, theta0, ka in angles:
            # Ensure parameters are valid numbers
            theta0 = float(theta0) if theta0 is not None else 2.0  # ~114 degrees
            ka = float(ka) if ka is not None else 0.5
            if ka <= 0:
                continue
            theta = self._compute_angle(coords[i], coords[j], coords[k])
            dt = theta - theta0
            total += 0.021914 * ka * dt * dt * (1 + self.CB * dt)
        return total

    def gradient(self, coords, angles):
        grad = np.zeros_like(coords, dtype=np.float64)
        for i, j, k, theta0, ka in angles:
            # Ensure parameters are valid numbers
            theta0 = float(theta0) if theta0 is not None else 2.0
            ka = float(ka) if ka is not None else 0.5
            if ka <= 0:
                continue
            theta = self._compute_angle(coords[i], coords[j], coords[k])
            dt = theta - theta0
            dE_dtheta = 0.021914 * ka * dt * (2 + 3 * self.CB * dt)
            g_i, g_j, g_k = self._angle_gradient(
                coords[i], coords[j], coords[k])
            grad[i] += dE_dtheta * g_i
            grad[j] += dE_dtheta * g_j
            grad[k] += dE_dtheta * g_k
        return grad

    @staticmethod
    def _compute_angle(a, b, c):
        v1 = a - b; v2 = c - b
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-10)
        return np.arccos(np.clip(cos_angle, -1.0, 1.0))

    @staticmethod
    def _angle_gradient(a, b, c):
        v1 = a - b; v2 = c - b
        r1 = np.linalg.norm(v1) + 1e-10; r2 = np.linalg.norm(v2) + 1e-10
        v1n = v1 / r1; v2n = v2 / r2
        cos_theta = np.clip(np.dot(v1n, v2n), -1.0, 1.0)
        sin_theta = np.sqrt(1.0 - cos_theta * cos_theta) + 1e-10
        g_a = (cos_theta * v1n - v2n) / (r1 * sin_theta)
        g_c = (cos_theta * v2n - v1n) / (r2 * sin_theta)
        g_b = -(g_a + g_c)
        return g_a, g_b, g_c
