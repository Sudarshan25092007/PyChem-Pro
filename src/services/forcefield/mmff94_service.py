# src/services/forcefield/mmff94_service.py
"""
Unified MMFF94 force field service.

Implements IForceField protocol. Integrates:
- Hydrogen addition
- BCI charge assignment
- Bond stretching energy + gradient
- Angle bending energy + gradient
- Torsion energy + gradient
- Van der Waals repulsion energy + gradient
- Steepest descent and L-BFGS optimizers
"""
import numpy as np
from src.core.protocols.forcefield import OptimizationResult
from src.core.domain.models.molecule import Molecule
from src.services.forcefield.hydrogen import HydrogenAdder
from src.services.forcefield.angle_bending import AngleBendingCalculator
from src.services.forcefield.torsion import TorsionCalculator
from src.services.forcefield.parameters import (
    get_bond_params, get_vdw_params, get_bci_charge, MMFF94_BCI
)


# ─── Module-level worker functions (picklable for spawn mode) ─────

def _vdw_energy_chunk(args):
    """Compute VdW energy for a chunk of pairs."""
    coords, pairs_chunk = args
    energy = 0.0
    for i, j, sigma, epsilon in pairs_chunk:
        # Ensure parameters are valid
        sigma = float(sigma) if sigma is not None else 3.4
        epsilon = float(epsilon) if epsilon is not None else 0.1
        if epsilon <= 0:
            continue
        r = np.linalg.norm(coords[i] - coords[j]) + 1e-8
        if r < sigma * 1.5:
            ratio = sigma / r
            energy += epsilon * (ratio ** 12 - 2.0 * ratio ** 6)
    return energy


def _vdw_gradient_chunk(args):
    """Compute VdW gradient for a chunk of pairs."""
    coords, pairs_chunk, n_atoms = args
    grad = np.zeros((n_atoms, 3))
    for i, j, sigma, epsilon in pairs_chunk:
        # Ensure parameters are valid
        sigma = float(sigma) if sigma is not None else 3.4
        epsilon = float(epsilon) if epsilon is not None else 0.1
        if epsilon <= 0:
            continue
        diff = coords[i] - coords[j]
        r = np.linalg.norm(diff) + 1e-8
        if r < sigma * 1.5:
            ratio = sigma / r
            force_mag = epsilon * (-12.0 * ratio**12 / r + 12.0 * ratio**6 / r)
            direction = diff / r
            grad[i] += force_mag * direction
            grad[j] -= force_mag * direction
    return grad


