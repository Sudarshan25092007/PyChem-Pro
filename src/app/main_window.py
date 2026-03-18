"""
Main Window — Central application window coordinating all components.
"""

import traceback
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QMenuBar, QMenu, QStatusBar, QFileDialog, QMessageBox,
    QSplitter, QApplication, QTabWidget, QColorDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QAction, QKeySequence

from src.shared.ui.theme import get_stylesheet, COLORS
from src.features.visualization_3d.ui.mol_viewer_3d import MolViewer3D
from src.features.visualization_2d.ui.mol_viewer_2d import MolViewer2D
from src.features.control_panel.ui.input_panel import InputPanel
from src.features.scripting_console.ui.python_console import PythonConsole


class ConversionWorker(QObject):
    """Worker for background SMILES conversion."""
    finished = Signal(object, str)  # (molecule, error_msg)
    progress = Signal(int)

    def __init__(self, smiles):
        super().__init__()
        self.smiles = smiles

    def run(self):
        try:
            self.progress.emit(10)

            # Parse SMILES
            from src.features.smiles_parser.services.parser import parse_smiles
            mol = parse_smiles(self.smiles)
            self.progress.emit(30)

            # Generate 3D coordinates
            from src.features.layout_2d.generators.coord_gen import generate_3d_coordinates
            generate_3d_coordinates(mol, optimize=True, max_opt_steps=300)
            self.progress.emit(70)

            # Compute charges
            from src.features.cheminformatics.electrostatics.gasteiger import compute_gasteiger_charges
            compute_gasteiger_charges(mol)
            self.progress.emit(90)

            # Assign types for export
            mol.assign_sybyl_types()
            self.progress.emit(100)

            self.finished.emit(mol, "")
        except Exception as e:
            self.finished.emit(None, str(e))


