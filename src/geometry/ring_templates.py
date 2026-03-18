"""
Ring Templates — Pre-computed ideal coordinates for common ring systems.

Provides planar coordinates for 3-8 membered rings, plus
special conformations (cyclohexane chair, etc.).
"""

import numpy as np


def get_ring_template(ring_size, conformation='default'):
    """
    Get ideal 2D coordinates for a ring of given size.

    Args:
        ring_size: Number of atoms in the ring (3-8)
        conformation: 'default', 'planar', or 'chair' (for 6-membered)

    Returns:
        Nx3 numpy array of coordinates
    """
    if ring_size < 3:
        return None

    if ring_size == 6 and conformation == 'chair':
        return _cyclohexane_chair()

    if conformation == 'planar' or ring_size <= 5:
        return _planar_ring(ring_size)

    # For rings > 5, use slightly puckered geometry
    if ring_size == 6:
        return _cyclohexane_chair()
    elif ring_size == 7:
        return _puckered_ring(ring_size, pucker_amplitude=0.3)
    elif ring_size == 8:
        return _puckered_ring(ring_size, pucker_amplitude=0.4)
    else:
        return _puckered_ring(ring_size, pucker_amplitude=0.2)


def _planar_ring(n, radius=None):
    """Generate planar regular polygon coordinates."""
    if radius is None:
        # Calculate radius from ideal C-C bond length (1.4 Å for aromatic, 1.54 for non)
        bond_length = 1.4
        radius = bond_length / (2 * np.sin(np.pi / n))

    coords = np.zeros((n, 3))
    for i in range(n):
        angle = 2 * np.pi * i / n - np.pi / 2  # Start from top
        coords[i, 0] = radius * np.cos(angle)
        coords[i, 1] = radius * np.sin(angle)
        coords[i, 2] = 0.0

    return coords


def _cyclohexane_chair():
    """Generate cyclohexane chair conformation coordinates."""
    coords = np.zeros((6, 3))
    # Chair conformation with alternating up/down
    r = 1.54 / (2 * np.sin(np.pi / 6))  # ~1.54 Å C-C bond

    for i in range(6):
        angle = 2 * np.pi * i / 6 - np.pi / 2
        coords[i, 0] = r * np.cos(angle)
        coords[i, 1] = r * np.sin(angle)
        # Alternating up/down displacement for chair
        coords[i, 2] = 0.25 * (1 if i % 2 == 0 else -1)

    return coords


def _puckered_ring(n, pucker_amplitude=0.3):
    """Generate a puckered ring conformation."""
    coords = _planar_ring(n)
    # Add sinusoidal puckering
    for i in range(n):
        coords[i, 2] = pucker_amplitude * np.sin(2 * np.pi * i / n)
    return coords


def apply_ring_template(molecule, ring_atoms, template_coords):
    """
    Apply ring template coordinates to a molecule.

    The template is centered at the origin and can be rotated/translated
    to fit within the larger molecular context.

    Args:
        molecule: Molecule object
        ring_atoms: List of atom indices forming the ring
        template_coords: Nx3 array of template coordinates

    Returns:
        None (modifies molecule atoms in-place)
    """
    if len(ring_atoms) != len(template_coords):
        raise ValueError(
            f"Ring has {len(ring_atoms)} atoms but template has {len(template_coords)} coords")

    for i, atom_idx in enumerate(ring_atoms):
        atom = molecule.atoms[atom_idx]
        atom.x = float(template_coords[i, 0])
        atom.y = float(template_coords[i, 1])
        atom.z = float(template_coords[i, 2])
