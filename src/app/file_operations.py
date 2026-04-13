"""
File Operations — Open, save, export, drag-and-drop, and recent-file handling.

All functions receive the MainWindow instance as ``window``.
"""

import os
import time

from src.shared.qt_compat import (
    QApplication, QFileDialog, QMessageBox, QAction, QSettings, Qt,
)
from src.core.performance import ParallelFileLoader, get_profiler

_DEBUG = False


# ── Open / Import ─────────────────────────────────────────────────

def open_smiles_file(window):
    filepath, _ = QFileDialog.getOpenFileName(
        window, "Open SMILES File", "",
        "Text Files (*.txt *.smi);;All Files (*)")
    if filepath:
        try:
            with open(filepath, 'r') as f:
                content = f.read().strip()
            smiles = content.split()[0]
            window.input_panel.smiles_input.setText(smiles)
            window._convert_smiles(smiles)
            add_recent_file(window, filepath)
        except Exception as e:
            QMessageBox.critical(window, "Error", f"Failed to read file:\n{e}")


def import_structure_file(window, filepath=None):
    """Import a molecule from MOL, SDF, MOL2, or PDB file."""
    if not filepath:
        filepath, _ = QFileDialog.getOpenFileName(
            window, "Import Structure File", "",
            "All Structure Files (*.mol *.sdf *.mol2 *.pdb *.ent);;"
            "PDB Files (*.pdb *.ent);;"
            "MOL Files (*.mol);;"
            "SDF Files (*.sdf);;"
            "MOL2 Files (*.mol2);;"
            "All Files (*)")
    if not filepath:
        print("[DEBUG] No file selected")
        return

    print(f"[DEBUG] Selected file: {filepath}")

    file_size = os.path.getsize(filepath) / 1024  # KB
    print(f"[DEBUG] File size: {file_size:.1f} KB")

    if file_size > 100:
        window.status_bar.showMessage(f"Importing large file ({file_size:.1f}KB): {filepath}")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    else:
        window.status_bar.showMessage(f"Importing: {filepath}")

    QApplication.processEvents()

    load_start_time = time.time()

    try:
        loader = ParallelFileLoader(parallel_threshold_kb=100.0, use_parallel=False)

        ext = filepath.lower().rsplit('.', 1)[-1] if '.' in filepath else ''
        print(f"[DEBUG] File extension: {ext}")

        with get_profiler().time_operation("file_load"):
            mol = loader.load_file(filepath)

        load_time = time.time() - load_start_time
        print(f"[DEBUG] File loaded in {load_time:.3f}s")

        if mol is None:
            raise ValueError("Failed to parse molecule - no atoms loaded")

        mol.properties['source_format'] = ext if ext in ('pdb', 'ent') else 'unknown'

        print(f"[DEBUG] Molecule loaded: {len(mol.atoms)} atoms, {len(mol.bonds)} bonds")
        print(f"[DEBUG] Molecule name: {mol.name}")
        print(f"[DEBUG] Properties: {mol.properties}")

        num_atoms = len(mol.atoms)
        if num_atoms <= 150:
            print("[DEBUG] Assigning hybridization...")
            try:
                mol.assign_hybridization()
                mol.assign_sybyl_types()

                from src.features.smiles_parser.rules.aromaticity import perceive_aromaticity
                perceive_aromaticity(mol)
            except Exception as e:
                print(f"[DEBUG] Molecule typing/aromaticity failed: {e}")

            print("[DEBUG] Computing charges...")
            has_charges = any(a.partial_charge != 0 for a in mol.atoms)
            if not has_charges:
                try:
                    from src.features.cheminformatics.electrostatics.gasteiger import compute_gasteiger_charges
                    compute_gasteiger_charges(mol)
                except Exception as e:
                    print(f"[DEBUG] charge computation failed: {e}")
        else:
            print("[DEBUG] Skipping hybridization/charges for large structure to ensure fast load speed")

        print("[DEBUG] Calling _set_molecule...")
        window._set_molecule(mol)

        is_protein = mol.properties.get('is_protein', False)
        info = f"Imported: {mol.name or filepath} -- {len(mol.atoms)} atoms, {len(mol.bonds)} bonds"
        if is_protein:
            info += " [PROTEIN]"
        window.status_bar.showMessage(info)
        add_recent_file(window, filepath)

    except Exception as e:
        window.status_bar.showMessage(f"Import error: {e}")
        QMessageBox.critical(window, "Import Error",
                            f"Failed to import file:\n\n{e}")
    finally:
        QApplication.restoreOverrideCursor()


# ── Export ────────────────────────────────────────────────────────

