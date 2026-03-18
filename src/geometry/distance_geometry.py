"""
Distance Geometry — Generate 3D coordinates from molecular graph using
distance bounds matrix and metric matrix embedding.

Algorithm:
1. Build distance bounds matrix (lower/upper bounds for all atom pairs)
2. Smooth bounds using triangle inequality
3. Sample random distances within bounds
4. Embed into 3D space via eigendecomposition
"""

import numpy as np
from ..core.elements import bond_length


def build_distance_bounds(molecule):
    """
    Build lower and upper distance bounds matrices.

    Bounds sources:
    - 1,2-distances (bonded): from covalent radii + bond order correction
    - 1,3-distances: from bond angles and bond lengths
    - Non-bonded: lower = sum of VdW radii * 0.5, upper = large value

    Args:
        molecule: Molecule with atoms and bonds

    Returns:
        (lower_bounds, upper_bounds) as NxN numpy arrays in Angstroms
    """
    n = len(molecule.atoms)
    lower = np.zeros((n, n))
    upper = np.full((n, n), 100.0)  # Large default upper bound

    # Diagonal = 0
    np.fill_diagonal(lower, 0.0)
    np.fill_diagonal(upper, 0.0)

    # ── 1,2-distances (bonded pairs) ──
    for bond in molecule.bonds:
        i = bond.begin_atom_idx
        j = bond.end_atom_idx
        sym_i = molecule.atoms[i].symbol
        sym_j = molecule.atoms[j].symbol
        d = bond_length(sym_i, sym_j, bond.order)
        # Allow ±5% tolerance
        lower[i][j] = lower[j][i] = d * 0.95
        upper[i][j] = upper[j][i] = d * 1.05

    # ── 1,3-distances (two bonds apart) ──
    for atom in molecule.atoms:
        neighbors = molecule.get_neighbors(atom.index)
        for k in range(len(neighbors)):
            for l in range(k + 1, len(neighbors)):
                i = neighbors[k]
                j = neighbors[l]

                # Get bond lengths
                bond_ij = molecule.get_bond_between(atom.index, i)
                bond_jk = molecule.get_bond_between(atom.index, j)
                d1 = bond_length(molecule.atoms[atom.index].symbol,
                                 molecule.atoms[i].symbol,
                                 bond_ij.order if bond_ij else 1)
                d2 = bond_length(molecule.atoms[atom.index].symbol,
                                 molecule.atoms[j].symbol,
                                 bond_jk.order if bond_jk else 1)

                # Get ideal angle based on hybridization
                angle = _ideal_angle(molecule.atoms[atom.index])

                # Law of cosines: d² = d1² + d2² - 2*d1*d2*cos(angle)
                d13 = np.sqrt(d1**2 + d2**2 - 2*d1*d2*np.cos(np.radians(angle)))

                lower[i][j] = lower[j][i] = max(lower[i][j], d13 * 0.90)
                upper[i][j] = upper[j][i] = min(upper[i][j], d13 * 1.10)

    # ── Non-bonded distances ──
    for i in range(n):
        for j in range(i + 1, n):
            if lower[i][j] == 0:  # Not already set by bonded/1-3
                vdw_i = molecule.atoms[i].element.vdw_radius
                vdw_j = molecule.atoms[j].element.vdw_radius
                # Lower bound: VdW contact distance (scaled down to allow some flexibility)
                lower[i][j] = lower[j][i] = max(lower[i][j], (vdw_i + vdw_j) * 0.5)

    return lower, upper


def smooth_bounds(lower, upper, max_iterations=50):
    """
    Smooth distance bounds using triangle inequality.

    For all triples (i, j, k):
        upper[i][j] <= upper[i][k] + upper[k][j]
        lower[i][j] >= lower[i][k] - upper[k][j]

    Uses a simplified approach (not full Floyd-Warshall for speed on large molecules).

    Args:
        lower: NxN lower bounds matrix
        upper: NxN upper bounds matrix
        max_iterations: Maximum smoothing iterations

    Returns:
        (smoothed_lower, smoothed_upper)
    """
    n = lower.shape[0]
    changed = True
    iteration = 0

    while changed and iteration < max_iterations:
        changed = False
        iteration += 1

        for k in range(n):
            for i in range(n):
                if i == k:
                    continue
                for j in range(i + 1, n):
                    if j == k:
                        continue

                    # Upper bound triangle inequality
                    new_upper = upper[i][k] + upper[k][j]
                    if new_upper < upper[i][j]:
                        upper[i][j] = upper[j][i] = new_upper
                        changed = True

                    # Lower bound triangle inequality
                    new_lower = lower[i][k] - upper[k][j]
                    if new_lower > lower[i][j]:
                        lower[i][j] = lower[j][i] = new_lower
                        changed = True

                    new_lower2 = lower[k][j] - upper[i][k]
                    if new_lower2 > lower[i][j]:
                        lower[i][j] = lower[j][i] = new_lower2
                        changed = True

        # For large molecules, limit iterations
        if n > 100 and iteration >= 3:
            break

    return lower, upper


def embed_distances(distance_matrix):
    """
    Embed a distance matrix into 3D coordinates using metric matrix method.

    Steps:
    1. Compute the metric (Gram) matrix G from distances
    2. Eigendecompose G
    3. Take top 3 eigenvalues/vectors for 3D coordinates

    Args:
        distance_matrix: NxN symmetric distance matrix

    Returns:
        Nx3 numpy array of 3D coordinates
    """
    n = distance_matrix.shape[0]

    if n == 1:
        return np.zeros((1, 3))

    if n == 2:
        coords = np.zeros((2, 3))
        coords[1, 0] = distance_matrix[0, 1]
        return coords

    # Compute squared distances
    D2 = distance_matrix ** 2

    # Centering matrix: H = I - (1/n) * ones
    # Metric matrix: G = -0.5 * H * D2 * H
    row_mean = np.mean(D2, axis=1)
    col_mean = np.mean(D2, axis=0)
    total_mean = np.mean(D2)

    G = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            G[i][j] = -0.5 * (D2[i][j] - row_mean[i] - col_mean[j] + total_mean)

    # Eigendecomposition
    eigenvalues, eigenvectors = np.linalg.eigh(G)

    # Sort by eigenvalue (descending)
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    # Take top 3 dimensions
    coords = np.zeros((n, 3))
    for dim in range(min(3, n)):
        if eigenvalues[dim] > 0:
            coords[:, dim] = eigenvectors[:, dim] * np.sqrt(eigenvalues[dim])

    return coords


def generate_distance_matrix(lower, upper):
    """
    Generate a random distance matrix within the bounds.

    Args:
        lower: NxN lower bounds
        upper: NxN upper bounds

    Returns:
        NxN symmetric distance matrix
    """
    n = lower.shape[0]
    D = np.zeros((n, n))

    for i in range(n):
        for j in range(i + 1, n):
            lo = max(lower[i][j], 0.1)
            hi = max(upper[i][j], lo + 0.01)
            d = np.random.uniform(lo, hi)
            D[i][j] = D[j][i] = d

    return D


def _ideal_angle(atom):
    """Get ideal bond angle based on hybridization."""
    hyb = atom.hybridization
    if hyb == 'sp':
        return 180.0
    elif hyb == 'sp2':
        return 120.0
    else:
        return 109.5  # sp3 default
