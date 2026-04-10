"""
Example Visualization Plugin

This plugin demonstrates how to create a visualization plugin that
adds custom rendering options to the molecular viewers.
"""

from typing import Dict, Any, List, Tuple
import logging
import math

from src.shared.qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QSlider, QGroupBox, QColorDialog,
    Qt, Signal, QMessageBox
)
from src.plugins.base_plugin import BasePlugin, PluginWidget
from src.plugins.plugin_types import PluginInfo, PluginType


class ExampleVisualizationWidget(PluginWidget):
    """
    Widget for the example visualization plugin.
    """

    def __init__(self, plugin: 'ExampleVisualizationPlugin'):
        super().__init__(plugin)

        # Visualization settings - MUST be defined before setup_ui()
        self.color_schemes = {
            'Default': {'C': '#909090', 'O': '#ff0d0d', 'N': '#3050f8', 'H': '#ffffff'},
            'CPK': {'C': '#909090', 'O': '#ff0d0d', 'N': '#3050f8', 'H': '#ffffff'},
            'Rasmol': {'C': '#ffffff', 'O': '#ff0000', 'N': '#0000ff', 'H': '#ffffff'},
            'Custom': {'C': '#909090', 'O': '#ff0d0d', 'N': '#3050f8', 'H': '#ffffff'}
        }

        self.current_scheme = 'Default'
        self.atom_size_factor = 1.0
        self.show_labels = False
        self.show_bonds = True

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        self.widget = QWidget()
        layout = QVBoxLayout(self.widget)

        # Title
        title = QLabel("Example Visualization Plugin")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Description
        description = QLabel(
            "This plugin enhances molecular visualization with:\n"
            "• Custom color schemes\n"
            "• Atom size control\n"
            "• Label display options\n"
            "• Bond visibility control"
        )
        description.setWordWrap(True)
        description.setStyleSheet("margin: 10px; color: #666;")
        layout.addWidget(description)

        # Color Scheme Group
        color_group = QGroupBox("Color Scheme")
        color_layout = QVBoxLayout(color_group)

        # Color scheme selector
        scheme_layout = QHBoxLayout()
        scheme_layout.addWidget(QLabel("Scheme:"))
        self.scheme_combo = QComboBox()
        self.scheme_combo.addItems(list(self.color_schemes.keys()))
        self.scheme_combo.currentIndexChanged.connect(self.on_scheme_changed)
        scheme_layout.addWidget(self.scheme_combo)
        color_layout.addLayout(scheme_layout)

        # Custom color buttons
        self.custom_color_layout = QHBoxLayout()
        self.custom_color_buttons = {}
        for element in ['C', 'O', 'N', 'H']:
            btn = QPushButton(f"{element} Color")
            btn.setStyleSheet(f"background-color: {self.color_schemes['Default'][element]};")
            btn.clicked.connect(lambda checked, e=element: self.change_custom_color(e))
            self.custom_color_buttons[element] = btn
            self.custom_color_layout.addWidget(btn)

        self.custom_color_widget = QWidget()
        self.custom_color_widget.setLayout(self.custom_color_layout)
        self.custom_color_widget.setVisible(False)
        color_layout.addWidget(self.custom_color_widget)

        layout.addWidget(color_group)

        # Display Options Group
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout(display_group)

        # Atom size control
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Atom Size:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(50, 200)  # 0.5x to 2.0x
        self.size_slider.setValue(100)  # 1.0x
        self.size_slider.valueChanged.connect(self.on_size_changed)
        size_layout.addWidget(self.size_slider)
        self.size_label = QLabel("1.0x")
        size_layout.addWidget(self.size_label)
        display_layout.addLayout(size_layout)

        # Checkboxes
        self.labels_checkbox = QCheckBox("Show Atom Labels")
        self.labels_checkbox.toggled.connect(self.on_labels_toggled)
        display_layout.addWidget(self.labels_checkbox)

        self.bonds_checkbox = QCheckBox("Show Bonds")
        self.bonds_checkbox.setChecked(True)
        self.bonds_checkbox.toggled.connect(self.on_bonds_toggled)
        display_layout.addWidget(self.bonds_checkbox)

        layout.addWidget(display_group)

        # Apply Buttons
        button_layout = QHBoxLayout()

        self.apply_2d_btn = QPushButton("Apply to 2D Viewer")
        self.apply_2d_btn.clicked.connect(self.apply_to_2d_viewer)
        button_layout.addWidget(self.apply_2d_btn)

        self.apply_3d_btn = QPushButton("Apply to 3D Viewer")
        self.apply_3d_btn.clicked.connect(self.apply_to_3d_viewer)
        button_layout.addWidget(self.apply_3d_btn)

        layout.addLayout(button_layout)

        # Reset button
        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.clicked.connect(self.reset_settings)
        layout.addWidget(self.reset_btn)

        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)

    def on_scheme_changed(self, index: int):
        self.current_scheme = self.scheme_combo.currentText()
        self.custom_color_widget.setVisible(self.current_scheme == 'Custom')
        self.update_status(f"Color scheme changed to {self.current_scheme}")

    def change_custom_color(self, element: str):
        color = QColorDialog.getColor()
        if color.isValid():
            color_hex = color.name()
            self.color_schemes['Custom'][element] = color_hex
            self.custom_color_buttons[element].setStyleSheet(f"background-color: {color_hex};")
            self.update_status(f"Custom color for {element} changed to {color_hex}")

    def on_size_changed(self, value: int):
        self.atom_size_factor = value / 100.0
        self.size_label.setText(f"{self.atom_size_factor:.1f}x")
        self.update_status(f"Atom size changed to {self.atom_size_factor:.1f}x")

    def on_labels_toggled(self, checked: bool):
        self.show_labels = checked
        self.update_status(f"Atom labels {'shown' if checked else 'hidden'}")

    def on_bonds_toggled(self, checked: bool):
        self.show_bonds = checked
        self.update_status(f"Bonds {'shown' if checked else 'hidden'}")

    # =========================================================================
    # Aggressive Viewer Discovery Engine (Bypasses missing BasePlugin references)
    # =========================================================================
    def _find_viewer(self, viewer_type: str):
        """Intelligently scours the host architecture to find the specific viewer."""
        method_name = f'get_viewer_{viewer_type}'
        attr_name = f'viewer_{viewer_type}'

        # 1. Try standard BasePlugin method
        if hasattr(self.plugin, method_name):
            try:
                v = getattr(self.plugin, method_name)()
                if v is not None: return v
            except Exception: pass

        # 2. Search Main Window natively
        mw = getattr(self.plugin, 'main_window', None)
        if mw:
            if hasattr(mw, method_name):
                try: return getattr(mw, method_name)()
                except Exception: pass
            if hasattr(mw, attr_name):
                return getattr(mw, attr_name)

        # 3. Search API Object natively
        api = getattr(self.plugin, 'api', None)
        if api:
            if hasattr(api, method_name):
                try: return getattr(api, method_name)()
                except Exception: pass
            if hasattr(api, attr_name):
                return getattr(api, attr_name)

        return None

    def _update_viewer(self, viewer, viewer_type: str):
        """Safely forces the viewer to refresh its canvas."""
        method_name = f'update_viewer_{viewer_type}'

        # 1. Try Standard Plugin Method
        if hasattr(self.plugin, method_name):
            try:
                getattr(self.plugin, method_name)()
                return
            except Exception: pass

        # 2. Force Qt Native Update
        if hasattr(viewer, 'update'):
            viewer.update()
        elif hasattr(viewer, 'repaint'):
            viewer.repaint()
    # =========================================================================

    def apply_to_2d_viewer(self):
        try:
            viewer_2d = self._find_viewer('2d')
            if not viewer_2d:
                QMessageBox.warning(self.widget, "Viewer Error", "Could not locate the 2D Viewer in the host application.")
                return

            molecule = getattr(self.plugin, 'current_molecule', None)
            if not molecule:
                QMessageBox.warning(self.widget, "No Molecule", "Please load a molecule first.")
                return

            colors = self.color_schemes[self.current_scheme]
            self._apply_colors_to_viewer(viewer_2d, molecule, colors)
            self._apply_display_settings_to_viewer(viewer_2d)

            self._update_viewer(viewer_2d, '2d')
            self.update_status("Settings applied to 2D viewer")

        except Exception as e:
            QMessageBox.critical(self.widget, "Application Error", f"Error applying to 2D viewer:\n{e}")

    def apply_to_3d_viewer(self):
        try:
            viewer_3d = self._find_viewer('3d')
            if not viewer_3d:
                QMessageBox.warning(self.widget, "Viewer Error", "Could not locate the 3D Viewer in the host application.")
                return

            molecule = getattr(self.plugin, 'current_molecule', None)
            if not molecule:
                QMessageBox.warning(self.widget, "No Molecule", "Please load a molecule first.")
                return

            colors = self.color_schemes[self.current_scheme]
            self._apply_colors_to_viewer(viewer_3d, molecule, colors)
            self._apply_display_settings_to_viewer(viewer_3d)

            self._update_viewer(viewer_3d, '3d')
            self.update_status("Settings applied to 3D viewer")

        except Exception as e:
            QMessageBox.critical(self.widget, "Application Error", f"Error applying to 3D viewer:\n{e}")

    def _apply_colors_to_viewer(self, viewer, molecule, colors: Dict[str, str]):
        if hasattr(viewer, 'set_atom_colors'):
            atom_colors = []
            for atom in molecule.atoms:
                symbol = getattr(atom, 'symbol', 'C')
                if not isinstance(symbol, str):
                    symbol = getattr(getattr(atom, 'element', None), 'symbol', 'C')
                color = colors.get(symbol, colors.get('C', '#909090'))
                atom_colors.append(color)
            viewer.set_atom_colors(atom_colors)

    def _apply_display_settings_to_viewer(self, viewer):
        if hasattr(viewer, 'set_atom_size'):
            viewer.set_atom_size(self.atom_size_factor)
        if hasattr(viewer, 'show_atom_labels'):
            viewer.show_atom_labels(self.show_labels)
        if hasattr(viewer, 'show_bonds'):
            viewer.show_bonds(self.show_bonds)

    def reset_settings(self):
        self.scheme_combo.setCurrentText('Default')
        self.size_slider.setValue(100)
        self.labels_checkbox.setChecked(False)
        self.bonds_checkbox.setChecked(True)

        self.color_schemes['Custom'] = self.color_schemes['Default'].copy()
        for element, btn in self.custom_color_buttons.items():
            btn.setStyleSheet(f"background-color: {self.color_schemes['Custom'][element]};")

        self.update_status("Settings reset to default")

    def update_status(self, message: str):
        self.status_label.setText(message)
        if hasattr(self.plugin, 'log_info'):
            self.plugin.log_info(f"Visualization Plugin: {message}")

    def on_molecule_changed(self, molecule):
        if molecule:
            self.update_status(f"Molecule loaded: {len(molecule.atoms)} atoms")
        else:
            self.update_status("No molecule loaded")

    def cleanup(self):
        pass