def export_sdf(window):
    if not window.molecule:
        return
    filepath, _ = QFileDialog.getSaveFileName(
        window, "Save SDF File", "",
        "SDF Files (*.sdf);;MOL Files (*.mol);;All Files (*)")
    if filepath:
        try:
            from src.features.io.exporters.sdf_writer import write_sdf
            write_sdf(window.molecule, filepath)
            window.status_bar.showMessage(f"Saved: {filepath}")
        except Exception as e:
            QMessageBox.critical(window, "Export Error", str(e))


def export_mol2(window):
    if not window.molecule:
        return
    filepath, _ = QFileDialog.getSaveFileName(
        window, "Save MOL2 File", "",
        "MOL2 Files (*.mol2);;All Files (*)")
    if filepath:
        try:
            from src.features.io.exporters.mol2_writer import write_mol2
            write_mol2(window.molecule, filepath)
            window.status_bar.showMessage(f"Saved: {filepath}")
        except Exception as e:
            QMessageBox.critical(window, "Export Error", str(e))


def export_image(window, dpi, white_bg):
    if not window.molecule:
        return

    current_viewer = window.viewer_tabs.currentWidget()

    filepath, _ = QFileDialog.getSaveFileName(
        window, f"Export Image ({dpi} DPI)", "",
        "PNG Image (*.png);;TIFF Image (*.tiff *.tif);;JPEG Image (*.jpg *.jpeg);;BMP Image (*.bmp);;All Files (*)")
    if filepath:
        try:
            success = current_viewer.export_image(filepath, dpi=dpi, bg_white=white_bg)
            if success:
                window.status_bar.showMessage(f"Image saved: {filepath} ({dpi} DPI)")
            else:
                QMessageBox.warning(window, "Export Error", "Failed to save image.")
        except Exception as e:
            QMessageBox.critical(window, "Export Error", str(e))


# ── Print ────────────────────────────────────────────────────────

