"""
Molecular Descriptor Calculator GUI

Comprehensive GUI for molecular descriptor calculation with selection support,
progress tracking, and export capabilities.
"""

import sys
import csv
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Try to import Qt framework (support both PySide6 and PyQt6)
try:
    from PySide6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
        QGroupBox, QLabel, QLineEdit, QPushButton, QCheckBox,
        QTreeWidget, QTreeWidgetItem, QTextEdit, QProgressBar,
        QFileDialog, QMessageBox, QSplitter, QComboBox, QSpinBox,
        QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
        QScrollArea, QFrame, QGridLayout, QRadioButton, QButtonGroup
    )
    from PySide6.QtCore import Qt, QThread, Signal, QTimer
    from PySide6.QtGui import QFont, QIcon, QPixmap
    QT_FRAMEWORK = "PySide6"
except ImportError:
    try:
        from PyQt6.QtWidgets import (
            QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
            QGroupBox, QLabel, QLineEdit, QPushButton, QCheckBox,
            QTreeWidget, QTreeWidgetItem, QTextEdit, QProgressBar,
            QFileDialog, QMessageBox, QSplitter, QComboBox, QSpinBox,
            QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
            QScrollArea, QFrame, QGridLayout, QRadioButton, QButtonGroup
        )
        from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal, QTimer
        from PyQt6.QtGui import QFont, QIcon, QPixmap
        QT_FRAMEWORK = "PyQt6"
    except ImportError:
        # If neither is available, create a dummy import for testing
        print("Warning: Neither PySide6 nor PyQt6 available. GUI will not work.")
        QT_FRAMEWORK = None

from ..cheminformatics.services.atom_properties import AtomPropertyAnalyzer
from .descriptor_engine import DescriptorEngine
from .descriptor_types import (
    DescriptorCategory, DescriptorInfo, DescriptorResult,
    CalculationProgress, AtomSelection, SelectionType
)
from ...shared.ui.theme import COLORS

# Only define GUI classes if Qt framework is available
if QT_FRAMEWORK is not None:

    class DescriptorCalculationThread(QThread):
    """Thread for descriptor calculations to avoid GUI freezing."""
    
    progress_updated = Signal(object)
    calculation_finished = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, engine, molecule, selection, categories):
        super().__init__()
        self.engine = engine
        self.molecule = molecule
        self.selection = selection
        self.categories = categories
    
    def run(self):
        try:
            # Set progress callback
            self.engine.set_progress_callback(self.progress_updated.emit)
            
            # Calculate descriptors
            results = self.engine.calculate_descriptors(
                self.molecule, self.selection, self.categories
            )
            
            self.calculation_finished.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

