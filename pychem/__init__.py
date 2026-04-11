"""
PyChem — Pure Python cheminformatics toolkit.

Public API for use in Jupyter notebooks and scripts.
No PySide6 dependency required for this package.
"""
from pychem.api import parse_smiles, generate_3d, optimize, descriptors
from src.core.domain.models.molecule import Molecule
from src.core.domain.models.atom import Atom
from src.core.domain.models.bond import Bond

__version__ = '2.0.0'

__all__ = [
    'Molecule', 'Atom', 'Bond',
    'parse_smiles', 'generate_3d', 'optimize', 'descriptors',
]
