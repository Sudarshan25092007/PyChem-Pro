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
from src.shared.qt_compat import QWidget, Qt, QTimer, Signal, QPointF, QRectF
from src.shared.qt_compat import (
    QPainter, QColor, QPen, QBrush, QFont, QWheelEvent,
    QRadialGradient, QLinearGradient, QImage, QConicalGradient, QPainterPath,
    QMenu, QAction
)
from src.shared.ui.theme import COLORS


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

    Selection
    ---------
    **Shift + left-drag** draws a rubber-band rectangle (PyMOL-style).
    Atoms whose projected screen positions fall inside the rectangle on
    mouse-release are added to ``selected_atoms``.  A plain left-click on
    empty space clears the selection.

    Deletion
    --------
    Pressing the **Delete** key while atoms are selected emits
    ``delete_requested`` so the main window can remove those atoms from
    the domain model and refresh both viewers.
    """

    # --- Signals ---
    atom_hovered = Signal(int)
    atom_clicked = Signal(int)
    selection_changed = Signal(object)   # emits set of selected atom indices
    delete_requested = Signal(object)    # emits set of atom indices to delete

    def __init__(self, parent=None):
        super().__init__(parent)
        self.molecule = None
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # receive key events

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

        # Rubber-band selection rectangle (screen coords, set during Shift+drag)
        self._sel_rect_origin = None   # QPointF or None
        self._sel_rect_end = None      # QPointF or None
        self._is_selecting = False     # True while Shift+left-drag is active

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
        self.show_sidechains = False
        self.render_mode = 'ball_and_stick'  # 'spacefill', 'wireframe', 'cartoon', 'ribbon', 'backbone'
        self.custom_atom_modes = {}
        self.sidechain_res_vis = {}
        self.labeled_residues = {}  # mapping res_seq to QColor
        self.use_ssao = False  # Fake real-time ray-tracing toggle
        self.use_gouraud = False  # Gouraud normal smoothing toggle
        self.bg_color = QColor(COLORS['viewer_bg'])

        # User-adjustable radius scales (1.0 = default)
        self.sphere_scale = 0.6   # Multiplier for atom sphere radius (60% default)
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
            # Auto-switch to cartoon for proteins, reset for small molecules
            is_protein = getattr(molecule, 'properties', {}).get('is_protein', False)
            if is_protein:
                self.render_mode = 'cartoon'
            else:
                self.render_mode = 'ball_and_stick'
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
            
            # Draw any custom-styled atoms over the protein backbone
            cam = getattr(self, 'custom_atom_modes', {})
            if cam:
                self._draw_bonds(painter, projected, custom_only=True)
                for atom_idx, sx, sy, sz, radius, color in sorted_atoms:
                    if atom_idx in cam:
                        self._draw_atom_sphere(painter, atom_idx, sx, sy, sz, radius, color)
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

        # Draw rubber-band selection rectangle (while Shift+dragging)
        if self._is_selecting and self._sel_rect_origin and self._sel_rect_end:
            self._draw_rubber_band(painter)

        # Draw SASA point-cloud surface 
        if getattr(self, 'show_sasa_surface', False):
            self._draw_sasa_surface(painter, width, height)

        # Draw labels if enabled
        if self.show_labels:
            for atom_idx, sx, sy, sz, radius, color in sorted_atoms:
                self._draw_label(painter, atom_idx, sx, sy, radius)

        # Draw specific residue labels dynamically
        if hasattr(self, 'labeled_residues') and self.labeled_residues:
            for atom_idx, sx, sy, sz, radius, color in sorted_atoms:
                atom = self.molecule.atoms[atom_idx]
                rs = getattr(atom, 'res_seq', None)
                if rs is not None and rs in self.labeled_residues:
                    # To keep it clean, only label the CA atom
                    if hasattr(atom, 'pdb_name') and atom.pdb_name.strip() == 'CA':
                        res_name = getattr(atom, 'res_name', 'UNK')
                        lbl_color = self.labeled_residues[rs]
                        self._draw_residue_label(painter, f"{res_name}{rs}", sx, sy, lbl_color, radius)

        # Draw dummy spheres (COM, centroid, custom)
        self._draw_dummy_spheres(painter, width, height)

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
            atom_render_mode = getattr(self, 'custom_atom_modes', {}).get(atom.index, self.render_mode)
            if atom_render_mode == 'spacefill':
                base_r = atom.element.vdw_radius * 0.5
            elif atom_render_mode == 'wireframe':
                base_r = 0.1
            display_r = base_r * self.zoom * self.sphere_scale

            # Depth-based size attenuation
            depth_factor = 1.0 + sz * 0.02
            display_r *= max(0.5, min(1.5, depth_factor))

            # Color from element
            color = _hex_to_rgb(atom.element.color)
            # Note: Removed hardcoded H color override to allow user customization

            projected.append((atom.index, sx, sy, sz, display_r, color))

        return projected

    def _draw_atom_sphere(self, painter, atom_idx, sx, sy, sz, radius, rgb, alpha=1.0):
        from src.features.visualization_3d.services.atom_rendering import draw_atom_sphere
        draw_atom_sphere(painter, sx, sy, sz, radius, rgb, 
                         is_hovered=(atom_idx == self._hovered_atom), 
                         use_ssao=getattr(self, 'use_ssao', False),
                         alpha=alpha)

    def _draw_selection_ring(self, painter, sx, sy, radius):
        from src.features.visualization_3d.services.atom_rendering import draw_selection_ring
        draw_selection_ring(painter, sx, sy, radius)

    def _draw_sasa_surface(self, painter, width, height):
        from src.features.visualization_3d.services.atom_rendering import draw_sasa_surface
        draw_sasa_surface(painter, self.molecule, width, height, 
                          self.pan_x, self.pan_y, self.rot_x, self.rot_y, self.zoom, 
                          self.selected_atoms, getattr(self, 'show_sasa_selected_only', False))

    def set_selected(self, atom_indices):
        """Set which atoms are highlighted (from console select commands)."""
        self.selected_atoms = set(atom_indices)
        self.update()

    def _draw_bonds(self, painter, projected, custom_only=False):
        """Draw bonds as lines/cylinders between atoms."""
        if not self.molecule:
            return

        proj_map = {p[0]: p for p in projected}
        cam = getattr(self, 'custom_atom_modes', {})

        for bond in self.molecule.bonds:
            i = bond.begin_atom_idx
            j = bond.end_atom_idx

            if i not in proj_map or j not in proj_map:
                continue

            if custom_only and i not in cam and j not in cam:
                continue

            _, x1, y1, z1, r1, c1 = proj_map[i]
            _, x2, y2, z2, r2, c2 = proj_map[j]

            avg_z = (z1 + z2) / 2
            depth_shade = max(0.35, min(1.0, 1.0 - avg_z * 0.025))

            bond_render_mode = self.render_mode
            cam = getattr(self, 'custom_atom_modes', {})
            
            is_custom = False
            if i in cam and j in cam:
                bond_render_mode = cam[i]
                is_custom = True
            elif i in cam:
                bond_render_mode = cam[i]
                is_custom = True
            elif j in cam:
                bond_render_mode = cam[j]
                is_custom = True

            base_width = max(2, self.zoom * 0.07 * self.stick_scale)
            if bond_render_mode == 'wireframe':
                base_width = max(1.5, self.zoom * 0.04 * self.line_scale)
            elif bond_render_mode == 'spacefill':
                base_width = max(1, self.zoom * 0.04 * self.stick_scale)
            elif bond_render_mode == 'ball_and_stick':
                base_width = max(3, self.zoom * 0.1 * self.stick_scale)

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
                                         c1, c2, base_width * 0.55, depth_shade, is_custom=is_custom)

            elif bond.is_triple or bond.order == 3.0:
                dx = y2 - y1
                dy = -(x2 - x1)
                length = math.sqrt(dx*dx + dy*dy) + 1e-10
                dx /= length
                dy /= length
                offset = base_width * 1.3

                self._draw_bond_line(painter, x1, y1, x2, y2,
                                     c1, c2, base_width * 0.5, depth_shade, is_custom=is_custom)
                for sign in (-1, 1):
                    ox = dx * offset * sign
                    oy = dy * offset * sign
                    self._draw_bond_line(painter, x1+ox, y1+oy, x2+ox, y2+oy,
                                         c1, c2, base_width * 0.45, depth_shade, is_custom=is_custom)
            elif bond.is_aromatic or bond.order == 1.5:
                dx = y2 - y1
                dy = -(x2 - x1)
                length = math.sqrt(dx*dx + dy*dy) + 1e-10
                dx /= length
                dy /= length
                offset = base_width * 0.7

                self._draw_bond_line(painter, x1, y1, x2, y2,
                                     c1, c2, base_width * 0.7, depth_shade, is_custom=is_custom)
                
                ox = dx * offset
                oy = dy * offset
                self._draw_bond_line(painter, x1+ox, y1+oy, x2+ox, y2+oy,
                                     c1, c2, base_width * 0.4, depth_shade, dashed=True, is_custom=is_custom)
            else:
                self._draw_bond_line(painter, x1, y1, x2, y2,
                                     c1, c2, base_width, depth_shade, is_custom=is_custom)

    def _draw_bond_line(self, painter, x1, y1, x2, y2, c1, c2, width, shade, dashed=False, is_custom=False):
        from src.features.visualization_3d.services.atom_rendering import draw_bond_line
        draw_bond_line(painter, x1, y1, x2, y2, c1, c2, width, shade, dashed, is_custom)

    def _draw_label(self, painter, atom_idx, sx, sy, radius):
        from src.features.visualization_3d.services.atom_rendering import draw_label
        atom = self.molecule.atoms[atom_idx]
        draw_label(painter, atom.symbol, sx, sy, radius, self.label_font_size, getattr(self, '_export_scale', 1.0))

    def _draw_residue_label(self, painter, text, sx, sy, color, radius):
        from src.features.visualization_3d.services.atom_rendering import draw_residue_label
        draw_residue_label(painter, text, sx, sy, color, radius, self.label_font_size, getattr(self, '_export_scale', 1.0))

    def _draw_overlay(self, painter):
        from src.features.visualization_3d.services.overlay_rendering import draw_overlay
        draw_overlay(painter, self.molecule, self._hovered_atom)

    def _draw_placeholder(self, painter, width, height):
        from src.features.visualization_3d.services.overlay_rendering import draw_placeholder
        draw_placeholder(painter, width, height)

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
        """Handle mouse press: start rotation, pan, or rubber-band selection."""
        self._last_mouse_pos = event.position()
        self._mouse_button = event.button()

        # Shift + left-click begins rubber-band selection (PyMOL-style)
        if (event.button() == Qt.MouseButton.LeftButton
                and event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self._is_selecting = True
            self._sel_rect_origin = event.position()
            self._sel_rect_end = event.position()

    def mouseMoveEvent(self, event):
        """Handle mouse move: rotate, pan, update rubber-band, or hover."""
        if self._last_mouse_pos is None:
            self._detect_hover(event.position())
            return

        # Rubber-band selection drag
        if self._is_selecting:
            self._sel_rect_end = event.position()
            self.update()  # repaint to show the rectangle
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
        """Handle mouse release: commit selection rect, clicks, measurements."""
        # --- Finish rubber-band selection ---
        if self._is_selecting and event.button() == Qt.MouseButton.LeftButton:
            self._commit_rubber_band_selection()
            self._is_selecting = False
            self._sel_rect_origin = None
            self._sel_rect_end = None
            self._last_mouse_pos = None
            self._mouse_button = None
            self.update()
            return

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
            else:
                # Click on empty space → clear selection
                if self.selected_atoms:
                    self.selected_atoms.clear()
                    self.selection_changed.emit(set())
                    self.update()

        if was_click and btn == Qt.MouseButton.RightButton:
            atom_idx = self._hit_test(event.position())
            if atom_idx >= 0:
                # Toggle atom selection
                if atom_idx in self.selected_atoms:
                    self.selected_atoms.discard(atom_idx)
                else:
                    self.selected_atoms.add(atom_idx)
                self.selection_changed.emit(set(self.selected_atoms))
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

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts — Delete key removes selected atoms."""
        if event.key() == Qt.Key.Key_Delete and self.selected_atoms:
            self.delete_requested.emit(set(self.selected_atoms))
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        """Show context menu for selected atoms/residues and general viewer options."""
        menu = QMenu(self)

        selected_res_seqs = set()
        bs_action, wf_action, sf_action = None, None, None
        show_sc_action, hide_sc_action = None, None
        label_res_action, clear_label_action = None, None

        if self.selected_atoms:
            # Styles
            style_menu = menu.addMenu("Set Style")
            bs_action = style_menu.addAction("Ball and Stick")
            wf_action = style_menu.addAction("Wireframe")
            sf_action = style_menu.addAction("Space Fill")
            
            # Determine if selected contains residues
            if self.molecule:
                for idx in self.selected_atoms:
                    atom = self.molecule.atoms[idx]
                    rs = getattr(atom, 'res_seq', None)
                    if rs is not None:
                        selected_res_seqs.add(rs)
            
            if selected_res_seqs:
                sidechain_menu = menu.addMenu("Side Chains")
                show_sc_action = sidechain_menu.addAction("Show")
                hide_sc_action = sidechain_menu.addAction("Hide")

                # Label action
                label_res_action = menu.addAction("Label Residue Color...")
                clear_label_action = menu.addAction("Clear Residue Label")
            
            menu.addSeparator()

        ssao_action = menu.addAction("Disable Fake Ray-Tracing" if self.use_ssao else "Enable Fake Ray-Tracing (SSAO)")
        gouraud_action = menu.addAction("Disable Smooth Shading" if self.use_gouraud else "Enable Smooth Shading (Gouraud)")

        action = menu.exec(event.globalPos())
        if not action:
            return
            
        if not hasattr(self, 'custom_atom_modes'):
            self.custom_atom_modes = {}
        if not hasattr(self, 'sidechain_res_vis'):
            self.sidechain_res_vis = {}
            
        if bs_action and action == bs_action:
            for idx in self.selected_atoms:
                self.custom_atom_modes[idx] = 'ball_and_stick'
            self.update()
        elif wf_action and action == wf_action:
            for idx in self.selected_atoms:
                self.custom_atom_modes[idx] = 'wireframe'
            self.update()
        elif sf_action and action == sf_action:
            for idx in self.selected_atoms:
                self.custom_atom_modes[idx] = 'spacefill'
            self.update()
        elif show_sc_action and action == show_sc_action:
            for rs in selected_res_seqs:
                self.sidechain_res_vis[rs] = True
            self.update()
        elif hide_sc_action and action == hide_sc_action:
            for rs in selected_res_seqs:
                self.sidechain_res_vis[rs] = False
            self.update()
        elif label_res_action and action == label_res_action:
            from PySide6.QtWidgets import QColorDialog
            color = QColorDialog.getColor(Qt.white, self, "Select Residue Label Color")
            if color.isValid():
                for rs in selected_res_seqs:
                    self.labeled_residues[rs] = color
                self.update()
        elif clear_label_action and action == clear_label_action:
            for rs in selected_res_seqs:
                if rs in self.labeled_residues:
                    del self.labeled_residues[rs]
            self.update()
        elif action == ssao_action:
            self.use_ssao = not self.use_ssao
            self.update()
        elif action == gouraud_action:
            self.use_gouraud = not self.use_gouraud
            self.update()



    # ─── Rubber-band Helpers ──────────────────────────────────────

    def _commit_rubber_band_selection(self):
        """
        Finalise a Shift+drag selection: find all projected atoms whose
        screen positions fall inside the rubber-band rectangle and add
        them to ``selected_atoms``.  Emits ``selection_changed``.
        """
        if not self._sel_rect_origin or not self._sel_rect_end:
            return

        # Build normalised rectangle
        x1 = min(self._sel_rect_origin.x(), self._sel_rect_end.x())
        y1 = min(self._sel_rect_origin.y(), self._sel_rect_end.y())
        x2 = max(self._sel_rect_origin.x(), self._sel_rect_end.x())
        y2 = max(self._sel_rect_origin.y(), self._sel_rect_end.y())

        # Tiny rectangle treated as a missed click — clear selection
        if (x2 - x1) < 4 and (y2 - y1) < 4:
            self.selected_atoms.clear()
            self.selection_changed.emit(set())
            return

        rect = QRectF(x1, y1, x2 - x1, y2 - y1)
        projected = self._project_atoms()
        newly_selected = set()
        for atom_idx, sx, sy, sz, radius, color in projected:
            if rect.contains(QPointF(sx, sy)):
                newly_selected.add(atom_idx)

        if newly_selected:
            self.selected_atoms |= newly_selected
        self.selection_changed.emit(set(self.selected_atoms))

    def _draw_rubber_band(self, painter):
        """Draw the semi-transparent selection rectangle overlay."""
        x1 = min(self._sel_rect_origin.x(), self._sel_rect_end.x())
        y1 = min(self._sel_rect_origin.y(), self._sel_rect_end.y())
        x2 = max(self._sel_rect_origin.x(), self._sel_rect_end.x())
        y2 = max(self._sel_rect_origin.y(), self._sel_rect_end.y())
        rect = QRectF(x1, y1, x2 - x1, y2 - y1)

        # Semi-transparent yellow fill
        painter.setPen(QPen(QColor(255, 200, 50, 200), 1.5,
                            Qt.PenStyle.DashLine))
        painter.setBrush(QBrush(QColor(255, 200, 50, 40)))
        painter.drawRect(rect)

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

    def focus_on_atoms(self, atom_indices):
        """Center the view on the given atoms and zoom in."""
        if not self.molecule or not atom_indices:
            return
            
        coords = []
        for idx in atom_indices:
            if idx < len(self.molecule.atoms):
                atom = self.molecule.atoms[idx]
                if atom.has_coords:
                    coords.append([atom.x, atom.y, atom.z])
                    
        if not coords:
            return
            
        coords = np.array(coords)
        centroid = np.mean(coords, axis=0)
        span = np.max(coords, axis=0) - np.min(coords, axis=0)
        max_span = max(span) if max(span) > 0 else 1.0

        viewport_size = min(self.width(), self.height())
        # Zoom tighter than auto_fit (0.4 vs 0.3) but capped at 100
        self.zoom = min(100, max(15, viewport_size * 0.4 / max_span))
        
        cos_x = math.cos(math.radians(self.rot_x))
        sin_x = math.sin(math.radians(self.rot_x))
        cos_y = math.cos(math.radians(self.rot_y))
        sin_y = math.sin(math.radians(self.rot_y))
        
        x, y, z = centroid[0], centroid[1], centroid[2]
        x1 = x * cos_y + z * sin_y
        z1 = -x * sin_y + z * cos_y
        y1 = y * cos_x - z1 * sin_x
        
        self.pan_x = -x1 * self.zoom
        self.pan_y = y1 * self.zoom
        
        self.update()

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
        
        try:
            from src.features.visualization_3d.services.protein_rendering import (
                render_protein_cartoon, render_protein_ribbon
            )
            
            # Draw based on render mode
            if self.render_mode == 'cartoon':
                render_protein_cartoon(
                    painter=painter,
                    molecule=self.molecule,
                    width=width,
                    height=height,
                    rot_x=self.rot_x,
                    rot_y=self.rot_y,
                    pan_x=self.pan_x,
                    pan_y=self.pan_y,
                    zoom=self.zoom,
                    color_scheme="secondary_structure",
                    use_ssao=getattr(self, 'use_ssao', False),
                    use_gouraud=getattr(self, 'use_gouraud', False)
                )
            elif self.render_mode == 'ribbon':
                render_protein_ribbon(
                    painter=painter,
                    molecule=self.molecule,
                    width=width,
                    height=height,
                    rot_x=self.rot_x,
                    rot_y=self.rot_y,
                    pan_x=self.pan_x,
                    pan_y=self.pan_y,
                    zoom=self.zoom,
                    color_scheme="rainbow"
                )
            elif self.render_mode == 'backbone':
                # Fallback to legacy backbone rendering
                residues = self._group_residues()
                self._draw_backbone(painter, residues)
            
            # Optionally draw side chains
            if getattr(self, 'show_sidechains', False) or getattr(self, 'sidechain_res_vis', {}):
                self._draw_side_chains(painter, projected)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            # Fallback to legacy rendering on error
            residues = self._group_residues()
            if self.render_mode == 'cartoon':
                self._draw_cartoon(painter, residues)
            elif self.render_mode == 'ribbon':
                self._draw_ribbon(painter, residues)
            elif self.render_mode == 'backbone':
                self._draw_backbone(painter, residues)

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
        """Draw PyMOL-style alpha helix with configurable color."""
        if len(points) < 2:
            return
        
        # Use configurable color from theme
        from src.shared.ui.theme import COLORS
        color = QColor(COLORS.get('ss_helix', '#dc3232'))  # Configurable helix color
        
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
        """Draw PyMOL-style beta sheet with configurable color."""
        if len(points) < 2:
            return
        
        # Use configurable color from theme
        from src.shared.ui.theme import COLORS
        color = QColor(COLORS.get('ss_sheet', '#3296dc'))  # Configurable sheet color
        
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
        """Draw PyMOL-style coil with configurable color."""
        if len(points) < 2:
            return
        
        # Use configurable color from theme
        from src.shared.ui.theme import COLORS
        color = QColor(COLORS.get('ss_coil', '#b4b4b4'))  # Configurable coil color
        
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
        show_all = getattr(self, 'show_sidechains', False)
        vis_map = getattr(self, 'sidechain_res_vis', {})
        cam = getattr(self, 'custom_atom_modes', {})

        # Create projection map
        proj_map = {i: (atom_idx, sx, sy, sz, radius, color) 
                   for atom_idx, sx, sy, sz, radius, color in projected 
                   for i in [atom_idx]}
        
        # Draw side chain bonds
        for bond in self.molecule.bonds:
            a1, a2 = bond.begin_atom_idx, bond.end_atom_idx
            
            if a1 in cam or a2 in cam:
                continue
            
            # Skip if both are backbone atoms (N, CA, C, O)
            atom1, atom2 = self.molecule.atoms[a1], self.molecule.atoms[a2]

            res_seq1 = getattr(atom1, 'res_seq', None)
            res_seq2 = getattr(atom2, 'res_seq', None)
            
            if not show_all:
                # If neither atom belongs to a residue explicitly marked to show sidechains, skip
                if not (vis_map.get(res_seq1, False) or vis_map.get(res_seq2, False)):
                    continue

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
            if atom_idx in cam:
                continue
            
            atom = self.molecule.atoms[atom_idx]
            
            res_seq = getattr(atom, 'res_seq', None)
            if not show_all and not vis_map.get(res_seq, False):
                continue
            
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
        text_rect = QRectF(10, self.height() - 30, 400, 25)
        
        # Semi-transparent background
        painter.fillRect(text_rect, QColor(0, 0, 0, 120))
        
        # Text
        painter.setPen(QColor(255, 255, 100))  # Yellow text
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                        indicator_text)

    def _draw_dummy_spheres(self, painter, width, height):
        """Draw dummy spheres (COM, centroid, custom) with alpha support and shell sorting."""
        if not self.molecule:
            return
            
        # Check if molecule has dummy spheres
        if not hasattr(self.molecule, 'dummy_spheres'):
            return
            
        dummy_spheres = self.molecule.dummy_spheres
        if not dummy_spheres:
            return

        cx = width / 2 + self.pan_x
        cy = height / 2 + self.pan_y

        cos_x = math.cos(math.radians(self.rot_x))
        sin_x = math.sin(math.radians(self.rot_x))
        cos_y = math.cos(math.radians(self.rot_y))
        sin_y = math.sin(math.radians(self.rot_y))
        
        # Sort spheres: Depth sorting first (furthest first), then Radius sorting for concentric shells.
        # For concentric shells (same position), smaller radius should be drawn inside larger translucent ones
        # to correctly layer them using the Painter's Algorithm.
        
        spheres_with_depth = []
        for sphere in dummy_spheres:
            if not sphere.visible:
                continue
            
            x, y, z = sphere.position
            # Project 3D to 2D for depth sorting
            x1 = x * cos_y + z * sin_y
            z1 = -x * sin_y + z * cos_y
            y1 = y * cos_x - z1 * sin_x
            z2 = y * sin_x + z1 * cos_x
            
            spheres_with_depth.append((sphere, z2))
            
        # Sort primarily by Z (furthest behind first) and secondarily by Radius (LARGER first)
        # This ensures outer shells are drawn BEFORE inner shells at same position,
        # so the inner shell correctly overwrites/layers over the outer shell in the Painter's Algorithm.
        sorted_spheres = sorted(spheres_with_depth, key=lambda s: (s[1], -s[0].radius))
        
        for sphere, sz in sorted_spheres:
            x, y, z = sphere.position
            radius = sphere.radius
            alpha = getattr(sphere, 'alpha', 1.0)
            
            # Use theme color if available
            from src.shared.ui.theme import COLORS
            color_hex = sphere.color # Use sphere instance color if theme doesn't override
            if sphere.label == 'COM':
                color_hex = COLORS.get('sphere_com', color_hex)
            elif sphere.label == 'Centroid':
                color_hex = COLORS.get('sphere_centroid', color_hex)
            
            # Reproject to screen coordinates
            x1 = x * cos_y + z * sin_y
            z1 = -x * sin_y + z * cos_y
            y1 = y * cos_x - z1 * sin_x
            
            sx = cx + x1 * self.zoom
            sy = cy - y1 * self.zoom
            
            # Display radius with depth scaling
            if getattr(sphere, 'label', '') in ['COM', 'Centroid']:
                display_r = radius * self.zoom * self.sphere_scale
            else:
                display_r = radius * self.zoom
            depth_factor = 1.0 + sz * 0.02
            display_r *= max(0.5, min(1.5, depth_factor))
            
            # Convert color to RGB
            color_rgb = _hex_to_rgb(color_hex)
            
            # Draw sphere with alpha
            self._draw_atom_sphere(painter, -1, sx, sy, sz, display_r, color_rgb, alpha=alpha)
            
            # Draw label if sphere has one (only if alpha is high enough to be visible)
            # Suppress 'Custom' label as requested by user to reduce clutter.
            is_custom = hasattr(sphere, 'label') and sphere.label.lower() == 'custom'
            if hasattr(sphere, 'label') and sphere.label and alpha > 0.3 and not is_custom:
                painter.setPen(QColor(255, 255, 255, int(alpha * 255)))
                painter.setFont(QFont('Segoe UI', 8))
                label_rect = QRectF(sx + display_r + 5, sy - 10, 150, 20)
                painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft, sphere.label)

