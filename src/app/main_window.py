"""
Main Window — Central application window coordinating all components.
"""

import traceback
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QMenuBar, QMenu, QStatusBar, QFileDialog, QMessageBox,
    QSplitter, QApplication, QTabWidget, QColorDialog,
    QComboBox, QPushButton, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QSettings
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
        self.setAcceptDrops(True)
        
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
        import_mol.triggered.connect(lambda: self._import_structure_file(None))
        file_menu.addAction(import_mol)

        self.recent_menu = file_menu.addMenu("Open &Recent")
        self._update_recent_files_menu()

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

        toggle_com = QAction("Toggle &COM Sphere", self)
        toggle_com.setCheckable(True)
        toggle_com.setChecked(False)
        toggle_com.triggered.connect(self._toggle_com_sphere)
        self._toggle_com_action = toggle_com  # Store reference in main window
        view_menu.addAction(toggle_com)

        toggle_centroid = QAction("Toggle &Centroid Sphere", self)
        toggle_centroid.setCheckable(True)
        toggle_centroid.setChecked(False)
        toggle_centroid.triggered.connect(self._toggle_centroid_sphere)
        self._toggle_centroid_action = toggle_centroid  # Store reference in main window
        view_menu.addAction(toggle_centroid)

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
        self.input_panel.setMinimumWidth(340)
        self.input_panel.setStyleSheet(f"background-color: {COLORS['bg_secondary']};")
        h_splitter.addWidget(self.input_panel)

        # Tabbed viewer area (right)
        self.viewer_tabs = QTabWidget()
        self.viewer_tabs.setTabPosition(QTabWidget.TabPosition.North)
        
        # Tools Toolbar (Top Right Corner)
        toolbar = QWidget()
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(0, 0, 8, 0)
        tb_layout.setSpacing(10)

        # Optimization method dropdown
        self.opt_combo = QComboBox()
        self.opt_combo.addItems(["MMFF94", "AM1"])
        self.opt_combo.setStyleSheet(f"QComboBox {{ background: {COLORS['bg_widget']}; color: {COLORS['text_primary']}; padding: 2px 6px; border-radius: 4px; }}")
        
        self.optimize_btn = QPushButton("Optimize")
        self.optimize_btn.setObjectName("btnSecondary")
        self.optimize_btn.clicked.connect(self._optimize_geometry)
        self.optimize_btn.setEnabled(False)
        
        tb_layout.addWidget(self.opt_combo)
        tb_layout.addWidget(self.optimize_btn)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFrameShadow(QFrame.Shadow.Sunken)
        tb_layout.addWidget(sep1)

        self.chg_combo = QComboBox()
        self.chg_combo.addItems(["Gasteiger", "MMFF94", "AM1", "PM3"])
        self.chg_combo.setStyleSheet(f"QComboBox {{ background: {COLORS['bg_widget']}; color: {COLORS['text_primary']}; padding: 2px 6px; border-radius: 4px; }}")
        self.charges_btn = QPushButton("Charges")
        self.charges_btn.setObjectName("btnSecondary")
        self.charges_btn.clicked.connect(self._compute_charges)
        self.charges_btn.setEnabled(False)
        tb_layout.addWidget(self.chg_combo)
        tb_layout.addWidget(self.charges_btn)
        
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        tb_layout.addWidget(sep2)
        
        # Color customization button
        self.color_btn = QPushButton("Colors")
        self.color_btn.setObjectName("btnSecondary")
        self.color_btn.clicked.connect(self._show_color_dialog)
        self.color_btn.setEnabled(False)
        tb_layout.addWidget(self.color_btn)
        
        # Dummy sphere buttons
        self.com_sphere_btn = QPushButton("COM Sphere")
        self.com_sphere_btn.setObjectName("btnSecondary")
        self.com_sphere_btn.clicked.connect(self._add_com_sphere)
        self.com_sphere_btn.setEnabled(False)
        tb_layout.addWidget(self.com_sphere_btn)
        
        self.centroid_sphere_btn = QPushButton("Centroid")
        self.centroid_sphere_btn.setObjectName("btnSecondary")
        self.centroid_sphere_btn.clicked.connect(self._add_centroid_sphere)
        self.centroid_sphere_btn.setEnabled(False)
        tb_layout.addWidget(self.centroid_sphere_btn)
        
        self.custom_sphere_btn = QPushButton("Custom Sphere")
        self.custom_sphere_btn.setObjectName("btnSecondary")
        self.custom_sphere_btn.clicked.connect(self._add_custom_sphere)
        self.custom_sphere_btn.setEnabled(False)
        tb_layout.addWidget(self.custom_sphere_btn)
        
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setFrameShadow(QFrame.Shadow.Sunken)
        tb_layout.addWidget(sep3)
        
        # Clear spheres button
        self.clear_spheres_btn = QPushButton("Clear Spheres")
        self.clear_spheres_btn.setObjectName("btnSecondary")
        self.clear_spheres_btn.clicked.connect(self._clear_all_spheres)
        self.clear_spheres_btn.setEnabled(False)
        tb_layout.addWidget(self.clear_spheres_btn)
        
        self.viewer_tabs.setCornerWidget(toolbar, Qt.Corner.TopRightCorner)

        self.viewer_3d = MolViewer3D()
        self.viewer_2d = MolViewer2D()

        self.viewer_tabs.addTab(self.viewer_3d, "3D View")
        self.viewer_tabs.addTab(self.viewer_2d, "2D View")

        h_splitter.addWidget(self.viewer_tabs)
        h_splitter.setStretchFactor(0, 0)
        h_splitter.setStretchFactor(1, 1)
        h_splitter.setSizes([340, 900])

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
        self.input_panel.show_sasa_check.toggled.connect(self._toggle_sasa)
        self.input_panel.sasa_selected_only_check.toggled.connect(self._toggle_sasa_selected_only)
        self.input_panel.render_combo.currentIndexChanged.connect(self._change_render_mode)

    def _toggle_sasa(self, checked):
        self.viewer_3d.show_sasa_surface = checked
        self.viewer_3d.update()

    def _toggle_sasa_selected_only(self, checked):
        self.viewer_3d.show_sasa_selected_only = checked
        if getattr(self.viewer_3d, 'show_sasa_surface', False):
            self.viewer_3d.update()

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
        
        try:
            from src.features.cheminformatics.services.spatial_properties import compute_sasa, compute_center_of_mass
            compute_sasa(molecule)
            compute_center_of_mass(molecule)
        except Exception as e:
            print(f"Skipping SASA/COM evaluation: {e}")
            
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
        self.optimize_btn.setEnabled(True)
        self.charges_btn.setEnabled(True)
        
        # Enable new feature buttons
        self.color_btn.setEnabled(True)
        self.com_sphere_btn.setEnabled(True)
        self.centroid_sphere_btn.setEnabled(True)
        self.custom_sphere_btn.setEnabled(True)
        self.clear_spheres_btn.setEnabled(True)

    def _optimize_geometry(self):
        if not self.molecule:
            return
        method = self.opt_combo.currentText()
        if "AM1" in method:
            self.status_bar.showMessage("Optimizing geometry (AM1)...")
        else:
            self.status_bar.showMessage("Optimizing geometry (MMFF94)...")
        QApplication.processEvents()
        try:
            if "AM1" in method:
                from src.features.cheminformatics.services.am1 import am1_optimize_geometry
                success = am1_optimize_geometry(self.molecule, max_steps=50)
                self.viewer_3d.set_molecule(self.molecule)
                status = "converged" if success else "max steps reached"
                self.status_bar.showMessage(f"Optimized (AM1: {status})")
            else:
                from src.features.cheminformatics.services.mmff94 import mmff94_optimize_geometry
                success = mmff94_optimize_geometry(self.molecule, max_iters=500)
                self.viewer_3d.set_molecule(self.molecule)
                status = "converged" if success else "max steps reached"
                self.status_bar.showMessage(f"Optimized (MMFF94: {status})")
        except Exception as e:
            self.status_bar.showMessage(f"Optimization error: {e}")

    def _compute_charges(self):
        if not self.molecule:
            return
        method = self.chg_combo.currentText()
        if "PM3" in method:
            self.status_bar.showMessage("Computing PM3 charges...")
        elif "AM1" in method:
            self.status_bar.showMessage("Computing AM1 charges...")
        elif "MMFF94" in method:
            self.status_bar.showMessage("Computing MMFF94 charges...")
        else:
            self.status_bar.showMessage("Computing Gasteiger charges...")
        QApplication.processEvents()
        try:
            if "PM3" in method:
                from src.features.cheminformatics.services.pm3 import pm3_assign_charges
                success = pm3_assign_charges(self.molecule)
                if success:
                    self.input_panel.update_molecule_info(self.molecule)
                    self.viewer_3d.update()
                    self.status_bar.showMessage("PM3 partial charges assigned successfully")
                else:
                    self.status_bar.showMessage("PM3 charge calculation failed")
            elif "AM1" in method:
                from src.features.cheminformatics.services.am1 import am1_assign_charges
                success = am1_assign_charges(self.molecule)
                if success:
                    self.input_panel.update_molecule_info(self.molecule)
                    self.viewer_3d.update()
                    self.status_bar.showMessage("AM1 partial charges assigned successfully")
                else:
                    self.status_bar.showMessage("AM1 charge calculation failed")
            elif "MMFF94" in method:
                from src.features.cheminformatics.services.mmff94 import mmff94_assign_charges
                success = mmff94_assign_charges(self.molecule)
                if success:
                    self.input_panel.update_molecule_info(self.molecule)
                    self.viewer_3d.update()
                    self.status_bar.showMessage("MMFF94 partial charges assigned successfully")
                else:
                    self.status_bar.showMessage("MMFF94 charge calculation failed")
            else:
                from src.features.cheminformatics.electrostatics.gasteiger import compute_gasteiger_charges
                compute_gasteiger_charges(self.molecule)
                self.input_panel.update_molecule_info(self.molecule)
                self.viewer_3d.update()
                self.status_bar.showMessage("Gasteiger charges computed")
        except Exception as e:
            self.status_bar.showMessage(f"Charge computation error: {e}")

    # ─── Import ────────────────────────────────────────────────────

    def _import_structure_file(self, filepath=None):
        """Import a molecule from MOL, SDF, MOL2, or PDB file."""
        if not filepath:
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
            self._add_recent_file(filepath)

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
                    content = f.read().strip()
                # Parse first word as SMILES
                smiles = content.split()[0]
                self.input_panel.smiles_input.setText(smiles)
                self._convert_smiles(smiles)
                self._add_recent_file(filepath)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read file:\n{e}")

    # ─── OS Events and UX ──────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                ext = urls[0].toLocalFile().lower()
                if ext.endswith(('.smi', '.mol', '.sdf', '.mol2', '.pdb', '.ent')):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            filepath = urls[0].toLocalFile()
            ext = filepath.lower()
            if ext.endswith('.smi'):
                try:
                    with open(filepath, 'r') as f:
                        smiles = f.read().strip().split()[0]
                    self.input_panel.smiles_input.setText(smiles)
                    self._convert_smiles(smiles)
                    self._add_recent_file(filepath)
                except Exception as e:
                    self.status_bar.showMessage(f"Error reading SMILES: {e}")
            else:
                self._import_structure_file(filepath)
            event.acceptProposedAction()

    def _update_recent_files_menu(self):
        """Update recent files context menu."""
        self.recent_menu.clear()
        settings = QSettings("SMILESApp", "Viewer")
        files = settings.value("recent_files", [])
        if not isinstance(files, list):
            files = []
        for f in files:
            action = QAction(f, self)
            action.triggered.connect(lambda checked=False, path=f: self._open_recent_file(path))
            self.recent_menu.addAction(action)
        if not files:
            action = QAction("No Recent Files", self)
            action.setEnabled(False)
            self.recent_menu.addAction(action)

    def _open_recent_file(self, filepath):
        import os
        if not os.path.exists(filepath):
            QMessageBox.warning(self, "Error", f"File not found:\n{filepath}")
            return
        ext = filepath.lower()
        if ext.endswith('.smi'):
            try:
                with open(filepath, 'r') as f:
                    smiles = f.read().strip().split()[0]
                self.input_panel.smiles_input.setText(smiles)
                self._convert_smiles(smiles)
            except Exception as e:
                self.status_bar.showMessage(f"Error reading SMILES: {e}")
        else:
            self._import_structure_file(filepath)

    def _add_recent_file(self, filepath):
        settings = QSettings("SMILESApp", "Viewer")
        files = settings.value("recent_files", [])
        if not isinstance(files, list):
            files = []
        if filepath in files:
            files.remove(filepath)
        files.insert(0, filepath)
        if len(files) > 5:
            files = files[:5]
        settings.setValue("recent_files", files)
        self._update_recent_files_menu()


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

    def _toggle_com_sphere(self):
        """Toggle COM dummy sphere visibility."""
        if not self.molecule:
            return
        
        # Initialize dummy spheres list if not exists
        if not hasattr(self.molecule, 'dummy_spheres'):
            self.molecule.dummy_spheres = []
        
        # Remove existing COM sphere if present
        self.molecule.dummy_spheres = [s for s in self.molecule.dummy_spheres if getattr(s, 'label', '') != 'COM']
        
        # Add COM sphere if toggled on
        if hasattr(self, '_toggle_com_action') and self._toggle_com_action.isChecked():
            try:
                from src.features.visualization_3d.services.dummy_sphere import DummySphere
                import numpy as np
                
                # Calculate COM
                if hasattr(self.molecule, 'atoms') and len(self.molecule.atoms) > 0:
                    positions = np.array([[atom.x, atom.y, atom.z] for atom in self.molecule.atoms if hasattr(atom, 'x')])
                    if len(positions) > 0:
                        com_pos = np.mean(positions, axis=0)
                        
                        com_sphere = DummySphere(
                            position=tuple(com_pos),
                            radius=0.5,
                            color='#ff0000',  # Red color for COM
                            label="COM"
                        )
                        self.molecule.dummy_spheres.append(com_sphere)
            except Exception as e:
                print(f"Could not create COM sphere: {e}")
        
        # Force viewer update
        if hasattr(self, 'viewer_3d') and hasattr(self.viewer_3d, 'set_molecule'):
            self.viewer_3d.set_molecule(self.molecule)

    def _toggle_centroid_sphere(self):
        """Toggle Centroid dummy sphere visibility."""
        if not self.molecule:
            return
        
        # Initialize dummy spheres list if not exists
        if not hasattr(self.molecule, 'dummy_spheres'):
            self.molecule.dummy_spheres = []
        
        # Remove existing centroid sphere if present
        self.molecule.dummy_spheres = [s for s in self.molecule.dummy_spheres if getattr(s, 'label', '') != 'Centroid']
        
        # Add centroid sphere if toggled on
        if hasattr(self, '_toggle_centroid_action') and self._toggle_centroid_action.isChecked():
            try:
                from src.features.visualization_3d.services.dummy_sphere import DummySphere
                import numpy as np
                
                # Calculate centroid (geometric center)
                if hasattr(self.molecule, 'atoms') and len(self.molecule.atoms) > 0:
                    positions = np.array([[atom.x, atom.y, atom.z] for atom in self.molecule.atoms if hasattr(atom, 'x')])
                    if len(positions) > 0:
                        centroid_pos = np.mean(positions, axis=0)
                        
                        centroid_sphere = DummySphere(
                            position=tuple(centroid_pos),
                            radius=0.5,
                            color='#00ff00',  # Green color for centroid
                            label="Centroid"
                        )
                        self.molecule.dummy_spheres.append(centroid_sphere)
            except Exception as e:
                print(f"Could not create centroid sphere: {e}")
        
        # Force viewer update
        if hasattr(self, 'viewer_3d') and hasattr(self.viewer_3d, 'set_molecule'):
            self.viewer_3d.set_molecule(self.molecule)

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

    def _show_color_dialog(self):
        """Show PySide6-native color dialog to avoid threading issues."""
        if not self.molecule:
            self.status_bar.showMessage("No molecule loaded for color customization")
            return
            
        try:
            # Use PySide6-native color dialog to avoid threading issues
            from src.features.ui.pyside6_color_dialog import show_pyside6_color_dialog, apply_pyside6_colors
            
            print("DEBUG: Opening PySide6 color dialog...")
            
            # Show PySide6 color dialog
            selected_colors = show_pyside6_color_dialog(self)
            
            print(f"DEBUG: Selected colors from PySide6 GUI: {selected_colors}")
            
            if selected_colors:
                print("DEBUG: Applying colors to theme...")
                
                # Apply colors to theme
                apply_pyside6_colors(selected_colors)
                
                print("DEBUG: Updating 3D viewer...")
                
                # Update colors in 3D viewer
                self._update_atom_colors(selected_colors)
                
                color_count = len(selected_colors)
                self.status_bar.showMessage(f"Applied {color_count} GUI colors")
                print(f"DEBUG: Successfully applied {color_count} colors")
            else:
                self.status_bar.showMessage("Color selection cancelled")
                print("DEBUG: Color selection cancelled")
            
        except Exception as e:
            print(f"ERROR in color dialog: {e}")
            import traceback
            traceback.print_exc()
            self.status_bar.showMessage(f"Color dialog error: {str(e)}")
    
    def _basic_color_toggle(self):
        """Basic color toggle as last resort."""
        try:
            from src.shared.ui.theme import COLORS
            
            # Simple color toggle between a few basic schemes
            if not hasattr(self, '_color_toggle_index'):
                self._color_toggle_index = 0
            
            basic_schemes = [
                {'atom_c': '#909090', 'atom_o': '#ff0d0d', 'atom_n': '#3050f8'},  # Default
                {'atom_c': '#ff6b6b', 'atom_o': '#4ecdc4', 'atom_n': '#45b7d1'},  # Pastel
                {'atom_c': '#2ecc71', 'atom_o': '#e74c3c', 'atom_n': '#3498db'},  # Vibrant
            ]
            
            current_scheme = basic_schemes[self._color_toggle_index % len(basic_schemes)]
            COLORS.update(current_scheme)
            
            self._update_atom_colors(current_scheme)
            self._color_toggle_index += 1
            
            scheme_names = ["Default", "Pastel", "Vibrant"]
            current_name = scheme_names[(self._color_toggle_index - 1) % len(scheme_names)]
            
            self.status_bar.showMessage(f"Applied {current_name} color scheme")
            
        except Exception as e:
            self.status_bar.showMessage(f"Color customization unavailable: {e}")

    def _update_atom_colors(self, colors):
        """Update atom colors in 3D viewer."""
        try:
            print(f"DEBUG: _update_atom_colors called with colors: {colors}")
            
            if not self.molecule:
                print("DEBUG: No molecule loaded for color update")
                return
            
            # Debug: Check what methods are available in viewer_3d
            print("DEBUG: Available methods in viewer_3d:")
            if hasattr(self.viewer_3d, '__dict__'):
                methods = [method for method in dir(self.viewer_3d) if not method.startswith('_')]
                print(f"DEBUG: Viewer methods: {methods[:10]}...")  # Show first 10
            
            # CRITICAL FIX: Update atom element colors directly
            print("DEBUG: Updating atom element colors directly...")
            for atom in self.molecule.atoms:
                element_symbol = atom.element.symbol.lower()
                color_key = f'atom_{element_symbol}'
                
                if color_key in colors:
                    new_color = colors[color_key]
                    print(f"DEBUG: Updating {atom.element.symbol} color from {atom.element.color} to {new_color}")
                    
                    # Update the element's color directly
                    atom.element.color = new_color
                    
                    # Also update in theme for consistency
                    from src.shared.ui.theme import COLORS
                    COLORS[color_key] = new_color
            
            # CRITICAL FIX: Update sphere and stick colors in theme
            print("DEBUG: Updating sphere and stick colors...")
            from src.shared.ui.theme import COLORS
            
            # Update sphere colors
            sphere_keys = ['sphere_default', 'sphere_com', 'sphere_centroid', 'sphere_custom']
            for key in sphere_keys:
                if key in colors:
                    COLORS[key] = colors[key]
                    print(f"DEBUG: Updated sphere color {key} to {colors[key]}")
            
            # CRITICAL FIX: Create test dummy sphere only if sphere colors selected
            sphere_keys = ['sphere_default', 'sphere_com', 'sphere_centroid', 'sphere_custom']
            sphere_colors_selected = any(key in colors for key in sphere_keys)
            
            if self.molecule and sphere_colors_selected:
                print("DEBUG: Creating specific dummy spheres (sphere colors selected)...")
                try:
                    from src.features.visualization_3d.services.dummy_sphere import DummySphere
                    import numpy as np
                    
                    # Initialize dummy spheres list if not exists
                    if not hasattr(self.molecule, 'dummy_spheres'):
                        self.molecule.dummy_spheres = []
                    
                    # Create a test sphere at molecule center
                    if hasattr(self.molecule, 'atoms') and len(self.molecule.atoms) > 0:
                        # Calculate molecule center
                        positions = np.array([[atom.x, atom.y, atom.z] for atom in self.molecule.atoms if hasattr(atom, 'x')])
                        if len(positions) > 0:
                            center = np.mean(positions, axis=0)
                            
                            # Create default sphere if default color selected
                            if 'sphere_default' in colors:
                                default_sphere = DummySphere(
                                    position=tuple(center + np.array([0.5, 0.0, 0.0])),
                                    radius=0.5,
                                    color=colors['sphere_default'],
                                    label="Default"
                                )
                                self.molecule.dummy_spheres.append(default_sphere)
                                print("DEBUG: Created default sphere")
                            
                            # Create COM sphere if COM color selected
                            if 'sphere_com' in colors:
                                com_sphere = DummySphere(
                                    position=tuple(center + np.array([0.0, 0.5, 0.0])),
                                    radius=0.5,
                                    color=colors['sphere_com'],
                                    label="COM"
                                )
                                self.molecule.dummy_spheres.append(com_sphere)
                                print("DEBUG: Created COM sphere")
                            
                            # Create centroid sphere if centroid color selected
                            if 'sphere_centroid' in colors:
                                centroid_sphere = DummySphere(
                                    position=tuple(center + np.array([0.0, -0.5, 0.0])),
                                    radius=0.5,
                                    color=colors['sphere_centroid'],
                                    label="Centroid"
                                )
                                self.molecule.dummy_spheres.append(centroid_sphere)
                                print("DEBUG: Created centroid sphere")
                            
                            # CRITICAL: Force viewer to re-render with new spheres
                            if hasattr(self.viewer_3d, 'set_molecule'):
                                print("DEBUG: Re-setting molecule to trigger sphere rendering")
                                self.viewer_3d.set_molecule(self.molecule)
                except Exception as e:
                    print(f"DEBUG: Could not create test sphere: {e}")
            
            # Update stick colors (bonds)
            stick_keys = ['stick_default', 'stick_single', 'stick_double', 'stick_triple', 'stick_selected', 'stick_highlight']
            for key in stick_keys:
                if key in colors:
                    COLORS[key] = colors[key]
                    print(f"DEBUG: Updated stick color {key} to {colors[key]}")
            
            # CRITICAL FIX: Update 3D viewer color settings if available
            if hasattr(self.viewer_3d, 'sphere_scale'):
                print("DEBUG: Viewer has sphere scale, checking for color settings")
                # Update any viewer-specific color settings if they exist
                for key, value in colors.items():
                    if hasattr(self.viewer_3d, key):
                        setattr(self.viewer_3d, key, value)
                        print(f"DEBUG: Set viewer.{key} = {value}")
            
            # Now force viewer to re-render with updated colors
            print("DEBUG: Forcing viewer re-render with updated atom colors...")
            
            # Method 1: Try direct color update
            if hasattr(self.viewer_3d, 'update_atom_colors'):
                print("DEBUG: Using viewer_3d.update_atom_colors")
                self.viewer_3d.update_atom_colors(colors)
            
            # Method 2: Try set_colors method
            elif hasattr(self.viewer_3d, 'set_colors'):
                print("DEBUG: Using viewer_3d.set_colors")
                self.viewer_3d.set_colors(colors)
            
            # Method 3: Try color_atoms method
            elif hasattr(self.viewer_3d, 'color_atoms'):
                print("DEBUG: Using viewer_3d.color_atoms")
                self.viewer_3d.color_atoms(colors)
            
            # Method 4: Try update_colors method
            elif hasattr(self.viewer_3d, 'update_colors'):
                print("DEBUG: Using viewer_3d.update_colors")
                self.viewer_3d.update_colors(colors)
            
            # Method 5: Force refresh with color update
            else:
                print("DEBUG: Using force refresh method")
                
                # Force the viewer to re-read COLORS from theme
                if hasattr(self.viewer_3d, 'COLORS'):
                    print("DEBUG: Refreshing viewer COLORS from theme")
                    from src.shared.ui.theme import COLORS
                    self.viewer_3d.COLORS.update(COLORS)
                
                # Update molecule with new colors (this is the key!)
                if hasattr(self.viewer_3d, 'set_molecule'):
                    print("DEBUG: Using viewer_3d.set_molecule to force re-render")
                    self.viewer_3d.set_molecule(self.molecule)
                
                # Force viewer update with multiple methods
                print("DEBUG: Forcing viewer refresh")
                
                # Method 5a: Update the viewer
                if hasattr(self.viewer_3d, 'update'):
                    print("DEBUG: Using viewer_3d.update")
                    self.viewer_3d.update()
                
                # Method 5b: Repaint the viewer
                if hasattr(self.viewer_3d, 'repaint'):
                    print("DEBUG: Using viewer_3d.repaint")
                    self.viewer_3d.repaint()
                
                # Method 5c: Refresh the viewer
                if hasattr(self.viewer_3d, 'refresh'):
                    print("DEBUG: Using viewer_3d.refresh")
                    self.viewer_3d.refresh()
                
                # Method 5d: Redraw the viewer
                if hasattr(self.viewer_3d, 'redraw'):
                    print("DEBUG: Using viewer_3d.redraw")
                    self.viewer_3d.redraw()
                
                # Method 5e: Force paint event
                if hasattr(self.viewer_3d, 'paintEvent'):
                    print("DEBUG: Forcing paintEvent")
                    try:
                        from PySide6.QtGui import QPaintEvent
                        self.viewer_3d.paintEvent(QPaintEvent())
                    except:
                        pass
                
                # Method 5f: Update geometry to force redraw
                if hasattr(self.viewer_3d, 'updateGeometry'):
                    print("DEBUG: Using viewer_3d.updateGeometry")
                    self.viewer_3d.updateGeometry()
            
            print("DEBUG: Color update completed")
            
        except Exception as e:
            print(f"ERROR in _update_atom_colors: {e}")
            import traceback
            traceback.print_exc()

    def _add_com_sphere(self):
        """Add dummy sphere at center of mass with color customization."""
        if not self.molecule:
            self.status_bar.showMessage("No molecule loaded for COM sphere")
            return
            
        try:
            from src.features.visualization_3d.services.dummy_sphere import create_dummy_sphere_at_com
            
            sphere_id = create_dummy_sphere_at_com(self.molecule, radius=0.5)
            
            # Calculate actual COM position
            from src.features.visualization_3d.services.dummy_sphere import DummySphereManager
            manager = DummySphereManager(self.molecule)
            com_position = manager.calculate_center_of_mass()
            
            # Get color from theme
            from src.shared.ui.theme import COLORS
            sphere_color = COLORS.get('sphere_com', COLORS.get('sphere_default', '#ff00ff'))
            
            # Add sphere to 3D viewer using available methods
            if hasattr(self.viewer_3d, 'add_sphere'):
                self.viewer_3d.add_sphere(com_position, 0.5, sphere_color, 'COM')
                self.status_bar.showMessage(f"COM sphere added at ({com_position[0]:.2f}, {com_position[1]:.2f}, {com_position[2]:.2f}) with color {sphere_color}")
            elif hasattr(self.viewer_3d, 'add_marker'):
                self.viewer_3d.add_marker(com_position, sphere_color, 'COM', size=0.5)
                self.status_bar.showMessage(f"COM marker added with color {sphere_color}")
            else:
                # Fallback: Create a dummy atom to represent the sphere
                self._create_dummy_atom_sphere(com_position, 0.5, sphere_color, 'COM')
                self.status_bar.showMessage(f"COM sphere created: {sphere_id} with color {sphere_color}")
                
        except Exception as e:
            self.status_bar.showMessage(f"COM sphere error: {e}")

    def _add_centroid_sphere(self):
        """Add dummy sphere at geometric centroid with color customization."""
        if not self.molecule:
            self.status_bar.showMessage("No molecule loaded for centroid sphere")
            return
            
        try:
            from src.features.visualization_3d.services.dummy_sphere import DummySphereManager
            
            manager = DummySphereManager(self.molecule)
            sphere_id = manager.create_sphere_at_centroid(radius=0.4, color='#00ff00', label='Centroid')
            centroid_position = manager.calculate_geometric_centroid()
            
            # Get color from theme
            from src.shared.ui.theme import COLORS
            sphere_color = COLORS.get('sphere_centroid', COLORS.get('sphere_default', '#00ff00'))
            
            # Add sphere to 3D viewer using available methods
            if hasattr(self.viewer_3d, 'add_sphere'):
                self.viewer_3d.add_sphere(centroid_position, 0.4, sphere_color, 'Centroid')
                self.status_bar.showMessage(f"Centroid sphere added at ({centroid_position[0]:.2f}, {centroid_position[1]:.2f}, {centroid_position[2]:.2f}) with color {sphere_color}")
            elif hasattr(self.viewer_3d, 'add_marker'):
                self.viewer_3d.add_marker(centroid_position, sphere_color, 'Centroid', size=0.4)
                self.status_bar.showMessage(f"Centroid marker added with color {sphere_color}")
            else:
                # Fallback: Create a dummy atom to represent the sphere
                self._create_dummy_atom_sphere(centroid_position, 0.4, sphere_color, 'Centroid')
                self.status_bar.showMessage(f"Centroid sphere created: {sphere_id} with color {sphere_color}")
                
        except Exception as e:
            self.status_bar.showMessage(f"Centroid sphere error: {e}")

    def _add_custom_sphere(self):
        """Add dummy sphere at custom position with user input and color customization."""
        if not self.molecule:
            self.status_bar.showMessage("No molecule loaded for custom sphere")
            return
            
        try:
            # Get user input for coordinates
            from PySide6.QtWidgets import QInputDialog
            
            # Get X coordinate
            x, ok = QInputDialog.getDouble(self, "Custom Sphere", "Enter X coordinate:", 0.0, -100.0, 100.0, 2)
            if not ok:
                return
                
            # Get Y coordinate
            y, ok = QInputDialog.getDouble(self, "Custom Sphere", "Enter Y coordinate:", 0.0, -100.0, 100.0, 2)
            if not ok:
                return
                
            # Get Z coordinate
            z, ok = QInputDialog.getDouble(self, "Custom Sphere", "Enter Z coordinate:", 0.0, -100.0, 100.0, 2)
            if not ok:
                return
            
            # Get radius
            radius, ok = QInputDialog.getDouble(self, "Custom Sphere", "Enter sphere radius:", 0.3, 0.1, 5.0, 2)
            if not ok:
                return
            
            # Create sphere
            from src.features.visualization_3d.services.dummy_sphere import DummySphereManager
            manager = DummySphereManager(self.molecule)
            sphere_id = manager.create_sphere_at_position(
                (x, y, z), radius=radius, color='#ffff00', label='Custom'
            )
            
            # Get color from theme
            from src.shared.ui.theme import COLORS
            sphere_color = COLORS.get('sphere_custom', COLORS.get('sphere_default', '#ffff00'))
            
            # Add sphere to 3D viewer using available methods
            if hasattr(self.viewer_3d, 'add_sphere'):
                self.viewer_3d.add_sphere((x, y, z), radius, sphere_color, 'Custom')
                self.status_bar.showMessage(f"Custom sphere added at ({x:.2f}, {y:.2f}, {z:.2f}) with color {sphere_color}")
            elif hasattr(self.viewer_3d, 'add_marker'):
                self.viewer_3d.add_marker((x, y, z), sphere_color, 'Custom', size=radius)
                self.status_bar.showMessage(f"Custom marker added with color {sphere_color}")
            else:
                # Fallback: Create a dummy atom to represent the sphere
                self._create_dummy_atom_sphere((x, y, z), radius, sphere_color, 'Custom')
                self.status_bar.showMessage(f"Custom sphere created: {sphere_id} with color {sphere_color}")
                
        except ImportError:
            # Fallback: Use molecule center as default position
            self._add_custom_sphere_fallback()
        except Exception as e:
            self.status_bar.showMessage(f"Custom sphere error: {e}")

    def _add_custom_sphere_fallback(self):
        """Fallback custom sphere creation without GUI input."""
        try:
            from src.features.visualization_3d.services.dummy_sphere import DummySphereManager
            
            manager = DummySphereManager(self.molecule)
            com = manager.calculate_center_of_mass()
            
            # Create sphere at COM with default settings
            sphere_id = manager.create_sphere_at_position(
                com, radius=0.3, color='#ffff00', label='Custom'
            )
            
            # Get color from theme
            from src.shared.ui.theme import COLORS
            sphere_color = COLORS.get('sphere_custom', COLORS.get('sphere_default', '#ffff00'))
            
            self._create_dummy_atom_sphere(com, 0.3, sphere_color, 'Custom')
            self.status_bar.showMessage(f"Custom sphere at COM: {sphere_id} with color {sphere_color}")
            
        except Exception as e:
            self.status_bar.showMessage(f"Custom sphere fallback error: {e}")

    def _create_dummy_atom_sphere(self, position, radius, color, label):
        """Create a dummy atom to represent a sphere in the 3D viewer."""
        try:
            from src.core.domain.models.atom import Atom
            
            # Create a dummy atom (using a large atom like Xenon to represent sphere)
            dummy_atom = Atom('Xe')  # Xenon is large and visually distinct
            dummy_atom.coords = position
            dummy_atom.partial_charge = 0.0
            
            # Add to molecule temporarily
            original_count = len(self.molecule.atoms)
            self.molecule.add_atom(dummy_atom)
            
            # Update 3D viewer
            if hasattr(self.viewer_3d, 'set_molecule'):
                self.viewer_3d.set_molecule(self.molecule)
            else:
                self.viewer_3d.update()
            
            # Store dummy atom info for potential removal
            if not hasattr(self, '_dummy_atoms'):
                self._dummy_atoms = []
            self._dummy_atoms.append(dummy_atom)
            
        except Exception as e:
            print(f"Dummy atom creation error: {e}")

    def _clear_all_spheres(self):
        """Clear all dummy spheres."""
        if not self.molecule:
            self.status_bar.showMessage("No molecule loaded")
            return
            
        try:
            from src.features.visualization_3d.services.dummy_sphere import DummySphereManager
            
            manager = DummySphereManager(self.molecule)
            original_count = len(manager.get_all_spheres())
            
            if original_count == 0:
                self.status_bar.showMessage("No spheres to clear")
                return
            
            # Clear all spheres
            manager.clear_all_spheres()
            
            # Remove dummy atoms if they exist
            if hasattr(self, '_dummy_atoms'):
                for dummy_atom in self._dummy_atoms:
                    if dummy_atom in self.molecule.atoms:
                        self.molecule.atoms.remove(dummy_atom)
                self._dummy_atoms.clear()
            
            # Update 3D viewer
            if hasattr(self.viewer_3d, 'set_molecule'):
                self.viewer_3d.set_molecule(self.molecule)
            else:
                self.viewer_3d.update()
            
            self.status_bar.showMessage(f"Cleared {original_count} sphere(s)")
            
        except Exception as e:
            self.status_bar.showMessage(f"Clear spheres error: {e}")
