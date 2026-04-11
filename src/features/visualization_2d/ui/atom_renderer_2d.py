"""
2D Atom Renderer — ChemDraw-quality atom labels, charges, and coloring.

Handles atom symbols, implicit hydrogen display, element-specific coloring,
formal charge notation, and direction-aware H placement.
Extracted from mol_viewer_2d.py as a pure refactor (no behavior change).
"""

import math
from src.shared.qt_compat import Qt, QPointF, QRectF
from src.shared.qt_compat import (
    QPainter, QColor, QPen, QBrush, QFont, QFontMetrics,
)


# ── ChemDraw-style element colors ────────────────────────────────
# Against dark bg: brighter; against white bg: standard ChemDraw colors
ELEMENT_COLORS = {
    'C':  QColor(220, 220, 220),   # Near-white (hidden in skeletal)
    'H':  QColor(170, 170, 180),   # Light gray
    'N':  QColor(48, 128, 255),    # Vivid blue
    'O':  QColor(255, 50, 50),     # Vivid red
    'S':  QColor(230, 195, 50),    # Gold-yellow
    'P':  QColor(255, 140, 30),    # Warm orange
    'F':  QColor(80, 210, 80),     # Bright green
    'Cl': QColor(80, 210, 80),     # Green
    'Br': QColor(180, 80, 40),     # Dark orange-brown
    'I':  QColor(170, 50, 170),    # Purple
    'B':  QColor(255, 180, 160),   # Salmon
    'Se': QColor(255, 160, 0),     # Orange
    'Si': QColor(200, 180, 140),   # Tan
}

# Against white (export) background
ELEMENT_COLORS_LIGHT = {
    'C':  QColor(30, 30, 30),
    'H':  QColor(80, 80, 80),
    'N':  QColor(10, 50, 220),
    'O':  QColor(220, 20, 20),
    'S':  QColor(180, 150, 0),
    'P':  QColor(220, 100, 0),
    'F':  QColor(0, 160, 0),
    'Cl': QColor(0, 160, 0),
    'Br': QColor(150, 60, 20),
    'I':  QColor(130, 0, 130),
    'B':  QColor(200, 130, 100),
    'Se': QColor(200, 120, 0),
    'Si': QColor(150, 130, 90),
}


