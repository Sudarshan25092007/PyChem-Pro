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

# ── Extracted modules ────────────────────────────────────────────
from src.app.conversion_worker import ConversionWorker
from src.app import menu_bar as _menu_bar
from src.app import file_operations as _file_ops
from src.app import chemistry_actions as _chem
from src.app import viewer_coordinator as _viewer
from src.app import molecule_controller as _mol_ctrl


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

    # ── Menu bar (delegated) ─────────────────────────────────────

    def _init_menu_bar(self):
        """Create menu bar."""
        _menu_bar.build_menu_bar(self)

    # ── Plugin system ────────────────────────────────────────────

    def _init_plugin_system(self):
        """Initialize the plugin system."""
        try:
            self.plugin_interface = PluginInterface(self)
            self.plugin_interface.initialize_plugin_system()
            print("Plugin system initialized successfully")
        except Exception as e:
            print(f"Error initializing plugin system: {e}")
            self.plugin_interface = None

    # ── Central widget ───────────────────────────────────────────

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

    # ── Plugin dock ──────────────────────────────────────────────

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
                    status = "\u2713" if name in loaded else "\u25cb"
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

    # ── Status bar ───────────────────────────────────────────────

    def _init_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready -- Enter a SMILES string to begin")

    # ── Signal wiring (delegated) ────────────────────────────────

    def _connect_signals(self):
        """Connect all widget signals."""
        _mol_ctrl.connect_signals(self)

    # ── Molecule controller delegates ────────────────────────────

    def _convert_smiles(self, smiles):
        _mol_ctrl.convert_smiles(self, smiles)

    def _on_conversion_done(self, molecule, error):
        _mol_ctrl.on_conversion_done(self, molecule, error)

    def _set_molecule(self, molecule):
        _mol_ctrl.set_molecule(self, molecule)

    def _delete_selected_atoms(self, atom_indices=None):
        _mol_ctrl.delete_selected_atoms(self, atom_indices)

    def _undo_delete(self):
        _mol_ctrl.undo_delete(self)

    def _close_molecule(self):
        _mol_ctrl.close_molecule(self)

    def _deselect_all(self):
        _mol_ctrl.deselect_all(self)

    def _show_substructure_dialog(self):
        _mol_ctrl.show_substructure_dialog(self)

    def _notify_plugins_molecule_changed(self):
        _mol_ctrl.notify_plugins_molecule_changed(self)

    # ── File operations delegates ────────────────────────────────

    def _open_smiles_file(self):
        _file_ops.open_smiles_file(self)

    def _import_structure_file(self, filepath=None):
        _file_ops.import_structure_file(self, filepath)

    def _export_sdf(self):
        _file_ops.export_sdf(self)

    def _export_mol2(self):
        _file_ops.export_mol2(self)

    def _export_image(self, dpi, white_bg):
        _file_ops.export_image(self, dpi, white_bg)

    def _update_recent_files_menu(self):
        _file_ops.update_recent_files_menu(self)

    def _open_recent_file(self, filepath):
        _file_ops.open_recent_file(self, filepath)

    def _add_recent_file(self, filepath):
        _file_ops.add_recent_file(self, filepath)

    def dragEnterEvent(self, event):
        _file_ops.handle_drag_enter(self, event)

    def dropEvent(self, event):
        _file_ops.handle_drop(self, event)

    # ── Chemistry action delegates ───────────────────────────────

    def _optimize_geometry(self, checked=False, method=None):
        _chem.optimize_geometry(self, checked, method)

    def _compute_charges(self, checked=False, method=None):
        _chem.compute_charges(self, checked, method)

    def _open_descriptor_calculator(self):
        _chem.open_descriptor_calculator(self)

    def _perceive_aromaticity_action(self):
        _chem.perceive_aromaticity_action(self)

    def _generate_smiles(self):
        _chem.generate_smiles(self)

    def _copy_smiles_to_clipboard(self):
        _chem.copy_smiles_to_clipboard(self)

    # ── Viewer coordinator delegates ─────────────────────────────

    def _toggle_hydrogens(self):
        _viewer.toggle_hydrogens(self)

    def _toggle_labels(self):
        _viewer.toggle_labels(self)

    def _toggle_sidechains(self):
        _viewer.toggle_sidechains(self)

    def _toggle_sasa(self, checked):
        _viewer.toggle_sasa(self, checked)

    def _toggle_sasa_selected_only(self, checked):
        _viewer.toggle_sasa_selected_only(self, checked)

    def _change_render_mode(self, index):
        _viewer.change_render_mode(self, index)

    def _change_3d_bg_color(self):
        _viewer.change_3d_bg_color(self)

    def _change_2d_bg_color(self):
        _viewer.change_2d_bg_color(self)

    def _toggle_com_sphere(self):
        _viewer.toggle_com_sphere(self)

    def _toggle_centroid_sphere(self):
        _viewer.toggle_centroid_sphere(self)

    def _show_color_dialog(self):
        _viewer.show_color_dialog(self)

    def _basic_color_toggle(self):
        _viewer.basic_color_toggle(self)

    def _show_protein_color_dialog(self):
        _viewer.show_protein_color_dialog(self)

    def _update_atom_colors(self, colors):
        _viewer.update_atom_colors(self, colors)

    def _add_com_sphere(self):
        _viewer.add_com_sphere(self)

    def _add_centroid_sphere(self):
        _viewer.add_centroid_sphere(self)

    def _add_custom_sphere(self):
        _viewer.add_custom_sphere(self)

    def _create_dummy_atom_sphere(self, position, radius, color, label):
        _viewer.create_dummy_atom_sphere(self, position, radius, color, label)

    def _clear_all_spheres(self):
        _viewer.clear_all_spheres(self)

    # ── Plugin management ────────────────────────────────────────

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

        except Exception as e:
            print(f"Error showing installed plugins dialog: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"Could not open installed plugins dialog: {str(e)}")

    def _refresh_plugins(self):
        """Refresh the plugin system."""
        if self.plugin_interface:
            try:
                self.plugin_interface.initialize_plugin_system()
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
            while self.viewer_tabs.count() > 2:
                self.viewer_tabs.removeTab(2)
            self.plugin_interface.create_plugin_tabs(self.viewer_tabs)

    # ── About ────────────────────────────────────────────────────

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

    # ── Window events ────────────────────────────────────────────

    def resizeEvent(self, event):
        """Handle window resize events safely."""
        try:
            super().resizeEvent(event)

            if hasattr(self, 'viewer_3d') and self.viewer_3d:
                self.viewer_3d.update()
            if hasattr(self, 'viewer_2d') and self.viewer_2d:
                self.viewer_2d.update()

        except Exception as e:
            print(f"Resize error: {e}")
            pass
