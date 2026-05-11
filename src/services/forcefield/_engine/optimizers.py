"""
Optimizers for MMFF94 (and any other force field with energy + gradient).

Both optimizers are decoupled from MMFF94 — they accept a generic
eg_fn: coords -> (E_float, grad_ndarray) callable. Useful for testing
against synthetic potentials before wiring up the engine.
"""
from __future__ import annotations
from typing import Callable, Tuple, List
import numpy as np

EgFn = Callable[[np.ndarray], Tuple[float, np.ndarray]]


def _rms(g: np.ndarray) -> float:
    return float(np.sqrt(np.mean(g * g)))


class SteepestDescent:
    """Adaptive-step steepest descent.

    Per step:
        1. Compute energy and gradient.
        2. Check RMS gradient convergence.
        3. Take a trial step of size `scale = min(step, 0.1 / max|g|)`.
        4. Accept if energy decreased; grow step by 1.2x (cap 0.1).
           Reject otherwise; shrink step by 0.5x.
        5. Stop if step shrinks below 1e-10.
    """

    def __init__(self, eg_fn: EgFn):
        self.eg = eg_fn

    def run(self, coords: np.ndarray, max_iters: int = 500,
            convergence: float = 1e-4) -> Tuple[np.ndarray, List[float], bool, int]:
        coords = coords.astype(np.float64, copy=True)
        step = 0.01
        e, g = self.eg(coords)
        traj = [float(e)]

        for k in range(max_iters):
            if _rms(g) < convergence:
                return coords, traj, True, k

            max_g = float(np.max(np.abs(g)))
            if max_g <= 0.0:
                return coords, traj, True, k

            scale = min(step, 0.1 / max_g)
            new_coords = coords - scale * g
            new_e, new_g = self.eg(new_coords)

            if new_e < e:
                coords, e, g = new_coords, new_e, new_g
                step = min(step * 1.2, 0.1)
            else:
                step *= 0.5

            traj.append(float(e))

            if step < 1e-10:
                break

        return coords, traj, False, max_iters