class AtomRenderer2D:
    """Stateless helper that draws atom labels on a QPainter.

    All rendering parameters are read from the *viewer* reference
    passed at construction time, so the renderer always stays in
    sync with the viewer's zoom / style settings.
    """

    def __init__(self, viewer):
        self._v = viewer  # MolViewer2D instance

    # ─── Fonts ────────────────────────────────────────────────────

    def _get_font(self):
        """Get the main atom label font, scaled properly for display and export."""
        v = self._v
        base_scale = v._original_scale if v._original_scale is not None else v._scale
        size = max(10, int(base_scale * 0.35))
        if v._original_scale is not None:
            size = min(size, 14)
        font = QFont('Arial', size)
        font.setWeight(QFont.Weight.DemiBold)
        return font

    def _get_subscript_font(self):
        """Get the subscript font (H count, charges), scaled properly."""
        v = self._v
        base_scale = v._original_scale if v._original_scale is not None else v._scale
        size = max(6, int(base_scale * 0.20))
        if v._original_scale is not None:
            size = min(size, 10)
        font = QFont('Arial', size)
        font.setWeight(QFont.Weight.DemiBold)
        return font

    # ─── Direction-aware H placement (ChemDraw-style) ─────────────

    def _get_h_placement_side(self, atom_idx, visible):
        """
        Determine whether H labels should be placed to the LEFT or RIGHT
        of the heteroatom symbol, based on the average direction of bonds.

        Returns:
            'right' -- H goes after the atom symbol (default: OH, NH)
            'left'  -- H goes before the atom symbol (HO, HN)
        """
        v = self._v
        if atom_idx not in v.coords_2d:
            return 'right'

        ax, ay = v.coords_2d[atom_idx]
        neighbors = v.molecule.get_neighbors(atom_idx)
        visible_neighbors = [n for n in neighbors if n in visible and n in v.coords_2d]

        if not visible_neighbors:
            return 'right'

        sum_dx = 0.0
        for n_idx in visible_neighbors:
            nx, ny = v.coords_2d[n_idx]
            sum_dx += (nx - ax)

        if sum_dx > 0.05:
            return 'left'
        else:
            return 'right'

    # ─── Draw all labels ──────────────────────────────────────────

    def draw_all_labels(self, painter, visible, has_label):
        v = self._v
        font = self._get_font()
        sub_font = self._get_subscript_font()
        fm = QFontMetrics(font)
        fm_sub = QFontMetrics(sub_font)

        char_gap = max(4, int(v._scale * 0.12))
        sub_gap = max(2, int(v._scale * 0.04))

        for idx in visible:
            if not has_label.get(idx, False):
                continue
            atom = v.molecule.atoms[idx]
            mx, my = v.coords_2d[idx]
            sx, sy = v._to_screen(mx, my)

            h_side = self._get_h_placement_side(idx, visible)
            parts = self._label_parts(atom, h_side)
            color = self._element_color(atom.symbol)

            total_w = 0
            for i, (text, is_sub) in enumerate(parts):
                m = fm_sub if is_sub else fm
                total_w += m.horizontalAdvance(text)
                if i > 0:
                    if is_sub:
                        total_w += sub_gap
                    elif not parts[i-1][1]:
                        total_w += char_gap

            h = fm.height()

            pad = v._label_padding + 1
            bg_rect = QRectF(sx - total_w / 2 - pad, sy - h / 2 - 2,
                             total_w + pad * 2, h + 4)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(v.bg_color))
            painter.drawRect(bg_rect)

            cx = sx - total_w / 2
            baseline_offset = (fm.ascent() - fm.descent()) / 2

            for i, (text, is_sub) in enumerate(parts):
                f = sub_font if is_sub else font
                m = fm_sub if is_sub else fm
                tw = m.horizontalAdvance(text)

                if i > 0:
                    if is_sub:
                        cx += sub_gap
                    elif not parts[i-1][1]:
                        cx += char_gap

                painter.setFont(f)
                painter.setPen(color)

                if is_sub:
                    sub_baseline = (fm_sub.ascent() - fm_sub.descent()) / 2
                    painter.drawText(
                        QPointF(cx, sy + sub_baseline + fm.descent() + 2), text)
                else:
                    painter.drawText(QPointF(cx, sy + baseline_offset), text)
                cx += tw

        # Draw explicit H atoms for heteroatoms AFTER all labels
        self._draw_explicit_h_atoms(painter, visible, has_label, font, fm)

    # ─── Explicit H atoms ─────────────────────────────────────────

    def _draw_explicit_h_atoms(self, painter, visible, has_label, font, fm):
        """Draw explicit hydrogen atoms as separate vertices with short bonds
        for heteroatoms (N, O, S, P, etc.)."""
        v = self._v
        h_color = self._element_color('H')
        bond_color = v._bond_color()
        bw = v._bond_width()
        h = fm.height()
        baseline_offset = (fm.ascent() - fm.descent()) / 2

        h_bond_len = v._scale * 0.45

        for idx in visible:
            if not has_label.get(idx, False):
                continue
            atom = v.molecule.atoms[idx]

            if atom.symbol == 'C' or atom.symbol == 'H':
                continue

            h_count = self._get_total_h_count(atom)
            if h_count == 0:
                continue

            mx, my = v.coords_2d[idx]
            sx, sy = v._to_screen(mx, my)

            label_half_w = fm.horizontalAdvance(atom.symbol) / 2 + v._label_padding

            h_positions = self._compute_h_positions(idx, visible, h_count, h_bond_len)

            for h_pos_x, h_pos_y in h_positions:
                dx = h_pos_x - sx
                dy = h_pos_y - sy
                dist = math.hypot(dx, dy)
                if dist < 1:
                    continue

                bond_start_x = sx + (dx / dist) * label_half_w
                bond_start_y = sy + (dy / dist) * label_half_w

                h_tw = fm.horizontalAdvance('H')
                h_label_half = h_tw / 2 + v._label_padding
                bond_end_x = h_pos_x - (dx / dist) * h_label_half
                bond_end_y = h_pos_y - (dy / dist) * h_label_half

                pen = QPen(bond_color, bw * 0.8, Qt.PenStyle.SolidLine,
                           Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawLine(QPointF(bond_start_x, bond_start_y),
                                 QPointF(bond_end_x, bond_end_y))

                h_label = 'H'
                tw = fm.horizontalAdvance(h_label)
                pad = v._label_padding
                bg_rect = QRectF(h_pos_x - tw / 2 - pad, h_pos_y - h / 2 - 2,
                                 tw + pad * 2, h + 4)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(v.bg_color))
                painter.drawRect(bg_rect)

                painter.setFont(font)
                painter.setPen(h_color)
                painter.drawText(
                    QPointF(h_pos_x - tw / 2, h_pos_y + baseline_offset), h_label)

    # ─── H position computation ───────────────────────────────────

    def _compute_h_positions(self, atom_idx, visible, h_count, h_bond_len):
        """Compute screen positions for explicit H atoms around a heteroatom."""
        v = self._v
        ax, ay = v.coords_2d[atom_idx]
        sx, sy = v._to_screen(ax, ay)

        neighbors = v.molecule.get_neighbors(atom_idx)
        visible_neighbors = [n for n in neighbors if n in visible and n in v.coords_2d]

        bond_angles = []
        for n_idx in visible_neighbors:
            nx, ny = v.coords_2d[n_idx]
            nsx, nsy = v._to_screen(nx, ny)
            angle = math.atan2(nsy - sy, nsx - sx)
            bond_angles.append(angle)

        positions = []

        if not bond_angles:
            positions.append((sx, sy + h_bond_len))
        elif len(bond_angles) == 1:
            base_angle = bond_angles[0] + math.pi
            if h_count == 1:
                positions.append((sx + h_bond_len * math.cos(base_angle),
                                  sy + h_bond_len * math.sin(base_angle)))
            elif h_count == 2:
                for offset in (-math.pi / 3, math.pi / 3):
                    a = base_angle + offset
                    positions.append((sx + h_bond_len * math.cos(a),
                                      sy + h_bond_len * math.sin(a)))
            else:
                for i in range(h_count):
                    a = base_angle + (i - (h_count - 1) / 2) * (math.pi / 3)
                    positions.append((sx + h_bond_len * math.cos(a),
                                      sy + h_bond_len * math.sin(a)))
        else:
            bond_angles.sort()
            gaps = []
            for i in range(len(bond_angles)):
                a1 = bond_angles[i]
                a2 = bond_angles[(i + 1) % len(bond_angles)]
                gap = (a2 - a1) % (2 * math.pi)
                gaps.append((gap, a1))

            gaps.sort(key=lambda g: g[0], reverse=True)

            placed = 0
            for gap_size, start_angle in gaps:
                if placed >= h_count:
                    break
                mid_angle = start_angle + gap_size / 2
                positions.append((sx + h_bond_len * math.cos(mid_angle),
                                  sy + h_bond_len * math.sin(mid_angle)))
                placed += 1

        return positions[:h_count]

    # ─── Hydrogen count ───────────────────────────────────────────

    def _get_total_h_count(self, atom):
        """Get total hydrogen count (implicit + explicit structural H)."""
        v = self._v
        h_count = atom.num_implicit_h
        for n_idx in v.molecule.get_neighbors(atom.index):
            if v.molecule.atoms[n_idx].symbol == 'H':
                h_count += 1
        return h_count

    # ─── Label parts ──────────────────────────────────────────────

    def _label_parts(self, atom, h_side='right'):
        """Return list of (text, is_subscript) for the atom label.

        For heteroatoms: returns ONLY the atom symbol (H drawn as explicit vertices).
        For carbon atoms: returns the full label with H count (CH3, CH2, etc.).
        """
        h_count = self._get_total_h_count(atom)

        if atom.symbol != 'C' and atom.symbol != 'H':
            parts = [(atom.symbol, False)]
            if atom.formal_charge > 0:
                ch = '+' if atom.formal_charge == 1 else f'+{atom.formal_charge}'
                parts.append((ch, True))
            elif atom.formal_charge < 0:
                ch = '-' if atom.formal_charge == -1 else str(atom.formal_charge)
                parts.append((ch, True))
            return parts

        h_parts = []
        if h_count == 1:
            h_parts.append(('H', False))
        elif h_count > 1:
            h_parts.append(('H', False))
            h_parts.append((str(h_count), True))

        charge_parts = []
        if atom.formal_charge > 0:
            ch = '+' if atom.formal_charge == 1 else f'+{atom.formal_charge}'
            charge_parts.append((ch, True))
        elif atom.formal_charge < 0:
            ch = '-' if atom.formal_charge == -1 else str(atom.formal_charge)
            charge_parts.append((ch, True))

        symbol_part = (atom.symbol, False)
        if h_side == 'left' and h_parts:
            parts = h_parts + [symbol_part] + charge_parts
        else:
            parts = [symbol_part] + h_parts + charge_parts

        return parts

    def _build_label(self, atom):
        """Simple flat label for shrink calculations."""
        v = self._v
        label = atom.symbol
        h_count = atom.num_implicit_h

        for n_idx in v.molecule.get_neighbors(atom.index):
            if v.molecule.atoms[n_idx].symbol == 'H':
                h_count += 1

        if h_count == 1:
            label += 'H'
        elif h_count > 1:
            label += f'H{h_count}'
        if atom.formal_charge > 0:
            label += '+' if atom.formal_charge == 1 else f'+{atom.formal_charge}'
        elif atom.formal_charge < 0:
            label += '-' if atom.formal_charge == -1 else str(atom.formal_charge)
        return label

    # ─── Element color ────────────────────────────────────────────

    def _element_color(self, symbol):
        """Return the QColor for the given element symbol."""
        v = self._v
        palette = ELEMENT_COLORS if v._is_dark_bg else ELEMENT_COLORS_LIGHT
        return palette.get(
            symbol,
            QColor(200, 200, 200) if v._is_dark_bg else QColor(30, 30, 30))
