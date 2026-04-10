"""
Electronic descriptor calculations.
Includes: partial charges, dipole moment, polar surface area.
"""
import numpy as np
from . import BaseCalculator


class ElectronicCalculator(BaseCalculator):
    """Calculator for electronic molecular descriptors."""

    def calc_total_charge(self, molecule, selection) -> float:
        """Calculate total molecular charge."""
        return sum(getattr(molecule.atoms[idx], 'partial_charge', 0.0)
                  for idx in self.get_selected_atoms(molecule, selection))

    def calc_max_partial_charge(self, molecule, selection) -> float:
        """Calculate maximum partial charge."""
        return max((getattr(molecule.atoms[idx], 'partial_charge', 0.0)
                   for idx in self.get_selected_atoms(molecule, selection)), default=0.0)

    def calc_min_partial_charge(self, molecule, selection) -> float:
        """Calculate minimum partial charge."""
        return min((getattr(molecule.atoms[idx], 'partial_charge', 0.0)
                   for idx in self.get_selected_atoms(molecule, selection)), default=0.0)

    def calc_max_positive_charge(self, molecule, selection) -> float:
        """Calculate maximum positive partial charge."""
        charges = [getattr(molecule.atoms[idx], 'partial_charge', 0.0)
                  for idx in self.get_selected_atoms(molecule, selection)
                  if getattr(molecule.atoms[idx], 'partial_charge', 0.0) > 0]
        return max(charges) if charges else 0.0

    def calc_max_negative_charge(self, molecule, selection) -> float:
        """Calculate maximum negative partial charge (most negative)."""
        charges = [getattr(molecule.atoms[idx], 'partial_charge', 0.0)
                  for idx in self.get_selected_atoms(molecule, selection)
                  if getattr(molecule.atoms[idx], 'partial_charge', 0.0) < 0]
        return min(charges) if charges else 0.0

    def calc_dipole_moment(self, molecule, selection) -> float:
        """Calculate molecular dipole moment."""
        dipole = np.array([0.0, 0.0, 0.0])

        for idx in self.get_selected_atoms(molecule, selection):
            atom = molecule.atoms[idx]
            charge = getattr(atom, 'partial_charge', 0.0)
            dipole += charge * np.array([atom.x, atom.y, atom.z])

        return np.linalg.norm(dipole) * 2.54  # Convert to Debye

    def calc_polar_surface_area(self, molecule, selection) -> float:
        """Calculate polar surface area."""
        from ...cheminformatics.services.atom_properties import AtomPropertyAnalyzer
        analyzer = AtomPropertyAnalyzer(molecule)
        polar_set = set(analyzer.POLAR_ATOMS)
        atomic_areas = {'O': 17.0, 'N': 12.0, 'S': 25.0, 'P': 25.0}

        return sum(atomic_areas.get(molecule.atoms[idx].symbol, 15.0)
                  for idx in self.get_selected_atoms(molecule, selection)
                  if molecule.atoms[idx].symbol in polar_set)

    def calc_apolar_surface_area(self, molecule, selection) -> float:
        """Calculate apolar (nonpolar) surface area."""
        from ..descriptor_engine import DescriptorEngine
        engine = DescriptorEngine()
        total_sasa = self.calc_sasa(molecule, selection)
        polar_sasa = self.calc_polar_surface_area(molecule, selection)
        return total_sasa - polar_sasa

    def calc_sasa(self, molecule, selection) -> float:
        """Calculate solvent accessible surface area (simplified)."""
        selected_set = self.get_selected_set(selection)
        total_area = 0.0
        atomic_radii = {'H': 1.2, 'C': 1.7, 'N': 1.55, 'O': 1.52,
                       'F': 1.47, 'Cl': 1.75, 'Br': 1.85, 'I': 1.98}

        for idx in selection.atom_indices:
            if idx < len(molecule.atoms):
                radius = atomic_radii.get(molecule.atoms[idx].symbol, 1.5)
                total_area += 4 * np.pi * radius ** 2

        return total_area

    def calc_mean_absolute_charge(self, molecule, selection) -> float:
        """Calculate mean absolute partial charge."""
        total = 0.0
        count = 0
        for idx in self.get_selected_atoms(molecule, selection):
            charge = getattr(molecule.atoms[idx], 'partial_charge', None)
            if charge is not None:
                total += abs(charge)
                count += 1
        return total / count if count > 0 else 0.0
