"""
Enhanced Plugin Interface for Main Application

This module provides an improved interface between the main application
and the plugin system, with better UI, browsing capabilities, and
comprehensive plugin management.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from pathlib import Path

from src.shared.qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit,
    QGroupBox, QCheckBox, QComboBox, QProgressBar,
    QMessageBox, Qt, Signal, QFileDialog, QLineEdit,
    QSplitter, QFrame, QScrollArea, QSpinBox
)
from src.plugins import PluginManager, PLUGIN_API_VERSION
from src.plugins.utils.integration import PluginIntegrationAPI


class PluginBrowserWidget(QWidget):
    """
    Widget for browsing and installing new plugins.
    """
    
    plugin_installed = Signal(str)
    
    def __init__(self, plugin_manager: PluginManager):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the plugin browser interface."""
        layout = QVBoxLayout(self)
        
        # Title and description
        title = QLabel("Plugin Browser")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2196F3;")
        layout.addWidget(title)
        
        desc = QLabel("Browse and install new plugins from local files or repositories")
        desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Installation section
        install_group = QGroupBox("Install Plugin")
        install_layout = QVBoxLayout(install_group)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select plugin file (.py)...")
        file_layout.addWidget(self.file_path_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_plugin_file)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        file_layout.addWidget(browse_btn)
        install_layout.addLayout(file_layout)
        
        # Install button
        self.install_btn = QPushButton("Install Plugin")
        self.install_btn.clicked.connect(self.install_plugin)
        self.install_btn.setEnabled(False)
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        install_layout.addWidget(self.install_btn)
        
        layout.addWidget(install_group)
        
        # Plugin templates
        templates_group = QGroupBox("Plugin Templates")
        templates_layout = QVBoxLayout(templates_group)
        
        template_desc = QLabel("Create new plugins from templates:")
        templates_layout.addWidget(template_desc)
        
        template_buttons = QHBoxLayout()
        
        analysis_btn = QPushButton("Analysis Plugin")
        analysis_btn.clicked.connect(lambda: self.create_template("analysis"))
        template_buttons.addWidget(analysis_btn)
        
        viz_btn = QPushButton("Visualization Plugin")
        viz_btn.clicked.connect(lambda: self.create_template("visualization"))
        template_buttons.addWidget(viz_btn)
        
        io_btn = QPushButton("I/O Plugin")
        io_btn.clicked.connect(lambda: self.create_template("io"))
        template_buttons.addWidget(io_btn)
        
        templates_layout.addLayout(template_buttons)
        layout.addWidget(templates_group)
        
        # Status
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
        # Connect file path edit
        self.file_path_edit.textChanged.connect(self.on_file_path_changed)
        
    def browse_plugin_file(self):
        """Browse for plugin file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Plugin File", "", "Python Files (*.py);;All Files (*)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)
            
    def on_file_path_changed(self):
        """Handle file path change."""
        self.install_btn.setEnabled(bool(self.file_path_edit.text().strip()))
        
    def install_plugin(self):
        """Install plugin from file."""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            return
            
        try:
            self.status_text.clear()
            self.status_text.append(f"Installing plugin from: {file_path}")
            
            # Copy plugin to plugins directory
            plugins_dir = Path(self.plugin_manager.plugins_directory)
            plugin_file = Path(file_path)
            
            if not plugin_file.exists():
                raise FileNotFoundError(f"Plugin file not found: {file_path}")
                
            # Read plugin file
            with open(plugin_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Validate plugin
            from src.plugins.utils.validation import validate_plugin_file
            validation_result = validate_plugin_file(str(plugin_file))
            
            if not validation_result.get('valid', False):
                errors = validation_result.get('errors', [])
                raise ValueError(f"Plugin validation failed: {errors}")
                
            # Copy to plugins directory
            dest_path = plugins_dir / plugin_file.name
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            self.status_text.append(f"✓ Plugin copied to: {dest_path}")
            self.status_text.append("✓ Refreshing plugin list...")
            
            # Refresh plugin list
            self.plugin_manager.discover_plugins()
            
            # Auto-load the installed plugin
            try:
                plugin_name = plugin_file.stem
                if self.plugin_manager.load_plugin(plugin_name):
                    self.status_text.append(f"✓ Plugin '{plugin_name}' loaded successfully!")
                else:
                    self.status_text.append(f"⚠ Plugin installed but could not be loaded automatically")
            except Exception as load_error:
                self.status_text.append(f"⚠ Plugin installed but failed to load: {str(load_error)}")
            
            self.plugin_installed.emit(plugin_file.stem)
            
            self.status_text.append("✓ Plugin installed successfully!")
            self.file_path_edit.clear()
            
            QMessageBox.information(self, "Success", 
                                   f"Plugin '{plugin_file.stem}' installed successfully!")
            
        except Exception as e:
            self.status_text.append(f"✗ Installation failed: {str(e)}")
            QMessageBox.critical(self, "Installation Error", 
                               f"Failed to install plugin:\n{str(e)}")
            
    def create_template(self, plugin_type):
        """Create a new plugin from template."""
        try:
            templates = {
                "analysis": self.get_analysis_template(),
                "visualization": self.get_visualization_template(),
                "io": self.get_io_template()
            }
            
            template_content = templates.get(plugin_type)
            if not template_content:
                return
                
            # Save template file
            file_path, _ = QFileDialog.getSaveFileName(
                self, f"Save {plugin_type.title()} Plugin Template", 
                f"{plugin_type}_plugin.py", "Python Files (*.py)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(template_content)
                    
                self.status_text.append(f"✓ Template saved to: {file_path}")
                QMessageBox.information(self, "Template Created", 
                                       f"Plugin template saved to:\n{file_path}")
                
        except Exception as e:
            self.status_text.append(f"✗ Template creation failed: {str(e)}")
            QMessageBox.critical(self, "Template Error", 
                               f"Failed to create template:\n{str(e)}")
            
    def get_analysis_template(self):
        """Get analysis plugin template."""
        return '''"""