class MainWindow(QMainWindow):
    """
    Main application window.

    Layout:
    +---------------------------------------------+
    | Menu Bar                                     |
    +---------------------------------------------+
    | Python Console (collapsible)                 |
    +-----------+---------------------------------+
    |           |  [3D View]  [2D View]  (tabs)   |
    | Input     |                                  |
    | Panel     |    Molecular Viewer              |
    |           |                                  |
    +-----------+---------------------------------+
    | Status Bar                                   |
    +---------------------------------------------+
    """

    def __init__(self):
        super().__init__()
        self.molecule = None
        self._worker = None
        self._thread = None

        self.setWindowTitle("SMILES to 3D -- Molecular Structure Converter")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        
        # Enable smooth resizing
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)

        # Apply theme
        self.setStyleSheet(get_stylesheet())

        self._init_menu_bar()
        self._init_central_widget()
        self._init_status_bar()
        self._connect_signals()

    def _init_menu_bar(self):
        """Create menu bar."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        open_smiles = QAction("Open &SMILES File...", self)
        open_smiles.setShortcut(QKeySequence.StandardKey.Open)
        open_smiles.triggered.connect(self._open_smiles_file)
        file_menu.addAction(open_smiles)

        import_mol = QAction("&Import MOL/SDF/MOL2...", self)
        import_mol.setShortcut(QKeySequence("Ctrl+I"))
        import_mol.triggered.connect(self._import_structure_file)
        file_menu.addAction(import_mol)

        file_menu.addSeparator()

        save_sdf = QAction("Save as &SDF...", self)
        save_sdf.setShortcut(QKeySequence("Ctrl+S"))
        save_sdf.triggered.connect(self._export_sdf)
        file_menu.addAction(save_sdf)

        save_mol2 = QAction("Save as &MOL2...", self)
        save_mol2.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_mol2.triggered.connect(self._export_mol2)
        file_menu.addAction(save_mol2)

        save_img = QAction("Export &Image...", self)
        save_img.setShortcut(QKeySequence("Ctrl+E"))
        save_img.triggered.connect(lambda: self._export_image(300, False))
        file_menu.addAction(save_img)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menu_bar.addMenu("&Tools")

        optimize_action = QAction("&Optimize Geometry", self)
        optimize_action.setShortcut(QKeySequence("Ctrl+O"))
        optimize_action.triggered.connect(self._optimize_geometry)
        tools_menu.addAction(optimize_action)

        charges_action = QAction("Compute &Charges", self)
        charges_action.setShortcut(QKeySequence("Ctrl+G"))
        charges_action.triggered.connect(self._compute_charges)
        tools_menu.addAction(charges_action)

        tools_menu.addSeparator()

        auto_rotate = QAction("Toggle &Auto-Rotate", self)
        auto_rotate.setShortcut(QKeySequence("Ctrl+R"))
        auto_rotate.triggered.connect(lambda: self.viewer_3d.toggle_auto_rotate())
        tools_menu.addAction(auto_rotate)

        reset_view = QAction("&Reset View", self)
        reset_view.setShortcut(QKeySequence("Ctrl+0"))
        reset_view.triggered.connect(lambda: self.viewer_3d.reset_view())
        tools_menu.addAction(reset_view)

        # View menu
        view_menu = menu_bar.addMenu("&View")

        toggle_h = QAction("Toggle &Hydrogens", self)
        toggle_h.setShortcut(QKeySequence("Ctrl+H"))
        toggle_h.triggered.connect(self._toggle_hydrogens)
        view_menu.addAction(toggle_h)

        toggle_labels = QAction("Toggle &Labels", self)
        toggle_labels.setShortcut(QKeySequence("Ctrl+L"))
        toggle_labels.triggered.connect(self._toggle_labels)
        view_menu.addAction(toggle_labels)

        view_menu.addSeparator()

        bg_color_action = QAction("&Background Color...", self)
        bg_color_action.setShortcut(QKeySequence("Ctrl+B"))
        bg_color_action.triggered.connect(self._change_bg_color)
        view_menu.addAction(bg_color_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_central_widget(self):
        """Create central widget with console on top, tabbed viewer below."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Vertical splitter: console on top, content below
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.setHandleWidth(3)

        # Python console (top)
        self.console = PythonConsole()
        v_splitter.addWidget(self.console)

        # Horizontal splitter: input panel + tabbed viewer (bottom)
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        h_splitter.setHandleWidth(2)

        # Input panel (left)
        self.input_panel = InputPanel()
        self.input_panel.setStyleSheet(f"background-color: {COLORS['bg_secondary']};")
        h_splitter.addWidget(self.input_panel)

        # Tabbed viewer area (right)
        self.viewer_tabs = QTabWidget()
        self.viewer_tabs.setTabPosition(QTabWidget.TabPosition.North)

        self.viewer_3d = MolViewer3D()
        self.viewer_2d = MolViewer2D()

        self.viewer_tabs.addTab(self.viewer_3d, "3D View")
        self.viewer_tabs.addTab(self.viewer_2d, "2D View")

        h_splitter.addWidget(self.viewer_tabs)
        h_splitter.setStretchFactor(0, 0)
        h_splitter.setStretchFactor(1, 1)

        v_splitter.addWidget(h_splitter)
        v_splitter.setStretchFactor(0, 0)
        v_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(v_splitter)

        # Set viewer references for console selection commands
        self.console.set_viewer(self.viewer_3d, self.viewer_2d)

    def _init_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready -- Enter a SMILES string to begin")

    def _connect_signals(self):
        """Connect all widget signals."""
        self.input_panel.convert_requested.connect(self._convert_smiles)
        self.input_panel.optimize_requested.connect(self._optimize_geometry)
        self.input_panel.charges_requested.connect(self._compute_charges)
        self.input_panel.export_sdf_requested.connect(self._export_sdf)
        self.input_panel.export_mol2_requested.connect(self._export_mol2)
        self.input_panel.export_image_requested.connect(self._export_image)

        # Radius sliders
        self.input_panel.sphere_scale_changed.connect(
            lambda v: setattr(self.viewer_3d, 'sphere_scale', v) or self.viewer_3d.update())
        self.input_panel.stick_scale_changed.connect(
            lambda v: setattr(self.viewer_3d, 'stick_scale', v) or self.viewer_3d.update())
        self.input_panel.line_scale_changed.connect(
            lambda v: setattr(self.viewer_3d, 'line_scale', v) or self.viewer_3d.update())

        # View options
        self.input_panel.show_h_check.toggled.connect(self._toggle_hydrogens)
        self.input_panel.show_labels_check.toggled.connect(self._toggle_labels)
        self.input_panel.show_sidechains_check.toggled.connect(self._toggle_sidechains)
        self.input_panel.render_combo.currentIndexChanged.connect(self._change_render_mode)

    # ─── Core Actions ──────────────────────────────────────────────

    def _convert_smiles(self, smiles):
        """Convert SMILES to 3D structure."""
        self.status_bar.showMessage(f"Converting: {smiles}")
        self.input_panel.set_progress(5)
        self.input_panel.convert_btn.setEnabled(False)

        self._thread = QThread()
        self._worker = ConversionWorker(smiles)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.input_panel.set_progress)
        self._worker.finished.connect(self._on_conversion_done)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_conversion_done(self, molecule, error):
        """Handle conversion result."""
        self.input_panel.convert_btn.setEnabled(True)
        self.input_panel.set_progress(0)

        if error:
            self.status_bar.showMessage(f"Error: {error}")
            QMessageBox.critical(self, "Conversion Error",
                                f"Failed to convert SMILES:\n\n{error}")
            return

        self._set_molecule(molecule)
        self.status_bar.showMessage(
            f"Converted: {molecule.molecular_formula()} -- "
            f"{len(molecule.atoms)} atoms, {len(molecule.bonds)} bonds")

    def _set_molecule(self, molecule):
        """Set molecule across all viewers and panels."""
        self.molecule = molecule
        self.viewer_3d.set_molecule(molecule)
        
        # Skip 2D generation for large proteins (>1000 atoms)
        is_protein = molecule.properties.get('is_protein', False)
        num_atoms = len(molecule.atoms)
        
        if is_protein and num_atoms > 1000:
            # Set 2D viewer to show placeholder instead of generating coordinates
            self.viewer_2d.clear()
            self.viewer_2d.show_protein_placeholder = True
            self.viewer_2d.update()
        else:
            # Generate 2D coordinates for small molecules
            self.viewer_2d.set_molecule(molecule)
            self.viewer_2d.show_protein_placeholder = False
        
        self.console.set_molecule(molecule)
        self.input_panel.update_molecule_info(molecule)
        self.input_panel.enable_tools(True)

    def _optimize_geometry(self):
        if not self.molecule:
            return
        self.status_bar.showMessage("Optimizing geometry...")
        QApplication.processEvents()
        try:
            from src.features.layout_3d.forcefield.optimizer import optimize_geometry
            energy, converged, steps = optimize_geometry(
                self.molecule, max_steps=500, method='lbfgs')
            self.viewer_3d.set_molecule(self.molecule)
            status = "converged" if converged else f"after {steps} steps"
            self.status_bar.showMessage(
                f"Optimized ({status}), Energy: {energy:.2f}")
        except Exception as e:
            self.status_bar.showMessage(f"Optimization error: {e}")

    def _compute_charges(self):
        if not self.molecule:
            return
        self.status_bar.showMessage("Computing charges...")
        QApplication.processEvents()
        try:
            from src.features.cheminformatics.electrostatics.gasteiger import compute_gasteiger_charges
            compute_gasteiger_charges(self.molecule)
            self.input_panel.update_molecule_info(self.molecule)
            self.viewer_3d.update()
            self.status_bar.showMessage("Gasteiger charges computed")
        except Exception as e:
            self.status_bar.showMessage(f"Charge computation error: {e}")

    # ─── Import ────────────────────────────────────────────────────

    def _import_structure_file(self):
        """Import a molecule from MOL, SDF, MOL2, or PDB file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Structure File", "",
            "All Structure Files (*.mol *.sdf *.mol2 *.pdb *.ent);;"
            "PDB Files (*.pdb *.ent);;"
            "MOL Files (*.mol);;"
            "SDF Files (*.sdf);;"
            "MOL2 Files (*.mol2);;"
            "All Files (*)")
        if not filepath:
            return

        # Check file size for large files
        import os
        file_size = os.path.getsize(filepath) / 1024  # KB
        
        if file_size > 100:  # Large file warning
            self.status_bar.showMessage(f"Importing large file ({file_size:.1f}KB): {filepath}")
            # Show loading cursor for large files
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            self.status_bar.showMessage(f"Importing: {filepath}")
        
        QApplication.processEvents()

        try:
            from src.features.io.loaders.file_reader import read_mol, read_sdf, read_mol2, read_pdb

            ext = filepath.lower().rsplit('.', 1)[-1] if '.' in filepath else ''

            if ext in ('pdb', 'ent'):
                mol = read_pdb(filepath)
            elif ext == 'sdf':
                mol = read_sdf(filepath)
            elif ext == 'mol2':
                mol = read_mol2(filepath)
            elif ext == 'mol':
                mol = read_mol(filepath)
            else:
                # Try PDB first (common), then SDF, MOL, MOL2
                try:
                    mol = read_pdb(filepath)
                except Exception:
                    try:
                        mol = read_sdf(filepath)
                    except Exception:
                        try:
                            mol = read_mol(filepath)
                        except Exception:
                            mol = read_mol2(filepath)

            # Assign hybridization and SYBYL types if not already set
            try:
                mol.assign_hybridization()
                mol.assign_sybyl_types()
            except Exception:
                pass

            # Compute charges if not present
            has_charges = any(a.partial_charge != 0 for a in mol.atoms)
            if not has_charges:
                try:
                    from src.features.cheminformatics.electrostatics.gasteiger import compute_gasteiger_charges
                    compute_gasteiger_charges(mol)
                except Exception:
                    pass

            self._set_molecule(mol)

            # Show protein-specific info
            is_protein = mol.properties.get('is_protein', False)
            info = f"Imported: {mol.name or filepath} -- {len(mol.atoms)} atoms, {len(mol.bonds)} bonds"
            if is_protein:
                info += " [PROTEIN]"
            self.status_bar.showMessage(info)

        except Exception as e:
            self.status_bar.showMessage(f"Import error: {e}")
            QMessageBox.critical(self, "Import Error",
                                f"Failed to import file:\n\n{e}")
        finally:
            # Restore cursor
            QApplication.restoreOverrideCursor()

    # ─── Export ────────────────────────────────────────────────────

    def _export_sdf(self):
        if not self.molecule:
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save SDF File", "",
            "SDF Files (*.sdf);;MOL Files (*.mol);;All Files (*)")
        if filepath:
            try:
                from src.features.io.exporters.sdf_writer import write_sdf
                write_sdf(self.molecule, filepath)
                self.status_bar.showMessage(f"Saved: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def _export_mol2(self):
        if not self.molecule:
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save MOL2 File", "",
            "MOL2 Files (*.mol2);;All Files (*)")
        if filepath:
            try:
                from src.features.io.exporters.mol2_writer import write_mol2
                write_mol2(self.molecule, filepath)
                self.status_bar.showMessage(f"Saved: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def _open_smiles_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open SMILES File", "",
            "Text Files (*.txt *.smi);;All Files (*)")
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                for line in lines:
                    smiles = line.strip().split()[0] if line.strip() else ""
                    if smiles:
                        self.input_panel.smiles_input.setPlainText(smiles)
                        self._convert_smiles(smiles)
                        break
            except Exception as e:
                QMessageBox.critical(self, "File Error", str(e))

    def _export_image(self, dpi, white_bg):
        if not self.molecule:
            return

        # Export from whichever tab is active
        current_viewer = self.viewer_tabs.currentWidget()

        filepath, _ = QFileDialog.getSaveFileName(
            self, f"Export Image ({dpi} DPI)", "",
            "PNG Image (*.png);;TIFF Image (*.tiff *.tif);;JPEG Image (*.jpg *.jpeg);;BMP Image (*.bmp);;All Files (*)")
        if filepath:
            try:
                success = current_viewer.export_image(filepath, dpi=dpi, bg_white=white_bg)
                if success:
                    self.status_bar.showMessage(f"Image saved: {filepath} ({dpi} DPI)")
                else:
                    QMessageBox.warning(self, "Export Error", "Failed to save image.")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    # ─── View Options ─────────────────────────────────────────────

    def _toggle_hydrogens(self):
        checked = self.input_panel.show_h_check.isChecked()
        self.viewer_3d.show_hydrogens = checked
        self.viewer_3d.update()
        self.viewer_2d.show_hydrogens = checked
        self.viewer_2d.update()

    def _toggle_labels(self):
        self.viewer_3d.show_labels = self.input_panel.show_labels_check.isChecked()
        self.viewer_3d.update()

    def _toggle_sidechains(self):
        self.viewer_3d.show_sidechains = self.input_panel.show_sidechains_check.isChecked()
        self.viewer_3d.update()

    def _change_render_mode(self, index):
        modes = ['ball_and_stick', 'spacefill', 'wireframe', 'cartoon', 'ribbon', 'backbone']
        if 0 <= index < len(modes):
            self.viewer_3d.render_mode = modes[index]
            self.viewer_3d.update()

    def _change_bg_color(self):
        """Open color picker to change viewer background."""
        from PySide6.QtGui import QColor
        current = self.viewer_3d.bg_color
        color = QColorDialog.getColor(
            current, self, "Choose Background Color",
            QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self.viewer_3d.bg_color = color
            self.viewer_3d.update()
            self.viewer_2d.bg_color = color
            self.viewer_2d.update()
            self.status_bar.showMessage(
                f"Background: {color.name()}")

    # ─── About ────────────────────────────────────────────────────

    def _show_about(self):
        QMessageBox.about(
            self, "About SMILES to 3D",
            "<h2>SMILES to 3D Converter</h2>"
            "<p>Version 1.1.0</p>"
            "<p>A from-scratch molecular structure converter with:</p>"
            "<ul>"
            "<li>Full-spec SMILES parser</li>"
            "<li>2D and 3D structure visualization</li>"
            "<li>Distance geometry 3D generation</li>"
            "<li>Geometry optimization</li>"
            "<li>Gasteiger-Marsili partial charges</li>"
            "<li>MOL/SDF/MOL2 import and export</li>"
            "<li>Embedded Python console</li>"
            "</ul>"
            "<p>Built entirely without external cheminformatics libraries.</p>"
        )

    def resizeEvent(self, event):
        """Handle window resize events safely."""
        try:
            # Call parent resize event
            super().resizeEvent(event)
            
            # Update viewers if they exist
            if hasattr(self, 'viewer_3d') and self.viewer_3d:
                self.viewer_3d.update()
            if hasattr(self, 'viewer_2d') and self.viewer_2d:
                self.viewer_2d.update()
                
        except Exception as e:
            # Prevent crashes during resize
            print(f"Resize error: {e}")
            pass
