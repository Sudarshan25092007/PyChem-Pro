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
    from pychem._bridge import get_registry
    return get_registry().forcefield.optimize_geometry(
        mol, max_iters=max_iters, convergence=convergence, method=method
    )


def compute_charges(mol) -> None:
    """Assign MMFF94 partial charges (BCI method) in-place on the molecule."""
    from pychem._bridge import get_registry
    get_registry().forcefield.assign_charges(mol)


def add_hydrogens(mol) -> int:
    """Add explicit hydrogens with 3D positions. Returns count added."""
    from pychem._bridge import get_registry
    return get_registry().forcefield.add_hydrogens(mol)


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