def _render_print_content(window, painter, page_rect, is_preview=False):
    """
    Render the print content (2D and 3D views) to a QPainter.
    
    Args:
        window: MainWindow instance
        painter: QPainter to render to
        page_rect: QRectF of the printable area
        is_preview: If True, add a watermark indicating preview mode
    """
    from PySide6.QtGui import QImage, QColor, QFont, QPainter
    from PySide6.QtCore import Qt, QRectF
    
    page_w = int(page_rect.width())
    page_h = int(page_rect.height())
    margin = int(min(page_w, page_h) * 0.03)

    # Split page into top (2D) and bottom (3D) halves
    half_h = (page_h - 3 * margin) // 2
    top_rect = QRectF(margin, margin, page_w - 2 * margin, half_h)
    bot_rect = QRectF(margin, margin * 2 + half_h,
                      page_w - 2 * margin, half_h)

    # Render each viewer into its own QImage
    def _render_viewer(viewer, width, height, viewer_name="viewer"):
        img = QImage(int(width), int(height),
                     QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor(255, 255, 255))
        p = QPainter(img)
        try:
            if hasattr(viewer, '_render'):
                # Both 3D and 2D viewers have _render method
                # 3D: _render(painter, w, h, is_export, scale)
                # 2D: _render(painter, w, h)
                old_bg = getattr(viewer, 'bg_color', None)
                if old_bg is not None:
                    viewer.bg_color = QColor(255, 255, 255)
                
                # Check if 2D or 3D viewer based on method signature
                import inspect
                sig = inspect.signature(viewer._render)
                params = list(sig.parameters.keys())
                
                if 'is_export' in params:
                    # 3D viewer
                    viewer._render(p, int(width), int(height),
                                   is_export=True, export_scale=1.0)
                else:
                    # 2D viewer - check if it has coordinates
                    if hasattr(viewer, 'coords_2d') and viewer.coords_2d:
                        # Temporarily adjust scale/offset for print dimensions
                        _saved_scale = viewer._scale
                        _saved_ox = viewer._offset_x
                        _saved_oy = viewer._offset_y
                        try:
                            # Compute fit for print dimensions
                            coords = viewer.coords_2d
                            visible = set(coords.keys())
                            xs = [c[0] for c in coords.values() if c[0] is not None]
                            ys = [c[1] for c in coords.values() if c[1] is not None]
                            if xs and ys:
                                min_x, max_x = min(xs), max(xs)
                                min_y, max_y = min(ys), max(ys)
                                span_x = max_x - min_x or 1
                                span_y = max_y - min_y or 1
                                cx = (min_x + max_x) / 2
                                cy = (min_y + max_y) / 2
                                margin = 40
                                scale_x = (width - margin * 2) / span_x
                                scale_y = (height - margin * 2) / span_y
                                viewer._scale = min(scale_x, scale_y, 80)
                                viewer._offset_x = width / 2 - cx * viewer._scale
                                viewer._offset_y = height / 2 + cy * viewer._scale
                            # Render with is_export=True
                            viewer._render(p, int(width), int(height), is_export=True, export_scale=1.0)
                        finally:
                            # Restore original view settings
                            viewer._scale = _saved_scale
                            viewer._offset_x = _saved_ox
                            viewer._offset_y = _saved_oy
                    else:
                        # Draw placeholder for empty 2D view
                        p.setPen(QColor(150, 150, 150))
                        font = QFont("Arial", 12)
                        p.setFont(font)
                        p.drawText(10, int(height/2), "2D view not available")
                
                if old_bg is not None:
                    viewer.bg_color = old_bg
            else:
                # Fallback: widget's default render
                viewer.render(p)
        except Exception as e:
            print(f"[PRINT RENDER ERROR] {viewer_name}: {e}")
            import traceback
            traceback.print_exc()
            # Draw error indicator on image
            p.setPen(QColor(255, 0, 0))
            font = QFont("Arial", 10)
            p.setFont(font)
            p.drawText(10, 20, f"Render error: {str(e)[:50]}")
        finally:
            p.end()
        return img

    # Render 2D
    v2d = window.viewer_2d
    img_2d = _render_viewer(v2d, top_rect.width(), top_rect.height(), "2D")

    # Render 3D
    v3d = window.viewer_3d
    img_3d = _render_viewer(v3d, bot_rect.width(), bot_rect.height(), "3D")

    # Draw headers
    title_font = QFont("Helvetica", 14)
    title_font.setBold(True)
    painter.setFont(title_font)
    painter.setPen(QColor(0, 0, 0))

    mol_name = getattr(window.molecule, 'name', None) or 'Molecule'
    try:
        mol_formula = window.molecule.molecular_formula()
    except:
        mol_formula = "?"
    num_atoms = getattr(window.molecule, 'num_atoms', 0)
    num_bonds = getattr(window.molecule, 'num_bonds', 0)
    
    header_text = (
        f"PyChem -- {mol_name}  |  "
        f"{mol_formula}  |  "
        f"{num_atoms} atoms, "
        f"{num_bonds} bonds"
    )
    painter.drawText(QRectF(margin, margin * 0.25,
                             page_w - 2 * margin, margin * 0.7),
                      int(Qt.AlignmentFlag.AlignLeft |
                          Qt.AlignmentFlag.AlignVCenter),
                      header_text)

    # Draw labels
    label_font = QFont("Helvetica", 10)
    label_font.setBold(True)
    painter.setFont(label_font)
    painter.drawText(QRectF(margin, top_rect.y() - margin * 0.6,
                             page_w - 2 * margin, margin * 0.6),
                      int(Qt.AlignmentFlag.AlignLeft),
                      "2D View")
    painter.drawText(QRectF(margin, bot_rect.y() - margin * 0.6,
                             page_w - 2 * margin, margin * 0.6),
                      int(Qt.AlignmentFlag.AlignLeft),
                      "3D View")

    # Draw the two images into their respective halves
    painter.drawImage(top_rect, img_2d)
    painter.drawImage(bot_rect, img_3d)
    
    # Add preview watermark if in preview mode
    if is_preview:
        watermark_font = QFont("Helvetica", 48)
        watermark_font.setBold(True)
        painter.setFont(watermark_font)
        painter.setPen(QColor(200, 200, 200, 100))  # Semi-transparent gray
        painter.drawText(page_rect, int(Qt.AlignmentFlag.AlignCenter), "PREVIEW")


def print_preview(window):
    """
    Show a print preview dialog for the 2D and 3D views.
    
    This allows users to see how the print will look before sending to printer.
    """
    if not window.molecule:
        window.status_bar.showMessage("No molecule to preview")
        return

    try:
        from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
        from PySide6.QtGui import QPainter
    except ImportError:
        QMessageBox.critical(
            window, "Print Preview Error",
            "Qt print support is not available. Please install PySide6 with "
            "print support (PySide6 >= 6.5 normally includes it)."
        )
        return

    # Configure printer with sensible defaults
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setDocName(f"PyChem - {window.molecule.name or 'molecule'}")

    # Create preview dialog
    preview_dialog = QPrintPreviewDialog(printer, window)
    preview_dialog.setWindowTitle("Print Preview - 2D + 3D Views")
    
    # Connect the paint requested signal
    def handle_paint_request(printer_obj):
        from PySide6.QtPrintSupport import QPrinter
        from PySide6.QtGui import QFont, QColor, QPainter
        painter = QPainter(printer_obj)
        try:
            page_rect = printer_obj.pageRect(QPrinter.Unit.DevicePixel)
            _render_print_content(window, painter, page_rect, is_preview=True)
        except Exception as e:
            print(f"[PRINT PREVIEW ERROR] {e}")
            import traceback
            traceback.print_exc()
            # Draw error message on page
            painter.setPen(QColor(255, 0, 0))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(100, 100, f"Preview Error: {str(e)}")
        finally:
            painter.end()
    
    preview_dialog.paintRequested.connect(handle_paint_request)
    preview_dialog.exec()