Analysis Plugin Template

This is a template for creating analysis plugins that calculate
molecular properties and display results.
"""

from typing import Dict, Any
import logging

from src.shared.qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTextEdit, Qt
)
from src.plugins.base_plugin import BasePlugin, PluginWidget
from src.plugins.plugin_types import PluginInfo, PluginType


class AnalysisWidget(PluginWidget):
    """Widget for the analysis plugin."""
    
    def __init__(self, plugin: 'AnalysisPlugin'):
        super().__init__(plugin)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface."""
        self.widget = QWidget()
        layout = QVBoxLayout(self.widget)
        
        # Title
        title = QLabel("Analysis Plugin")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Calculate button
        self.calculate_btn = QPushButton("Calculate Properties")
        self.calculate_btn.clicked.connect(self.calculate_properties)
        layout.addWidget(self.calculate_btn)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(["Property", "Value"])
        layout.addWidget(self.results_table)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
    def calculate_properties(self):
        """Calculate molecular properties."""
        if not self.plugin.current_molecule:
            self.status_text.append("No molecule loaded")
            return
            
        try:
            mol = self.plugin.current_molecule
            self.status_text.append("Calculating properties...")
            
            # Add your property calculations here
            # Example:
            # weight = calculate_molecular_weight(mol)
            # self.results_table.setItem(0, 0, QTableWidgetItem("Molecular Weight"))
            # self.results_table.setItem(0, 1, QTableWidgetItem(str(weight)))
            
            self.status_text.append("Calculation completed!")
            
        except Exception as e:
            self.status_text.append(f"Error: {str(e)}")
    
    def on_molecule_changed(self, molecule):
        """Handle molecule changes."""
        self.plugin.current_molecule = molecule
        if molecule:
            self.calculate_btn.setEnabled(True)
            self.status_text.append(f"Molecule loaded: {len(molecule.atoms)} atoms")
        else:
            self.calculate_btn.setEnabled(False)
            self.status_text.clear()


class AnalysisPlugin(BasePlugin):
    """Analysis plugin template."""
    
    def __init__(self):
        super().__init__()
        self.current_molecule = None
        
    def get_info(self) -> PluginInfo:
        """Get plugin information."""
        return PluginInfo(
            name="Analysis Plugin",
            version="1.0.0",
            description="Template for analysis plugins",
            author="Your Name",
            plugin_type=PluginType.ANALYSIS,
            dependencies=[]
        )
    
    def create_widget(self) -> 'AnalysisWidget':
        """Create the plugin widget."""
        return AnalysisWidget(self)
    
    def initialize(self):
        """Initialize the plugin."""
        self.logger.info("Analysis plugin initialized")
        return True
    
    def cleanup(self):
        """Clean up plugin resources."""
        self.logger.info("Analysis plugin cleaned up")
    
    def on_molecule_changed(self, molecule):
        """Handle molecule changes."""
        self.current_molecule = molecule
        if hasattr(self, 'widget') and self.widget:
            self.widget.on_molecule_changed(molecule)
