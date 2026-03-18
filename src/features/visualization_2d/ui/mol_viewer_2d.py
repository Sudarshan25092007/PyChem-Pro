"""
2D Molecular Viewer — ChemDraw-quality skeletal formula renderer.

Renders molecules in publication-quality 2D skeletal notation using QPainter.
Uses CoordinateGenerator2D for layout.

ChemDraw-like aesthetics:
- Clean black bonds on white/dark background
- Proper bond width proportions relative to bond length
- Double bond inner line with proper spacing
- Triple bond with even triple lines
- Wedge and hash bonds for stereochemistry
- Heteroatom labels in element-specific colors
- Implicit H notation with subscript counts
- Background clearing behind labels
- Proper skeletal formula (C vertices hidden)
- Hydrogen toggle support
- Selection highlighting
"""

import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QFontMetrics,
    QImage, QPainterPath, QPolygonF
)
from src.shared.ui.theme import COLORS


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


class MolViewer2D(QWidget):
    """
    Publication-quality 2D skeletal formula viewer.
    Mimics the aesthetic of ChemDraw / RDKit depiction.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.molecule = None
        self.coords_2d = {}
        self.selected_atoms = set()
        self.setMinimumSize(400, 400)

        # Display settings
        self.bg_color = QColor(COLORS['viewer_bg'])
        self._scale = 40.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self.show_hydrogens = False  # ChemDraw default: hide H
        self.show_all_labels = False
        self.show_protein_placeholder = False  # For large proteins

        # Rendering quality tuning (relative to bond length)
        self._bond_width_ratio = 0.028     # Bond line width / bond pixel length
        self._double_offset_ratio = 0.15   # Offset for inner double bond line
        self._triple_offset_ratio = 0.18   # Offset for triple bond lines
        self._label_padding = 4            # px padding around labels
        self._wedge_width_ratio = 0.12     # Half-width of wedge tip

        # Mouse
        self._last_mouse_pos = None
        self._mouse_button = None
        self._is_dark_bg = True

    def set_molecule(self, molecule, coords_2d=None):
        self.molecule = molecule
        self.selected_atoms = set()

        if coords_2d:
            self.coords_2d = coords_2d
        elif molecule and molecule.atoms:
            from src.features.layout_2d.generators.coordgen2d import CoordinateGenerator2D
            self.coords_2d = CoordinateGenerator2D(molecule).generate()
        else:
            self.coords_2d = {}

        self._auto_fit()
        self.update()

    def clear(self):
        self.molecule = None
        self.coords_2d = {}
        self.selected_atoms = set()
        self.update()

    def set_selected(self, atom_indices):
        self.selected_atoms = set(atom_indices)
        self.update()

    # ─── Rendering ────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        self._render(painter, self.width(), self.height())
        painter.end()

    def _render(self, painter, width, height, is_export=False):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        self._is_dark_bg = (self.bg_color.lightnessF() < 0.4)
        painter.fillRect(0, 0, width, height, self.bg_color)

        # Show placeholder for large proteins instead of trying to generate 2D
        if self.show_protein_placeholder and self.molecule:
            self._draw_protein_placeholder(painter, width, height)
            return

        if not self.molecule or not self.coords_2d:
            if not is_export:
                self._draw_placeholder(painter, width, height)
            return

        visible = self._get_visible_atoms()
        has_label = self._compute_labels(visible)

        # Layer 1: Bonds
        self._draw_all_bonds(painter, visible, has_label)

        # Layer 2: Atom labels
        self._draw_all_labels(painter, visible, has_label)

        # Layer 3: Selection
        if self.selected_atoms:
            self._draw_selection(painter, visible)

        if not is_export:
            self._draw_overlay(painter)

    def _get_visible_atoms(self):
        """Return set of atom indices that should be rendered."""
        if not self.molecule:
            return set()
        visible = set()
        for atom in self.molecule.atoms:
            if atom.index not in self.coords_2d:
                continue
            if atom.symbol == 'H' and not self.show_hydrogens:
                # Hide implicit H — but show explicit H on heteroatoms
                neighbors = list(self.molecule.get_neighbors(atom.index))
                if len(neighbors) == 1:
                    parent = self.molecule.atoms[neighbors[0]]
                    if parent.symbol == 'C':
                        continue  # Hide H bonded to carbon
                    # Check if this H is explicit (in bracket) or was added
                    # For non-carbon parents, show H only if show_hydrogens is on
                    continue
            visible.add(atom.index)
        return visible

    def _compute_labels(self, visible):
        """Decide which atoms get text labels."""
        has_label = {}
        for idx in visible:
            atom = self.molecule.atoms[idx]
            if self.show_all_labels:
                has_label[idx] = True
            elif atom.symbol == 'H':
                has_label[idx] = True  # Always label visible H
            elif atom.symbol == 'C' and atom.formal_charge == 0:
                # Skeletal: hide C labels unless terminal or charged
                degree = sum(1 for n in self.molecule.get_neighbors(idx) if n in visible)
                has_label[idx] = (degree <= 1)
            else:
                has_label[idx] = True  # All heteroatoms get labels
        return has_label

    def _to_screen(self, mx, my):
        sx = mx * self._scale + self._offset_x
        sy = -my * self._scale + self._offset_y
        return sx, sy

    def _bond_color(self):
        return QColor(220, 225, 233) if self._is_dark_bg else QColor(30, 30, 35)

    def _bond_width(self):
        return max(1.5, self._scale * self._bond_width_ratio)

    # ─── Bond Drawing ─────────────────────────────────────────────

    def _draw_all_bonds(self, painter, visible, has_label):
        bond_color = self._bond_color()
        bw = self._bond_width()

        for bond in self.molecule.bonds:
            i, j = bond.begin_atom_idx, bond.end_atom_idx
            if i not in visible or j not in visible:
                continue
            if i not in self.coords_2d or j not in self.coords_2d:
                continue

            x1, y1 = self._to_screen(*self.coords_2d[i])
            x2, y2 = self._to_screen(*self.coords_2d[j])

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
                self._draw_aromatic(painter, x1, y1, x2, y2, bond_color, bw)
            else:
                self._draw_single(painter, x1, y1, x2, y2, bond_color, bw, bond)

    def _label_shrink(self, idx, has_label):
        """Compute how much to shrink bonds near labeled atoms."""
        if not has_label.get(idx, False):
            return 0
        atom = self.molecule.atoms[idx]
        label = self._build_label(atom)
        font = self._get_font()
        fm = QFontMetrics(font)
        w = fm.horizontalAdvance(label)
        return (w / 2) + self._label_padding

    def _draw_single(self, painter, x1, y1, x2, y2, color, width, bond=None):
        """Draw a single bond — optionally as wedge/dash."""
        pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_double(self, painter, x1, y1, x2, y2, color, width, bond=None):
        """ChemDraw-style double bond: one full line + one inner shorter line."""
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 2:
            return
        ux, uy = dx / dist, dy / dist
        # Normal perpendicular
        nx, ny = -uy, ux
        offset = self._scale * self._double_offset_ratio

        # Decide which side for inner bond (prefer ring interior)
        side = self._double_bond_side(bond, x1, y1, x2, y2, nx, ny)
        onx, ony = nx * offset * side, ny * offset * side

        pen_main = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        pen_inner = QPen(color, width * 0.75, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)

        # Main bond (full length)
        painter.setPen(pen_main)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Inner bond (shortened ~18% each end)
        shrink = 0.18
        ix1 = x1 + dx * shrink + onx
        iy1 = y1 + dy * shrink + ony
        ix2 = x2 - dx * shrink + onx
        iy2 = y2 - dy * shrink + ony

        painter.setPen(pen_inner)
        painter.drawLine(QPointF(ix1, iy1), QPointF(ix2, iy2))

    def _draw_triple(self, painter, x1, y1, x2, y2, color, width):
        """Triple bond: three parallel lines."""
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 2:
            return
        nx, ny = -dy / dist, dx / dist
        offset = self._scale * self._triple_offset_ratio

        pen = QPen(color, width * 0.75, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        painter.drawLine(
            QPointF(x1 + nx * offset, y1 + ny * offset),
            QPointF(x2 + nx * offset, y2 + ny * offset))
        painter.drawLine(
            QPointF(x1 - nx * offset, y1 - ny * offset),
            QPointF(x2 - nx * offset, y2 - ny * offset))

    def _draw_aromatic(self, painter, x1, y1, x2, y2, color, width):
        """Aromatic bond: solid + dashed inner line."""
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 2:
            return
        nx, ny = -dy / dist, dx / dist
        offset = self._scale * self._double_offset_ratio

        pen_main = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_main)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Dashed inner bond
        shrink = 0.18
        ix1 = x1 + dx * shrink + nx * offset
        iy1 = y1 + dy * shrink + ny * offset
        ix2 = x2 - dx * shrink + nx * offset
        iy2 = y2 - dy * shrink + ny * offset

        pen_dash = QPen(color, width * 0.65)
        pen_dash.setStyle(Qt.PenStyle.DashLine)
        pen_dash.setDashPattern([3.5, 2.5])
        pen_dash.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen_dash)
        painter.drawLine(QPointF(ix1, iy1), QPointF(ix2, iy2))

    def _double_bond_side(self, bond, x1, y1, x2, y2, nx, ny):
        """Determine which side the inner double bond should be on.
        Prefers the side towards the ring center."""
        if bond is None:
            return 1

        # If both atoms in a ring, put inner bond towards ring center
        a1 = self.molecule.atoms[bond.begin_atom_idx]
        a2 = self.molecule.atoms[bond.end_atom_idx]

        if hasattr(self.molecule, '_rings') and self.molecule._rings:
            for ring in self.molecule._rings:
                if bond.begin_atom_idx in ring and bond.end_atom_idx in ring:
                    # Compute ring center
                    cx_r = sum(self.coords_2d.get(r, (0, 0))[0] for r in ring) / len(ring)
                    cy_r = sum(self.coords_2d.get(r, (0, 0))[1] for r in ring) / len(ring)
                    cx_s, cy_s = self._to_screen(cx_r, cy_r)
                    mx = (x1 + x2) / 2
                    my = (y1 + y2) / 2
                    # Dot product to determine side
                    dot = (cx_s - mx) * nx + (cy_s - my) * ny
                    return 1 if dot > 0 else -1

        return 1

    # ─── Label Drawing ────────────────────────────────────────────

    def _get_font(self):
        size = max(10, int(self._scale * 0.35))
        font = QFont('Arial', size)
        font.setWeight(QFont.Weight.DemiBold)  # Slightly bolder like ChemDraw
        return font

    def _get_subscript_font(self):
        size = max(7, int(self._scale * 0.24))
        font = QFont('Arial', size)
        font.setWeight(QFont.Weight.DemiBold)
        return font

    def _draw_all_labels(self, painter, visible, has_label):
        font = self._get_font()
        sub_font = self._get_subscript_font()
        fm = QFontMetrics(font)
        fm_sub = QFontMetrics(sub_font)

        for idx in visible:
            if not has_label.get(idx, False):
                continue
            atom = self.molecule.atoms[idx]
            mx, my = self.coords_2d[idx]
            sx, sy = self._to_screen(mx, my)

            parts = self._label_parts(atom)
            color = self._element_color(atom.symbol)

            # Measure total width
            total_w = 0
            for text, is_sub in parts:
                f = sub_font if is_sub else font
                m = fm_sub if is_sub else fm
                total_w += m.horizontalAdvance(text)

            h = fm.height()

            # Background clearing rectangle (covers bonds behind label)
            pad = self._label_padding + 1
            bg_rect = QRectF(sx - total_w / 2 - pad, sy - h / 2 - 2, total_w + pad * 2, h + 4)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self.bg_color))
            painter.drawRect(bg_rect)

            # Draw label parts
            cx = sx - total_w / 2
            for text, is_sub in parts:
                f = sub_font if is_sub else font
                m = fm_sub if is_sub else fm
                tw = m.horizontalAdvance(text)

                painter.setFont(f)
                painter.setPen(color)

                if is_sub:
                    # Subscript: drop baseline
                    painter.drawText(QPointF(cx, sy + h * 0.35), text)
                else:
                    painter.drawText(QPointF(cx, sy + h * 0.3), text)
                cx += tw

    def _label_parts(self, atom):
        """Return list of (text, is_subscript) for the atom label."""
        parts = [(atom.symbol, False)]
        h_count = atom.num_implicit_h

        if self.show_hydrogens or atom.symbol != 'C':
            if h_count == 1:
                parts.append(('H', False))
            elif h_count > 1:
                parts.append(('H', False))
                parts.append((str(h_count), True))

        if atom.formal_charge > 0:
            ch = '+' if atom.formal_charge == 1 else f'+{atom.formal_charge}'
            parts.append((ch, True))
        elif atom.formal_charge < 0:
            ch = '-' if atom.formal_charge == -1 else str(atom.formal_charge)
            parts.append((ch, True))

        return parts

    def _build_label(self, atom):
        """Simple flat label for shrink calculations."""
        label = atom.symbol
        h_count = atom.num_implicit_h
        if self.show_hydrogens or atom.symbol != 'C':
            if h_count == 1:
                label += 'H'
            elif h_count > 1:
                label += f'H{h_count}'
        if atom.formal_charge > 0:
            label += '+' if atom.formal_charge == 1 else f'+{atom.formal_charge}'
        elif atom.formal_charge < 0:
            label += '-' if atom.formal_charge == -1 else str(atom.formal_charge)
        return label

    def _element_color(self, symbol):
        palette = ELEMENT_COLORS if self._is_dark_bg else ELEMENT_COLORS_LIGHT
        return palette.get(symbol, QColor(200, 200, 200) if self._is_dark_bg else QColor(30, 30, 30))

    # ─── Selection ────────────────────────────────────────────────

    def _draw_selection(self, painter, visible):
        for idx in self.selected_atoms:
            if idx not in visible or idx not in self.coords_2d:
                continue
            mx, my = self.coords_2d[idx]
            sx, sy = self._to_screen(mx, my)
            r = self._scale * 0.28

            # Outer glow
            pen = QPen(QColor(255, 200, 50, 140), max(2.5, self._scale * 0.045))
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(255, 200, 50, 35)))
            painter.drawEllipse(QPointF(sx, sy), r, r)

    # ─── Overlay ──────────────────────────────────────────────────

    def _draw_overlay(self, painter):
        if not self.molecule:
            return
        font = QFont('Segoe UI', 10)
        painter.setFont(font)
        painter.setPen(QColor(COLORS['text_muted']))

        info = f"2D | {len(self.molecule.atoms)} atoms, {len(self.molecule.bonds)} bonds"
        if not self.show_hydrogens:
            info += " | H hidden"
        if self.selected_atoms:
            info += f" | {len(self.selected_atoms)} selected"
        painter.drawText(8, 18, info)

    def _draw_placeholder(self, painter, width, height):
        font = QFont('Segoe UI', 16)
        painter.setFont(font)
        painter.setPen(QColor(COLORS['text_muted']))
        painter.drawText(QRectF(0, 0, width, height), Qt.AlignmentFlag.AlignCenter,
                         "2D structure will appear here")

    # ─── Image Export ─────────────────────────────────────────────

    def export_image(self, filepath, dpi=300, bg_white=False):
        scale_factor = dpi / 96.0
        img_w = int(self.width() * scale_factor)
        img_h = int(self.height() * scale_factor)

        image = QImage(img_w, img_h, QImage.Format.Format_ARGB32_Premultiplied)
        image.setDotsPerMeterX(int(dpi / 0.0254))
        image.setDotsPerMeterY(int(dpi / 0.0254))

        orig_bg = self.bg_color
        orig_scale = self._scale
        orig_ox = self._offset_x
        orig_oy = self._offset_y

        if bg_white:
            self.bg_color = QColor(255, 255, 255)

        self._scale *= scale_factor
        self._offset_x *= scale_factor
        self._offset_y *= scale_factor

        painter = QPainter(image)
        self._render(painter, img_w, img_h, is_export=True)
        painter.end()

        self.bg_color = orig_bg
        self._scale = orig_scale
        self._offset_x = orig_ox
        self._offset_y = orig_oy

        return image.save(filepath)

    # ─── Mouse Interaction ────────────────────────────────────────

    def mousePressEvent(self, event):
        self._last_mouse_pos = event.position()
        self._mouse_button = event.button()

    def mouseMoveEvent(self, event):
        if self._last_mouse_pos is None:
            return
        dx = event.position().x() - self._last_mouse_pos.x()
        dy = event.position().y() - self._last_mouse_pos.y()

        if self._mouse_button == Qt.MouseButton.LeftButton:
            self._offset_x += dx
            self._offset_y += dy

        self._last_mouse_pos = event.position()
        self.update()

    def mouseReleaseEvent(self, event):
        self._last_mouse_pos = None
        self._mouse_button = None

    def wheelEvent(self, event):
        pos = event.position()
        delta = event.angleDelta().y()
        factor = 1.12 if delta > 0 else 1.0 / 1.12

        # Zoom towards mouse cursor
        old_mx = (pos.x() - self._offset_x) / self._scale
        old_my = -(pos.y() - self._offset_y) / self._scale

        self._scale *= factor
        self._scale = max(10, min(250, self._scale))

        self._offset_x = pos.x() - old_mx * self._scale
        self._offset_y = pos.y() + old_my * self._scale

        self.update()

    # ─── Utils ────────────────────────────────────────────────────

    def _auto_fit(self):
        if not self.coords_2d:
            return

        # Filter to visible atoms
        visible = self._get_visible_atoms() if self.molecule else set(self.coords_2d.keys())
        if not visible:
            visible = set(self.coords_2d.keys())

        visible_coords = {k: v for k, v in self.coords_2d.items() if k in visible}
        if not visible_coords:
            return

        xs = [c[0] for c in visible_coords.values()]
        ys = [c[1] for c in visible_coords.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max_x - min_x or 1
        span_y = max_y - min_y or 1
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2

        w = self.width() or 600
        h = self.height() or 500
        margin = 70

        scale_x = (w - margin * 2) / span_x
        scale_y = (h - margin * 2) / span_y
        self._scale = min(scale_x, scale_y, 120)
        self._offset_x = w / 2 - cx * self._scale
        self._offset_y = h / 2 + cy * self._scale

    def _draw_protein_placeholder(self, painter, width, height):
        """Draw placeholder for large proteins instead of generating 2D coordinates."""
        # Set up font
        font = QFont('Segoe UI', 14)
        painter.setFont(font)
        
        # Draw protein icon representation
        cx, cy = width / 2, height / 2
        
        # Draw simplified protein representation
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        
        # Draw a simple helix representation
        helix_width = 60
        helix_height = 120
        helix_x = cx - helix_width / 2
        helix_y = cy - helix_height / 2
        
        # Draw helix as a spiral
        for i in range(20):
            y = helix_y + i * (helix_height / 20)
            x_offset = 15 * math.sin(i * 0.5)
            painter.drawEllipse(QPointF(helix_x + helix_width/2 + x_offset, y), 3, 3)
        
        # Draw sheet representation
        sheet_x = cx + 40
        sheet_y = cy - 40
        arrow_points = [
            QPointF(sheet_x, sheet_y),
            QPointF(sheet_x + 40, sheet_y + 20),
            QPointF(sheet_x + 40, sheet_y + 10),
            QPointF(sheet_x + 50, sheet_y + 15),
            QPointF(sheet_x + 40, sheet_y + 20),
            QPointF(sheet_x + 40, sheet_y + 30),
            QPointF(sheet_x, sheet_y + 10)
        ]
        painter.setBrush(QBrush(QColor(50, 150, 220, 100)))
        painter.drawPolygon(QPolygonF(arrow_points))
        
        # Draw text information
        painter.setPen(QColor(60, 60, 60))
        title_font = QFont('Segoe UI', 16, QFont.Weight.Bold)
        painter.setFont(title_font)
        title = "Large Protein Structure"
        title_rect = QRectF(0, cy - 180, width, 30)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, title)
        
        # Draw stats
        info_font = QFont('Segoe UI', 12)
        painter.setFont(info_font)
        painter.setPen(QColor(80, 80, 80))
        
        num_atoms = len(self.molecule.atoms) if self.molecule else 0
        num_residues = len(set((a.res_seq, a.chain_id) for a in self.molecule.atoms 
                              if hasattr(a, 'res_seq') and hasattr(a, 'chain_id'))) if self.molecule else 0
        
        info_lines = [
            f"Atoms: {num_atoms:,}",
            f"Residues: {num_residues:,}",
            "",
            "2D representation skipped for performance",
            "Use 3D viewer for protein visualization"
        ]
        
        y_offset = cy + 80
        for line in info_lines:
            if line:
                rect = QRectF(0, y_offset, width, 25)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, line)
            y_offset += 25
        
        # Draw border
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(10, 10, width - 20, height - 20)