class SelectionBuilder(QWidget):
    """Widget for building atom selections."""
    
    def __init__(self, molecule, parent=None):
        super().__init__(parent)
        self.molecule = molecule
        self.selection_history = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Selection type group
        type_group = QGroupBox("Selection Type")
        type_layout = QVBoxLayout(type_group)
        
        self.selection_type_group = QButtonGroup()
        
        self.all_radio = QRadioButton("All Atoms")
        self.all_radio.setChecked(True)
        self.selection_type_group.addButton(self.all_radio, 0)
        
        self.custom_radio = QRadioButton("Custom Selection")
        self.selection_type_group.addButton(self.custom_radio, 1)
        
        self.fragment_radio = QRadioButton("Fragment")
        self.selection_type_group.addButton(self.fragment_radio, 2)
        
        self.environment_radio = QRadioButton("Environment")
        self.selection_type_group.addButton(self.environment_radio, 3)
        
        type_layout.addWidget(self.all_radio)
        type_layout.addWidget(self.custom_radio)
        type_layout.addWidget(self.fragment_radio)
        type_layout.addWidget(self.environment_radio)
        
        layout.addWidget(type_group)
        
        # Custom selection input
        custom_group = QGroupBox("Custom Selection")
        custom_layout = QVBoxLayout(custom_group)
        
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Enter atom indices (e.g., 1,2,3-5,7)")
        custom_layout.addWidget(QLabel("Atom Indices:"))
        custom_layout.addWidget(self.custom_input)
        
        layout.addWidget(custom_group)
        
        # Selection algebra
        algebra_group = QGroupBox("Selection Algebra")
        algebra_layout = QGridLayout(algebra_group)
        
        self.algebra_input = QLineEdit()
        self.algebra_input.setPlaceholderText("e.g., sele('lipo') and within(5.0, sele('donor'))")
        algebra_layout.addWidget(QLabel("Expression:"), 0, 0)
        algebra_layout.addWidget(self.algebra_input, 0, 1)
        
        self.apply_algebra_btn = QPushButton("Apply Algebra")
        self.apply_algebra_btn.clicked.connect(self.apply_algebra)
        algebra_layout.addWidget(self.apply_algebra_btn, 1, 0, 1, 2)
        
        layout.addWidget(algebra_group)
        
        # Current selection display
        current_group = QGroupBox("Current Selection")
        current_layout = QVBoxLayout(current_group)
        
        self.current_selection = QTextEdit()
        self.current_selection.setMaximumHeight(100)
        self.current_selection.setReadOnly(True)
        current_layout.addWidget(QLabel("Selected Atoms:"))
        current_layout.addWidget(self.current_selection)
        
        layout.addWidget(current_group)
        
        # Selection buttons
        button_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("Preview Selection")
        self.preview_btn.clicked.connect(self.preview_selection)
        button_layout.addWidget(self.preview_btn)
        
        self.clear_btn = QPushButton("Clear Selection")
        self.clear_btn.clicked.connect(self.clear_selection)
        button_layout.addWidget(self.clear_btn)
        
        self.save_btn = QPushButton("Save Selection")
        self.save_btn.clicked.connect(self.save_selection)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
        # Update selection display
        self.update_selection_display()
    
    def get_selection(self) -> AtomSelection:
        """Get current atom selection."""
        selected_type = self.selection_type_group.checkedId()
        
        if selected_type == 0:  # All atoms
            return AtomSelection(
                SelectionType.ALL,
                list(range(len(self.molecule.atoms))),
                "All atoms"
            )
        elif selected_type == 1:  # Custom
            indices = self.parse_custom_selection()
            return AtomSelection(
                SelectionType.CUSTOM,
                indices,
                f"Custom: {self.custom_input.text()}"
            )
        elif selected_type == 2:  # Fragment
            # Would implement fragment selection logic
            return AtomSelection(
                SelectionType.FRAGMENT,
                list(range(len(self.molecule.atoms))),
                "Fragment selection"
            )
        elif selected_type == 3:  # Environment
            # Would implement environment selection logic
            return AtomSelection(
                SelectionType.ENVIRONMENT,
                list(range(len(self.molecule.atoms))),
                "Environment selection"
            )
        
        return AtomSelection(SelectionType.ALL, [], "Empty selection")
    
    def parse_custom_selection(self) -> List[int]:
        """Parse custom selection input."""
        text = self.custom_input.text().strip()
        if not text:
            return []
        
        indices = []
        parts = text.split(',')
        
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Range like 3-7
                start, end = map(int, part.split('-'))
                indices.extend(range(start, end + 1))
            else:
                # Single index
                indices.append(int(part))
        
        return sorted(set(indices))
    
    def apply_algebra(self):
        """Apply selection algebra expression."""
        expression = self.algebra_input.text().strip()
        if not expression:
            return
        
        # This would implement selection algebra parsing
        # For now, just show a placeholder
        self.current_selection.setText(f"Algebra: {expression}\n(Not implemented yet)")
    
    def preview_selection(self):
        """Preview current selection."""
        selection = self.get_selection()
        self.update_selection_display()
    
    def clear_selection(self):
        """Clear current selection."""
        self.custom_input.clear()
        self.algebra_input.clear()
        self.all_radio.setChecked(True)
        self.update_selection_display()
    
    def save_selection(self):
        """Save current selection."""
        selection = self.get_selection()
        self.selection_history.append(selection)
        QMessageBox.information(self, "Selection Saved", 
                           f"Selection '{selection.description}' saved.")
    
    def update_selection_display(self):
        """Update the selection display."""
        selection = self.get_selection()
        
        if len(selection.atom_indices) <= 20:
            indices_str = ", ".join(map(str, selection.atom_indices))
        else:
            indices_str = f"{len(selection.atom_indices)} atoms: {selection.atom_indices[:10]}..."
        
        display_text = f"Type: {selection.selection_type.value}\n"
        display_text += f"Description: {selection.description}\n"
        display_text += f"Indices: {indices_str}"
        
        self.current_selection.setText(display_text)

