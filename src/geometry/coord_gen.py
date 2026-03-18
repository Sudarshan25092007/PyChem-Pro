"""
3D Coordinate Generation Pipeline — Main entry point for generating
3D molecular structures from SMILES-parsed molecular graphs.

Pipeline:
1. Add explicit hydrogens
2. Detect rings and apply templates
3. Build distance bounds matrix
4. Smooth bounds (triangle inequality)
5. Sample distances and embed into 3D
6. Optimize geometry
"""

import numpy as np
from .distance_geometry import (
    build_distance_bounds, smooth_bounds,
    generate_distance_matrix, embed_distances
)
from .ring_templates import get_ring_template, apply_ring_template
from .optimizer import optimize_geometry


def generate_3d_coordinates(molecule, optimize=True, max_opt_steps=300):
    """
    Generate 3D coordinates for a molecule.

    Args:
        molecule: Molecule object (atoms + bonds, no coordinates yet)
        optimize: Whether to optimize geometry after initial placement
        max_opt_steps: Maximum optimization steps

    Returns:
        molecule with 3D coordinates assigned to all atoms
    """
    if len(molecule.atoms) == 0:
        return molecule

    # ── Step 1: Add explicit hydrogens ──
    molecule.add_explicit_hydrogens()

    # ── Step 2: Re-assign hybridization after adding H ──
    molecule.assign_hybridization()

    n = len(molecule.atoms)

    if n == 1:
        # Single atom
        molecule.atoms[0].coords = (0.0, 0.0, 0.0)
        return molecule

    if n == 2:
        # Two atoms — just place along x-axis
        from ..core.elements import bond_length
        d = bond_length(molecule.atoms[0].symbol, molecule.atoms[1].symbol)
        molecule.atoms[0].coords = (0.0, 0.0, 0.0)
        molecule.atoms[1].coords = (d, 0.0, 0.0)
        return molecule

    # ── Step 3: Apply ring templates ──
    _apply_ring_templates(molecule)

    # ── Step 4: Distance geometry for full molecule ──
    try:
        lower, upper = build_distance_bounds(molecule)
        lower, upper = smooth_bounds(lower, upper, max_iterations=min(10, n))

        # Generate distance matrix
        D = generate_distance_matrix(lower, upper)

        # For atoms with ring template coordinates, fix their distances
        _fix_ring_distances(molecule, D)

        # Embed into 3D
        coords = embed_distances(D)

        # Assign coordinates
        for i, atom in enumerate(molecule.atoms):
            atom.x = float(coords[i, 0])
            atom.y = float(coords[i, 1])
            atom.z = float(coords[i, 2])

    except Exception:
        # Fallback: simple placement using graph traversal
        _fallback_coordinate_generation(molecule)

    # ── Step 5: Optimize geometry ──
    if optimize and n > 2:
        try:
            # First pass: steepest descent (robust)
            optimize_geometry(molecule, max_steps=max_opt_steps // 2,
                            convergence=1e-3, method='steepest_descent')
            # Second pass: L-BFGS (refinement)
            optimize_geometry(molecule, max_steps=max_opt_steps // 2,
                            convergence=1e-4, method='lbfgs')
        except Exception:
            # If optimization fails, keep distance geometry coordinates
            pass

    # ── Step 6: Center molecule at origin ──
    _center_molecule(molecule)

    return molecule


def _apply_ring_templates(molecule):
    """Apply coordinate templates to detected rings."""
    rings = molecule.find_rings()

    for ring in rings:
        ring_size = len(ring)
        if ring_size < 3 or ring_size > 8:
            continue

        # Determine if ring should be planar (aromatic)
        is_aromatic = all(molecule.atoms[idx].is_aromatic for idx in ring)
        conformation = 'planar' if is_aromatic else 'default'

        template = get_ring_template(ring_size, conformation)
        if template is not None:
            apply_ring_template(molecule, ring, template)


def _fix_ring_distances(molecule, D):
    """
    For atoms that already have coordinates from ring templates,
    compute actual distances and update the distance matrix.
    """
    for i in range(len(molecule.atoms)):
        if not molecule.atoms[i].has_coords:
            continue
        for j in range(i + 1, len(molecule.atoms)):
            if not molecule.atoms[j].has_coords:
                continue
            # Compute actual distance from template coordinates
            ci = np.array(molecule.atoms[i].coords)
            cj = np.array(molecule.atoms[j].coords)
            d = np.linalg.norm(ci - cj)
            D[i][j] = D[j][i] = d


def _fallback_coordinate_generation(molecule):
    """
    Simple fallback coordinate generation using graph traversal.
    Places atoms at ideal bond lengths along growing directions.
    """
    from collections import deque
    from ..core.elements import bond_length

    n = len(molecule.atoms)
    placed = set()

    # Place first atom at origin
    molecule.atoms[0].coords = (0.0, 0.0, 0.0)
    placed.add(0)

    # BFS to place remaining atoms
    queue = deque([0])
    while queue:
        current = queue.popleft()
        neighbors = molecule.get_neighbor_bonds(current)

        angle_step = 0
        for n_idx, bond in neighbors:
            if n_idx in placed:
                continue

            # Calculate position relative to current atom
            d = bond_length(molecule.atoms[current].symbol,
                          molecule.atoms[n_idx].symbol, bond.order)

            # Determine direction
            parent_pos = np.array(molecule.atoms[current].coords)

            # Use tetrahedral or planar angles
            hyb = molecule.atoms[current].hybridization
            if hyb == 'sp2':
                base_angle = 120.0
            elif hyb == 'sp':
                base_angle = 180.0
            else:
                base_angle = 109.5

            theta = np.radians(base_angle * angle_step / max(len(neighbors) - 1, 1))
            phi = np.radians(angle_step * 72)  # Dihedral variation

            # Spherical to cartesian
            dx = d * np.sin(theta) * np.cos(phi)
            dy = d * np.sin(theta) * np.sin(phi)
            dz = d * np.cos(theta)

            molecule.atoms[n_idx].coords = (
                parent_pos[0] + dx,
                parent_pos[1] + dy,
                parent_pos[2] + dz
            )
            placed.add(n_idx)
            queue.append(n_idx)
            angle_step += 1

    # Handle disconnected atoms
    offset = 5.0
    for i in range(n):
        if i not in placed:
            molecule.atoms[i].coords = (offset, 0.0, 0.0)
            offset += 3.0
            placed.add(i)


def _center_molecule(molecule):
    """Center molecule at origin."""
    coords = []
    for atom in molecule.atoms:
        if atom.has_coords:
            coords.append([atom.x, atom.y, atom.z])

    if not coords:
        return

    center = np.mean(coords, axis=0)
    for atom in molecule.atoms:
        if atom.has_coords:
            atom.x -= center[0]
            atom.y -= center[1]
            atom.z -= center[2]
