"""
3D Molecular Viewer — High-quality software-rendered molecular visualization.

Features:
- Smooth radial-gradient sphere rendering (realistic 3D look)
- Ball-and-stick / spacefill / wireframe rendering modes
- CPK coloring
- Mouse rotation, zoom, and pan
- Atom highlighting on hover
- High-DPI image export
"""

import math
import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, Signal, QPointF, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QWheelEvent,
    QRadialGradient, QLinearGradient, QImage, QConicalGradient, QPainterPath
)
from .theme import COLORS


def _hex_to_rgb(hex_color):
    """Convert hex color string to (r, g, b) tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


# Atom radii for display (scaled for visual appeal)
DISPLAY_RADIUS = {
    'H': 0.25, 'He': 0.31, 'C': 0.40, 'N': 0.38, 'O': 0.36, 'F': 0.32,
    'P': 0.44, 'S': 0.42, 'Cl': 0.39, 'Br': 0.41, 'I': 0.44, 'B': 0.38,
    'Si': 0.44, 'Se': 0.42, 'Na': 0.50, 'K': 0.55, 'Ca': 0.48, 'Fe': 0.44,
}


class MolViewer3D(QWidget):
    """
    Software-rendered 3D molecular viewer with mouse interaction.
    Uses QPainter with QRadialGradient for smooth, realistic sphere rendering.
    """

    atom_hovered = Signal(int)
    atom_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.molecule = None
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)

        # Camera state
        self.rot_x = 20.0
        self.rot_y = -30.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 40.0
        self.auto_scale = True

        # Mouse interaction
        self._last_mouse_pos = None
        self._mouse_button = None
        self._hovered_atom = -1
        self.selected_atoms = set()  # Set of atom indices to highlight

        # Measurement state
        self._measure_atoms = []   # List of picked atoms for distance/angle
        self._measurements = []    # List of completed measurements

        # Animation
        self._auto_rotate = False
        self._rotation_timer = QTimer(self)
        self._rotation_timer.timeout.connect(self._auto_rotate_step)

        # Rendering settings
        self.show_hydrogens = True
        self.show_labels = False
        self.show_sidechains = True
        self.render_mode = 'ball_and_stick'  # 'spacefill', 'wireframe', 'cartoon', 'ribbon', 'backbone'
        self.bg_color = QColor(COLORS['viewer_bg'])

        # User-adjustable radius scales (1.0 = default)
        self.sphere_scale = 1.0   # Multiplier for atom sphere radius
        self.stick_scale = 1.0    # Multiplier for bond stick width
        self.line_scale = 1.0     # Multiplier for wireframe line width
        self.label_font_size = 9  # Fixed label font size in points

        # Light direction (normalized) — top-left-front
        self._light_dir = np.array([-0.4, -0.5, 1.0])
        self._light_dir = self._light_dir / np.linalg.norm(self._light_dir)

    def set_molecule(self, molecule):
        self.molecule = molecule
        if molecule and len(molecule.atoms) > 0:
            self._auto_fit()
            # Auto-switch to cartoon for proteins
            is_protein = getattr(molecule, 'properties', {}).get('is_protein', False)
            if is_protein:
                self.render_mode = 'cartoon'
        self.update()

    def clear(self):
        self.molecule = None
        self.update()

    def toggle_auto_rotate(self):
        self._auto_rotate = not self._auto_rotate
        if self._auto_rotate:
            self._rotation_timer.start(33)
        else:
            self._rotation_timer.stop()

    def reset_view(self):
        self.rot_x = 20.0
        self.rot_y = -30.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        if self.molecule:
            self._auto_fit()
        self.update()

    # ─── Rendering ─────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        self._render(painter, self.width(), self.height())
        painter.end()

    def _render(self, painter, width, height, is_export=False, export_scale=1.0):
        """Core rendering logic — used by both paintEvent and export."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        self._export_scale = export_scale

        # Background
        painter.fillRect(0, 0, width, height, self.bg_color)

        if not self.molecule or len(self.molecule.atoms) == 0:
            if not is_export:
                self._draw_placeholder(painter, width, height)
            return

        # Project atoms
        projected = self._project_atoms(width, height)
        if not projected:
            return

        # Sort by depth (furthest first = painter's algorithm)
        sorted_atoms = sorted(projected, key=lambda x: x[3])

        # --- Protein modes ---
        if self.render_mode in ('cartoon', 'ribbon', 'backbone'):
            self._draw_protein(painter, projected, width, height)
        else:
            # Optimize rendering for large molecules
            num_atoms = len(sorted_atoms)
            use_simple_rendering = num_atoms > 500  # Use simple rendering for >500 atoms
            
            if use_simple_rendering and self.render_mode == 'ball_and_stick':
                # Fast rendering for large molecules
                self._draw_large_molecule_fast(painter, projected, sorted_atoms)
            else:
                # Draw bonds first (behind atoms)
                self._draw_bonds(painter, projected)

                # Draw atoms with smooth gradient spheres
                for atom_idx, sx, sy, sz, radius, color in sorted_atoms:
                    if use_simple_rendering:
                        self._draw_atom_simple(painter, sx, sy, radius, color)
                    else:
                        self._draw_atom_sphere(painter, atom_idx, sx, sy, sz, radius, color)

        # Draw selection highlights
        if self.selected_atoms:
            for atom_idx, sx, sy, sz, radius, color in sorted_atoms:
                if atom_idx in self.selected_atoms:
                    self._draw_selection_ring(painter, sx, sy, radius)

        # Draw labels if enabled
        if self.show_labels:
            for atom_idx, sx, sy, sz, radius, color in sorted_atoms:
                self._draw_label(painter, atom_idx, sx, sy, radius)

        # Draw measurements
        if self._measure_atoms or self._measurements:
            self._draw_measurements(painter, projected)

        # Draw info overlay (not on exports)
        if not is_export:
            self._draw_overlay(painter)
            
            # Show performance indicator for large molecules
            if len(projected) > 500:
                self._draw_performance_indicator(painter, len(projected))

    def _project_atoms(self, vp_width=None, vp_height=None):
        """Project 3D atom coordinates to 2D screen coordinates."""
        if not self.molecule:
            return []

        w = vp_width or self.width()
        h = vp_height or self.height()
        cx = w / 2 + self.pan_x
        cy = h / 2 + self.pan_y

        cos_x = math.cos(math.radians(self.rot_x))
        sin_x = math.sin(math.radians(self.rot_x))
        cos_y = math.cos(math.radians(self.rot_y))
        sin_y = math.sin(math.radians(self.rot_y))

        projected = []
        for atom in self.molecule.atoms:
            if not atom.has_coords:
                continue
            if atom.symbol == 'H' and not self.show_hydrogens:
                continue

            x, y, z = atom.x, atom.y, atom.z

            # Rotation around Y then X
            x1 = x * cos_y + z * sin_y
            z1 = -x * sin_y + z * cos_y
            y1 = y * cos_x - z1 * sin_x
            z2 = y * sin_x + z1 * cos_x

            sx = cx + x1 * self.zoom
            sy = cy - y1 * self.zoom
            sz = z2

            # Display radius with user scale
            base_r = DISPLAY_RADIUS.get(atom.symbol, 0.35)
            if self.render_mode == 'spacefill':
                base_r = atom.element.vdw_radius * 0.5
            elif self.render_mode == 'wireframe':
                base_r = 0.1
            display_r = base_r * self.zoom * self.sphere_scale

            # Depth-based size attenuation
            depth_factor = 1.0 + sz * 0.02
            display_r *= max(0.5, min(1.5, depth_factor))

            # Color from element
            color = _hex_to_rgb(atom.element.color)
            if atom.symbol == 'H':
                color = (185, 195, 210)

            projected.append((atom.index, sx, sy, sz, display_r, color))

        return projected

    def _draw_atom_sphere(self, painter, atom_idx, sx, sy, sz, radius, rgb):
        """
        Draw a single atom as a smooth, realistic sphere using QRadialGradient.
        The gradient simulates Phong-like shading:
        - Bright specular highlight (upper-left)
        - Base color in the middle
        - Dark shadow at the edges
        """
        r, g, b = rgb

        # Depth-based shading
        depth_shade = max(0.5, min(1.0, 1.0 - sz * 0.025))
        r = int(r * depth_shade)
        g = int(g * depth_shade)
        b = int(b * depth_shade)

        # Highlight hovered atom
        if atom_idx == self._hovered_atom:
            r = min(255, r + 50)
            g = min(255, g + 50)
            b = min(255, b + 50)

        # Clamp
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))

        # ── Smooth radial gradient for sphere illusion ──
        # Specular highlight position: offset towards top-left
        highlight_x = sx - radius * 0.30
        highlight_y = sy - radius * 0.30

        gradient = QRadialGradient(
            QPointF(sx, sy),        # center of the gradient circle
            radius,                  # radius of the gradient
            QPointF(highlight_x, highlight_y)  # focal point (brightest spot)
        )

        # Specular highlight — bright white-ish center
        highlight_r = min(255, r + 160)
        highlight_g = min(255, g + 160)
        highlight_b = min(255, b + 160)

        # Shadow — dark edge
        shadow_r = max(0, int(r * 0.20))
        shadow_g = max(0, int(g * 0.20))
        shadow_b = max(0, int(b * 0.20))

        # Mid tone
        mid_r = max(0, min(255, int(r * 0.85)))
        mid_g = max(0, min(255, int(g * 0.85)))
        mid_b = max(0, min(255, int(b * 0.85)))

        gradient.setColorAt(0.0, QColor(highlight_r, highlight_g, highlight_b, 255))
        gradient.setColorAt(0.25, QColor(r, g, b, 255))
        gradient.setColorAt(0.7, QColor(mid_r, mid_g, mid_b, 255))
        gradient.setColorAt(1.0, QColor(shadow_r, shadow_g, shadow_b, 255))

        # Draw sphere
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QRectF(sx - radius, sy - radius, radius * 2, radius * 2))

        # ── Extra specular dot for gloss ──
        if radius > 6:
            spec_radius = radius * 0.18
            spec_x = sx - radius * 0.28
            spec_y = sy - radius * 0.28

            spec_grad = QRadialGradient(
                QPointF(spec_x, spec_y), spec_radius,
                QPointF(spec_x, spec_y)
            )
            spec_grad.setColorAt(0.0, QColor(255, 255, 255, 180))
            spec_grad.setColorAt(0.5, QColor(255, 255, 255, 60))
            spec_grad.setColorAt(1.0, QColor(255, 255, 255, 0))

            painter.setBrush(QBrush(spec_grad))
            painter.drawEllipse(QRectF(
                spec_x - spec_radius, spec_y - spec_radius,
                spec_radius * 2, spec_radius * 2
            ))

    def _draw_selection_ring(self, painter, sx, sy, radius):
        """Draw a glowing yellow ring around a selected atom."""
        ring_r = radius + max(3, radius * 0.25)
        pen = QPen(QColor(255, 200, 50, 200), max(2, radius * 0.12))
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 200, 50, 30)))
        painter.drawEllipse(QRectF(sx - ring_r, sy - ring_r, ring_r * 2, ring_r * 2))

    def set_selected(self, atom_indices):
        """Set which atoms are highlighted (from console select commands)."""
        self.selected_atoms = set(atom_indices)
        self.update()

    def _draw_bonds(self, painter, projected):
        """Draw bonds as lines/cylinders between atoms."""
        if not self.molecule:
            return

        proj_map = {p[0]: p for p in projected}

        for bond in self.molecule.bonds:
            i = bond.begin_atom_idx
            j = bond.end_atom_idx

            if i not in proj_map or j not in proj_map:
                continue

            _, x1, y1, z1, r1, c1 = proj_map[i]
            _, x2, y2, z2, r2, c2 = proj_map[j]

            avg_z = (z1 + z2) / 2
            depth_shade = max(0.35, min(1.0, 1.0 - avg_z * 0.025))

            base_width = max(2, self.zoom * 0.07 * self.stick_scale)
            if self.render_mode == 'wireframe':
                base_width = max(1, self.zoom * 0.03 * self.line_scale)
            elif self.render_mode == 'spacefill':
                base_width = max(1, self.zoom * 0.04 * self.stick_scale)

            if bond.is_double or bond.order == 2.0:
                dx = y2 - y1
                dy = -(x2 - x1)
                length = math.sqrt(dx*dx + dy*dy) + 1e-10
                dx /= length
                dy /= length
                offset = base_width * 0.9

                for sign in (-1, 1):
                    ox = dx * offset * sign
                    oy = dy * offset * sign
                    self._draw_bond_line(painter, x1+ox, y1+oy, x2+ox, y2+oy,
                                         c1, c2, base_width * 0.55, depth_shade)

            elif bond.is_triple or bond.order == 3.0:
                dx = y2 - y1
                dy = -(x2 - x1)
                length = math.sqrt(dx*dx + dy*dy) + 1e-10
                dx /= length
                dy /= length
                offset = base_width * 1.3

                self._draw_bond_line(painter, x1, y1, x2, y2,
                                     c1, c2, base_width * 0.5, depth_shade)
                for sign in (-1, 1):
                    ox = dx * offset * sign
                    oy = dy * offset * sign
                    self._draw_bond_line(painter, x1+ox, y1+oy, x2+ox, y2+oy,
                                         c1, c2, base_width * 0.45, depth_shade)
            else:
                self._draw_bond_line(painter, x1, y1, x2, y2,
                                     c1, c2, base_width, depth_shade)

    def _draw_bond_line(self, painter, x1, y1, x2, y2, c1, c2, width, shade):
        """Draw a split-colored bond line with rounded caps."""
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2

        r1, g1, b1 = c1
        color1 = QColor(
            max(0, min(255, int(r1*shade))),
            max(0, min(255, int(g1*shade))),
            max(0, min(255, int(b1*shade)))
        )
        pen = QPen(color1, max(1, width))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(x1, y1), QPointF(mx, my))

        r2, g2, b2 = c2
        color2 = QColor(
            max(0, min(255, int(r2*shade))),
            max(0, min(255, int(g2*shade))),
            max(0, min(255, int(b2*shade)))
        )
        pen = QPen(color2, max(1, width))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(mx, my), QPointF(x2, y2))

    def _draw_label(self, painter, atom_idx, sx, sy, radius):
        atom = self.molecule.atoms[atom_idx]
        label = atom.symbol

        # Use fixed font size — does NOT scale with sphere radius or export DPI
        font_size = self.label_font_size
        # For exports, keep label size reasonable (don't let DPI scaling blow them up)
        eff_scale = getattr(self, '_export_scale', 1.0)
        if eff_scale > 1.0:
            font_size = max(7, int(font_size * min(eff_scale * 0.5, 1.5)))

        font = QFont('Segoe UI', font_size)
        font.setBold(True)
        painter.setFont(font)

        # Offset label just outside the sphere
        offset_x = int(radius * 0.5 + 2)
        offset_y = int(-radius * 0.3)

        # Drop shadow for readability
        painter.setPen(QColor(0, 0, 0, 180))
        painter.drawText(int(sx + offset_x + 1), int(sy + offset_y + 1), label)
        painter.setPen(QColor(255, 255, 255, 230))
        painter.drawText(int(sx + offset_x), int(sy + offset_y), label)

    def _draw_overlay(self, painter):
        if not self.molecule:
            return

        font = QFont('Segoe UI', 11)
        painter.setFont(font)
        painter.setPen(QColor(COLORS['text_secondary']))

        y = 20
        texts = [
            f"Atoms: {len(self.molecule.atoms)}",
            f"Bonds: {len(self.molecule.bonds)}",
        ]

        if 0 <= self._hovered_atom < len(self.molecule.atoms):
            atom = self.molecule.atoms[self._hovered_atom]
            texts.append("-------------")
            texts.append(f"Atom: {atom.symbol}{self._hovered_atom + 1}")
            if atom.has_coords:
                texts.append(f"Pos: ({atom.x:.2f}, {atom.y:.2f}, {atom.z:.2f})")
            texts.append(f"Charge: {atom.partial_charge:.4f}")

        for text in texts:
            painter.drawText(10, y, text)
            y += 18

    def _draw_placeholder(self, painter, width, height):
        font = QFont('Segoe UI', 16)
        painter.setFont(font)
        painter.setPen(QColor(COLORS['text_muted']))
        rect = QRectF(0, 0, width, height)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                         "Enter a SMILES string and click\n'Convert to 3D' to visualize")

    # ─── Image Export ─────────────────────────────────────────────

    def export_image(self, filepath, dpi=300, bg_white=True):
        """
        Export the current view as a high-resolution image.

        Args:
            filepath: Output file path (.png, .jpg, .tiff, .bmp)
            dpi: Resolution in dots per inch (72, 150, 300, 600, etc.)
            bg_white: If True, use white background instead of dark

        Returns:
            True if successful
        """
        # Calculate pixel dimensions from current widget size and DPI
        scale_factor = dpi / 96.0  # 96 DPI is the default screen DPI
        img_width = int(self.width() * scale_factor)
        img_height = int(self.height() * scale_factor)

        # Create high-res image
        image = QImage(img_width, img_height, QImage.Format.Format_ARGB32_Premultiplied)
        image.setDotsPerMeterX(int(dpi / 0.0254))
        image.setDotsPerMeterY(int(dpi / 0.0254))

        # Save and modify state for export
        original_bg = self.bg_color
        original_zoom = self.zoom
        original_pan_x = self.pan_x
        original_pan_y = self.pan_y

        if bg_white:
            self.bg_color = QColor(255, 255, 255)

        # Scale zoom and pan for higher resolution
        self.zoom *= scale_factor
        self.pan_x *= scale_factor
        self.pan_y *= scale_factor

        # Render into image
        painter = QPainter(image)
        self._render(painter, img_width, img_height, is_export=True, export_scale=scale_factor)
        painter.end()

        # Restore state
        self.bg_color = original_bg
        self.zoom = original_zoom
        self.pan_x = original_pan_x
        self.pan_y = original_pan_y

        # Save
        result = image.save(filepath)
        return result

    # ─── Mouse Interaction ────────────────────────────────────────

    def mousePressEvent(self, event):
        self._last_mouse_pos = event.position()
        self._mouse_button = event.button()

    def mouseMoveEvent(self, event):
        if self._last_mouse_pos is None:
            self._detect_hover(event.position())
            return

        dx = event.position().x() - self._last_mouse_pos.x()
        dy = event.position().y() - self._last_mouse_pos.y()

        if self._mouse_button == Qt.MouseButton.LeftButton:
            self.rot_y += dx * 0.5
            self.rot_x += dy * 0.5
        elif self._mouse_button == Qt.MouseButton.MiddleButton:
            self.pan_x += dx
            self.pan_y += dy

        self._last_mouse_pos = event.position()
        self.update()

    def mouseReleaseEvent(self, event):
        was_click = False
        if self._last_mouse_pos is not None:
            moved = (abs(event.position().x() - self._last_mouse_pos.x()) +
                     abs(event.position().y() - self._last_mouse_pos.y()))
            was_click = moved < 3

        btn = event.button()

        if was_click and btn == Qt.MouseButton.LeftButton:
            atom_idx = self._hit_test(event.position())
            if atom_idx >= 0:
                self.atom_clicked.emit(atom_idx)

        if was_click and btn == Qt.MouseButton.RightButton:
            atom_idx = self._hit_test(event.position())
            if atom_idx >= 0:
                # Toggle atom selection
                if atom_idx in self.selected_atoms:
                    self.selected_atoms.discard(atom_idx)
                else:
                    self.selected_atoms.add(atom_idx)
                # Add to measurement picks
                self._measure_atoms.append(atom_idx)
                if len(self._measure_atoms) == 2:
                    self._complete_distance_measurement()
                elif len(self._measure_atoms) == 3:
                    self._complete_angle_measurement()
                self.update()
            else:
                # Right-click on empty: clear measurements
                self._measure_atoms.clear()
                self._measurements.clear()
                self.update()

        self._last_mouse_pos = None
        self._mouse_button = None

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        self.zoom *= factor
        self.zoom = max(5, min(200, self.zoom))
        self.update()

    def _detect_hover(self, pos):
        atom_idx = self._hit_test(pos)
        if atom_idx != self._hovered_atom:
            self._hovered_atom = atom_idx
            self.atom_hovered.emit(atom_idx)
            self.update()

    def _hit_test(self, pos):
        projected = self._project_atoms()
        if not projected:
            return -1

        mx = pos.x()
        my = pos.y()
        best_idx = -1
        best_z = float('inf')

        for atom_idx, sx, sy, sz, radius, color in projected:
            dx = mx - sx
            dy = my - sy
            dist_sq = dx*dx + dy*dy
            if dist_sq <= (radius + 3) ** 2:
                if sz < best_z:
                    best_z = sz
                    best_idx = atom_idx

        return best_idx

    # ─── Camera Utilities ─────────────────────────────────────────

    def _auto_fit(self):
        if not self.molecule or not self.molecule.atoms:
            return

        coords = []
        for atom in self.molecule.atoms:
            if atom.has_coords:
                coords.append([atom.x, atom.y, atom.z])

        if not coords:
            return

        coords = np.array(coords)
        span = np.max(coords, axis=0) - np.min(coords, axis=0)
        max_span = max(span) if max(span) > 0 else 1.0

        viewport_size = min(self.width(), self.height())
        self.zoom = min(100, max(10, viewport_size * 0.3 / max_span))
        self.pan_x = 0
        self.pan_y = 0

    def _auto_rotate_step(self):
        self.rot_y += 0.8
        self.update()

    # ─── Measurements ─────────────────────────────────────────────

    def _complete_distance_measurement(self):
        """Record distance between 2 picked atoms."""
        if len(self._measure_atoms) < 2:
            return
        i, j = self._measure_atoms[-2], self._measure_atoms[-1]
        a1 = self.molecule.atoms[i]
        a2 = self.molecule.atoms[j]
        if a1.has_coords and a2.has_coords:
            dx = a1.x - a2.x
            dy = a1.y - a2.y
            dz = (a1.z or 0) - (a2.z or 0)
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            self._measurements.append(('dist', i, j, dist))

    def _complete_angle_measurement(self):
        """Record angle between 3 picked atoms (vertex is the middle one)."""
        if len(self._measure_atoms) < 3:
            return
        i, j, k = self._measure_atoms[-3], self._measure_atoms[-2], self._measure_atoms[-1]
        a1 = self.molecule.atoms[i]
        a2 = self.molecule.atoms[j]
        a3 = self.molecule.atoms[k]
        if a1.has_coords and a2.has_coords and a3.has_coords:
            import numpy as np
            v1 = np.array([a1.x - a2.x, a1.y - a2.y, (a1.z or 0) - (a2.z or 0)])
            v2 = np.array([a3.x - a2.x, a3.y - a2.y, (a3.z or 0) - (a2.z or 0)])
            cos_a = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-12)
            angle = math.degrees(math.acos(max(-1, min(1, cos_a))))
            self._measurements.append(('angle', i, j, k, angle))
        # Reset picks after angle measurement
        self._measure_atoms.clear()

    def _draw_measurements(self, painter, projected):
        """Draw distance/angle measurement overlays."""
        proj_map = {p[0]: p for p in projected}

        # Draw dotted lines for pending picks
        if len(self._measure_atoms) >= 1:
            pen = QPen(QColor(255, 200, 50, 200), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            for m in range(len(self._measure_atoms) - 1):
                i = self._measure_atoms[m]
                j = self._measure_atoms[m + 1]
                if i in proj_map and j in proj_map:
                    _, x1, y1, *_ = proj_map[i]
                    _, x2, y2, *_ = proj_map[j]
                    painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        font = QFont('Segoe UI', 11)
        font.setBold(True)
        painter.setFont(font)

        for meas in self._measurements:
            if meas[0] == 'dist':
                _, i, j, dist = meas
                if i in proj_map and j in proj_map:
                    _, x1, y1, *_ = proj_map[i]
                    _, x2, y2, *_ = proj_map[j]
                    # Dashed yellow line
                    pen = QPen(QColor(50, 220, 255, 200), 2, Qt.PenStyle.DashDotLine)
                    painter.setPen(pen)
                    painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                    # Label at midpoint
                    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                    label = f"{dist:.2f} A"
                    # Background
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
                    painter.drawRoundedRect(QRectF(mx - 30, my - 12, 60, 20), 4, 4)
                    painter.setPen(QColor(50, 220, 255))
                    painter.drawText(QRectF(mx - 30, my - 12, 60, 20),
                                   Qt.AlignmentFlag.AlignCenter, label)

            elif meas[0] == 'angle':
                _, i, j, k, angle = meas
                if j in proj_map:
                    _, vx, vy, *_ = proj_map[j]
                    # Draw from j
                    if i in proj_map:
                        _, x1, y1, *_ = proj_map[i]
                        pen = QPen(QColor(255, 150, 50, 200), 2, Qt.PenStyle.DashDotLine)
                        painter.setPen(pen)
                        painter.drawLine(QPointF(vx, vy), QPointF(x1, y1))
                    if k in proj_map:
                        _, x3, y3, *_ = proj_map[k]
                        painter.drawLine(QPointF(vx, vy), QPointF(x3, y3))

                    label = f"{angle:.1f} deg"
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
                    painter.drawRoundedRect(QRectF(vx - 35, vy - 30, 70, 20), 4, 4)
                    painter.setPen(QColor(255, 150, 50))
                    painter.drawText(QRectF(vx - 35, vy - 30, 70, 20),
                                   Qt.AlignmentFlag.AlignCenter, label)

    # ─── Protein Rendering ─────────────────────────────────────────────

    def _draw_protein(self, painter, projected, width, height):
        """Draw protein structures with cartoon/ribbon/backbone representations."""
        if not self.molecule:
            return
            
        # Group atoms by residue and chain
        residues = self._group_residues()
        
        # Draw based on render mode
        if self.render_mode == 'cartoon':
            self._draw_cartoon(painter, residues)
        elif self.render_mode == 'ribbon':
            self._draw_ribbon(painter, residues)
        elif self.render_mode == 'backbone':
            self._draw_backbone(painter, residues)
            
        # Optionally draw side chains
        if getattr(self, 'show_sidechains', True):
            self._draw_side_chains(painter, projected)

    def _group_residues(self):
        """Group atoms into residues for protein rendering."""
        residues = {}
        
        for i, atom in enumerate(self.molecule.atoms):
            if not hasattr(atom, 'chain_id') or not hasattr(atom, 'res_seq'):
                continue
                
            chain_id = atom.chain_id or 'A'
            res_seq = atom.res_seq
            
            key = (chain_id, res_seq)
            if key not in residues:
                residues[key] = {
                    'chain_id': chain_id,
                    'res_seq': res_seq,
                    'res_name': getattr(atom, 'res_name', 'UNK'),
                    'atoms': [],
                    'ss_type': getattr(atom, 'ss_type', 'C')
                }
            
            residues[key]['atoms'].append(i)
            
            # Use the secondary structure from the first atom with valid ss_type
            if residues[key]['ss_type'] == 'C' and hasattr(atom, 'ss_type'):
                residues[key]['ss_type'] = atom.ss_type
        
        return residues

    def _get_ss_color(self, ss_type):
        """Get color for secondary structure type."""
        colors = {
            'H': QColor(220, 50, 50),    # Helix - red
            'E': QColor(50, 150, 220),    # Sheet - blue  
            'C': QColor(180, 180, 180),  # Coil - gray
        }
        return colors.get(ss_type, QColor(180, 180, 180))

    def _draw_cartoon(self, painter, residues):
        """Draw PyMOL-style cartoon representation."""
        if not residues or len(residues) == 0:
            return
            
        # Sort residues by chain and sequence number
        sorted_residues = sorted(residues.items(), 
                               key=lambda x: (x[0][0], x[0][1]))  # chain, res_seq
        
        # Group residues by secondary structure for smooth rendering
        chains = {}
        for (chain_id, res_seq), residue in sorted_residues:
            if chain_id not in chains:
                chains[chain_id] = []
            
            # Find CA atom
            ca_idx = None
            for atom_idx in residue['atoms']:
                atom = self.molecule.atoms[atom_idx]
                if hasattr(atom, 'pdb_name') and atom.pdb_name == 'CA':
                    ca_idx = atom_idx
                    break
            
            if ca_idx is None:
                continue
                
            ca_atom = self.molecule.atoms[ca_idx]
            if not ca_atom.has_coords:
                continue
            
            # Project to screen coordinates
            w, h = self.width(), self.height()
            cx = w / 2 + self.pan_x
            cy = h / 2 + self.pan_y
            
            cos_x = math.cos(math.radians(self.rot_x))
            sin_x = math.sin(math.radians(self.rot_x))
            cos_y = math.cos(math.radians(self.rot_y))
            sin_y = math.sin(math.radians(self.rot_y))
            
            x, y, z = ca_atom.x, ca_atom.y, ca_atom.z
            x1 = x * cos_y + z * sin_y
            z1 = -x * sin_y + z * cos_y
            y1 = y * cos_x - z1 * sin_x
            z2 = y * sin_x + z1 * cos_x
            
            sx = cx + x1 * self.zoom
            sy = cy - y1 * self.zoom
            
            chains[chain_id].append({
                'res_seq': res_seq,
                'ss_type': residue['ss_type'],
                'x': sx,
                'y': sy,
                'z': z2
            })
        
        # Draw cartoon for each chain
        for chain_id, points in chains.items():
            if len(points) < 2:
                continue
            
            self._draw_pyMOL_cartoon_chain(painter, points)

    def _draw_pyMOL_cartoon_chain(self, painter, points):
        """Draw PyMOL-style cartoon chain with proper secondary structure."""
        if not points or len(points) < 2:
            return
            
        # Group consecutive residues with same secondary structure
        segments = []
        current_segment = []
        current_ss = None
        
        for point in points:
            ss_type = point['ss_type']
            if current_ss is None:
                current_ss = ss_type
                current_segment = [point]
            elif ss_type == current_ss:
                current_segment.append(point)
            else:
                # End current segment
                if len(current_segment) >= 1:
                    segments.append((current_ss, current_segment))
                # Start new segment
                current_ss = ss_type
                current_segment = [point]
        
        # Add last segment
        if len(current_segment) >= 1:
            segments.append((current_ss, current_segment))
        
        # Draw each segment with PyMOL style
        for ss_type, segment in segments:
            if len(segment) < 2:
                continue
                
            if ss_type == 'H':
                self._draw_pyMOL_helix(painter, segment)
            elif ss_type == 'E':
                self._draw_pyMOL_sheet(painter, segment)
            else:
                self._draw_pyMOL_coil(painter, segment)

    def _draw_pyMOL_helix(self, painter, points):
        """Draw PyMOL-style alpha helix."""
        if len(points) < 2:
            return
        
        color = QColor(220, 50, 50)  # PyMOL helix red
        
        # Create smooth path
        path = QPainterPath()
        path.moveTo(points[0]['x'], points[0]['y'])
        
        for i in range(1, len(points)):
            path.lineTo(points[i]['x'], points[i]['y'])
        
        # Draw main helix cylinder - VERY THICK AND VISIBLE
        pen = QPen(color, 15)  # Very thick for visibility
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)
        
        # Add strong highlight for 3D effect
        highlight_pen = QPen(QColor(255, 255, 255, 150), 6)  # Strong highlight
        highlight_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(highlight_pen)
        painter.drawPath(path)

    def _draw_pyMOL_sheet(self, painter, points):
        """Draw PyMOL-style beta sheet."""
        if len(points) < 2:
            return
        
        color = QColor(50, 150, 220)  # PyMOL sheet blue
        
        # Create smooth path
        path = QPainterPath()
        path.moveTo(points[0]['x'], points[0]['y'])
        
        for i in range(1, len(points)):
            path.lineTo(points[i]['x'], points[i]['y'])
        
        # Draw flat sheet ribbon - VERY THICK AND VISIBLE
        pen = QPen(color, 12)  # Very thick for visibility
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)
        
        # Draw VERY LARGE rectangular arrowhead at the end
        if len(points) >= 2:
            last_point = points[-1]
            second_last = points[-2]
            
            # Calculate arrow direction
            dx = last_point['x'] - second_last['x']
            dy = last_point['y'] - second_last['y']
            angle = math.atan2(dy, dx)
            
            # LARGE rectangular arrowhead
            arrow_length = 20
            arrow_width = 12
            
            # Calculate rectangle points
            base_x = last_point['x'] - arrow_length * math.cos(angle)
            base_y = last_point['y'] - arrow_length * math.sin(angle)
            
            perp_angle = angle + math.pi/2
            offset_x = arrow_width/2 * math.cos(perp_angle)
            offset_y = arrow_width/2 * math.sin(perp_angle)
            
            # Draw filled rectangle arrowhead
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            
            rect_points = [
                QPointF(base_x - offset_x, base_y - offset_y),
                QPointF(base_x + offset_x, base_y + offset_y),
                QPointF(last_point['x'] + offset_x, last_point['y'] + offset_y),
                QPointF(last_point['x'] - offset_x, last_point['y'] - offset_y)
            ]
            
            polygon = QPolygonF(rect_points)
            painter.drawPolygon(polygon)

    def _draw_pyMOL_coil(self, painter, points):
        """Draw PyMOL-style coil."""
        if len(points) < 2:
            return
        
        color = QColor(180, 180, 180)  # PyMOL coil gray
        
        # Create smooth path
        path = QPainterPath()
        path.moveTo(points[0]['x'], points[0]['y'])
        
        for i in range(1, len(points)):
            path.lineTo(points[i]['x'], points[i]['y'])
        
        # Draw coil line - VERY THICK AND VISIBLE
        pen = QPen(color, 8)  # Very thick for visibility
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)

    def _draw_ribbon(self, painter, residues):
        """Draw ribbon representation with smooth curves."""
        sorted_residues = sorted(residues.items(), 
                               key=lambda x: (x[0][0], x[0][1]))
        
        points_by_chain = {}
        
        # Collect CA points by chain
        for (chain_id, res_seq), residue in sorted_residues:
            # Find CA atom
            ca_idx = None
            for atom_idx in residue['atoms']:
                atom = self.molecule.atoms[atom_idx]
                if hasattr(atom, 'pdb_name') and atom.pdb_name == 'CA':
                    ca_idx = atom_idx
                    break
            
            if ca_idx is None:
                continue
                
            ca_atom = self.molecule.atoms[ca_idx]
            if not ca_atom.has_coords:
                continue
                
            # Project to screen coordinates
            w, h = self.width(), self.height()
            cx = w / 2 + self.pan_x
            cy = h / 2 + self.pan_y
            
            cos_x = math.cos(math.radians(self.rot_x))
            sin_x = math.sin(math.radians(self.rot_x))
            cos_y = math.cos(math.radians(self.rot_y))
            sin_y = math.sin(math.radians(self.rot_y))
            
            x, y, z = ca_atom.x, ca_atom.y, ca_atom.z
            x1 = x * cos_y + z * sin_y
            z1 = -x * sin_y + z * cos_y
            y1 = y * cos_x - z1 * sin_x
            z2 = y * sin_x + z1 * cos_x
            
            sx = cx + x1 * self.zoom
            sy = cy - y1 * self.zoom
            
            if chain_id not in points_by_chain:
                points_by_chain[chain_id] = []
            
            points_by_chain[chain_id].append((sx, sy, residue['ss_type']))
        
        # Draw smooth ribbons for each chain
        for chain_id, points in points_by_chain.items():
            if len(points) < 2:
                continue
                
            # Draw ribbon as connected segments with secondary structure coloring
            for i in range(len(points) - 1):
                x1, y1, ss1 = points[i]
                x2, y2, ss2 = points[i + 1]
                color = self._get_ss_color(ss1)
                self._draw_smooth_ribbon(painter, x1, y1, x2, y2, color, 6)

    def _draw_backbone(self, painter, residues):
        """Draw simple backbone trace."""
        sorted_residues = sorted(residues.items(), 
                               key=lambda x: (x[0][0], x[0][1]))
        
        prev_point = None
        
        for (chain_id, res_seq), residue in sorted_residues:
            # Find CA atom
            ca_idx = None
            for atom_idx in residue['atoms']:
                atom = self.molecule.atoms[atom_idx]
                if hasattr(atom, 'pdb_name') and atom.pdb_name == 'CA':
                    ca_idx = atom_idx
                    break
            
            if ca_idx is None:
                continue
                
            ca_atom = self.molecule.atoms[ca_idx]
            if not ca_atom.has_coords:
                continue
                
            # Project to screen coordinates
            w, h = self.width(), self.height()
            cx = w / 2 + self.pan_x
            cy = h / 2 + self.pan_y
            
            cos_x = math.cos(math.radians(self.rot_x))
            sin_x = math.sin(math.radians(self.rot_x))
            cos_y = math.cos(math.radians(self.rot_y))
            sin_y = math.sin(math.radians(self.rot_y))
            
            x, y, z = ca_atom.x, ca_atom.y, ca_atom.z
            x1 = x * cos_y + z * sin_y
            z1 = -x * sin_y + z * cos_y
            y1 = y * cos_x - z1 * sin_x
            z2 = y * sin_x + z1 * cos_x
            
            sx = cx + x1 * self.zoom
            sy = cy - y1 * self.zoom
            
            # Draw backbone line
            if prev_point:
                color = self._get_ss_color(residue['ss_type'])
                pen = QPen(color, 3)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawLine(QPointF(*prev_point), QPointF(sx, sy))
            
            # Draw small sphere for CA atom
            color = self._get_ss_color(residue['ss_type'])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(sx, sy), 3, 3)
            
            prev_point = (sx, sy)

    def _draw_side_chains(self, painter, projected):
        """Draw side chain atoms as sticks."""
        # Create projection map
        proj_map = {i: (atom_idx, sx, sy, sz, radius, color) 
                   for atom_idx, sx, sy, sz, radius, color in projected 
                   for i in [atom_idx]}
        
        # Draw side chain bonds
        for bond in self.molecule.bonds:
            a1, a2 = bond.begin_atom_idx, bond.end_atom_idx
            
            # Skip if both are backbone atoms (N, CA, C, O)
            atom1, atom2 = self.molecule.atoms[a1], self.molecule.atoms[a2]
            if (hasattr(atom1, 'pdb_name') and atom1.pdb_name in ['N', 'CA', 'C', 'O'] and
                hasattr(atom2, 'pdb_name') and atom2.pdb_name in ['N', 'CA', 'C', 'O']):
                continue
            
            # Draw bond as thin stick
            if a1 in proj_map and a2 in proj_map:
                _, x1, y1, *_ = proj_map[a1]
                _, x2, y2, *_ = proj_map[a2]
                pen = QPen(QColor(150, 150, 150), 2)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        
        # Draw side chain atoms as small spheres
        for atom_idx, sx, sy, sz, radius, color in projected:
            atom = self.molecule.atoms[atom_idx]
            if hasattr(atom, 'pdb_name') and atom.pdb_name in ['N', 'CA', 'C', 'O']:
                continue  # Skip backbone atoms
            
            # Draw small sphere
            painter.setPen(Qt.PenStyle.NoPen)
            # Ensure color is a QColor object
            if isinstance(color, tuple):
                color = QColor(*color)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(sx, sy), 2, 2)

    def _draw_cylinder(self, painter, x1, y1, x2, y2, color, width):
        """Draw a cylinder between two points."""
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_arrow(self, painter, x1, y1, x2, y2, color, width):
        """Draw an arrow between two points."""
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        painter.setPen(pen)
        
        # Draw line
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        
        # Draw arrowhead
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_length = width * 2
        arrow_angle = 0.5
        
        ax1 = x2 - arrow_length * math.cos(angle - arrow_angle)
        ay1 = y2 - arrow_length * math.sin(angle - arrow_angle)
        ax2 = x2 - arrow_length * math.cos(angle + arrow_angle)
        ay2 = y2 - arrow_length * math.sin(angle + arrow_angle)
        
        painter.drawLine(QPointF(x2, y2), QPointF(ax1, ay1))
        painter.drawLine(QPointF(x2, y2), QPointF(ax2, ay2))

    def _draw_tube(self, painter, x1, y1, x2, y2, color, width):
        """Draw a smooth tube between two points."""
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_smooth_ribbon(self, painter, x1, y1, x2, y2, color, width):
        """Draw a smooth ribbon segment."""
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_large_molecule_fast(self, painter, projected, sorted_atoms):
        """Fast rendering for large molecules (>500 atoms)."""
        # Create projection map for fast bond lookup
        proj_map = {i: (atom_idx, sx, sy, sz, radius, color) 
                   for atom_idx, sx, sy, sz, radius, color in projected 
                   for i in [atom_idx]}
        
        # Draw bonds as simple lines
        pen = QPen(QColor(100, 100, 100), 1)
        painter.setPen(pen)
        for bond in self.molecule.bonds:
            a1, a2 = bond.begin_atom_idx, bond.end_atom_idx
            if a1 in proj_map and a2 in proj_map:
                _, x1, y1, *_ = proj_map[a1]
                _, x2, y2, *_ = proj_map[a2]
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        
        # Draw atoms as simple circles (no gradients)
        for atom_idx, sx, sy, sz, radius, color in sorted_atoms:
            self._draw_atom_simple(painter, sx, sy, radius, color)

    def _draw_atom_simple(self, painter, sx, sy, radius, color):
        """Draw atom as simple filled circle (fast for large molecules)."""
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QPointF(sx, sy), max(2, radius), max(2, radius))

    def _draw_performance_indicator(self, painter, num_atoms):
        """Draw performance indicator for large molecules."""
        font = QFont('Segoe UI', 10)
        painter.setFont(font)
        
        # Background for indicator
        indicator_text = f"Large molecule ({num_atoms} atoms) - Fast rendering active"
        text_rect = QRectF(10, self.height() - 30, 300, 25)
        
        # Semi-transparent background
        painter.fillRect(text_rect, QColor(0, 0, 0, 120))
        
        # Text
        painter.setPen(QColor(255, 255, 100))  # Yellow text
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                        indicator_text)