'''
            
    def get_visualization_template(self):
        """Get visualization plugin template."""
        return '''"""
Visualization Plugin Template

This is a template for creating visualization plugins that
display molecules in different ways.
"""

from typing import Dict, Any
import logging

from src.shared.qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, Qt, QPainter, QColor
)
from src.plugins.base_plugin import BasePlugin, PluginWidget
from src.plugins.plugin_types import PluginInfo, PluginType


class VisualizationWidget(PluginWidget):
    """Widget for the visualization plugin."""
    
    def __init__(self, plugin: 'VisualizationPlugin'):
        super().__init__(plugin)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface."""
        self.widget = QWidget()
        layout = QVBoxLayout(self.widget)
        
        # Title
        title = QLabel("Visualization Plugin")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Visualization area
        self.viz_widget = QWidget()
        self.viz_widget.setMinimumHeight(300)
        self.viz_widget.setStyleSheet("border: 1px solid #ccc; background-color: white;")
        layout.addWidget(self.viz_widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.render_btn = QPushButton("Render")
        self.render_btn.clicked.connect(self.render_molecule)
        controls_layout.addWidget(self.render_btn)
        
        layout.addLayout(controls_layout)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
    def render_molecule(self):
        """Render the molecule."""
        if not self.plugin.current_molecule:
            self.status_text.append("No molecule loaded")
            return
            
        try:
            self.status_text.append("Rendering molecule...")
            
            # Add your visualization code here
            # Example: Custom drawing, charts, etc.
            
            self.status_text.append("Rendering completed!")
            
        except Exception as e:
            self.status_text.append(f"Error: {str(e)}")
    
    def on_molecule_changed(self, molecule):
        """Handle molecule changes."""
        self.plugin.current_molecule = molecule
        if molecule:
            self.render_btn.setEnabled(True)
            self.status_text.append(f"Molecule loaded: {len(molecule.atoms)} atoms")
        else:
            self.render_btn.setEnabled(False)
            self.status_text.clear()


class VisualizationPlugin(BasePlugin):
    """Visualization plugin template."""
    
    def __init__(self):
        super().__init__()
        self.current_molecule = None
        
    def get_info(self) -> PluginInfo:
        """Get plugin information."""
        return PluginInfo(
            name="Visualization Plugin",
            version="1.0.0",
            description="Template for visualization plugins",
            author="Your Name",
            plugin_type=PluginType.VISUALIZATION,
            dependencies=[]
        )
    
    def create_widget(self) -> 'VisualizationWidget':
        """Create the plugin widget."""
        return VisualizationWidget(self)
    
    def initialize(self):
        """Initialize the plugin."""
        self.logger.info("Visualization plugin initialized")
        return True
    
    def cleanup(self):
        """Clean up plugin resources."""
        self.logger.info("Visualization plugin cleaned up")
    
    def on_molecule_changed(self, molecule):
        """Handle molecule changes."""
        self.current_molecule = molecule
        if hasattr(self, 'widget') and self.widget:
            self.widget.on_molecule_changed(molecule)
'''
            
    def get_io_template(self):
        """Get I/O plugin template."""
        return '''"""
I/O Plugin Template

