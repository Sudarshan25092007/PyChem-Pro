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
