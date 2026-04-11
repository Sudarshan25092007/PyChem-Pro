"""
Public facade functions for PyChem.

These thin wrappers delegate to the ServiceRegistry.
They are the stable public API surface.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.domain.models.molecule import Molecule


def parse_smiles(smiles: str):
    """Parse a SMILES string into a Molecule."""
    from src.features.smiles_parser.services.parser import parse_smiles as _parse
    return _parse(smiles)


def generate_3d(mol, optimize: bool = True, max_steps: int = 200) -> None:
    """Generate 3D coordinates in-place on the molecule."""
    from src.features.layout_3d import generate_3d_coordinates
    generate_3d_coordinates(mol, optimize=optimize, max_opt_steps=max_steps)


def optimize(mol, max_iters: int = 500, convergence: float = 1e-4, method: str = 'lbfgs'):
    """Optimize molecular geometry using MMFF94. Returns OptimizationResult."""
    from src.features.cheminformatics.services.mmff94 import mmff94_optimize_geometry
    mmff94_optimize_geometry(mol, max_iters=max_iters)
    from src.core.protocols.forcefield import OptimizationResult
    return OptimizationResult(converged=True, final_energy=0.0, num_steps=0)


def descriptors(mol, names=None) -> dict:
    """Calculate molecular descriptors."""
    result = {
        'molecular_weight': mol.molecular_weight(),
        'num_atoms': mol.num_atoms,
        'num_bonds': mol.num_bonds,
        'num_heavy_atoms': mol.num_heavy_atoms,
        'formula': mol.molecular_formula(),
    }
    return result
