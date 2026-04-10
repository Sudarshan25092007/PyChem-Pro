"""
Geometric descriptor calculations.
Includes: surface areas, volumes, radius of gyration, shape descriptors, principal moments.
"""
import numpy as np
from . import BaseCalculator


class GeometricCalculator(BaseCalculator):
    """Calculator for geometric (3D) molecular descriptors."""

    def calc_sasa(self, molecule, selection) -> float:
        """Calculate solvent accessible surface area."""
        selected_set = self.get_selected_set(selection)
        total_area = 0.0
        atomic_radii = {'H': 1.2, 'C': 1.7, 'N': 1.55, 'O': 1.52,
                       'F': 1.47, 'Cl': 1.75, 'Br': 1.85, 'I': 1.98}

        for idx in selection.atom_indices:
            if idx < len(molecule.atoms):
                radius = atomic_radii.get(molecule.atoms[idx].symbol, 1.5)
                total_area += 4 * np.pi * radius ** 2

        return total_area

    def calc_molecular_volume(self, molecule, selection) -> float:
        """Calculate molecular volume."""
        selected_set = self.get_selected_set(selection)
        total_volume = 0.0
        atomic_volumes = {'H': 7.2, 'C': 20.6, 'N': 16.6, 'O': 14.7,
                         'F': 13.3, 'Cl': 22.4, 'Br': 28.2, 'I': 32.6}

        for idx in selection.atom_indices:
            if idx < len(molecule.atoms):
                total_volume += atomic_volumes.get(molecule.atoms[idx].symbol, 15.0)

        return total_volume

    def calc_radius_of_gyration(self, molecule, selection) -> float:
        """Calculate radius of gyration."""
        coords = []
        for idx in selection.atom_indices:
            if idx < len(molecule.atoms):
                atom = molecule.atoms[idx]
                coords.append([atom.x, atom.y, atom.z])

        if not coords:
            return 0.0

        coords = np.array(coords)
        center = np.mean(coords, axis=0)
        distances = np.sum((coords - center) ** 2, axis=1)
        return np.sqrt(np.mean(distances))

    def calc_asphericity(self, molecule, selection) -> float:
        """Calculate molecular asphericity."""
        eigenvalues = self.get_gyration_eigenvalues(molecule, selection)
        if len(eigenvalues) < 3:
            return 0.0

        l1, l2, l3 = sorted(eigenvalues, reverse=True)
        sum_l = l1 + l2 + l3
        if sum_l == 0:
            return 0.0
        return 1.0 - 3.0 * (l1*l2 + l2*l3 + l1*l3) / (sum_l ** 2)

    def calc_eccentricity(self, molecule, selection) -> float:
        """Calculate molecular eccentricity."""
        eigenvalues = self.get_gyration_eigenvalues(molecule, selection)
        if len(eigenvalues) < 3:
            return 0.0

        l1, l2, l3 = sorted(eigenvalues, reverse=True)
        if l1 > 0:
            return np.sqrt(l1**2 - l3**2) / l1
        return 0.0

    def calc_principal_moment_1(self, molecule, selection) -> float:
        """Calculate first principal moment of inertia."""
        eigenvalues = self.get_gyration_eigenvalues(molecule, selection)
        return max(eigenvalues) if len(eigenvalues) > 0 else 0.0

    def calc_principal_moment_2(self, molecule, selection) -> float:
        """Calculate second principal moment of inertia."""
        eigenvalues = self.get_gyration_eigenvalues(molecule, selection)
        if len(eigenvalues) >= 2:
            return sorted(eigenvalues, reverse=True)[1]
        return 0.0

    def calc_principal_moment_3(self, molecule, selection) -> float:
        """Calculate third principal moment of inertia."""
        eigenvalues = self.get_gyration_eigenvalues(molecule, selection)
        if len(eigenvalues) >= 3:
            return sorted(eigenvalues, reverse=True)[2]
        return 0.0

    def calc_molecular_diameter(self, molecule, selection) -> float:
        """Calculate molecular diameter (max distance between atoms)."""
        coords = []
        for idx in selection.atom_indices:
            if idx < len(molecule.atoms):
                atom = molecule.atoms[idx]
                if atom.x is not None and atom.y is not None and atom.z is not None:
                    coords.append(np.array([atom.x, atom.y, atom.z]))

        if len(coords) < 2:
            return 0.0

        max_dist = 0.0
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                dist = np.linalg.norm(coords[i] - coords[j])
                max_dist = max(max_dist, dist)

        return max_dist