class MMFF94Service:
    """
    Complete MMFF94 force field service.

    Optimization pipeline:
    1. Assign hybridization
    2. Add explicit hydrogens with 3D positions
    3. Assign partial charges (BCI method)
    4. Build interaction lists (bonds, angles, torsions, VdW pairs)
    5. Minimize energy via steepest descent or L-BFGS
    """

    def __init__(self, executor=None):
        self.executor = executor
        self.h_adder = HydrogenAdder()
        self.angle_calc = AngleBendingCalculator()
        self.torsion_calc = TorsionCalculator()

    def add_hydrogens(self, mol: Molecule) -> int:
        return self.h_adder.add_hydrogens(mol)

    def assign_atom_types(self, mol: Molecule) -> None:
        mol.assign_hybridization()

    def _seed_coords_from_2d(self, mol: Molecule) -> None:
        """Ensure every atom has numeric 3D coords before optimization.

        Priority: keep existing 3D → else use cached OASA 2D (x2d/y2d) →
        else generate 2D layout now → last resort, origin.
        
        The z-coordinate is intelligently seeded based on atom properties
        (hybridization, atom type) and then developed during optimization.
        This provides better starting points for 3D structure generation
        compared to flat 2D layouts.
        """
        needs_seed = any(
            a.x is None or a.y is None or a.z is None for a in mol.atoms
        )
        if not needs_seed:
            return

        have_2d = all(
            getattr(a, 'x2d', None) is not None and getattr(a, 'y2d', None) is not None
            for a in mol.atoms
        )
        if not have_2d:
            try:
                # Use the SMILES-based OASA coordinate generator for better 2D layouts
                from src.features.layout_2d.generators.coordgen2d_smiles_pure_oasa import CoordinateGenerator2DSMILES
                CoordinateGenerator2DSMILES(mol, force_regenerate=True).generate()
            except Exception:
                try:
                    # Fallback to standard generator
                    from src.features.layout_2d.generators.coordgen2d import CoordinateGenerator2D
                    CoordinateGenerator2D(mol, force_regenerate=False).generate()
                except Exception:
                    pass  # fall through to origin below

        # Assign hybridization for z-coordinate seeding
        mol.assign_hybridization()
        
        for a in mol.atoms:
            # Use 2D coordinates for x and y (from OASA)
            if a.x is None:
                a.x = float(a.x2d) if getattr(a, 'x2d', None) is not None else 0.0
            if a.y is None:
                a.y = float(a.y2d) if getattr(a, 'y2d', None) is not None else 0.0
            
            # Intelligently seed z-coordinate based on atom properties
            # This gives the optimizer a better starting point than flat z=0
            if a.z is None:
                z_seed = self._compute_initial_z(a, mol)
                a.z = z_seed

    def _compute_initial_z(self, atom, mol) -> float:
        """Compute an intelligent initial z-coordinate for an atom.
        
        Uses atom properties to create a non-flat initial conformation:
        - sp3 atoms get small random z (tetrahedral hint)
        - sp2 atoms stay near plane (planar hint)
        - sp atoms stay near plane (linear hint)
        - Heavy atoms get slightly more variation than hydrogens
        
        This seeds the 3D structure with hints about preferred geometry
        that the MMFF94 optimizer will then develop further.
        """
        import random
        random.seed(atom.index)  # Deterministic for reproducibility
        
        hyb = getattr(atom, 'hybridization', 'sp3') or 'sp3'
        symbol = atom.symbol
        
        # Base z variation by hybridization
        if hyb == 'sp':
            # Linear - stay near plane
            z_base = random.uniform(-0.1, 0.1)
        elif hyb == 'sp2':
            # Planar - small deviation from plane
            z_base = random.uniform(-0.2, 0.2)
        else:  # sp3
            # Tetrahedral - allow more variation
            z_base = random.uniform(-0.5, 0.5)
        
        # Adjust based on atom type
        if symbol == 'H':
            # Hydrogens closer to plane (they extend from heavy atoms)
            z_scale = 0.3
        elif symbol in ('C', 'N', 'O'):
            # Common organic atoms - standard variation
            z_scale = 1.0
        elif symbol in ('S', 'P'):
            # Larger atoms - slightly more variation
            z_scale = 1.2
        else:
            # Other atoms - moderate variation
            z_scale = 0.8
        
        return z_base * z_scale

    def assign_charges(self, mol: Molecule) -> None:
        for atom in mol.atoms:
            atom.partial_charge = 0.0
            atom.partial_charge += atom.formal_charge if atom.formal_charge is not None else 0.0
        for bond in mol.bonds:
            a1 = mol.atoms[bond.begin_atom_idx]
            a2 = mol.atoms[bond.end_atom_idx]
            bci = get_bci_charge(a1.symbol, a2.symbol)
            # Ensure bci is a valid number
            try:
                bci = float(bci) if bci is not None else 0.0
            except (TypeError, ValueError):
                bci = 0.0
            a1.partial_charge += bci
            a2.partial_charge -= bci

    def compute_energy(self, mol: Molecule) -> float:
        self._seed_coords_from_2d(mol)
        coords = np.array([[a.x, a.y, a.z] for a in mol.atoms], dtype=np.float64)
        mol.assign_hybridization()
        bond_list = self._build_bond_list(mol)
        angle_list = self.angle_calc.build_angle_list(mol)
        torsion_list = self.torsion_calc.build_torsion_list(mol)
        vdw_pairs = self._build_vdw_pairs(mol)
        return self._total_energy(coords, bond_list, angle_list, torsion_list, vdw_pairs)

    def optimize_geometry(self, mol: Molecule, max_iters=500,
                          convergence=1e-4, method='steepest_descent'):
        # 0. Seed 3D coords from OASA 2D layout if missing (SMILES input)
        self._seed_coords_from_2d(mol)

        # 1. Assign hybridization
        mol.assign_hybridization()

        # 2. Add hydrogens
        self.h_adder.add_hydrogens(mol)

        # 3. Assign charges
        self.assign_charges(mol)

        # 4. Build all interaction lists
        bond_list = self._build_bond_list(mol)
        angle_list = self.angle_calc.build_angle_list(mol)
        torsion_list = self.torsion_calc.build_torsion_list(mol)
        vdw_pairs = self._build_vdw_pairs(mol)

        # 5. Get coordinates
        coords = np.array([[a.x, a.y, a.z] for a in mol.atoms], dtype=np.float64)
        # Fallback: add small Z perturbation if coordinates are still flat
        # (should rarely happen with intelligent z-seeding in _seed_coords_from_2d)
        if np.allclose(coords[:, 2], 0.0, atol=0.01):
            coords[:, 2] += np.random.uniform(-0.1, 0.1, len(coords))

        # 6. Optimize
        if method == 'lbfgs':
            coords, energy_traj, converged, steps = self._lbfgs(
                coords, bond_list, angle_list, torsion_list, vdw_pairs,
                max_iters, convergence)
        else:
            coords, energy_traj, converged, steps = self._steepest_descent(
                coords, bond_list, angle_list, torsion_list, vdw_pairs,
                max_iters, convergence)

        # 7. Write back coordinates
        for i, atom in enumerate(mol.atoms):
            atom.x, atom.y, atom.z = float(coords[i, 0]), float(coords[i, 1]), float(coords[i, 2])

        final_energy = energy_traj[-1] if energy_traj else 0.0
        grad = self._total_gradient(coords, bond_list, angle_list, torsion_list, vdw_pairs)
        rms_grad = float(np.sqrt(np.mean(grad ** 2)))

        return OptimizationResult(
            converged=converged,
            final_energy=final_energy,
            num_steps=steps,
            energy_trajectory=energy_traj,
            rms_gradient=rms_grad
        )

    # ─── Energy Functions ──────────────────────────────────────

    def _total_energy(self, coords, bond_list, angle_list, torsion_list, vdw_pairs):
        e = 0.0
        e += self._bond_energy(coords, bond_list)
        e += self.angle_calc.energy(coords, angle_list)
        e += self.torsion_calc.energy(coords, torsion_list)
        e += self._vdw_energy(coords, vdw_pairs)
        return e

    def _bond_energy(self, coords, bond_list):
        energy = 0.0
        for i, j, r0, kb in bond_list:
            # Ensure parameters are valid
            r0 = float(r0) if r0 is not None else 1.5
            kb = float(kb) if kb is not None else 4.0
            if kb <= 0:
                continue
            r = np.linalg.norm(coords[i] - coords[j])
            energy += 71.94 / 2.0 * kb * (r - r0) ** 2
        return energy

    def _vdw_energy_sequential(self, coords, vdw_pairs):
        energy = 0.0
        for i, j, sigma, epsilon in vdw_pairs:
            # Ensure parameters are valid
            sigma = float(sigma) if sigma is not None else 3.4
            epsilon = float(epsilon) if epsilon is not None else 0.1
            if epsilon <= 0:
                continue
            r = np.linalg.norm(coords[i] - coords[j]) + 1e-8
            if r < sigma * 1.5:
                ratio = sigma / r
                energy += epsilon * (ratio ** 12 - 2.0 * ratio ** 6)
        return energy

    def _vdw_energy(self, coords, vdw_pairs):
        if len(vdw_pairs) < 200 or self.executor is None:
            return self._vdw_energy_sequential(coords, vdw_pairs)
        # Split pairs into chunks for parallel execution
        chunk_size = max(50, len(vdw_pairs) // self.executor.num_workers)
        chunks = [(coords, vdw_pairs[i:i + chunk_size])
                  for i in range(0, len(vdw_pairs), chunk_size)]
        results = self.executor.map(_vdw_energy_chunk, chunks)
        return sum(results)

    # ─── Gradient Functions ────────────────────────────────────

    def _total_gradient(self, coords, bond_list, angle_list, torsion_list, vdw_pairs):
        grad = np.zeros_like(coords)
        grad += self._bond_gradient(coords, bond_list)
        grad += self.angle_calc.gradient(coords, angle_list)
        grad += self.torsion_calc.gradient(coords, torsion_list)
        grad += self._vdw_gradient(coords, vdw_pairs)
        return grad

    def _bond_gradient(self, coords, bond_list):
        grad = np.zeros_like(coords)
        for i, j, r0, kb in bond_list:
            # Ensure parameters are valid
            r0 = float(r0) if r0 is not None else 1.5
            kb = float(kb) if kb is not None else 4.0
            if kb <= 0:
                continue
            diff = coords[i] - coords[j]
            r = np.linalg.norm(diff) + 1e-8
            force = 71.94 * kb * (r - r0) / r
            grad[i] += force * diff / r
            grad[j] -= force * diff / r
        return grad

    def _vdw_gradient_sequential(self, coords, vdw_pairs):
        grad = np.zeros_like(coords)
        for i, j, sigma, epsilon in vdw_pairs:
            # Ensure parameters are valid
            sigma = float(sigma) if sigma is not None else 3.4
            epsilon = float(epsilon) if epsilon is not None else 0.1
            if epsilon <= 0:
                continue
            diff = coords[i] - coords[j]
            r = np.linalg.norm(diff) + 1e-8
            if r < sigma * 1.5:
                ratio = sigma / r
                force_mag = epsilon * (-12.0 * ratio**12 / r + 12.0 * ratio**6 / r)
                direction = diff / r
                grad[i] += force_mag * direction
                grad[j] -= force_mag * direction
        return grad

    def _vdw_gradient(self, coords, vdw_pairs):
        if len(vdw_pairs) < 200 or self.executor is None:
            return self._vdw_gradient_sequential(coords, vdw_pairs)
        # Split pairs into chunks for parallel execution
        n_atoms = coords.shape[0]
        chunk_size = max(50, len(vdw_pairs) // self.executor.num_workers)
        chunks = [(coords, vdw_pairs[i:i + chunk_size], n_atoms)
                  for i in range(0, len(vdw_pairs), chunk_size)]
        results = self.executor.map(_vdw_gradient_chunk, chunks)
        # Sum partial gradients from all chunks
        grad = np.zeros_like(coords)
        for partial_grad in results:
            grad += partial_grad
        return grad

    # ─── Interaction List Builders ─────────────────────────────

    def _build_bond_list(self, mol):
        bond_list = []
        for bond in mol.bonds:
            i, j = bond.begin_atom_idx, bond.end_atom_idx
            sym1 = mol.atoms[i].symbol
            sym2 = mol.atoms[j].symbol
            params = get_bond_params(sym1, sym2, bond.order)
            # Ensure valid parameters
            if params is None or not isinstance(params, (list, tuple)) or len(params) != 2:
                r0, kb = 1.5, 4.0  # Default bond parameters
            else:
                r0, kb = params
                try:
                    r0 = float(r0) if r0 is not None else 1.5
                    kb = float(kb) if kb is not None else 4.0
                except (TypeError, ValueError):
                    r0, kb = 1.5, 4.0
            bond_list.append((i, j, r0, kb))
        return bond_list

    def _build_vdw_pairs(self, mol):
        n = len(mol.atoms)
        # Exclude 1-2 pairs (bonded)
        excluded = set()
        for bond in mol.bonds:
            pair = (min(bond.begin_atom_idx, bond.end_atom_idx),
                    max(bond.begin_atom_idx, bond.end_atom_idx))
            excluded.add(pair)
        # Exclude 1-3 pairs
        for atom in mol.atoms:
            neighbors = mol.get_neighbors(atom.index)
            for a in range(len(neighbors)):
                for b in range(a + 1, len(neighbors)):
                    pair = (min(neighbors[a], neighbors[b]),
                            max(neighbors[a], neighbors[b]))
                    excluded.add(pair)

        vdw_pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                if (i, j) not in excluded:
                    params1 = get_vdw_params(mol.atoms[i].symbol)
                    params2 = get_vdw_params(mol.atoms[j].symbol)
                    # Ensure valid parameters
                    if params1 is None or not isinstance(params1, (list, tuple)) or len(params1) != 2:
                        r1, e1 = 1.7, 0.1  # Default carbon VdW
                    else:
                        r1, e1 = params1
                        try:
                            r1 = float(r1) if r1 is not None else 1.7
                            e1 = float(e1) if e1 is not None else 0.1
                        except (TypeError, ValueError):
                            r1, e1 = 1.7, 0.1
                    if params2 is None or not isinstance(params2, (list, tuple)) or len(params2) != 2:
                        r2, e2 = 1.7, 0.1
                    else:
                        r2, e2 = params2
                        try:
                            r2 = float(r2) if r2 is not None else 1.7
                            e2 = float(e2) if e2 is not None else 0.1
                        except (TypeError, ValueError):
                            r2, e2 = 1.7, 0.1
                    sigma = r1 + r2
                    epsilon = (e1 * e2) ** 0.5 if e1 > 0 and e2 > 0 else 0.0
                    vdw_pairs.append((i, j, sigma, epsilon))
        return vdw_pairs

    # ─── Optimizers ────────────────────────────────────────────

    def _steepest_descent(self, coords, bond_list, angle_list, torsion_list,
                          vdw_pairs, max_iters, convergence):
        step_size = 0.01
        energy = self._total_energy(coords, bond_list, angle_list, torsion_list, vdw_pairs)
        energy_traj = [float(energy)]

        for step in range(max_iters):
            grad = self._total_gradient(coords, bond_list, angle_list, torsion_list, vdw_pairs)
            rms_grad = float(np.sqrt(np.mean(grad ** 2)))

            if rms_grad < convergence:
                return coords, energy_traj, True, step + 1

            direction = -grad
            max_grad = np.max(np.abs(direction))
            if max_grad > 0:
                scale = min(step_size, 0.1 / max_grad)
            else:
                break

            new_coords = coords + scale * direction
            new_energy = self._total_energy(new_coords, bond_list, angle_list,
                                            torsion_list, vdw_pairs)

            if new_energy < energy:
                coords = new_coords
                energy = new_energy
                step_size = min(step_size * 1.2, 0.1)
            else:
                step_size *= 0.5

            energy_traj.append(float(energy))
            if step_size < 1e-10:
                break

        return coords, energy_traj, False, max_iters

    def _lbfgs(self, coords, bond_list, angle_list, torsion_list,
               vdw_pairs, max_iters, convergence, m=10):
        flat = coords.flatten()

        def energy_fn(x):
            c = x.reshape(-1, 3)
            return self._total_energy(c, bond_list, angle_list, torsion_list, vdw_pairs)

        def grad_fn(x):
            c = x.reshape(-1, 3)
            return self._total_gradient(c, bond_list, angle_list, torsion_list, vdw_pairs).flatten()

        s_list, y_list, rho_list = [], [], []
        energy = energy_fn(flat)
        grad = grad_fn(flat)
        energy_traj = [float(energy)]

        for step in range(max_iters):
            rms_grad = float(np.sqrt(np.mean(grad ** 2)))
            if rms_grad < convergence:
                return flat.reshape(-1, 3), energy_traj, True, step + 1

            # L-BFGS two-loop recursion
            q = grad.copy()
            alphas = []
            for i in range(len(s_list) - 1, -1, -1):
                alpha = rho_list[i] * np.dot(s_list[i], q)
                alphas.insert(0, alpha)
                q -= alpha * y_list[i]

            if s_list:
                gamma = np.dot(s_list[-1], y_list[-1]) / (np.dot(y_list[-1], y_list[-1]) + 1e-10)
                r = gamma * q
            else:
                r = q * 0.01

            for i in range(len(s_list)):
                beta = rho_list[i] * np.dot(y_list[i], r)
                r += s_list[i] * (alphas[i] - beta)

            direction = -r

            # Backtracking line search
            step_size = 1.0
            c1 = 1e-4
            dir_deriv = np.dot(grad, direction)
            if dir_deriv >= 0:
                direction = -grad
                dir_deriv = np.dot(grad, direction)

            for _ in range(20):
                new_flat = flat + step_size * direction
                new_energy = energy_fn(new_flat)
                if new_energy <= energy + c1 * step_size * dir_deriv:
                    break
                step_size *= 0.5
            else:
                break

            s = new_flat - flat
            new_grad = grad_fn(new_flat)
            y = new_grad - grad
            sy = np.dot(s, y)

            if sy > 1e-10:
                s_list.append(s)
                y_list.append(y)
                rho_list.append(1.0 / sy)
                if len(s_list) > m:
                    s_list.pop(0)
                    y_list.pop(0)
                    rho_list.pop(0)

            flat = new_flat
            energy = energy_fn(flat)
            grad = new_grad
            energy_traj.append(float(energy))

        return flat.reshape(-1, 3), energy_traj, False, max_iters