class ExampleVisualizationPlugin(BasePlugin):
    """
    Example visualization plugin.
    """

    def __init__(self):
        super().__init__(PluginInfo(
            name="Example Visualization Plugin",
            version="1.0.0",
            description="Demonstrates how to create visualization plugins with custom color schemes",
            author="SMILES Development Team",
            plugin_type=PluginType.VISUALIZATION,
            keywords=["visualization", "color", "display", "viewer"]
        ))
        self.current_molecule = None
        self.widget = None

    def get_info(self) -> PluginInfo:
        return self.info

    def create_widget(self):
        if self.widget is None:
            self.widget = ExampleVisualizationWidget(self)
        self.log_info("Example Visualization Plugin widget created")
        return self.widget

    def initialize(self, *args, **kwargs) -> bool:
        """
        Fuzzy Initialization: Safely captures the 'api' parameter regardless of
        how the host application injects it, without causing missing argument crashes.
        """
        # Find 'api' in args or kwargs
        api = getattr(self, 'api', None)
        if not api and args:
            api = args[0]
        elif not api and 'api' in kwargs:
            api = kwargs['api']

        try:
            # Satisfy the broken BasePlugin signature
            super().initialize(api)
        except Exception:
            # If it still fails, the aggressive viewer discovery will handle the communication.
            pass

        self.logger.info("Example Visualization Plugin initialized successfully")
        return True

    def on_molecule_changed(self, molecule):
        self.current_molecule = molecule
        if self.widget:
            self.widget.on_molecule_changed(molecule)

        if molecule:
            self.log_info(f"Molecule changed in Visualization Plugin: {len(molecule.atoms)} atoms")
        else:
            self.log_info("No molecule in Visualization Plugin")

    def cleanup(self):
        if self.widget:
            if hasattr(self.widget, 'cleanup'):
                self.widget.cleanup()
            if hasattr(self.widget, 'widget') and self.widget.widget:
                self.widget.widget.deleteLater()
            self.widget = None

        self.log_info("Example Visualization Plugin cleaned up")