class DescriptorConfigWidget(QWidget):
    """Widget for configuring descriptor categories."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = DescriptorEngine()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Category selection
        category_group = QGroupBox("Descriptor Categories")
        category_layout = QVBoxLayout(category_group)
        
        self.category_checkboxes = {}
        for category in DescriptorCategory:
            checkbox = QCheckBox(f"{category.value} ({len(self.engine.descriptors[category])} descriptors)")
            checkbox.setChecked(True)
            self.category_checkboxes[category] = checkbox
            category_layout.addWidget(checkbox)
        
        layout.addWidget(category_group)
        
        # Quick select buttons
        button_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_categories)
        button_layout.addWidget(self.select_all_btn)
        
        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.clicked.connect(self.select_none_categories)
        button_layout.addWidget(self.select_none_btn)
        
        self.select_basic_btn = QPushButton("Basic Only")
        self.select_basic_btn.clicked.connect(self.select_basic_categories)
        button_layout.addWidget(self.select_basic_btn)
        
        layout.addLayout(button_layout)
        
        # Descriptor preview
        preview_group = QGroupBox("Selected Descriptors")
        preview_layout = QVBoxLayout(preview_group)
        
        self.descriptor_preview = QTextEdit()
        self.descriptor_preview.setMaximumHeight(150)
        self.descriptor_preview.setReadOnly(True)
        preview_layout.addWidget(self.descriptor_preview)
        
        layout.addWidget(preview_group)
        
        # Update preview
        self.update_descriptor_preview()
        
        # Connect checkbox signals
        for checkbox in self.category_checkboxes.values():
            checkbox.toggled.connect(self.update_descriptor_preview)
    
    def get_selected_categories(self) -> List[DescriptorCategory]:
        """Get selected descriptor categories."""
        selected = []
        for category, checkbox in self.category_checkboxes.items():
            if checkbox.isChecked():
                selected.append(category)
        return selected
    
    def select_all_categories(self):
        """Select all categories."""
        for checkbox in self.category_checkboxes.values():
            checkbox.setChecked(True)
    
    def select_none_categories(self):
        """Select no categories."""
        for checkbox in self.category_checkboxes.values():
            checkbox.setChecked(False)
    
    def select_basic_categories(self):
        """Select only basic categories."""
        basic_categories = [DescriptorCategory.CONSTITUTIONAL, DescriptorCategory.TOPOLOGICAL]
        
        for category, checkbox in self.category_checkboxes.items():
            checkbox.setChecked(category in basic_categories)
    
    def update_descriptor_preview(self):
        """Update descriptor preview."""
        selected_categories = self.get_selected_categories()
        
        preview_text = f"Selected {len(selected_categories)} categories:\n"
        total_descriptors = 0
        
        for category in selected_categories:
            descriptors = self.engine.descriptors[category]
            total_descriptors += len(descriptors)
            preview_text += f"  • {category.value}: {len(descriptors)} descriptors\n"
        
        preview_text += f"\nTotal: {total_descriptors} descriptors"
        
        self.descriptor_preview.setText(preview_text)

class DescriptorCalculatorDialog(QMainWindow):
    """Main descriptor calculator dialog."""
    
    def __init__(self, molecule, parent=None):
        super().__init__(parent)
        self.molecule = molecule
        self.current_results = {}
        self.calculation_thread = None
        
        self.setWindowTitle("Molecular Descriptor Calculator")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set window icon if available
        try:
            self.setWindowIcon(QIcon("icons/descriptor_calculator.png"))
        except:
            pass
        
        self.init_ui()
        self.apply_styles()
    
    def init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel (tabs)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        self.tab_widget = QTabWidget()
        
        # Selection tab
        self.selection_widget = SelectionBuilder(self.molecule)
        self.tab_widget.addTab(self.selection_widget, "Selection")
        
        # Configuration tab
        self.config_widget = DescriptorConfigWidget()
        self.tab_widget.addTab(self.config_widget, "Configuration")
        
        left_layout.addWidget(self.tab_widget)
        
        # Right panel (results and controls)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Calculation controls
        controls_group = QGroupBox("Calculation Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        controls_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Ready")
        controls_layout.addWidget(self.progress_label)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.calculate_btn = QPushButton("Calculate Descriptors")
        self.calculate_btn.clicked.connect(self.calculate_descriptors)
        button_layout.addWidget(self.calculate_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_calculation)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        controls_layout.addLayout(button_layout)
        right_layout.addWidget(controls_group)
        
        # Results table
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Descriptor", "Value", "Unit", "Category"])
        
        # Set column widths
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        results_layout.addWidget(self.results_table)
        right_layout.addWidget(results_group)
        
        # Export controls
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)
        
        export_button_layout = QHBoxLayout()
        
        self.export_values_btn = QPushButton("Export Values (CSV)")
        self.export_values_btn.clicked.connect(self.export_values_csv)
        export_button_layout.addWidget(self.export_values_btn)
        
        self.export_docs_btn = QPushButton("Export Documentation (CSV)")
        self.export_docs_btn.clicked.connect(self.export_documentation_csv)
        export_button_layout.addWidget(self.export_docs_btn)
        
        export_layout.addLayout(export_button_layout)
        right_layout.addWidget(export_group)
        
        # Add panels to main layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])
        
        main_layout.addWidget(splitter)
    
    def apply_styles(self):
        """Apply custom styles."""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
            }}
            
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {COLORS['border']};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                background-color: {COLORS['panel']};
            }}
            
            QTabBar::tab {{
                background-color: {COLORS['button']};
                color: {COLORS['text']};
                padding: 8px 15px;
                margin-right: 2px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {COLORS['accent']};
            }}
            
            QPushButton {{
                background-color: {COLORS['button']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: {COLORS['accent']};
            }}
            
            QPushButton:disabled {{
                background-color: {COLORS['border']};
                color: {COLORS['text_secondary']};
            }}
            
            QTableWidget {{
                background-color: {COLORS['panel']};
                gridline-color: {COLORS['border']};
                selection-background-color: {COLORS['accent']};
            }}
            
            QHeaderView::section {{
                background-color: {COLORS['button']};
                padding: 5px;
                font-weight: bold;
            }}
            
            QProgressBar {{
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                text-align: center;
            }}
            
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
            }}
        """)
    
    def calculate_descriptors(self):
        """Start descriptor calculation."""
        # Get selection and categories
        selection = self.selection_widget.get_selection()
        categories = self.config_widget.get_selected_categories()
        
        if not categories:
            QMessageBox.warning(self, "No Categories", 
                            "Please select at least one descriptor category.")
            return
        
        if not selection.atom_indices:
            QMessageBox.warning(self, "No Selection", 
                            "Please select at least one atom.")
            return
        
        # Start calculation thread
        self.calculate_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting calculation...")
        
        self.calculation_thread = DescriptorCalculationThread(
            self.config_widget.engine, self.molecule, selection, categories
        )
        
        self.calculation_thread.progress_updated.connect(self.update_progress)
        self.calculation_thread.calculation_finished.connect(self.calculation_completed)
        self.calculation_thread.error_occurred.connect(self.calculation_error)
        
        self.calculation_thread.start()
    
    def stop_calculation(self):
        """Stop descriptor calculation."""
        if self.calculation_thread and self.calculation_thread.isRunning():
            self.calculation_thread.terminate()
            self.calculation_thread.wait()
            
            self.calculate_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.progress_bar.setVisible(False)
            self.progress_label.setText("Calculation stopped")
    
    def update_progress(self, progress: CalculationProgress):
        """Update calculation progress."""
        self.progress_bar.setValue(int(progress.percentage))
        self.progress_label.setText(f"Calculating {progress.current_descriptor} "
                              f"({progress.completed}/{progress.total})")
    
    def calculation_completed(self, results: Dict[str, DescriptorResult]):
        """Handle calculation completion."""
        self.current_results = results
        self.populate_results_table(results)
        
        self.calculate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setText(f"Calculation completed: {len(results)} descriptors")
        
        QMessageBox.information(self, "Calculation Complete", 
                           f"Successfully calculated {len(results)} descriptors.")
    
    def calculation_error(self, error_message: str):
        """Handle calculation error."""
        self.calculate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Calculation failed")
        
        QMessageBox.critical(self, "Calculation Error", 
                          f"Error during calculation:\n{error_message}")
    
    def populate_results_table(self, results: Dict[str, DescriptorResult]):
        """Populate results table with descriptor values."""
        self.results_table.setRowCount(len(results))
        
        for row, (name, result) in enumerate(results.items()):
            # Descriptor name
            self.results_table.setItem(row, 0, QTableWidgetItem(name))
            
            # Value
            value_str = str(result.value) if result.value is not None else "N/A"
            self.results_table.setItem(row, 1, QTableWidgetItem(value_str))
            
            # Unit (get from descriptor info)
            unit = ""
            for category_descriptors in self.config_widget.engine.descriptors.values():
                for desc_info in category_descriptors:
                    if desc_info.name == name:
                        unit = desc_info.unit
                        break
                if unit:
                    break
            
            self.results_table.setItem(row, 2, QTableWidgetItem(unit))
            
            # Category (get from descriptor info)
            category = ""
            for cat, category_descriptors in self.config_widget.engine.descriptors.items():
                for desc_info in category_descriptors:
                    if desc_info.name == name:
                        category = cat.value
                        break
                if category:
                    break
            
            self.results_table.setItem(row, 3, QTableWidgetItem(category))
    
    def export_values_csv(self):
        """Export descriptor values to CSV."""
        if not self.current_results:
            QMessageBox.warning(self, "No Results", 
                            "No descriptor results to export.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Descriptor Values", 
            f"descriptors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['Molecule', 'Selection', 'Descriptor', 'Value', 'Unit', 'Category', 'CalculationTime']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for name, result in self.current_results.items():
                        # Get unit and category
                        unit = ""
                        category = ""
                        for cat, category_descriptors in self.config_widget.engine.descriptors.items():
                            for desc_info in category_descriptors:
                                if desc_info.name == name:
                                    unit = desc_info.unit
                                    category = cat.value
                                    break
                            if category:
                                break
                        
                        writer.writerow({
                            'Molecule': result.molecule_id,
                            'Selection': result.selection_id,
                            'Descriptor': name,
                            'Value': result.value,
                            'Unit': unit,
                            'Category': category,
                            'CalculationTime': result.calculation_time
                        })
                
                QMessageBox.information(self, "Export Complete", 
                                   f"Descriptor values exported to:\n{filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", 
                                  f"Error exporting values:\n{str(e)}")
    
    def export_documentation_csv(self):
        """Export descriptor documentation to CSV."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Documentation", 
            f"descriptor_documentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['Name', 'Description', 'Category', 'Formula', 'Unit', 
                               'RangeMin', 'RangeMax']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for category, descriptors in self.config_widget.engine.descriptors.items():
                        for desc_info in descriptors:
                            writer.writerow({
                                'Name': desc_info.name,
                                'Description': desc_info.description,
                                'Category': category.value,
                                'Formula': desc_info.formula,
                                'Unit': desc_info.unit,
                                'RangeMin': desc_info.range_min,
                                'RangeMax': desc_info.range_max
                            })
                
                QMessageBox.information(self, "Export Complete", 
                                   f"Documentation exported to:\n{filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", 
                                  f"Error exporting documentation:\n{str(e)}")

def show_descriptor_calculator(molecule, parent=None):
    """Show descriptor calculator dialog."""
    if QT_FRAMEWORK is None:
        print("Error: No Qt framework available. Cannot show GUI.")
        print("Please install PySide6 or PyQt6:")
        print("  pip install PySide6")
        print("  or")
        print("  pip install PyQt6")
        return None
    
    dialog = DescriptorCalculatorDialog(molecule, parent)
    dialog.show()
    return dialog

# End of Qt availability check
else:
    # Define dummy functions when Qt is not available
    def show_descriptor_calculator(molecule, parent=None):
        """Dummy function when Qt is not available."""
        print("GUI not available: No Qt framework installed")
        print("Install PySide6 or PyQt6 to use the GUI")
        return None
