"""
Cartoon Generator — Faithful port of CPPCartoon's createChainMesh.

Orchestrates the full pipeline:
  1. Extract PeptidePlanes from molecule (3-residue windows)
  2. Ensure consistent side-vector orientation
  3. Slide a 4-plane window and generate mesh segments
  4. Cache the result for interactive performance

Includes Adaptive LOD for large proteins.
"""

import numpy as np
from typing import Dict, Tuple, Optional

from src.features.visualization_3d.services.peptide_plane import compute_chain_planes
from src.features.visualization_3d.services.mesh_builder import (
    MeshAccumulator, create_segment_mesh, discontinuity
)

# ─── LOD Settings ────────────────────────────────────────────────────────────
# CPPCartoon defaults: splineSteps = 16, profileDetail = 8
# We scale based on protein size for performance on older hardware.

LOD_SETTINGS = {
    'high':   {'spline_steps': 16, 'profile_detail': 12},   # < 500 atoms
    'medium': {'spline_steps': 16, 'profile_detail': 8},    # 500-2000 atoms
    'low':    {'spline_steps': 12, 'profile_detail': 8},    # > 2000 atoms
}


def _select_lod(num_atoms):
    """Select LOD settings based on atom count."""
    if num_atoms < 500:
        return LOD_SETTINGS['high']
    elif num_atoms < 2000:
        return LOD_SETTINGS['medium']
    else:
        return LOD_SETTINGS['low']


def generate_cartoon_mesh(molecule, spline_steps=None, profile_detail=None):
    """
    Generate the full protein cartoon mesh.
    
    Matches CPPCartoon's createChainMesh() logic:
    - Build peptide planes per chain
    - Slide a 4-plane window (i, i+1, i+2, i+3) through the chain
    - Skip discontinuities (chain breaks)
    - Generate mesh segments
    
    Returns: (vertices, triangles, colors) or (None, None, None)
    """
    # Auto-select LOD if not specified
    if spline_steps is None or profile_detail is None:
        lod = _select_lod(len(molecule.atoms))
        spline_steps = spline_steps or lod['spline_steps']
        profile_detail = profile_detail or lod['profile_detail']

    # 1. Extract peptide planes per chain
    chains = compute_chain_planes(molecule)
    
    if not chains:
        return None, None, None

    mesh = MeshAccumulator()

    for chain_id in sorted(chains.keys()):
        planes = chains[chain_id]
        
        # Need at least 4 planes for the sliding window
        n = len(planes) - 3
        if n <= 0:
            continue

        for i in range(n):
            pp1 = planes[i]
            pp2 = planes[i + 1]
            pp3 = planes[i + 2]
            pp4 = planes[i + 3]

            # Skip chain breaks
            if discontinuity(pp1, pp2, pp3, pp4):
                continue

            create_segment_mesh(mesh, pp1, pp2, pp3, pp4,
                                spline_steps, profile_detail)

    return mesh.to_arrays()


class CartoonGenerator:
    """
    Cached cartoon mesh generator.
    Generates mesh once and caches it for interactive rotation/zoom.
    """
    
    def __init__(self):
        self._cache = {}  # molecule id -> (vertices, triangles, colors)
    
    def get_mesh(self, molecule):
        """Retrieve cached mesh or generate a new one."""
        mol_id = id(molecule)
        if mol_id in self._cache:
            return self._cache[mol_id]
        
        mesh = generate_cartoon_mesh(molecule)
        if mesh[0] is not None:
            self._cache[mol_id] = mesh
        
        return mesh
    
    def invalidate(self, molecule=None):
        """Clear cache for a specific molecule, or all."""
        if molecule is None:
            self._cache.clear()
        else:
            mol_id = id(molecule)
            self._cache.pop(mol_id, None)