def print_views(window):
    """
    Print both 2D and 3D views of the current molecule to a single page.

    Opens a native QPrintDialog, then renders:
      * the 2D viewer into the top half of the printable area
      * the 3D viewer into the bottom half of the printable area
    Both views are fitted and centered inside their half, preserving
    aspect ratio, so the molecule is fully visible on the page.
    """
    if not window.molecule:
        window.status_bar.showMessage("No molecule to print")
        return

    try:
        from PySide6.QtPrintSupport import QPrinter, QPrintDialog
        from PySide6.QtGui import QPainter
    except ImportError:
        QMessageBox.critical(
            window, "Print Error",
            "Qt print support is not available. Please install PySide6 with "
            "print support (PySide6 >= 6.5 normally includes it)."
        )
        return

    # Configure printer with sensible defaults
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setDocName(f"PyChem - {window.molecule.name or 'molecule'}")

    dialog = QPrintDialog(printer, window)
    dialog.setWindowTitle("Print 2D + 3D Views")
    if dialog.exec() != QPrintDialog.DialogCode.Accepted:
        return

    try:
        # Get printable area in device pixels
        page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        
        # Paint onto the printer
        page_painter = QPainter(printer)
        try:
            _render_print_content(window, page_painter, page_rect, is_preview=False)
        finally:
            page_painter.end()

        window.status_bar.showMessage("Print job sent")
    except Exception as e:
        QMessageBox.critical(window, "Print Error",
                             f"Failed to print:\n{e}")
        window.status_bar.showMessage(f"Print error: {e}")


# ── Drag & Drop ──────────────────────────────────────────────────

def handle_drag_enter(window, event):
    if event.mimeData().hasUrls():
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            ext = urls[0].toLocalFile().lower()
            if ext.endswith(('.smi', '.mol', '.sdf', '.mol2', '.pdb', '.ent')):
                event.acceptProposedAction()
                return
    event.ignore()


def handle_drop(window, event):
    urls = event.mimeData().urls()
    if urls and urls[0].isLocalFile():
        filepath = urls[0].toLocalFile()
        ext = filepath.lower()
        if ext.endswith('.smi'):
            try:
                with open(filepath, 'r') as f:
                    smiles = f.read().strip().split()[0]
                window.input_panel.smiles_input.setText(smiles)
                window._convert_smiles(smiles)
                add_recent_file(window, filepath)
            except Exception as e:
                window.status_bar.showMessage(f"Error reading SMILES: {e}")
        else:
            window._import_structure_file(filepath)
        event.acceptProposedAction()


# ── Recent Files ─────────────────────────────────────────────────

def update_recent_files_menu(window):
    """Update recent files context menu."""
    window.recent_menu.clear()
    settings = QSettings("PyChem", "Viewer")
    files = settings.value("recent_files", [])
    if not isinstance(files, list):
        files = []
    for f in files:
        action = QAction(f, window)
        action.triggered.connect(lambda checked=False, path=f: open_recent_file(window, path))
        window.recent_menu.addAction(action)
    if not files:
        action = QAction("No Recent Files", window)
        action.setEnabled(False)
        window.recent_menu.addAction(action)


def open_recent_file(window, filepath):
    if not os.path.exists(filepath):
        QMessageBox.warning(window, "Error", f"File not found:\n{filepath}")
        return
    ext = filepath.lower()
    if ext.endswith('.smi'):
        try:
            with open(filepath, 'r') as f:
                smiles = f.read().strip().split()[0]
            window.input_panel.smiles_input.setText(smiles)
            window._convert_smiles(smiles)
        except Exception as e:
            window.status_bar.showMessage(f"Error reading SMILES: {e}")
    else:
        window._import_structure_file(filepath)


def add_recent_file(window, filepath):
    settings = QSettings("PyChem", "Viewer")
    files = settings.value("recent_files", [])
    if not isinstance(files, list):
        files = []
    if filepath in files:
        files.remove(filepath)
    files.insert(0, filepath)
    if len(files) > 5:
        files = files[:5]
    settings.setValue("recent_files", files)
    update_recent_files_menu(window)
