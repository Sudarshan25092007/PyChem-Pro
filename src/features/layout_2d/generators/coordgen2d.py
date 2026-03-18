"""
2D Coordinate Generator — Force-directed layout with smart initialization.

Uses a force-directed relaxation approach that produces clean 2D layouts:
1. Detects ring systems and initializes ring atoms on regular polygons
2. Places chain atoms with zig-zag initial guesses
3. Relaxes the entire structure with spring (bond) and repulsion forces
4. Applies special intra-ring distance constraints for planar rings
5. Aligns the principal axis horizontally and centers

This is a robust approach that handles fused ring systems, long chains,
and complex branching topologies correctly.
"""

import math
import random
from collections import deque


class CoordinateGenerator2D:
    def __init__(self, molecule):
        self.molecule = molecule
        self.coords = {}
        self.BOND_LENGTH = 1.5

    def generate(self):
        if not self.molecule.atoms:
            return {}

        rings = self.molecule.find_rings()
        ring_systems = self._find_ring_systems(rings)

        # Step 1: Initialize atom positions
        self._smart_initialize(rings, ring_systems)

        # Step 2: Force-directed relaxation
        self._relax_coordinates(rings)

        # Step 3: Post-process
        self._align_principal_axis()
        self._center_coords()

        return {idx: (c[0], c[1]) for idx, c in self.coords.items()}

    # ─── Initialization ───────────────────────────────────────────

    def _smart_initialize(self, rings, ring_systems):
        """Place atoms with good initial positions before relaxation."""
        placed = set()

        # Place ring systems as polygons first
        offset_x = 0.0
        for system in ring_systems:
            self._place_ring_system(system, offset_x, 0.0, placed)
            # Compute bounding box for offset
            if self.coords:
                max_x = max(c[0] for idx, c in self.coords.items() if idx in placed)
                offset_x = max_x + self.BOND_LENGTH * 2

        # Place remaining atoms via BFS with zig-zag
        all_atoms = set(a.index for a in self.molecule.atoms)
        unplaced = all_atoms - placed

        if not placed and unplaced:
            # No rings — start from a terminal atom
            start = self._find_terminal()
            self.coords[start] = [0.0, 0.0]
            placed.add(start)
            unplaced.discard(start)

        # BFS from placed atoms to place chains
        self._bfs_place_chains(placed, unplaced)

        # Handle disconnected fragments
        remaining = all_atoms - set(self.coords.keys())
        if remaining:
            x_offset = 0.0
            if self.coords:
                x_offset = max(c[0] for c in self.coords.values()) + self.BOND_LENGTH * 3
            for idx in remaining:
                self.coords[idx] = [x_offset, 0.0]
                placed.add(idx)
                x_offset += self.BOND_LENGTH

    def _find_ring_systems(self, rings):
        """Group rings that share atoms into fused systems."""
        if not rings:
            return []
        n = len(rings)
        ring_sets = [set(r) for r in rings]
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            a, b = find(a), find(b)
            if a != b:
                parent[a] = b

        for i in range(n):
            for j in range(i + 1, n):
                if ring_sets[i] & ring_sets[j]:
                    union(i, j)

        groups = {}
        for i in range(n):
            root = find(i)
            groups.setdefault(root, []).append(i)

        return [[rings[i] for i in group] for group in groups.values()]

    def _place_ring_system(self, ring_system, cx, cy, placed):
        """Place a ring system starting with the largest ring."""
        # Sort: largest first
        sorted_rings = sorted(ring_system, key=len, reverse=True)

        # Place first ring as polygon
        first_ring = sorted_rings[0]
        n = len(first_ring)
        radius = self.BOND_LENGTH / (2 * math.sin(math.pi / max(n, 3)))

        # Orient: bottom-flat for even, vertex-up for odd
        start_angle = math.pi / 2 + (math.pi / n if n % 2 == 0 else 0)

        for i, idx in enumerate(first_ring):
            angle = start_angle + 2 * math.pi * i / n
            self.coords[idx] = [cx + radius * math.cos(angle),
                                cy + radius * math.sin(angle)]
            placed.add(idx)

        # Place fused rings
        for ring in sorted_rings[1:]:
            self._place_fused_ring(ring, placed)

    def _place_fused_ring(self, ring, placed):
        """Place a fused ring that shares atoms with already-placed atoms."""
        ring_set = set(ring)
        shared = ring_set & placed
        unplaced = [idx for idx in ring if idx not in placed]

        if not unplaced:
            return  # All atoms already placed

        if len(shared) >= 2:
            # Find shared edge (two adjacent shared atoms)
            shared_list = list(shared)
            # Find two shared atoms that are bonded
            edge = None
            for i, a in enumerate(shared_list):
                for b in shared_list[i+1:]:
                    if b in self.molecule.get_neighbors(a):
                        edge = (a, b)
                        break
                if edge:
                    break

            if edge:
                self._place_ring_on_edge(ring, edge, placed, unplaced)
                return

        # Fallback: place as separate polygon near shared atoms
        if shared:
            ref = next(iter(shared))
            cx, cy = self.coords[ref]
            cx += self.BOND_LENGTH * 2
        else:
            cx, cy = 0.0, 0.0

        n = len(ring)
        radius = self.BOND_LENGTH / (2 * math.sin(math.pi / max(n, 3)))
        start_angle = math.pi / 2

        for i, idx in enumerate(ring):
            if idx in placed:
                continue
            angle = start_angle + 2 * math.pi * i / n
            self.coords[idx] = [cx + radius * math.cos(angle),
                                cy + radius * math.sin(angle)]
            placed.add(idx)

    def _place_ring_on_edge(self, ring, edge, placed, unplaced):
        """Place a fused ring by reflecting around a shared edge."""
        a, b = edge
        ax, ay = self.coords[a]
        bx, by = self.coords[b]

        mx, my = (ax + bx) / 2, (ay + by) / 2
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        if length < 0.001:
            length = 0.001

        # Normal to shared edge
        nx, ny = -dy / length, dx / length

        # Choose the side with fewer existing atoms (avoid overlap)
        test1_x, test1_y = mx + nx * self.BOND_LENGTH, my + ny * self.BOND_LENGTH
        test2_x, test2_y = mx - nx * self.BOND_LENGTH, my - ny * self.BOND_LENGTH

        score1 = sum(1 for idx in placed
                     if math.hypot(self.coords[idx][0] - test1_x,
                                   self.coords[idx][1] - test1_y) < self.BOND_LENGTH)
        score2 = sum(1 for idx in placed
                     if math.hypot(self.coords[idx][0] - test2_x,
                                   self.coords[idx][1] - test2_y) < self.BOND_LENGTH)

        if score1 <= score2:
            side_nx, side_ny = nx, ny
        else:
            side_nx, side_ny = -nx, -ny

        # Place unplaced atoms in an arc on the chosen side
        n = len(ring)
        n_new = len(unplaced)
        ring_radius = self.BOND_LENGTH / (2 * math.sin(math.pi / max(n, 3)))

        # Center of new ring
        h = math.sqrt(max(0, ring_radius ** 2 - (length / 2) ** 2))
        center_x = mx + side_nx * h
        center_y = my + side_ny * h

        # Compute angles from center to a and b
        angle_a = math.atan2(ay - center_y, ax - center_x)
        angle_b = math.atan2(by - center_y, bx - center_x)

        # Arc from b to a going through the new side
        arc = angle_a - angle_b
        if arc < 0:
            arc += 2 * math.pi
        if arc > 2 * math.pi:
            arc -= 2 * math.pi
        # If arc is too small, take the other way
        if arc < math.pi / 2:
            arc = 2 * math.pi - arc
            for i, idx in enumerate(unplaced):
                frac = (i + 1.0) / (n_new + 1.0)
                angle = angle_b - arc * frac
                self.coords[idx] = [center_x + ring_radius * math.cos(angle),
                                    center_y + ring_radius * math.sin(angle)]
                placed.add(idx)
        else:
            for i, idx in enumerate(unplaced):
                frac = (i + 1.0) / (n_new + 1.0)
                angle = angle_b + arc * frac
                self.coords[idx] = [center_x + ring_radius * math.cos(angle),
                                    center_y + ring_radius * math.sin(angle)]
                placed.add(idx)

    def _bfs_place_chains(self, placed, unplaced):
        """BFS place chain atoms with zig-zag angles."""
        if not placed:
            return

        depth = {idx: 0 for idx in placed}
        queue = deque(list(placed))

        while queue:
            current = queue.popleft()
            neighbors = self.molecule.get_neighbors(current)
            unplaced_nb = [n for n in neighbors if n in unplaced]

            if not unplaced_nb:
                continue

            # Direction from a placed neighbor for zig-zag
            placed_nb = [n for n in neighbors if n in placed and n != current]
            if placed_nb:
                ref = placed_nb[0]
                ref_angle = math.atan2(
                    self.coords[current][1] - self.coords[ref][1],
                    self.coords[current][0] - self.coords[ref][0])
            else:
                ref_angle = 0.0

            cur_depth = depth.get(current, 0)
            n_new = len(unplaced_nb)

            for i, nb in enumerate(unplaced_nb):
                child_depth = cur_depth + 1

                if n_new == 1:
                    # Zig-zag: alternate ±60° based on depth
                    if child_depth % 2 == 0:
                        angle = ref_angle + math.pi / 3
                    else:
                        angle = ref_angle - math.pi / 3
                elif n_new == 2:
                    angle = ref_angle + (math.pi / 3 if i == 0 else -math.pi / 3)
                else:
                    spread = 2 * math.pi / (n_new + 1)
                    angle = ref_angle - math.pi + spread * (i + 1)

                x = self.coords[current][0] + self.BOND_LENGTH * math.cos(angle)
                y = self.coords[current][1] + self.BOND_LENGTH * math.sin(angle)

                self.coords[nb] = [x, y]
                placed.add(nb)
                unplaced.discard(nb)
                depth[nb] = child_depth
                queue.append(nb)

    def _find_terminal(self):
        """Find a terminal atom (degree 1) or return 0."""
        for atom in self.molecule.atoms:
            if self.molecule.degree(atom.index) <= 1:
                return atom.index
        return 0

    # ─── Force-Directed Relaxation ────────────────────────────────

    def _relax_coordinates(self, rings):
        """Spring-embed relaxation with bond + ring constraints + repulsion."""
        bonds = [(b.begin_atom_idx, b.end_atom_idx) for b in self.molecule.bonds]

        # Build distance targets
        targets = {}
        for i, j in bonds:
            targets[tuple(sorted((i, j)))] = self.BOND_LENGTH

        # Ring intra-atom distance constraints (keeps rings planar)
        for ring in rings:
            n = len(ring)
            for i in range(n):
                for j in range(i + 1, n):
                    k = min(j - i, n - (j - i))
                    if k == 1:
                        continue  # Already a bond
                    target_dist = self.BOND_LENGTH * (
                        math.sin(k * math.pi / n) / math.sin(math.pi / n))
                    pair = tuple(sorted((ring[i], ring[j])))
                    targets[pair] = target_dist

        # Non-bonded angle constraints (120° separation for sp2)
        for atom in self.molecule.atoms:
            neighbors = list(self.molecule.get_neighbors(atom.index))
            for i in range(len(neighbors)):
                for j in range(i + 1, len(neighbors)):
                    pair = tuple(sorted((neighbors[i], neighbors[j])))
                    if pair not in targets:
                        targets[pair] = self.BOND_LENGTH * 1.732  # sqrt(3)

        indices = list(self.coords.keys())
        n_atoms = len(indices)

        for iteration in range(2000):
            forces = {idx: [0.0, 0.0] for idx in indices}
            max_force = 0.0

            # Spring forces from distance targets
            for (i, j), target_dist in targets.items():
                if i not in self.coords or j not in self.coords:
                    continue
                dx = self.coords[j][0] - self.coords[i][0]
                dy = self.coords[j][1] - self.coords[i][1]
                dist = math.hypot(dx, dy)
                if dist < 0.001:
                    dx = random.uniform(-0.1, 0.1)
                    dy = random.uniform(-0.1, 0.1)
                    dist = math.hypot(dx, dy) or 0.1

                k = 2.0 if target_dist == self.BOND_LENGTH else 1.0
                f_mag = k * (dist - target_dist)
                fx = f_mag * dx / dist
                fy = f_mag * dy / dist

                forces[i][0] += fx
                forces[i][1] += fy
                forces[j][0] -= fx
                forces[j][1] -= fy

            # Global repulsion (all-pairs, short-range)
            for idx1 in range(n_atoms):
                for idx2 in range(idx1 + 1, n_atoms):
                    i, j = indices[idx1], indices[idx2]
                    dx = self.coords[j][0] - self.coords[i][0]
                    dy = self.coords[j][1] - self.coords[i][1]
                    dist = math.hypot(dx, dy)
                    if dist < 0.001:
                        dx = random.uniform(-0.1, 0.1)
                        dy = random.uniform(-0.1, 0.1)
                        dist = 0.1

                    if dist < self.BOND_LENGTH * 2.5:
                        f_mag = 0.5 / (dist ** 2)
                        fx = f_mag * dx / dist
                        fy = f_mag * dy / dist
                        forces[i][0] -= fx
                        forces[i][1] -= fy
                        forces[j][0] += fx
                        forces[j][1] += fy

            # Apply forces with decaying step size
            step_size = max(0.005, 0.05 * (1.0 - iteration / 2000.0))
            for idx in indices:
                fx, fy = forces[idx]
                f_len = math.hypot(fx, fy)
                if f_len > 10.0:
                    fx, fy = fx * 10.0 / f_len, fy * 10.0 / f_len
                self.coords[idx][0] += fx * step_size
                self.coords[idx][1] += fy * step_size
                max_force = max(max_force, f_len)

            if max_force < 0.01:
                break

    # ─── Post-processing ──────────────────────────────────────────

    def _align_principal_axis(self):
        """PCA: rotate so longest dimension is horizontal."""
        if len(self.coords) < 2:
            return

        cx = sum(c[0] for c in self.coords.values()) / len(self.coords)
        cy = sum(c[1] for c in self.coords.values()) / len(self.coords)

        cxx = cyy = cxy = 0.0
        for x, y in self.coords.values():
            dx, dy = x - cx, y - cy
            cxx += dx * dx
            cyy += dy * dy
            cxy += dx * dy

        angle = 0.5 * math.atan2(2 * cxy, cxx - cyy)
        cos_a, sin_a = math.cos(-angle), math.sin(-angle)

        for i in self.coords:
            dx, dy = self.coords[i][0] - cx, self.coords[i][1] - cy
            self.coords[i][0] = cx + dx * cos_a - dy * sin_a
            self.coords[i][1] = cy + dx * sin_a + dy * cos_a

    def _center_coords(self):
        """Center coordinates at origin."""
        cx = sum(c[0] for c in self.coords.values()) / len(self.coords)
        cy = sum(c[1] for c in self.coords.values()) / len(self.coords)
        for i in self.coords:
            self.coords[i][0] -= cx
            self.coords[i][1] -= cy