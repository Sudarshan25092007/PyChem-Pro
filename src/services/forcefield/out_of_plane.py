# src/services/forcefield/out_of_plane.py
"""
MMFF94 Out-of-Plane (OOP) bending energy and analytical gradient.
E_oop = 0.043844 / 2.0 * koop * d^2
where d is the distance of the central atom from the plane of its 3 neighbors.
"""
import numpy as np
from src.core.domain.models.molecule import Molecule
from src.services.forcefield.parameters import get_oop_params

class OutOfPlaneCalculator:
    
    def build_oop_list(self, mol: Molecule) -> list:
        oop_list = []
        for atom in mol.atoms:
            neighbors = mol.get_neighbors(atom.index)
            if len(neighbors) == 3:
                # MMFF94 OOP is defined for atoms with exactly 3 neighbors
                # (e.g. sp2 carbons, planar nitrogens)
                hyb = getattr(atom, 'hybridization', 'sp3')
                if hyb == 'sp2':
                    koop = get_oop_params(atom.symbol, [mol.atoms[n].symbol for n in neighbors])
                    oop_list.append((atom.index, neighbors[0], neighbors[1], neighbors[2], koop))
        return oop_list

    def energy(self, coords, oop_list):
        total = 0.0
        for center, i, j, k, koop in oop_list:
            d = self._compute_oop_distance(coords[center], coords[i], coords[j], coords[k])
            total += 0.043844 / 2.0 * koop * d * d
        return total

    def gradient(self, coords, oop_list):
        grad = np.zeros_like(coords, dtype=np.float64)
        for center, i, j, k, koop in oop_list:
            d, g_center, g_i, g_j, g_k = self._oop_gradient(
                coords[center], coords[i], coords[j], coords[k])
            force = 0.043844 * koop * d
            grad[center] += force * g_center
            grad[i] += force * g_i
            grad[j] += force * g_j
            grad[k] += force * g_k
        return grad

    @staticmethod
    def _compute_oop_distance(p_c, p_i, p_j, p_k):
        """Distance of p_c from the plane formed by p_i, p_j, p_k."""
        v1 = p_j - p_i
        v2 = p_k - p_i
        normal = np.cross(v1, v2)
        norm = np.linalg.norm(normal) + 1e-10
        unit_normal = normal / norm
        vec = p_c - p_i
        return np.dot(vec, unit_normal)

    @staticmethod
    def _oop_gradient(p_c, p_i, p_j, p_k):
        """Analytical gradient of the OOP distance d w.r.t p_c, p_i, p_j, p_k."""
        v1 = p_j - p_i
        v2 = p_k - p_i
        normal = np.cross(v1, v2)
        norm = np.linalg.norm(normal) + 1e-10
        unit_normal = normal / norm
        
        # d = (p_c - p_i) . unit_normal
        # dd/dp_c = unit_normal
        g_center = unit_normal
        
        # Derivatives w.r.t i, j, k are more complex because unit_normal depends on them.
        # But we can approximate for stability or use the full expression.
        # Here we use a simpler version: g_i, g_j, g_k are such that sum(g) = 0
        # and they act to flatten the triangle i-j-k.
        
        # Full expression for d = (p_c - p_i) . (v1 x v2) / |v1 x v2|
        # Let n = v1 x v2. d = (p_c - p_i) . n / |n|
        
        vec = p_c - p_i
        # dd/dn = (vec / |n|) - (vec.n / |n|^3) * n
        dd_dn = (vec / norm) - (np.dot(vec, normal) / (norm**3)) * normal
        
        # dn/dp_j = d( (p_j - p_i) x (p_k - p_i) ) / dp_j = - (p_k - p_i) x I
        # Using cross product matrix representation:
        def cross_matrix(v):
            return np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        
        # dn/dp_j = -cross_matrix(v2)
        # dn/dp_k = cross_matrix(v1)
        
        g_j = np.dot(dd_dn, -cross_matrix(v2))
        g_k = np.dot(dd_dn, cross_matrix(v1))
        
        # dd/dp_i is trickier as it's in vec AND v1, v2.
        # Use sum(grad) = 0
        g_i = -(g_center + g_j + g_k)
        
        return np.dot(vec, unit_normal), g_center, g_i, g_j, g_k