This is a template for creating I/O plugins that handle
file import/export operations.
"""

from typing import Dict, Any
import logging

from src.shared.qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, Qt, QFileDialog
)
from src.plugins.base_plugin import BasePlugin, PluginWidget
from src.plugins.plugin_types import PluginInfo, PluginType


class IOWidget(PluginWidget):
    """Widget for the I/O plugin."""
    
    def __init__(self, plugin: 'IOPlugin'):
        super().__init__(plugin)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface."""
        self.widget = QWidget()
        layout = QVBoxLayout(self.widget)
        
        # Title
        title = QLabel("I/O Plugin")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # File operations
        file_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("Import File")
        self.import_btn.clicked.connect(self.import_file)
        file_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("Export File")
        self.export_btn.clicked.connect(self.export_file)
        file_layout.addWidget(self.export_btn)
        
        layout.addLayout(file_layout)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
    def import_file(self):
        """Import a file."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Import File", "", "All Files (*)"
            )
            
            if file_path:
                self.status_text.append(f"Importing: {file_path}")
                
                # Add your import logic here
                # Example: Read file, parse data, create molecule
                
                self.status_text.append("Import completed!")
                
        except Exception as e:
            self.status_text.append(f"Import error: {str(e)}")
    
    def export_file(self):
        """Export a file."""
        if not self.plugin.current_molecule:
            self.status_text.append("No molecule to export")
            return
            
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export File", "", "All Files (*)"
            )
            
            if file_path:
                self.status_text.append(f"Exporting: {file_path}")
                
                # Add your export logic here
                # Example: Write molecule data to file
                
                self.status_text.append("Export completed!")
                
        except Exception as e:
            self.status_text.append(f"Export error: {str(e)}")
    
    def on_molecule_changed(self, molecule):
        """Handle molecule changes."""
        self.plugin.current_molecule = molecule
        if molecule:
            self.status_text.append(f"Molecule loaded: {len(molecule.atoms)} atoms")
        else:
            self.status_text.clear()


class IOPlugin(BasePlugin):
    """I/O plugin template."""
    
    def __init__(self):
        super().__init__()
        self.current_molecule = None
        
    def get_info(self) -> PluginInfo:
        """Get plugin information."""
        return PluginInfo(
            name="I/O Plugin",
            version="1.0.0",
            description="Template for I/O plugins",
            author="Your Name",
            plugin_type=PluginType.IO,
            dependencies=[]
        )
    
    def create_widget(self) -> 'IOWidget':
        """Create the plugin widget."""
        return IOWidget(self)
    
    def initialize(self):
        """Initialize the plugin."""
        self.logger.info("I/O plugin initialized")
        return True
    
    def cleanup(self):
        """Clean up plugin resources."""
        self.logger.info("I/O plugin cleaned up")
    
    def on_molecule_changed(self, molecule):
        """Handle molecule changes."""
        self.current_molecule = molecule
        if hasattr(self, 'widget') and self.widget:
            self.widget.on_molecule_changed(molecule)
'''


class EnhancedPluginManagerWidget(QWidget):
    """
    Enhanced widget for managing plugins.
    
    Provides comprehensive plugin management with browsing,
    installation, and detailed information.
    """
    
    def __init__(self, plugin_manager: PluginManager):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.setup_ui()
        self.refresh_plugin_list()
        
    def setup_ui(self):
        """Setup the enhanced user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Plugin Manager")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #2196F3; margin: 10px;")
        layout.addWidget(header)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Plugin Management Tab
        self.management_tab = self.create_management_tab()
        self.tab_widget.addTab(self.management_tab, "Manage Plugins")
        
        # Plugin Browser Tab
        self.browser_tab = PluginBrowserWidget(self.plugin_manager)
        self.browser_tab.plugin_installed.connect(self.on_plugin_installed)
        self.tab_widget.addTab(self.browser_tab, "Browse & Install")
        
        # Plugin Documentation Tab
        self.docs_tab = self.create_documentation_tab()
        self.tab_widget.addTab(self.docs_tab, "Documentation")
        
    def create_management_tab(self):
        """Create the plugin management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Search and filter
        filter_group = QGroupBox("Search & Filter")
        filter_layout = QHBoxLayout(filter_group)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search plugins...")
        self.search_edit.textChanged.connect(self.filter_plugins)
        filter_layout.addWidget(self.search_edit)
        
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "Analysis", "Visualization", "I/O", "Utility"])
        self.type_filter.currentTextChanged.connect(self.filter_plugins)
        filter_layout.addWidget(self.type_filter)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "Active", "Inactive", "Error"])
        self.status_filter.currentTextChanged.connect(self.filter_plugins)
        filter_layout.addWidget(self.status_filter)
        
        layout.addWidget(filter_group)
        
        # Plugin table
        self.plugin_table = QTableWidget()
        self.plugin_table.setColumnCount(7)
        self.plugin_table.setHorizontalHeaderLabels([
            "Name", "Version", "Type", "Status", "Author", "Description", "Actions"
        ])
        self.plugin_table.horizontalHeader().setStretchLastSection(True)
        self.plugin_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.plugin_table.itemSelectionChanged.connect(self.on_plugin_selected)
        layout.addWidget(self.plugin_table)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_plugin_list)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(self.refresh_btn)
        
        self.load_all_btn = QPushButton("Load All")
        self.load_all_btn.clicked.connect(self.load_all_plugins)
        button_layout.addWidget(self.load_all_btn)
        
        self.unload_all_btn = QPushButton("Unload All")
        self.unload_all_btn.clicked.connect(self.unload_all_plugins)
        button_layout.addWidget(self.unload_all_btn)
        
        self.reload_btn = QPushButton("Reload Selected")
        self.reload_btn.clicked.connect(self.reload_selected_plugin)
        button_layout.addWidget(self.reload_btn)
        
        layout.addLayout(button_layout)
        
        # Plugin details
        details_group = QGroupBox("Plugin Details")
        details_layout = QVBoxLayout(details_group)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(150)
        details_layout.addWidget(self.details_text)
        
        layout.addWidget(details_group)
        
        return tab
        
    def create_documentation_tab(self):
        """Create the documentation tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Documentation content
        docs_text = QTextEdit()
        docs_text.setReadOnly(True)
        docs_text.setHtml(self.get_plugin_documentation())
        layout.addWidget(docs_text)
        
        return tab
        
    def get_plugin_documentation(self):
        """Get plugin documentation HTML."""
        return """
        <h2>Plugin System Documentation</h2>
        
        <h3>Overview</h3>
        <p>The SMILES application supports a flexible plugin system that allows you to extend functionality with custom analysis, visualization, and I/O plugins.</p>
        
        <h3>Plugin Types</h3>
        <ul>
        <li><strong>Analysis Plugins:</strong> Calculate molecular properties, perform statistical analysis, generate reports</li>
        <li><strong>Visualization Plugins:</strong> Create custom molecular visualizations, charts, and interactive displays</li>
        <li><strong>I/O Plugins:</strong> Handle file import/export for different formats, connect to external databases</li>
        <li><strong>Utility Plugins:</strong> Provide helper functions, tools, and utilities</li>
        </ul>
        
        <h3>Creating Plugins</h3>
        <p>Use the "Browse & Install" tab to create plugins from templates. Templates include:</p>
        <ul>
        <li>Basic plugin structure</li>
        <li>UI components</li>
        <li>Error handling</li>
        <li>Integration with the main application</li>
        </ul>
        
        <h3>Plugin Structure</h3>
        <p>Each plugin must include:</p>
        <ul>
        <li>A class inheriting from <code>BasePlugin</code></li>
        <li>A widget class inheriting from <code>PluginWidget</code></li>
        <li>Plugin information via <code>PluginInfo</code></li>
        <li>Proper initialization and cleanup methods</li>
        </ul>
        
        <h3>Installation</h3>
        <p>To install plugins:</p>
        <ol>
        <li>Go to the "Browse & Install" tab</li>
        <li>Click "Browse..." to select a plugin file</li>
        <li>Click "Install Plugin"</li>
        <li>The plugin will be automatically detected and available</li>
        </ol>
        
        <h3>API Reference</h3>
        <p>Plugins have access to:</p>
        <ul>
        <li>Current molecule data</li>
        <li>Qt widgets for UI creation</li>
        <li>Logging system</li>
        <li>Plugin integration API</li>
        <li>Event system for molecule changes</li>
        </ul>
        
        <h3>Best Practices</h3>
        <ul>
        <li>Follow the plugin template structure</li>
        <li>Include proper error handling</li>
        <li>Use the logging system for debugging</li>
        <li>Test plugins thoroughly before distribution</li>
        <li>Document plugin functionality clearly</li>
        </ul>
        
        <h3>Troubleshooting</h3>
        <p>Common issues:</p>
        <ul>
        <li><strong>Plugin not loading:</strong> Check for syntax errors and missing dependencies</li>
        <li><strong>UI not appearing:</strong> Ensure the widget is properly created and returned</li>
        <li><strong>Errors on molecule change:</strong> Implement proper null checks in <code>on_molecule_changed</code></li>
        </ul>
        """
        
    def refresh_plugin_list(self):
        """Refresh the plugin list with enhanced information."""
        try:
            # Discover plugins
            plugins = self.plugin_manager.discover_plugins()
            
            # Store all plugins for filtering
            self.all_plugins = plugins
            
            # Update table
            self.update_plugin_table(plugins)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error refreshing plugin list: {e}")
            
    def update_plugin_table(self, plugins):
        """Update the plugin table with filtered plugins."""
        self.plugin_table.setRowCount(len(plugins))
        
        for row, (name, metadata) in enumerate(plugins.items()):
            # Name
            name_item = QTableWidgetItem(name)
            name_item.setToolTip(f"Plugin: {name}")
            self.plugin_table.setItem(row, 0, name_item)
            
            # Version
            version_item = QTableWidgetItem(metadata.info.version)
            self.plugin_table.setItem(row, 1, version_item)
            
            # Type
            type_item = QTableWidgetItem(metadata.info.plugin_type.value)
            self.plugin_table.setItem(row, 2, type_item)
            
            # Status
            status = metadata.status.value if metadata.status else "inactive"
            status_item = QTableWidgetItem(status)
            if metadata.status and metadata.status.value == "active":
                status_item.setStyleSheet("color: green; font-weight: bold;")
            elif metadata.status and metadata.status.value == "error":
                status_item.setStyleSheet("color: red; font-weight: bold;")
            self.plugin_table.setItem(row, 3, status_item)
            
            # Author
            author_item = QTableWidgetItem(metadata.info.author)
            self.plugin_table.setItem(row, 4, author_item)
            
            # Description
            desc_item = QTableWidgetItem(metadata.info.description[:50] + "..." if len(metadata.info.description) > 50 else metadata.info.description)
            desc_item.setToolTip(metadata.info.description)
            self.plugin_table.setItem(row, 5, desc_item)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            if self.plugin_manager.is_plugin_loaded(name):
                unload_btn = QPushButton("Unload")
                unload_btn.clicked.connect(lambda checked, n=name: self.unload_plugin(n))
                unload_btn.setStyleSheet("background-color: #f44336; color: white; padding: 4px 8px;")
                actions_layout.addWidget(unload_btn)
            else:
                load_btn = QPushButton("Load")
                load_btn.clicked.connect(lambda checked, n=name: self.load_plugin(n))
                load_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 4px 8px;")
                actions_layout.addWidget(load_btn)
            
            self.plugin_table.setCellWidget(row, 6, actions_widget)
        
        self.plugin_table.resizeColumnsToContents()
        
    def filter_plugins(self):
        """Filter plugins based on search and filters."""
        if not hasattr(self, 'all_plugins'):
            return
            
        search_text = self.search_edit.text().lower()
        type_filter = self.type_filter.currentText()
        status_filter = self.status_filter.currentText()
        
        filtered = {}
        
        for name, metadata in self.all_plugins.items():
            # Search filter
            if search_text and search_text not in name.lower() and search_text not in metadata.info.description.lower():
                continue
                
            # Type filter
            if type_filter != "All Types" and metadata.info.plugin_type.value != type_filter.lower():
                continue
                
            # Status filter
            status = metadata.status.value if metadata.status else "inactive"
            if status_filter != "All Status" and status != status_filter.lower():
                continue
                
            filtered[name] = metadata
            
        self.update_plugin_table(filtered)
        
    def on_plugin_selected(self):
        """Handle plugin selection."""
        current_row = self.plugin_table.currentRow()
        if current_row >= 0:
            name_item = self.plugin_table.item(current_row, 0)
            if name_item:
                plugin_name = name_item.text()
                self.show_plugin_details(plugin_name)
                
    def show_plugin_details(self, plugin_name):
        """Show detailed information about a plugin."""
        try:
            plugins = self.plugin_manager.discover_plugins()
            if plugin_name in plugins:
                metadata = plugins[plugin_name]
                
                details = f"""
<strong>Plugin Details:</strong>

Name: {metadata.info.name}
Version: {metadata.info.version}
Type: {metadata.info.plugin_type.value}
Author: {metadata.info.author}
Status: {metadata.status.value if metadata.status else 'inactive'}

Description:
{metadata.info.description}

Dependencies: {', '.join(metadata.info.dependencies) if metadata.info.dependencies else 'None'}

File: {metadata.module_path}
Min API Version: {metadata.info.min_api_version}
"""
                
                self.details_text.setHtml(details)
                
        except Exception as e:
            self.details_text.setPlainText(f"Error loading details: {str(e)}")
            
    def load_plugin(self, plugin_name: str):
        """Load a specific plugin."""
        try:
            if self.plugin_manager.load_plugin(plugin_name):
                QMessageBox.information(self, "Success", f"Plugin {plugin_name} loaded successfully")
                self.refresh_plugin_list()
            else:
                QMessageBox.critical(self, "Error", f"Failed to load plugin {plugin_name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading plugin: {e}")
            
    def unload_plugin(self, plugin_name: str):
        """Unload a specific plugin."""
        try:
            if self.plugin_manager.unload_plugin(plugin_name):
                QMessageBox.information(self, "Success", f"Plugin {plugin_name} unloaded successfully")
                self.refresh_plugin_list()
            else:
                QMessageBox.critical(self, "Error", f"Failed to unload plugin {plugin_name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error unloading plugin: {e}")
            
    def load_all_plugins(self):
        """Load all available plugins."""
        try:
            plugins = self.plugin_manager.discover_plugins()
            loaded_count = 0
            
            for plugin_name in plugins.keys():
                if not self.plugin_manager.is_plugin_loaded(plugin_name):
                    if self.plugin_manager.load_plugin(plugin_name):
                        loaded_count += 1
                        
            QMessageBox.information(self, "Success", f"Loaded {loaded_count} plugins")
            self.refresh_plugin_list()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading plugins: {e}")
            
    def unload_all_plugins(self):
        """Unload all loaded plugins."""
        try:
            plugins = self.plugin_manager.discover_plugins()
            unloaded_count = 0
            
            for plugin_name in plugins.keys():
                if self.plugin_manager.is_plugin_loaded(plugin_name):
                    if self.plugin_manager.unload_plugin(plugin_name):
                        unloaded_count += 1
                        
            QMessageBox.information(self, "Success", f"Unloaded {unloaded_count} plugins")
            self.refresh_plugin_list()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error unloading plugins: {e}")
            
    def reload_selected_plugin(self):
        """Reload the selected plugin."""
        current_row = self.plugin_table.currentRow()
        if current_row >= 0:
            name_item = self.plugin_table.item(current_row, 0)
            if name_item:
                plugin_name = name_item.text()
                
                # Unload first
                if self.plugin_manager.is_plugin_loaded(plugin_name):
                    self.plugin_manager.unload_plugin(plugin_name)
                    
                # Then load
                if self.plugin_manager.load_plugin(plugin_name):
                    QMessageBox.information(self, "Success", f"Plugin {plugin_name} reloaded successfully")
                    self.refresh_plugin_list()
                else:
                    QMessageBox.critical(self, "Error", f"Failed to reload plugin {plugin_name}")
                    
    def on_plugin_installed(self, plugin_name):
        """Handle plugin installation."""
        self.refresh_plugin_list()


