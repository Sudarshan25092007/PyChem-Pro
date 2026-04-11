"""
2D Bond Renderer — ChemDraw-quality bond drawing for skeletal formulas.

Handles single, double, triple, aromatic, wedge, and hash (dash) bonds.
Extracted from mol_viewer_2d.py as a pure refactor (no behavior change).
"""

import math
from src.shared.qt_compat import Qt, QPointF
from src.shared.qt_compat import QPainter, QPen, QBrush, QPainterPath


class BondRenderer2D:
    """Stateless helper that draws bonds on a QPainter.

    All rendering parameters are read from the *viewer* reference
    passed at construction time, so the renderer always stays in
    sync with the viewer's zoom / style settings.
    """

    def __init__(self, viewer):
        self._v = viewer  # MolViewer2D instance

    # ─── Public entry point ───────────────────────────────────────

    def draw_all_bonds(self, painter, visible, has_label):
        """Draw every bond whose both endpoints are in *visible*."""
        v = self._v
        bond_color = v._bond_color()
        bw = v._bond_width()

        for bond in v.molecule.bonds:
            i, j = bond.begin_atom_idx, bond.end_atom_idx
            if i not in visible or j not in visible:
                continue
            if i not in v.coords_2d or j not in v.coords_2d:
                continue

            x1, y1 = v._to_screen(*v.coords_2d[i])
            x2, y2 = v._to_screen(*v.coords_2d[j])

            # Shrink towards labelled atoms
            dx, dy = x2 - x1, y2 - y1
            dist = math.hypot(dx, dy)
            if dist < 1:
                continue
            nx, ny = dx / dist, dy / dist

            # Shrink amount based on font metrics
            shrink1 = self._label_shrink(i, has_label)
            shrink2 = self._label_shrink(j, has_label)

            if dist > (shrink1 + shrink2 + 4):
                x1 += nx * shrink1
                y1 += ny * shrink1
                x2 -= nx * shrink2
                y2 -= ny * shrink2
                dx, dy = x2 - x1, y2 - y1
                dist = math.hypot(dx, dy)

            order = bond.order
            if bond.is_aromatic:
                order = 1.5

            if order == 2.0 or bond.is_double:
                self._draw_double(painter, x1, y1, x2, y2, bond_color, bw, bond)
            elif order == 3.0 or bond.is_triple:
                self._draw_triple(painter, x1, y1, x2, y2, bond_color, bw)
            elif order == 1.5:
                self._draw_aromatic(painter, x1, y1, x2, y2, bond_color, bw, bond)
            else:
                self._draw_single(painter, x1, y1, x2, y2, bond_color, bw, bond)

    # ─── Label shrink helper ──────────────────────────────────────

    def _label_shrink(self, idx, has_label):
        """Compute how much to shrink bonds near labeled atoms."""
        v = self._v
        if not has_label.get(idx, False):
            return 0
        atom = v.molecule.atoms[idx]
        label = v._atom_renderer._build_label(atom)
        font = v._atom_renderer._get_font()
        from src.shared.qt_compat import QFontMetrics
        fm = QFontMetrics(font)
        w = fm.horizontalAdvance(label)
        return (w / 2) + v._label_padding

    # ─── Single bond ──────────────────────────────────────────────

    def _draw_single(self, painter, x1, y1, x2, y2, color, width, bond=None):
        """Single bond — with wedge/hash stereochemistry support."""
        if bond and hasattr(bond, 'stereo'):
            if bond.stereo == 'up':
                self._draw_wedge(painter, x1, y1, x2, y2, color, width)
                return
            elif bond.stereo == 'down':
                self._draw_hash(painter, x1, y1, x2, y2, color, width)
                return

        pen = QPen(color, width, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    # ─── Wedge bond ───────────────────────────────────────────────

    def _draw_wedge(self, painter, x1, y1, x2, y2, color, width):
        """Draw wedge bond (solid triangle) for stereochemistry."""
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 2:
            return

        nx, ny = -dy / dist, dx / dist
        wedge_width = self._v._scale * self._v._wedge_width_ratio

        p1 = QPointF(x1, y1)
        p2 = QPointF(x1 - nx * wedge_width, y1 - ny * wedge_width)
        p3 = QPointF(x1 + nx * wedge_width, y1 + ny * wedge_width)

        path = QPainterPath()
        path.moveTo(p1)
        path.lineTo(p2)
        path.lineTo(p3)
        path.closeSubpath()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPath(path)

        pen = QPen(color, width * 0.5, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    # ─── Hash bond ────────────────────────────────────────────────

    def _draw_hash(self, painter, x1, y1, x2, y2, color, width):
        """Draw hash bond (parallel lines) for stereochemistry."""
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 2:
            return

        nx, ny = -dy / dist, dx / dist
        hash_width = self._v._scale * self._v._wedge_width_ratio

        pen = QPen(color, width * 0.5, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        for i in range(1, 6):
            t = i / 6.0
            hx = x1 + dx * t
            hy = y1 + dy * t
            h1x = hx - nx * hash_width
            h1y = hy - ny * hash_width
            h2x = hx + nx * hash_width
            h2y = hy + ny * hash_width
            painter.drawLine(QPointF(h1x, h1y), QPointF(h2x, h2y))

    # ─── Double bond ──────────────────────────────────────────────

    def _draw_double(self, painter, x1, y1, x2, y2, color, width, bond=None):
        """ChemDraw-style double bond: one full line + one inner shorter line."""
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 2:
            return
        ux, uy = dx / dist, dy / dist
        nx, ny = -uy, ux
        offset = self._v._scale * self._v._double_offset_ratio

        side = self._double_bond_side(bond, x1, y1, x2, y2, nx, ny)
        onx, ony = nx * offset * side, ny * offset * side

        pen_main = QPen(color, width, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_main)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        shrink = 0.18
        ix1 = x1 + dx * shrink + onx
        iy1 = y1 + dy * shrink + ony
        ix2 = x2 - dx * shrink + onx
        iy2 = y2 - dy * shrink + ony

        pen_inner = QPen(color, width * 0.85, Qt.PenStyle.SolidLine,
                         Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_inner)
        painter.drawLine(QPointF(ix1, iy1), QPointF(ix2, iy2))

    # ─── Triple bond ──────────────────────────────────────────────

    def _draw_triple(self, painter, x1, y1, x2, y2, color, width):
        """Triple bond: one center line + two offset lines."""
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 2:
            return
        ux, uy = dx / dist, dy / dist
        nx, ny = -uy, ux
        offset = self._v._scale * self._v._triple_offset_ratio

        pen = QPen(color, width * 0.8, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        for sign in (1, -1):
            ox, oy = nx * offset * sign, ny * offset * sign
            painter.drawLine(QPointF(x1 + ox, y1 + oy),
                             QPointF(x2 + ox, y2 + oy))

    # ─── Aromatic bond ────────────────────────────────────────────

    def _draw_aromatic(self, painter, x1, y1, x2, y2, color, width, bond=None):
        """Aromatic bond: solid + dashed inner line."""
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 2:
            return
        ux, uy = dx / dist, dy / dist
        nx, ny = -uy, ux
        offset = self._v._scale * self._v._double_offset_ratio

        side = self._double_bond_side(bond, x1, y1, x2, y2, nx, ny)
        onx, ony = nx * offset * side, ny * offset * side

        pen_main = QPen(color, width, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_main)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        shrink = 0.18
        ix1 = x1 + dx * shrink + onx
        iy1 = y1 + dy * shrink + ony
        ix2 = x2 - dx * shrink + onx
        iy2 = y2 - dy * shrink + ony

        pen_dash = QPen(color, max(1.0, width * 0.65))
        pen_dash.setStyle(Qt.PenStyle.DashLine)
        pen_dash.setDashPattern([3.5, 2.5])
        pen_dash.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen_dash)
        painter.drawLine(QPointF(ix1, iy1), QPointF(ix2, iy2))

    # ─── Double bond side logic ───────────────────────────────────

    def _double_bond_side(self, bond, x1, y1, x2, y2, nx, ny):
        """Determine which side the inner double bond should be on.
        Prefers the side towards the ring center."""
        v = self._v
        if bond is None:
            return 1

        if hasattr(v.molecule, '_rings') and v.molecule._rings:
            target_ring = None
            min_ring_size = 999

            for ring in v.molecule._rings:
                if bond.begin_atom_idx in ring and bond.end_atom_idx in ring:
                    if len(ring) < min_ring_size:
                        min_ring_size = len(ring)
                        target_ring = ring

            if target_ring:
                cx_r = sum(v.coords_2d.get(r, (0, 0))[0] for r in target_ring) / len(target_ring)
                cy_r = sum(v.coords_2d.get(r, (0, 0))[1] for r in target_ring) / len(target_ring)
                cx_s, cy_s = v._to_screen(cx_r, cy_r)
                mx = (x1 + x2) / 2
                my = (y1 + y2) / 2
                dot = (cx_s - mx) * nx + (cy_s - my) * ny
                return 1 if dot > 0 else -1

        return 1
