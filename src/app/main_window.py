"""
Main Window — Central application window coordinating all components.
"""

import traceback
import time
from src.shared.qt_compat import *

# Performance optimization imports
from src.core.performance import ParallelFileLoader, get_profiler, profile_operation

_DEBUG = False

from src.shared.ui.theme import get_stylesheet, COLORS
from src.features.control_panel.ui.input_panel import InputPanel
from src.app.plugin_interface import PluginInterface
from src.core.domain.models.bond import BondType
from src.features.ui.substructure_dialog import SubstructureDialog


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
            mol = parse_smiles(self.smiles, use_bkchem_tokenizer=True)
            self.progress.emit(30)

            # Generate 3D coordinates
            from src.features.layout_3d import generate_3d_coordinates
            generate_3d_coordinates(mol, optimize=True, max_opt_steps=100)
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
        self._undo_stack = []       # Molecule.clone() snapshots for Ctrl+Z (max 10)
        self._UNDO_LIMIT = 10
        self._com_radius = 0.5
        self._centroid_radius = 0.4

        self.setWindowTitle("PyChem -- Molecular Viewer and Cheminformatics Software")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        self.setAcceptDrops(True)
        
        # Enable smooth resizing
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)

        # Apply theme
        self.setStyleSheet(get_stylesheet())

        # Initialize plugin system first
        self._init_plugin_system()
        
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
        save_img.triggered.connect(lambda: self._export_image(300, True))
        file_menu.addAction(save_img)

        file_menu.addSeparator()

        close_action = QAction("&Close Molecule", self)
        close_action.setShortcut(QKeySequence("Ctrl+W"))
        close_action.triggered.connect(self._close_molecule)
        file_menu.addAction(close_action)
        self._close_action = close_action

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")

        self._undo_action = QAction("&Undo Delete", self)
        self._undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        self._undo_action.triggered.connect(self._undo_delete)
        self._undo_action.setEnabled(False)
        edit_menu.addAction(self._undo_action)

        delete_sel_action = QAction("&Delete Selected", self)
        delete_sel_action.setShortcut(QKeySequence("Delete"))
        delete_sel_action.triggered.connect(
            lambda: self._delete_selected_atoms(
                set(self.viewer_3d.selected_atoms) if hasattr(self, 'viewer_3d') else set()))
        edit_menu.addAction(delete_sel_action)

        edit_menu.addSeparator()

        deselect_action = QAction("Deselect &All", self)
        deselect_action.setShortcut(QKeySequence("Escape"))
        deselect_action.triggered.connect(self._deselect_all)
        edit_menu.addAction(deselect_action)


        # Tools menu
        tools_menu = menu_bar.addMenu("&Tools")

        tools_menu.addSeparator()



        auto_rotate = QAction("Toggle &Auto-Rotate", self)
        auto_rotate.setShortcut(QKeySequence("Ctrl+R"))
        auto_rotate.triggered.connect(lambda: self.viewer_3d.toggle_auto_rotate())
        tools_menu.addAction(auto_rotate)

        reset_view = QAction("&Reset View", self)
        reset_view.setShortcut(QKeySequence("Ctrl+0"))
        reset_view.triggered.connect(lambda: self.viewer_3d.reset_view())
        tools_menu.addAction(reset_view)

        # Plugins menu
        plugins_menu = menu_bar.addMenu("&Plugins")

        installed_plugins_action = QAction("&Installed Plugins...", self)
        installed_plugins_action.setShortcut(QKeySequence("Ctrl+Shift+I"))
        installed_plugins_action.triggered.connect(self._toggle_plugin_dock)
        plugins_menu.addAction(installed_plugins_action)


        plugin_manager_action = QAction("&Plugin Manager...", self)
        plugin_manager_action.setShortcut(QKeySequence("Ctrl+P"))
        plugin_manager_action.triggered.connect(self._show_plugin_manager)
        plugins_menu.addAction(plugin_manager_action)

        plugins_menu.addSeparator()

        refresh_plugins_action = QAction("&Refresh Plugins", self)
        refresh_plugins_action.triggered.connect(self._refresh_plugins)
        plugins_menu.addAction(refresh_plugins_action)

        load_all_plugins_action = QAction("&Load All Plugins", self)
        load_all_plugins_action.triggered.connect(self._load_all_plugins)
        plugins_menu.addAction(load_all_plugins_action)

        unload_all_plugins_action = QAction("&Unload All Plugins", self)
        unload_all_plugins_action.triggered.connect(self._unload_all_plugins)
        plugins_menu.addAction(unload_all_plugins_action)

        # View menu
        view_menu = menu_bar.addMenu("&View")

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

        bg_color_3d_action = QAction("3D Background Color...", self)
        bg_color_3d_action.setShortcut(QKeySequence("Ctrl+Shift+B"))
        bg_color_3d_action.triggered.connect(self._change_3d_bg_color)
        view_menu.addAction(bg_color_3d_action)

        bg_color_2d_action = QAction("2D Background Color...", self)
        bg_color_2d_action.setShortcut(QKeySequence("Ctrl+Alt+B"))
        bg_color_2d_action.triggered.connect(self._change_2d_bg_color)
        view_menu.addAction(bg_color_2d_action)

        # Applications menu
        applications_menu = menu_bar.addMenu("&Applications")
        
        descriptor_calc = QAction("Molecular &Descriptor Calculator", self)
        descriptor_calc.setShortcut(QKeySequence("Ctrl+D"))
        descriptor_calc.triggered.connect(self._open_descriptor_calculator)
        applications_menu.addAction(descriptor_calc)
        
        applications_menu.addSeparator()
        

        opt_menu = applications_menu.addMenu("&Optimize Geometry")
        
        opt_mmff94 = QAction("MMFF94", self)
        opt_mmff94.triggered.connect(lambda checked: self._optimize_geometry(method="MMFF94"))
        opt_menu.addAction(opt_mmff94)
        
        opt_am1 = QAction("AM1", self)
        opt_am1.triggered.connect(lambda checked: self._optimize_geometry(method="AM1"))
        opt_menu.addAction(opt_am1)
        
        self.opt_menu_actions = [opt_mmff94, opt_am1]
        
        chg_menu = applications_menu.addMenu("&Compute Charges")
        
        chg_gasteiger = QAction("Gasteiger", self)
        chg_gasteiger.triggered.connect(lambda checked: self._compute_charges(method="Gasteiger"))
        chg_menu.addAction(chg_gasteiger)
        
        chg_mmff94 = QAction("MMFF94", self)
        chg_mmff94.triggered.connect(lambda checked: self._compute_charges(method="MMFF94"))
        chg_menu.addAction(chg_mmff94)
        
        chg_am1 = QAction("AM1", self)
        chg_am1.triggered.connect(lambda checked: self._compute_charges(method="AM1"))
        chg_menu.addAction(chg_am1)
        
        chg_pm3 = QAction("PM3", self)
        chg_pm3.triggered.connect(lambda checked: self._compute_charges(method="PM3"))
        chg_menu.addAction(chg_pm3)
        
        self.chg_menu_actions = [chg_gasteiger, chg_mmff94, chg_am1, chg_pm3]
        
        applications_menu.addSeparator()

        self.aromaticity_action = QAction("Perceive Aromaticity", self)
        self.aromaticity_action.triggered.connect(self._perceive_aromaticity_action)
        applications_menu.addAction(self.aromaticity_action)

        applications_menu.addSeparator()
        
        find_substructure_action = QAction("Find &Substructure...", self)
        find_substructure_action.setShortcut(QKeySequence("Ctrl+F"))
        find_substructure_action.triggered.connect(self._show_substructure_dialog)
        applications_menu.addAction(find_substructure_action)

        copy_smiles_action = QAction("Copy S&MILES", self)
        copy_smiles_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        copy_smiles_action.triggered.connect(self._copy_smiles_to_clipboard)
        applications_menu.addAction(copy_smiles_action)

        applications_menu.addSeparator()

        # SMILES Generation
        smiles_action = QAction("&SMILES Generation", self)
        smiles_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        smiles_action.triggered.connect(self._generate_smiles)
        applications_menu.addAction(smiles_action)
        
        applications_menu.addSeparator()
        
        self.color_action = QAction("Atom &Colors...", self)
        self.color_action.triggered.connect(self._show_color_dialog)
        applications_menu.addAction(self.color_action)
        
        self.protein_color_action = QAction("&Protein Colors...", self)
        self.protein_color_action.triggered.connect(self._show_protein_color_dialog)
        applications_menu.addAction(self.protein_color_action)
        
        applications_menu.addSeparator()
        
        tools_submenu = applications_menu.addMenu("&Tools")
        
        self.com_sphere_action = QAction("COM Sphere", self)
        self.com_sphere_action.triggered.connect(self._add_com_sphere)
        tools_submenu.addAction(self.com_sphere_action)
        
        self.centroid_action_tool = QAction("Centroid", self)
        self.centroid_action_tool.triggered.connect(self._add_centroid_sphere)
        tools_submenu.addAction(self.centroid_action_tool)
        
        self.custom_sphere_action = QAction("Custom Sphere", self)
        self.custom_sphere_action.triggered.connect(self._add_custom_sphere)
        tools_submenu.addAction(self.custom_sphere_action)
        
        tools_submenu.addSeparator()
        
        self.clear_spheres_action = QAction("Clear Spheres", self)
        self.clear_spheres_action.triggered.connect(self._clear_all_spheres)
        tools_submenu.addAction(self.clear_spheres_action)
        
        self.tools_submenu_actions = [self.com_sphere_action, self.centroid_action_tool, self.custom_sphere_action, self.clear_spheres_action]
        
        # Disable actions initially
        for action in self.opt_menu_actions + self.chg_menu_actions + [self.color_action, self.protein_color_action, self.aromaticity_action] + self.tools_submenu_actions:
            action.setEnabled(False)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_plugin_system(self):
        """Initialize the plugin system."""
        try:
            self.plugin_interface = PluginInterface(self)
            self.plugin_interface.initialize_plugin_system()
            print("Plugin system initialized successfully")
        except Exception as e:
            print(f"Error initializing plugin system: {e}")
            self.plugin_interface = None

    def _init_central_widget(self):
        """Create central widget with console on top, tabbed viewer below."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Vertical splitter: console row on top, content below
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.setHandleWidth(3)

        # Console row: 75% console + 25% right button panel (PyMOL-style)
        console_row = QSplitter(Qt.Orientation.Horizontal)
        console_row.setHandleWidth(2)

        # Python console (left 75% normally, but now takes full row since right panel removed)
        self.console = PythonConsole()
        console_row.addWidget(self.console)

        # The python console now takes all horizontal space in this splitter.
        console_row.setStretchFactor(0, 1)

        v_splitter.addWidget(console_row)

        # Horizontal splitter: input panel + tabbed viewer (bottom)
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        h_splitter.setHandleWidth(2)

        # Input panel (left) - more flexible sizing for small screens
        self.input_panel = InputPanel()
        self.input_panel.setMinimumWidth(280)  # Reduced from 340 for small screens
        self.input_panel.setMaximumWidth(450)  # Allow some expansion but not too much
        self.input_panel.setStyleSheet(f"background-color: {COLORS['bg_secondary']};")
        h_splitter.addWidget(self.input_panel)

        # Tabbed viewer area (right)
        self.viewer_tabs = QTabWidget()
        self.viewer_tabs.setTabPosition(QTabWidget.TabPosition.North)
        
        self.viewer_3d = MolViewer3D()
        self.viewer_2d = MolViewer2D()

        self.viewer_tabs.addTab(self.viewer_3d, "3D View")
        self.viewer_tabs.addTab(self.viewer_2d, "2D View")

        # Plugin dock widget (right side) instead of tab bar
        self._init_plugin_dock()

        h_splitter.addWidget(self.viewer_tabs)
        h_splitter.setStretchFactor(0, 0)
        h_splitter.setStretchFactor(1, 1)
        # More flexible initial sizes - left panel 25%, main area 75%
        h_splitter.setSizes([240, 960])  # 25% left panel, 75% main area for more toolbar space

        v_splitter.addWidget(h_splitter)
        v_splitter.setStretchFactor(0, 0)
        v_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(v_splitter)

        # Set viewer references for console selection commands
        self.console.set_viewer(self.viewer_3d, self.viewer_2d)

    def _init_plugin_dock(self):
        """Create a dockable sidebar for plugin management."""
        self.plugin_dock = QDockWidget("Plugins", self)
        self.plugin_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        self.plugin_dock.setMinimumWidth(220)
        
        dock_container = QWidget()
        dock_layout = QVBoxLayout(dock_container)
        dock_layout.setContentsMargins(6, 6, 6, 6)
        dock_layout.setSpacing(6)
        
        # Header label
        header = QLabel("Installed Plugins")
        header.setStyleSheet(f"font-weight: bold; color: {COLORS['text_primary']}; font-size: 13px;")
        dock_layout.addWidget(header)
        
        # Plugin list
        self.plugin_list = QListWidget()
        self.plugin_list.setStyleSheet(f"""
            QListWidget {{
                background: {COLORS['bg_widget']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 6px 8px;
            }}
            QListWidget::item:selected {{
                background: {COLORS['accent']};
            }}
        """)
        dock_layout.addWidget(self.plugin_list)
        
        # Plugin action buttons
        btn_row = QHBoxLayout()
        btn_style = f"""
            QPushButton {{
                background: {COLORS['bg_widget']};
                color: {COLORS['text_primary']};
                padding: 4px 10px;
                border-radius: 3px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {COLORS['accent']};
            }}
        """
        
        load_btn = QPushButton("Load")
        load_btn.setStyleSheet(btn_style)
        load_btn.setToolTip("Load selected plugin")
        load_btn.clicked.connect(self._load_selected_plugin)
        btn_row.addWidget(load_btn)
        
        unload_btn = QPushButton("Unload")
        unload_btn.setStyleSheet(btn_style)
        unload_btn.setToolTip("Unload selected plugin")
        unload_btn.clicked.connect(self._unload_selected_plugin)
        btn_row.addWidget(unload_btn)
        
        dock_layout.addLayout(btn_row)
        
        # Plugin detail area
        self.plugin_detail = QTextEdit()
        self.plugin_detail.setReadOnly(True)
        self.plugin_detail.setMaximumHeight(120)
        self.plugin_detail.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['bg_widget']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-size: 11px;
                padding: 4px;
            }}
        """)
        self.plugin_detail.setPlaceholderText("Select a plugin to see details...")
        dock_layout.addWidget(self.plugin_detail)
        
        dock_container.setStyleSheet(f"background-color: {COLORS['bg_secondary']};")
        self.plugin_dock.setWidget(dock_container)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plugin_dock)
        self.plugin_dock.hide()  # Hidden by default
        
        # Populate plugin list
        self._refresh_plugin_list()
        
        # Connect selection change
        self.plugin_list.currentRowChanged.connect(self._on_plugin_selected)
    
    def _refresh_plugin_list(self):
        """Refresh the plugin list in the dock widget."""
        self.plugin_list.clear()
        if self.plugin_interface:
            try:
                pm = self.plugin_interface.get_plugin_manager()
                plugins = pm.get_all_plugins()
                loaded = pm.get_loaded_plugins()
                for name, meta in plugins.items():
                    status = "✓" if name in loaded else "○"
                    self.plugin_list.addItem(f"{status}  {name}")
            except Exception as e:
                self.plugin_list.addItem(f"Error: {e}")
    
    def _on_plugin_selected(self, row):
        """Show details for selected plugin."""
        if row < 0 or not self.plugin_interface:
            self.plugin_detail.clear()
            return
        try:
            pm = self.plugin_interface.get_plugin_manager()
            plugins = pm.get_all_plugins()
            names = list(plugins.keys())
            if row < len(names):
                name = names[row]
                meta = plugins[name]
                info = meta.info
                loaded = pm.get_loaded_plugins()
                details = f"Name: {name}\n"
                details += f"Status: {'Loaded' if name in loaded else 'Not loaded'}\n"
                details += f"Version: {info.version}\n"
                details += f"Type: {info.plugin_type.value if hasattr(info.plugin_type, 'value') else info.plugin_type}\n"
                details += f"Description: {info.description}\n"
                details += f"Author: {info.author}\n"
                self.plugin_detail.setPlainText(details)
        except Exception:
            pass
    
    def _load_selected_plugin(self):
        """Load the currently selected plugin."""
        row = self.plugin_list.currentRow()
        if row < 0 or not self.plugin_interface:
            return
        try:
            pm = self.plugin_interface.get_plugin_manager()
            plugins = pm.get_all_plugins()
            names = list(plugins.keys())
            if row < len(names):
                pm.load_plugin(names[row])
                self._refresh_plugin_list()
                self._refresh_plugin_tabs()
                self.status_bar.showMessage(f"Plugin '{names[row]}' loaded")
        except Exception as e:
            self.status_bar.showMessage(f"Error loading plugin: {e}")
    
    def _unload_selected_plugin(self):
        """Unload the currently selected plugin."""
        row = self.plugin_list.currentRow()
        if row < 0 or not self.plugin_interface:
            return
        try:
            pm = self.plugin_interface.get_plugin_manager()
            plugins = pm.get_all_plugins()
            names = list(plugins.keys())
            if row < len(names):
                pm.unload_plugin(names[row])
                self._refresh_plugin_list()
                self._refresh_plugin_tabs()
                self._on_plugin_selected(row) # Refresh details text immediately
                self.status_bar.showMessage(f"Plugin '{names[row]}' unloaded")
        except Exception as e:
            self.status_bar.showMessage(f"Error unloading plugin: {e}")
    
    def _toggle_plugin_dock(self):
        """Toggle visibility of the plugin dock widget."""
        if self.plugin_dock.isVisible():
            self.plugin_dock.hide()
        else:
            self._refresh_plugin_list()
            self.plugin_dock.show()

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

        # ---------- Selection synchronization (3D ↔ 2D) ----------
        #   When one viewer's selection changes, mirror it in the other.
        #   A guard flag prevents infinite signal loops.

        self._syncing_selection = False

        def _sync_from_3d(selected):
            """Forward 3D selection to 2D viewer."""
            if self._syncing_selection:
                return
            self._syncing_selection = True
            self.viewer_2d.selected_atoms = set(selected)
            self.viewer_2d.update()
            self._syncing_selection = False

        def _sync_from_2d(selected):
            """Forward 2D selection to 3D viewer."""
            if self._syncing_selection:
                return
            self._syncing_selection = True
            self.viewer_3d.selected_atoms = set(selected)
            self.viewer_3d.update()
            self._syncing_selection = False

        self.viewer_3d.selection_changed.connect(_sync_from_3d)
        self.viewer_2d.selection_changed.connect(_sync_from_2d)

        # ---------- Delete requests from either viewer ----------
        self.viewer_3d.delete_requested.connect(self._delete_selected_atoms)
        self.viewer_2d.delete_requested.connect(self._delete_selected_atoms)

    def _toggle_sasa(self, checked):
        self.viewer_3d.show_sasa_surface = checked
        if checked and self.molecule:
            # Lazily compute SASA on first activation
            has_points = any(
                getattr(a, 'sasa_points', None)
                for a in self.molecule.atoms
            )
            if not has_points:
                self.status_bar.showMessage("Computing SASA surface...")
                QApplication.processEvents()
                try:
                    from src.features.cheminformatics.services.spatial_properties import compute_sasa
                    compute_sasa(self.molecule)
                    self.status_bar.showMessage("SASA surface computed")
                except Exception as e:
                    self.status_bar.showMessage(f"SASA computation failed: {e}")
        self.viewer_3d.update()

    def _toggle_sasa_selected_only(self, checked):
        self.viewer_3d.show_sasa_selected_only = checked
        self.viewer_3d.update()

    # ─── Selection, Delete, Undo, Close ────────────────────────────

    def _delete_selected_atoms(self, atom_indices=None):
        """
        Delete the given atom indices from the molecule.

        Pushes a snapshot onto the undo stack before modifying, then
        rebuilds both viewers.  If all atoms are removed, behaves
        like File → Close.

        Args:
            atom_indices: set of int — atom indices to remove.
                          Falls back to the 3D viewer's current selection.
        """
        if not self.molecule:
            return

        indices = set(atom_indices) if atom_indices else set(self.viewer_3d.selected_atoms)
        if not indices:
            self.status_bar.showMessage("Nothing selected to delete")
            return

        # --- Snapshot for undo ---
        self._undo_stack.append(self.molecule.clone())
        if len(self._undo_stack) > self._UNDO_LIMIT:
            self._undo_stack.pop(0)
        self._undo_action.setEnabled(True)

        # --- Remove atoms ---
        removed = self.molecule.remove_atoms(indices)
        self.status_bar.showMessage(
            f"Deleted {removed} atom(s) — {len(self.molecule.atoms)} remaining  "
            f"(Ctrl+Z to undo)")

        # --- Refresh viewers ---
        if len(self.molecule.atoms) == 0:
            self._close_molecule()
            return

        self.viewer_3d.selected_atoms.clear()
        self.viewer_2d.selected_atoms.clear()
        self.viewer_3d.set_molecule(self.molecule)
        self.viewer_2d.set_molecule(self.molecule)
        self.input_panel.update_molecule_info(self.molecule)

    def _undo_delete(self):
        """
        Restore the molecule to its state before the last delete.

        Pops the most recent snapshot from the undo stack and pushes
        it into both viewers.
        """
        if not self._undo_stack:
            self.status_bar.showMessage("Nothing to undo")
            return

        self.molecule = self._undo_stack.pop()

        # Refresh viewers
        self.viewer_3d.selected_atoms.clear()
        self.viewer_2d.selected_atoms.clear()
        self.viewer_3d.set_molecule(self.molecule)
        self.viewer_2d.set_molecule(self.molecule)
        self.console.set_molecule(self.molecule)
        self.input_panel.update_molecule_info(self.molecule)
        if not self._undo_stack:
            self._undo_action.setEnabled(False)

        self.status_bar.showMessage(
            f"Undo: restored {len(self.molecule.atoms)} atoms, "
            f"{len(self.molecule.bonds)} bonds")

    def _close_molecule(self):
        """
        Clear the current molecule from both viewers without closing
        the application window.

        Resets all molecule-dependent state including the undo stack,
        the console reference, and disables molecule-dependent menu
        actions.
        """
        self.molecule = None
        self._undo_stack.clear()
        self._undo_action.setEnabled(False)

        # Clear viewers
        self.viewer_3d.selected_atoms.clear()
        self.viewer_2d.selected_atoms.clear()
        self.viewer_3d.clear()
        self.viewer_2d.clear()

        # Reset console
        if hasattr(self, 'console') and self.console:
            self.console.set_molecule(None)

        # Reset input panel
        if hasattr(self, 'input_panel') and self.input_panel:
            self.input_panel.enable_tools(False)

        self.status_bar.showMessage("Ready — Enter a SMILES string to begin")

    def _deselect_all(self):
        """Clear atom selection in both viewers."""
        self.viewer_3d.selected_atoms.clear()
        self.viewer_2d.selected_atoms.clear()
        self.viewer_3d.update()
        self.viewer_2d.update()
        self.status_bar.showMessage("Selection cleared")

    def _show_substructure_dialog(self):
        """Show the SMILES/SMARTS substructure matcher dialog."""
        if not hasattr(self, '_substructure_dialog') or not self._substructure_dialog:
            self._substructure_dialog = SubstructureDialog(self)
        self._substructure_dialog.show()
        self._substructure_dialog.raise_()
        self._substructure_dialog.activateWindow()

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
        
        if _DEBUG:
            print("[DEBUG] _set_molecule called: {} atoms, is_protein={}".format(len(molecule.atoms), molecule.properties.get('is_protein', False)))
        
        set_start_time = time.time()
        
        # Always compute Center of Mass (fast O(N))
        # Deferred SASA computing to when it's explicitly needed to avoid freezing molecule loading.
        with get_profiler().time_operation("center_of_mass"):
            try:
                from src.features.cheminformatics.services.spatial_properties import compute_center_of_mass
                compute_center_of_mass(molecule)
            except Exception as e:
                if _DEBUG:
                    print(f"[DEBUG] Skipping COM calculation: {e}")
            
        self.molecule = molecule
        if _DEBUG:
            print("[DEBUG] Setting 3D viewer molecule...")
        with get_profiler().time_operation("3d_viewer_update"):
            self.viewer_3d.set_molecule(molecule)
        if _DEBUG:
            print("[DEBUG] 3D viewer updated")
        
        # Skip 2D generation for large proteins and PDB files
        # Rule 1: Always skip if PDB and atoms >= 700
        # Rule 2: Skip for other formats if atoms > 1000 and is_protein
        source_format = molecule.properties.get('source_format', 'unknown')
        is_pdb = source_format in ('pdb', 'ent')
        
        should_skip_2d = False
        is_protein = molecule.properties.get('is_protein', False)
        num_atoms = len(molecule.atoms)
        
        if is_pdb and num_atoms >= 700:
            should_skip_2d = True
        elif is_protein and num_atoms > 1000:
            should_skip_2d = True

        if should_skip_2d:
            if _DEBUG:
                print(f"[DEBUG] Skipping 2D layout: is_pdb={is_pdb}, num_atoms={num_atoms}")
            self.viewer_2d.clear()
            self.viewer_2d.show_protein_placeholder = True
            self.viewer_2d.update()
        else:
            if _DEBUG:
                print("[DEBUG] Generating 2D coordinates...")
            # Generate 2D coordinates with profiling
            with get_profiler().time_operation("2d_viewer_update"):
                self.viewer_2d.set_molecule(molecule)
            self.viewer_2d.show_protein_placeholder = False
        
        if _DEBUG:
            print("[DEBUG] Updating console and input panel...")
        with get_profiler().time_operation("console_panel_update"):
            self.console.set_molecule(molecule)
            self.input_panel.update_molecule_info(molecule)
            self.input_panel.enable_tools(True)
        
        # Notify plugins of molecule change
        if _DEBUG:
            print("[DEBUG] Notifying plugins...")
        with get_profiler().time_operation("plugin_notification"):
            self._notify_plugins_molecule_changed()
        
        for action in self.opt_menu_actions: action.setEnabled(True)
        for action in self.chg_menu_actions: action.setEnabled(True)
        
        # Enable new feature buttons in menu
        self.color_action.setEnabled(True)
        self.protein_color_action.setEnabled(True)
        self.aromaticity_action.setEnabled(True)
        for action in self.tools_submenu_actions: action.setEnabled(True)

    def _optimize_geometry(self, checked=False, method=None):
        if not self.molecule:
            return
        if method is None or not isinstance(method, str):
            method = "MMFF94" # Default callback action from main tools menu
            
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

    def _compute_charges(self, checked=False, method=None):
        if not self.molecule:
            return
        if method is None or not isinstance(method, str):
            method = "Gasteiger"
            
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

    def _open_descriptor_calculator(self):
        """Open molecular descriptor calculator dialog."""
        if _DEBUG:
            print(f"[DEBUG] Opening descriptor calculator...")
            print(f"[DEBUG] Molecule available: {self.molecule is not None}")
        
        if not self.molecule:
            QMessageBox.warning(self, "No Molecule", 
                            "Please load a molecule first before calculating descriptors.")
            return
        
        try:
            if _DEBUG:
                print(f"[DEBUG] Molecule atoms: {len(self.molecule.atoms)}, bonds: {len(self.molecule.bonds)}")
            
            # Validate molecule has coordinates
            if _DEBUG and hasattr(self.molecule.atoms[0], 'x'):
                print(f"[DEBUG] Molecule has coordinates")
            
            from src.features.descriptor_calculator.gui import show_descriptor_calculator
            dialog = show_descriptor_calculator(self.molecule, self)
            
            if _DEBUG:
                print(f"[DEBUG] Dialog created: {type(dialog)}")
            
            # Check if it's the dummy function
            if hasattr(dialog, '__name__') and dialog.__name__ == 'show_descriptor_calculator':
                if _DEBUG:
                    print(f"[DEBUG] ERROR: Dummy function was called")
                QMessageBox.critical(self, "GUI Error", 
                                  "The descriptor calculator GUI is not available.\n"
                                  "Qt framework is not working properly.\n"
                                  "Please use the alternative Tkinter GUI:\n"
                                  "python tkinter_descriptor_gui.py")
                return
            
            # Keep reference to prevent garbage collection
            self.descriptor_calculator_dialog = dialog
            
            print(f"[DEBUG] Dialog stored as instance variable")
            print(f"[DEBUG] Descriptor calculator should now be visible")
            
        except ImportError as e:
            print(f"[DEBUG] Import Error: {e}")
            QMessageBox.critical(self, "Import Error", 
                              f"Could not import descriptor calculator:\n{str(e)}")
        except Exception as e:
            print(f"[DEBUG] General Error: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", 
                              f"Error opening descriptor calculator:\n{str(e)}")

    def _perceive_aromaticity_action(self):
        """Manually trigger aromaticity perception on the loaded molecule."""
        if not self.molecule:
            return
        self.status_bar.showMessage("Perceiving aromaticity...")
        QApplication.processEvents()
        try:
            from src.features.smiles_parser.rules.aromaticity import perceive_aromaticity
            perceive_aromaticity(self.molecule)
            # Re-assign types to reflect aromaticity (e.g. C.ar)
            self.molecule.assign_sybyl_types()
            # Refresh viewers to show aromatic rings if highlighted/colored differently
            self.viewer_3d.update()
            self.viewer_2d.update()
            self.status_bar.showMessage("Aromaticity perceived successfully and SYBYL types updated")
        except Exception as e:
            self.status_bar.showMessage(f"Aromaticity perception failed: {e}")
            QMessageBox.warning(self, "Aromaticity Error", f"Perception failed: {e}")

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
            print("[DEBUG] No file selected")
            return

        print(f"[DEBUG] Selected file: {filepath}")
        
        # Check file size for large files
        import os
        file_size = os.path.getsize(filepath) / 1024  # KB
        print(f"[DEBUG] File size: {file_size:.1f} KB")
        
        if file_size > 100:  # Large file warning
            self.status_bar.showMessage(f"Importing large file ({file_size:.1f}KB): {filepath}")
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            self.status_bar.showMessage(f"Importing: {filepath}")
        
        QApplication.processEvents()

        load_start_time = time.time()

        try:
            # Use ParallelFileLoader (parallel disabled by default due to numpy/multiprocessing issues)
            # Set use_parallel=True manually if you want to test parallel loading
            loader = ParallelFileLoader(parallel_threshold_kb=100.0, use_parallel=False)
            
            ext = filepath.lower().rsplit('.', 1)[-1] if '.' in filepath else ''
            print(f"[DEBUG] File extension: {ext}")

            # Profile the file loading operation
            with get_profiler().time_operation("file_load"):
                mol = loader.load_file(filepath)

            load_time = time.time() - load_start_time
            print(f"[DEBUG] File loaded in {load_time:.3f}s")

            if mol is None:
                raise ValueError("Failed to parse molecule - no atoms loaded")
            
            # Mark if this is a PDB file for 2D view handling
            mol.properties['source_format'] = ext if ext in ('pdb', 'ent') else 'unknown'
            
            print(f"[DEBUG] Molecule loaded: {len(mol.atoms)} atoms, {len(mol.bonds)} bonds")
            print(f"[DEBUG] Molecule name: {mol.name}")
            print(f"[DEBUG] Properties: {mol.properties}")

            # Skip expensive calculations for anything other than small molecules
            # Ring detection and Gasteiger are extremely slow in pure Python for large arrays.
            num_atoms = len(mol.atoms)
            if num_atoms <= 150:
                print("[DEBUG] Assigning hybridization...")
                try:
                    mol.assign_hybridization()
                    mol.assign_sybyl_types()
                    
                    # Perceive aromaticity for chemical accuracy and better matching
                    from src.features.smiles_parser.rules.aromaticity import perceive_aromaticity
                    perceive_aromaticity(mol)
                except Exception as e:
                    print(f"[DEBUG] Molecule typing/aromaticity failed: {e}")
                    pass

                print("[DEBUG] Computing charges...")
                has_charges = any(a.partial_charge != 0 for a in mol.atoms)
                if not has_charges:
                    try:
                        from src.features.cheminformatics.electrostatics.gasteiger import compute_gasteiger_charges
                        compute_gasteiger_charges(mol)
                    except Exception as e:
                        print(f"[DEBUG] charge computation failed: {e}")
                        pass
            else:
                print("[DEBUG] Skipping hybridization/charges for large structure to ensure fast load speed")

            print("[DEBUG] Calling _set_molecule...")
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

    def _generate_smiles(self):
        """Generate SMILES notation from loaded 3D structure using BKChem algorithms."""
        if not self.molecule:
            QMessageBox.warning(self, "No Molecule", "Please load a molecule first.")
            return
        
        try:
            # Try BKChem-style SMILES generation first
            try:
                from src.features.smiles_generator import generate_smiles
                smiles = generate_smiles(self.molecule)
                if smiles and len(smiles) > 0:
                    print(f"[DEBUG] BKChem SMILES generated: {smiles}")
                else:
                    raise ValueError("Empty SMILES from BKChem generator")
            except Exception as bkchem_error:
                print(f"[DEBUG] BKChem SMILES failed: {bkchem_error}, falling back to basic")
                # Fallback to basic SMILES generation
                smiles = self._molecule_to_smiles_basic(self.molecule)
            
            # Validate SMILES by trying to parse it
            try:
                from src.features.smiles_parser.services.parser import parse_smiles
                test_mol = parse_smiles(smiles)
                if not test_mol or len(test_mol.atoms) == 0:
                    raise ValueError("Generated SMILES could not be parsed")
            except Exception as parse_error:
                # If parsing fails, provide a simplified representation
                smiles = self._generate_simple_formula()
                self.status_bar.showMessage("Generated molecular formula instead of SMILES due to complexity")
            
            # Print to Python console
            if hasattr(self, 'console') and self.console:
                try:
                    self.console._append_output(f"\n# Generated SMILES/Formula")
                    self.console._append_output(f"smiles = '{smiles}'")
                    self.console._append_output(f"# Generated: {smiles}")
                except Exception as console_err:
                    print(f"[DEBUG] Could not write to console: {console_err}")
            
            # Show in message box
            msg = QMessageBox(self)
            msg.setWindowTitle("SMILES Generated")
            msg.setText(f"SMILES notation has been generated and printed to the console.")
            msg.setDetailedText(f"SMILES: {smiles}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            
            self.status_bar.showMessage(f"SMILES generated: {smiles}")
            
        except Exception as e:
            QMessageBox.critical(self, "SMILES Generation Error", 
                               f"Failed to generate SMILES: {str(e)}")
            self.status_bar.showMessage("SMILES generation failed")

    def _molecule_to_smiles_basic(self, molecule):
        """Basic SMILES generation - attempts to generate SMILES, falls back to formula."""
        if not molecule or not molecule.atoms:
            return ""
        
        print(f"DEBUG: Attempting SMILES generation for {len(molecule.atoms)} atoms")
        
        try:
            # Attempt basic SMILES generation
            visited = set()
            fragments = []
            
            # Find connected components (fragments)
            for start_idx in range(len(molecule.atoms)):
                if start_idx not in visited:
                    fragment_atoms = self._dfs_fragment(molecule, start_idx, visited)
                    print(f"DEBUG: Found fragment with {len(fragment_atoms)} atoms")
                    if fragment_atoms:
                        fragment_smiles = self._fragment_to_smiles(molecule, fragment_atoms)
                        print(f"DEBUG: Fragment SMILES: {fragment_smiles}")
                        fragments.append(fragment_smiles)
            
            smiles_result = '.'.join(fragments)
            print(f"DEBUG: Combined SMILES result: {smiles_result}")
            
            # Basic validation: if it's empty or clearly malformed, fall back
            if not smiles_result:
                print("DEBUG: Empty SMILES result, falling back to formula")
                raise ValueError("Empty SMILES result")
            
            # Check for obvious malformed patterns
            if any(c in smiles_result for c in ['(', ')', '[', ']']):
                if smiles_result.count('(') != smiles_result.count(')') or smiles_result.count('[') != smiles_result.count(']'):
                    print("DEBUG: Unmatched brackets, falling back to formula")
                    raise ValueError("Unmatched brackets")
            
            print(f"DEBUG: Successfully generated SMILES: {smiles_result}")
            return smiles_result
            
        except Exception as e:
            # Fallback to molecular formula if basic SMILES generation fails
            print(f"DEBUG: Basic SMILES generation failed: {e}. Falling back to formula.")
            return self._generate_simple_formula()
    
    def _dfs_fragment(self, molecule, start_idx, visited):
        """DFS to find all atoms in a connected fragment."""
        fragment = []
        stack = [start_idx]
        
        while stack:
            idx = stack.pop()
            if idx in visited:
                continue
            
            visited.add(idx)
            fragment.append(idx)
            
            # Add neighbors
            for neighbor_idx, _ in molecule._adjacency.get(idx, []):
                if neighbor_idx not in visited:
                    stack.append(neighbor_idx)
        
        return fragment
    
    def _fragment_to_smiles(self, molecule, fragment_atoms):
        """Convert a connected fragment to SMILES."""
        if not fragment_atoms:
            return ""
        
        print(f"DEBUG: Converting fragment with {len(fragment_atoms)} atoms")
        
        # For very simple molecules, try a linear approach first
        if len(fragment_atoms) <= 2:
            return self._linear_smiles(molecule, fragment_atoms)
        
        # For medium molecules, try a simple chain approach
        if len(fragment_atoms) <= 20:
            return self._simple_chain_smiles(molecule, fragment_atoms)
        
        # For larger molecules, try a path-based approach
        if len(fragment_atoms) <= 200:
            return self._path_based_smiles(molecule, fragment_atoms)
        
        print("DEBUG: Fragment too complex, falling back to formula")
        raise ValueError("Fragment too complex for basic SMILES generation")
    
    def _path_based_smiles(self, molecule, fragment_atoms):
        """Generate SMILES using a simple neighbor-based approach."""
        if len(fragment_atoms) == 1:
            atom = molecule.atoms[fragment_atoms[0]]
            return atom.element.symbol
        
        # Build a simple connectivity map
        connectivity = {}
        for idx in fragment_atoms:
            connectivity[idx] = []
            for neighbor_idx, bond_idx in molecule._adjacency.get(idx, []):
                if neighbor_idx in fragment_atoms:
                    bond = molecule.bonds[bond_idx]
                    # Skip hydrogens
                    if molecule.atoms[neighbor_idx].element.symbol != 'H':
                        connectivity[idx].append((neighbor_idx, bond))
        
        # Find a good starting point (most connected)
        start_idx = max(fragment_atoms, 
                       key=lambda i: len(connectivity.get(i, [])))
        
        # Build SMILES using a simple depth-first traversal
        visited = set()
        result = ""
        
        def build_smiles(current_idx, parent_idx=None):
            nonlocal result
            if current_idx in visited:
                return ""
            
            visited.add(current_idx)
            atom = molecule.atoms[current_idx]
            
            # Add current atom
            symbol = atom.element.symbol
            if symbol in ['B', 'C', 'N', 'O', 'P', 'S', 'F', 'Cl', 'Br', 'I']:
                result += symbol
            else:
                result += f'[{symbol}]'
            
            # Get neighbors (excluding parent and visited)
            neighbors = []
            for neighbor_idx, bond in connectivity.get(current_idx, []):
                if neighbor_idx != parent_idx and neighbor_idx not in visited:
                    neighbors.append((neighbor_idx, bond))
            
            if not neighbors:
                return ""
            
            # Sort by atomic number for consistency
            neighbors.sort(key=lambda x: molecule.atoms[x[0]].element.atomic_number)
            
            # Main chain (first neighbor)
            main_neighbor, main_bond = neighbors[0]
            bond_symbol = self._bond_to_symbol(main_bond)
            result += bond_symbol
            build_smiles(main_neighbor, current_idx)
            
            # Branches (remaining neighbors)
            for neighbor_idx, bond in neighbors[1:3]:  # Max 2 branches
                bond_symbol = self._bond_to_symbol(bond)
                branch_smiles = ""
                temp_visited = visited.copy()
                
                # Build branch
                branch_smiles = _build_branch(molecule, connectivity, neighbor_idx, current_idx, temp_visited)
                print(f"DEBUG: Branch {neighbor_idx}: {branch_smiles}")
                
                if branch_smiles and branch_smiles != "" and branch_smiles != "()":
                    result += '(' + bond_symbol + branch_smiles + ')'
                    print(f"DEBUG: Added branch: ({bond_symbol}{branch_smiles})")
                else:
                    print(f"DEBUG: Skipped empty branch")
            
            return result
        
        def _build_branch(molecule, connectivity, start_idx, parent_idx, visited_set):
            """Build a branch SMILES string."""
            if start_idx in visited_set:
                return ""
            
            visited_set.add(start_idx)
            atom = molecule.atoms[start_idx]
            
            # Start with atom
            branch = atom.element.symbol
            if atom.element.symbol not in ['B', 'C', 'N', 'O', 'P', 'S', 'F', 'Cl', 'Br', 'I']:
                branch = f'[{atom.element.symbol}]'
            
            # Get neighbors
            neighbors = []
            for neighbor_idx, bond in connectivity.get(start_idx, []):
                if neighbor_idx != parent_idx and neighbor_idx not in visited_set:
                    neighbors.append((neighbor_idx, bond))
            
            if neighbors:
                # Take first neighbor as continuation
                neighbor_idx, bond = neighbors[0]
                bond_symbol = self._bond_to_symbol(bond)
                branch += bond_symbol
                branch += _build_branch(molecule, connectivity, neighbor_idx, start_idx, visited_set)
            
            return branch
        
        # Keep building until all atoms are visited
        current_result = ""
        while len(visited) < len(fragment_atoms):
            # Find an unvisited atom to start from
            if not current_result:
                # First time - use the best starting point
                build_smiles(start_idx)
                current_result = result
            else:
                # Find remaining unvisited atoms and connect them
                unvisited = [idx for idx in fragment_atoms if idx not in visited]
                if unvisited:
                    # Find an unvisited atom connected to visited atoms
                    next_start = None
                    for visited_idx in visited:
                        for neighbor_idx, bond in connectivity.get(visited_idx, []):
                            if neighbor_idx in unvisited:
                                next_start = neighbor_idx
                                # Connect with a bond
                                bond_symbol = self._bond_to_symbol(bond)
                                current_result += bond_symbol
                                break
                        if next_start:
                            break
                    
                    if next_start:
                        build_smiles(next_start)
                        current_result = result
                    else:
                        # Disconnected fragment - add dot and start new
                        current_result += "."
                        build_smiles(unvisited[0])
                        current_result = result
                else:
                    break
        
        result = current_result
        
        print(f"DEBUG: Final SMILES result: {result}")
        print(f"DEBUG: Visited {len(visited)} out of {len(fragment_atoms)} atoms")
        
        return result
    
    def _simple_chain_smiles(self, molecule, fragment_atoms):
        """Generate SMILES for simple chain molecules."""
        if len(fragment_atoms) == 1:
            atom = molecule.atoms[fragment_atoms[0]]
            return atom.element.symbol
        
        # Try to build a simple chain
        result = ""
        used_atoms = {fragment_atoms[0]}
        current_atom = fragment_atoms[0]
        
        while len(used_atoms) < len(fragment_atoms):
            atom = molecule.atoms[current_atom]
            result += atom.element.symbol
            
            # Find next unused neighbor
            next_atom = None
            for neighbor_idx, bond_idx in molecule._adjacency.get(current_atom, []):
                if neighbor_idx not in used_atoms:
                    next_atom = neighbor_idx
                    used_atoms.add(neighbor_idx)
                    
                    # Add bond symbol
                    bond = molecule.bonds[bond_idx]
                    result += self._bond_to_symbol(bond)
                    break
            
            if next_atom is None:
                break  # No more connections in chain
            current_atom = next_atom
        
        # Add the last atom
        if current_atom is not None:
            result += molecule.atoms[current_atom].element.symbol
        
        print(f"DEBUG: Simple chain result: {result}")
        return result
    
    def _linear_smiles(self, molecule, fragment_atoms):
        """Generate SMILES for simple linear molecules."""
        if len(fragment_atoms) == 1:
            atom = molecule.atoms[fragment_atoms[0]]
            return atom.element.symbol
        
        # For 2 atoms, just connect them
        idx1, idx2 = fragment_atoms
        atom1 = molecule.atoms[idx1]
        atom2 = molecule.atoms[idx2]
        
        # Find bond between them
        bond_symbol = "-"
        for neighbor_idx, bond_idx in molecule._adjacency.get(idx1, []):
            if neighbor_idx == idx2:
                bond = molecule.bonds[bond_idx]
                bond_symbol = self._bond_to_symbol(bond)
                break
        
        return f"{atom1.element.symbol}{bond_symbol}{atom2.element.symbol}"
    
    def _atom_to_smiles_recursive(self, molecule, atom_idx, parent_idx, 
                                 visited, fragment_atoms):
        """Recursively convert atom and its neighbors to SMILES."""
        if atom_idx in visited:
            return ""
        
        visited.add(atom_idx)
        atom = molecule.atoms[atom_idx]
        
        # Get atom symbol
        symbol = atom.element.symbol
        if symbol in ['B', 'C', 'N', 'O', 'P', 'S', 'F', 'Cl', 'Br', 'I']:
            # Organic subset - no brackets needed for standard valence
            atom_smiles = symbol
        else:
            # Inorganic elements - need brackets
            atom_smiles = f'[{symbol}]'
        
        # Get neighbors sorted by atomic number (for consistency)
        neighbors = []
        for neighbor_idx, bond_idx in molecule._adjacency.get(atom_idx, []):
            if neighbor_idx != parent_idx and neighbor_idx in fragment_atoms:
                bond = molecule.bonds[bond_idx]
                neighbors.append((neighbor_idx, bond))
        
        # Sort neighbors for consistent SMILES
        neighbors.sort(key=lambda x: molecule.atoms[x[0]].element.atomic_number)
        
        # Separate branches (non-ring) and ring closures
        branches = []
        ring_bonds = []
        next_neighbor = None
        
        for neighbor_idx, bond in neighbors:
            if neighbor_idx in visited:
                # Ring closure - only handle simple cases
                if len(ring_bonds) < 2:  # Limit complexity
                    ring_num = self._get_ring_number(atom_idx, neighbor_idx, visited)
                    ring_bonds.append((bond, ring_num))
            else:
                # Branch or main chain
                if not next_neighbor:
                    next_neighbor = (neighbor_idx, bond)
                else:
                    branches.append((neighbor_idx, bond))
        
        # Add ring closures to atom symbol
        for bond, ring_num in ring_bonds:
            bond_symbol = self._bond_to_symbol(bond)
            atom_smiles += bond_symbol + str(ring_num)
        
        # Process main chain
        if next_neighbor:
            bond_symbol = self._bond_to_symbol(next_neighbor[1])
            chain_smiles = self._atom_to_smiles_recursive(
                molecule, next_neighbor[0], atom_idx, visited, fragment_atoms)
            atom_smiles += bond_symbol + chain_smiles
        
        # Process branches (limit to 2 branches to avoid complexity)
        for i, (neighbor_idx, bond) in enumerate(branches[:2]):
            bond_symbol = self._bond_to_symbol(bond)
            branch_smiles = self._atom_to_smiles_recursive(
                molecule, neighbor_idx, atom_idx, visited, fragment_atoms)
            atom_smiles += '(' + bond_symbol + branch_smiles + ')'
        
        return atom_smiles
    
    def _bond_to_symbol(self, bond):
        """Convert bond type to SMILES symbol."""
        if bond.bond_type == BondType.SINGLE:
            return ''
        elif bond.bond_type == BondType.DOUBLE:
            return '='
        elif bond.bond_type == BondType.TRIPLE:
            return '#'
        else:
            return ''
    
    def _get_ring_number(self, atom1_idx, atom2_idx, visited):
        """Generate a ring number for ring closure."""
        # Use a simpler approach - just use sequential numbers
        return (len(visited) % 9) + 1  # Ring numbers 1-9
    
    def _generate_simple_formula(self):
        """Generate molecular formula as fallback."""
        if not self.molecule:
            return ""
        
        # Count atoms
        atom_counts = {}
        for atom in self.molecule.atoms:
            symbol = atom.element.symbol
            atom_counts[symbol] = atom_counts.get(symbol, 0) + 1
        
        # Generate formula in Hill system order
        formula_parts = []
        
        # Carbon first
        if 'C' in atom_counts:
            count = atom_counts['C']
            formula_parts.append(f"C{count if count > 1 else ''}")
            del atom_counts['C']
        
        # Hydrogen second
        if 'H' in atom_counts:
            count = atom_counts['H']
            formula_parts.append(f"H{count if count > 1 else ''}")
            del atom_counts['H']
        
        # Other elements in alphabetical order
        for symbol in sorted(atom_counts.keys()):
            count = atom_counts[symbol]
            formula_parts.append(f"{symbol}{count if count > 1 else ''}")
        
        return "".join(formula_parts)

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
        settings = QSettings("PyChem", "Viewer")
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

    def _copy_smiles_to_clipboard(self):
        """Generate SMILES for the current molecule and copy to clipboard."""
        if not self.molecule:
            self.status_bar.showMessage("No molecule loaded")
            return
        try:
            from src.vendors.oasa_bridge import domain_to_oasa_mol
            import src.vendors.oasa.smiles as oasa_smiles

            o_mol, _ = domain_to_oasa_mol(self.molecule)
            sm_engine = oasa_smiles.smiles()
            smiles_str = sm_engine.get_smiles(o_mol)

            if smiles_str:
                clipboard = QApplication.clipboard()
                clipboard.setText(smiles_str)
                self.status_bar.showMessage(f"SMILES copied: {smiles_str}")
            else:
                self.status_bar.showMessage("Could not generate SMILES for this molecule")
        except Exception as e:
            self.status_bar.showMessage(f"SMILES generation failed: {e}")

    # ─── View Options ─────────────────────────────────────────────

    def _toggle_hydrogens(self):
        checked = self.input_panel.show_h_check.isChecked()
        self.viewer_3d.show_hydrogens = checked
        self.viewer_3d.update()
        self.viewer_2d.show_hydrogens = checked
        self.viewer_2d.update()

    def _toggle_labels(self):
        checked = self.input_panel.show_labels_check.isChecked()
        self.viewer_3d.show_labels = checked
        self.viewer_3d.update()

    # ─── Plugin Management ────────────────────────────────────────────
    
    def _show_plugin_manager(self):
        """Show the plugin manager dialog."""
        if self.plugin_interface:
            self.plugin_interface.show_plugin_manager()
        else:
            QMessageBox.warning(self, "Plugins", "Plugin system not available")
    
    def _show_installed_plugins_dialog(self):
        """Show the installed plugins selection dialog."""
        try:
            from src.app.installed_plugins_dialog import show_installed_plugins_dialog
            
            result, active_plugins = show_installed_plugins_dialog(
                self.plugin_interface, 
                self
            )
            
            if result:
                print(f"Plugins selected: {active_plugins}")
                self.status_bar.showMessage(f"Selected {len(active_plugins)} plugins for toolbar")
                
                # TODO: Update toolbar with selected plugins
                # This will be implemented when integrating with the toolbar system
                
        except Exception as e:
            print(f"Error showing installed plugins dialog: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"Could not open installed plugins dialog: {str(e)}")
    
    def _refresh_plugins(self):
        """Refresh the plugin system."""
        if self.plugin_interface:
            try:
                # Re-initialize plugin system
                self.plugin_interface.initialize_plugin_system()
                
                # Refresh plugin tabs
                self._refresh_plugin_tabs()
                
                QMessageBox.information(self, "Plugins", "Plugin system refreshed successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to refresh plugins:\n{str(e)}")
        else:
            QMessageBox.warning(self, "Plugins", "Plugin system not available")
    
    def _load_all_plugins(self):
        """Load all available plugins."""
        if self.plugin_interface and self.plugin_interface.plugin_manager:
            try:
                plugins = self.plugin_interface.plugin_manager.discover_plugins()
                loaded_count = 0
                
                for plugin_name in plugins.keys():
                    if not self.plugin_interface.plugin_manager.is_plugin_loaded(plugin_name):
                        if self.plugin_interface.plugin_manager.load_plugin(plugin_name):
                            loaded_count += 1
                
                self._refresh_plugin_tabs()
                QMessageBox.information(self, "Plugins", f"Loaded {loaded_count} plugins")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load plugins:\n{str(e)}")
        else:
            QMessageBox.warning(self, "Plugins", "Plugin system not available")
    
    def _unload_all_plugins(self):
        """Unload all loaded plugins."""
        if self.plugin_interface and self.plugin_interface.plugin_manager:
            try:
                plugins = self.plugin_interface.plugin_manager.discover_plugins()
                unloaded_count = 0
                
                for plugin_name in plugins.keys():
                    if self.plugin_interface.plugin_manager.is_plugin_loaded(plugin_name):
                        if self.plugin_interface.plugin_manager.unload_plugin(plugin_name):
                            unloaded_count += 1
                
                self._refresh_plugin_tabs()
                QMessageBox.information(self, "Plugins", f"Unloaded {unloaded_count} plugins")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to unload plugins:\n{str(e)}")
        else:
            QMessageBox.warning(self, "Plugins", "Plugin system not available")
    
    def _refresh_plugin_tabs(self):
        """Refresh plugin tabs."""
        if self.plugin_interface and hasattr(self, 'viewer_tabs'):
            # Clear existing plugin tabs (keep first two tabs for 3D and 2D viewer)
            while self.viewer_tabs.count() > 2:
                self.viewer_tabs.removeTab(2)
            
            # Recreate plugin tabs
            self.plugin_interface.create_plugin_tabs(self.viewer_tabs)

    def _toggle_com_sphere(self):
        """Toggle COM dummy sphere visibility."""
        if not self.molecule:
            return
        
        from src.features.visualization_3d.services.dummy_sphere import DummySphereManager
        manager = DummySphereManager(self.molecule)
        
        # Remove existing COM spheres
        for s in manager.get_all_spheres():
            if s.label == 'COM':
                manager.remove_sphere(s.sphere_id)
        
        # Add COM sphere if toggled on
        if hasattr(self, '_toggle_com_action') and self._toggle_com_action.isChecked():
            manager.create_sphere_at_com(radius=self._com_radius)
        
        self.viewer_3d.update()

    def _toggle_centroid_sphere(self):
        """Toggle Centroid dummy sphere visibility."""
        if not self.molecule:
            return
        
        from src.features.visualization_3d.services.dummy_sphere import DummySphereManager
        manager = DummySphereManager(self.molecule)
        
        # Remove existing Centroid spheres
        for s in manager.get_all_spheres():
            if s.label == 'Centroid':
                manager.remove_sphere(s.sphere_id)
        
        # Add Centroid sphere if toggled on
        if hasattr(self, '_toggle_centroid_action') and self._toggle_centroid_action.isChecked():
            manager.create_sphere_at_centroid(radius=self._centroid_radius)
        
        self.viewer_3d.update()

    def _toggle_sidechains(self):
        self.viewer_3d.show_sidechains = self.input_panel.show_sidechains_check.isChecked()
        self.viewer_3d.update()

    def _change_render_mode(self, index):
        modes = ['ball_and_stick', 'spacefill', 'wireframe', 'cartoon', 'ribbon', 'backbone']
        if 0 <= index < len(modes):
            self.viewer_3d.render_mode = modes[index]
            self.viewer_3d.update()

    def _change_3d_bg_color(self):
        """Open color picker to change 3D viewer background."""
        from PySide6.QtGui import QColor
        current = self.viewer_3d.bg_color
        color = QColorDialog.getColor(
            current, self, "Choose 3D Background Color",
            QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self.viewer_3d.bg_color = color
            self.viewer_3d.update()
            self.status_bar.showMessage(
                f"3D Background: {color.name()}")

    def _change_2d_bg_color(self):
        """Open color picker to change 2D viewer background."""
        from PySide6.QtGui import QColor
        current = self.viewer_2d.bg_color
        color = QColorDialog.getColor(
            current, self, "Choose 2D Background Color",
            QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self.viewer_2d.bg_color = color
            self.viewer_2d.update()
            self.status_bar.showMessage(
                f"2D Background: {color.name()}")

    # ─── About ────────────────────────────────────────────────────

    def _show_about(self):
        QMessageBox.about(
            self, "About PyChem",
            "<h2>PyChem</h2>"
            "<p>Version 1.0.0</p>"
            "<p>A molecular viewer and cheminformatics software with:</p>"
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
            "<p>Developed by Dr. Vijay Masand, Mr. Gaurav Masand, and Mr. Krish Masand.</p>"
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
                {'atom_c': '#55ff7f', 'atom_h': '#d0d0d0', 'atom_o': '#ff0d0d', 'atom_n': '#3050f8'},  # Default
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

    def _show_protein_color_dialog(self):
        """Show protein color customization dialog."""
        if not self.molecule:
            self.status_bar.showMessage("No molecule loaded for protein color customization")
            return
        
        try:
            from src.features.visualization_3d.ui.protein_color_dialog import show_protein_color_dialog
            
            print("DEBUG: Opening protein color dialog...")
            
            # Show protein color dialog
            selected_colors = show_protein_color_dialog(self)
            
            if selected_colors:
                print(f"DEBUG: Selected colors: {selected_colors}")
                
                # CRITICAL: Force immediate viewer refresh with new colors
                print("DEBUG: Forcing viewer repaint...")
                
                # Force multiple update methods for maximum compatibility
                if hasattr(self.viewer_3d, 'repaint'):
                    self.viewer_3d.repaint()  # Immediate repaint
                
                if hasattr(self.viewer_3d, 'update'):
                    self.viewer_3d.update()  # Schedule update
                
                # Invalidate cartoon mesh cache so new colors apply
                try:
                    from src.features.visualization_3d.services.protein_rendering import _cartoon_gen
                    _cartoon_gen.invalidate()
                except ImportError:
                    pass
                
                # Process events to ensure paint happens immediately
                from PySide6.QtCore import QCoreApplication
                QCoreApplication.processEvents()
                
                self.status_bar.showMessage(f"Applied protein colors: Helix={selected_colors.get('ss_helix', 'N/A')}, Sheet={selected_colors.get('ss_sheet', 'N/A')}")
            else:
                self.status_bar.showMessage("Protein color selection cancelled")
                
        except Exception as e:
            print(f"ERROR in protein color dialog: {e}")
            import traceback
            traceback.print_exc()
            self.status_bar.showMessage(f"Protein color dialog error: {str(e)}")

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
        """Add dummy sphere at center of mass with radius selection."""
        if not self.molecule:
            self.status_bar.showMessage("No molecule loaded for COM sphere")
            return
            
        # Prompt for radius
        radius, ok = QInputDialog.getDouble(
            self, "COM Sphere Radius", 
            "Enter radius (Å):", self._com_radius, 0.1, 50.0, 2
        )
        if not ok:
            return
            
        self._com_radius = radius
            
        try:
            from src.features.visualization_3d.services.dummy_sphere import DummySphereManager
            manager = DummySphereManager(self.molecule)
            
            # Remove existing COM spheres to avoid duplicates
            for s in manager.get_all_spheres():
                if s.label == 'COM':
                    manager.remove_sphere(s.sphere_id)
            
            # Create new COM sphere
            sphere_id = manager.create_sphere_at_com(radius=self._com_radius)
            com_pos = manager.calculate_center_of_mass()
            
            self.viewer_3d.update()
            self.status_bar.showMessage(f"COM sphere added at ({com_pos[0]:.2f}, {com_pos[1]:.2f}, {com_pos[2]:.2f}) with radius {self._com_radius} Å")
                
        except Exception as e:
            self.status_bar.showMessage(f"COM sphere error: {e}")

    def _add_centroid_sphere(self):
        """Add dummy sphere at geometric centroid with radius selection."""
        if not self.molecule:
            self.status_bar.showMessage("No molecule loaded for centroid sphere")
            return
            
        # Prompt for radius
        radius, ok = QInputDialog.getDouble(
            self, "Centroid Sphere Radius", 
            "Enter radius (Å):", self._centroid_radius, 0.1, 50.0, 2
        )
        if not ok:
            return
            
        self._centroid_radius = radius
            
        try:
            from src.features.visualization_3d.services.dummy_sphere import DummySphereManager
            manager = DummySphereManager(self.molecule)
            
            # Remove existing Centroid spheres
            for s in manager.get_all_spheres():
                if s.label == 'Centroid':
                    manager.remove_sphere(s.sphere_id)
            
            # Create new Centroid sphere
            sphere_id = manager.create_sphere_at_centroid(radius=self._centroid_radius)
            centroid_pos = manager.calculate_geometric_centroid()
            
            self.viewer_3d.update()
            self.status_bar.showMessage(f"Centroid sphere added at ({centroid_pos[0]:.2f}, {centroid_pos[1]:.2f}, {centroid_pos[2]:.2f}) with radius {self._centroid_radius} Å")
                
        except Exception as e:
            self.status_bar.showMessage(f"Centroid sphere error: {e}")

    def _add_custom_sphere(self):
        """Add multi-layered dummy spheres at custom position using unified dialog."""
        if not self.molecule:
            self.status_bar.showMessage("No molecule loaded for custom sphere")
            return
            
        try:
            from src.features.ui.custom_sphere_dialog import CustomSphereDialog
            dialog = CustomSphereDialog(self.molecule, self)
            
            if dialog.exec():
                pos, layers = dialog.get_result()
                
                from src.features.visualization_3d.services.dummy_sphere import DummySphereManager
                manager = DummySphereManager(self.molecule)
                
                created_count = 0
                for layer in layers:
                    sphere_id = manager.create_sphere_at_position(
                        pos, 
                        radius=layer['radius'], 
                        color=layer['color'], 
                        alpha=layer['alpha'],
                        label='Custom'
                    )
                    created_count += 1
                
                # Refresh 3D viewer
                if hasattr(self.viewer_3d, 'update'):
                    self.viewer_3d.update()
                
                self.status_bar.showMessage(f"Added {created_count} custom sphere shell(s) at ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")
                
        except Exception as e:
            self.status_bar.showMessage(f"Custom sphere error: {e}")
            import traceback
            traceback.print_exc()

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

    def _notify_plugins_molecule_changed(self):
        """Notify all plugins that the molecule has changed."""
        if self.plugin_interface and self.plugin_interface.plugin_manager:
            # Use the new set_current_molecule method
            self.plugin_interface.plugin_manager.set_current_molecule(self.molecule)