class PluginInterface:
    """
    Enhanced interface between the main application and plugin system.
    
    Provides comprehensive plugin management with browsing,
    installation, and integration capabilities.
    """
    
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.plugin_manager = None
        self.plugin_widget = None
        self.plugin_tab_widget = None  # Add this missing attribute
        self.plugin_tabs = {}  # Add this missing attribute
        self.logger = logging.getLogger("plugin.interface")
        
    def initialize_plugin_system(self):
        """Initialize the plugin system."""
        try:
            from src.plugins import PluginManager
            
            # Get plugins directory
            plugins_dir = Path("plugins")
            if not plugins_dir.exists():
                plugins_dir.mkdir(exist_ok=True)
                
            # Create plugin manager
            self.plugin_manager = PluginManager(str(plugins_dir))
            
            # Create and set plugin API
            from src.plugins.utils.integration import PluginIntegrationAPI
            self.plugin_api = PluginIntegrationAPI(self.parent)
            self.plugin_manager.set_api(self.plugin_api)
            
            # Discover plugins
            self.plugin_manager.discover_plugins()
            
            self.logger.info("Plugin system initialized successfully with API")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize plugin system: {e}")
            return False
            
    def setup_event_handlers(self):
        """Setup event handlers for plugin system."""
        if self.plugin_manager:
            # Handle molecule changes
            self.plugin_manager.add_event_handler('molecule_changed', self.on_molecule_changed)
            
    def create_plugin_manager_widget(self) -> EnhancedPluginManagerWidget:
        """Create the enhanced plugin manager widget."""
        if self.plugin_manager:
            return EnhancedPluginManagerWidget(self.plugin_manager)
        else:
            return QWidget()
            
    def create_plugin_tabs(self, tab_widget: QTabWidget):
        """Create tabs for all loaded plugins."""
        if not self.plugin_manager:
            return
            
        try:
            plugins = self.plugin_manager.discover_plugins()
            loaded_count = 0
            
            for plugin_name, metadata in plugins.items():
                if self.plugin_manager.is_plugin_loaded(plugin_name):
                    try:
                        plugin = self.plugin_manager.get_plugin(plugin_name)
                        if plugin and hasattr(plugin, 'create_widget'):
                            widget = plugin.create_widget()
                            if widget:
                                # Handle both PluginWidget wrappers and direct QWidgets
                                real_widget = widget.widget if hasattr(widget, 'widget') and widget.widget else widget
                                tab_widget.addTab(real_widget, plugin_name)
                                loaded_count += 1
                                
                    except Exception as e:
                        self.logger.error(f"Error creating tab for plugin {plugin_name}: {e}")
                        
            self.logger.info(f"Created {loaded_count} plugin tabs")
            
        except Exception as e:
            self.logger.error(f"Error creating plugin tabs: {e}")
            
    def on_molecule_changed(self, event):
        """Handle molecule changes from plugin system."""
        molecule = event.data.get('molecule')
        
        # Notify all plugins
        if self.plugin_manager:
            self.plugin_manager.on_molecule_changed(molecule)
            
    def get_plugin_manager(self) -> Optional[object]:
        """Get the plugin manager."""
        return self.plugin_manager
        
    def get_plugin_api(self) -> PluginIntegrationAPI:
        """Get the plugin integration API."""
        if self.plugin_manager:
            return PluginIntegrationAPI(self.plugin_manager)
        return None
        
    def show_plugin_manager(self):
        """Show the plugin manager dialog."""
        if not self.plugin_manager:
            QMessageBox.warning(self.parent, "Plugin System", 
                              "Plugin system not initialized")
            return
            
        # Create and show plugin manager widget
        manager_widget = self.create_plugin_manager_widget()
        manager_widget.setWindowTitle("Plugin Manager")
        manager_widget.resize(800, 600)
        manager_widget.show()
        
        # Store reference if needed
        self.plugin_widget = manager_widget
    
    def refresh_plugin_tabs(self):
        """Refresh plugin tabs."""
        if not self.plugin_tab_widget:
            return
        
        # Clear existing plugin tabs (except manager tab)
        for i in range(self.plugin_tab_widget.count() - 1, 0, -1):
            tab_text = self.plugin_tab_widget.tabText(i)
            if tab_text != "Plugin Manager":
                self.plugin_tab_widget.removeTab(i)
        
        # Add tabs for loaded plugins
        loaded_plugins = self.plugin_manager.get_loaded_plugins()
        for plugin_name, plugin in loaded_plugins.items():
            try:
                widget = plugin.create_widget()
                if widget:
                    self.plugin_tab_widget.addTab(widget, plugin_name)
                    self.plugin_tabs[plugin_name] = widget
                    self.logger.info(f"Added tab for plugin: {plugin_name}")
            except Exception as e:
                self.logger.error(f"Error creating tab for plugin {plugin_name}: {e}")
    
    def show_plugin_tab(self, plugin_name: str):
        """
        Show a specific plugin tab.
        
        Args:
            plugin_name: Name of the plugin to show
        """
        if not self.plugin_tab_widget:
            return
        
        # Find the tab index for the plugin
        for i in range(self.plugin_tab_widget.count()):
            if self.plugin_tab_widget.tabText(i) == plugin_name:
                self.plugin_tab_widget.setCurrentIndex(i)
                self.plugin_manager.on_plugin_activated(plugin_name)
                return
        
        # If tab not found, try to create it
        plugin = self.plugin_manager.get_plugin(plugin_name)
        if plugin:
            try:
                widget = plugin.create_widget()
                if widget:
                    index = self.plugin_tab_widget.addTab(widget, plugin_name)
                    self.plugin_tab_widget.setCurrentIndex(index)
                    self.plugin_manager.on_plugin_activated(plugin_name)
            except Exception as e:
                self.logger.error(f"Error creating tab for plugin {plugin_name}: {e}")
    
    def on_molecule_changed(self, event):
        """
        Handle molecule changes from plugin system.
        
        Args:
            event: Molecule changed event
        """
        molecule = event.data.get('molecule')
        
        # Notify all plugins
        self.plugin_manager.on_molecule_changed(molecule)
    
    def get_plugin_manager(self) -> PluginManager:
        """Get the plugin manager."""
        return self.plugin_manager
    
    def get_plugin_api(self) -> PluginIntegrationAPI:
        """Get the plugin API."""
        return self.plugin_api
    
    def cleanup(self):
        """Clean up the plugin interface."""
        try:
            # Unload all plugins
            loaded_plugins = list(self.plugin_manager.get_loaded_plugins().keys())
            for plugin_name in loaded_plugins:
                self.plugin_manager.unload_plugin(plugin_name)
            
            self.logger.info("Plugin interface cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up plugin interface: {e}")
    
    def get_plugin_statistics(self) -> Dict[str, Any]:
        """Get plugin system statistics."""
        stats = self.plugin_manager.get_statistics()
        stats.update({
            'api_version': PLUGIN_API_VERSION,
            'loaded_plugins': len(self.plugin_manager.get_loaded_plugins()),
            'available_plugins': len(self.plugin_manager.get_all_plugins()),
            'active_tabs': len(self.plugin_tabs)
        })
        return stats
