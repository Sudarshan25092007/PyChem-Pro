"""
PySide6-native color dialog to avoid threading issues.

Uses PySide6 components instead of tkinter for better integration.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTabWidget, QWidget, QFrame,
    QButtonGroup, QRadioButton, QMessageBox, QColorDialog
)
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt, Signal
from typing import Dict, Optional


class PySide6ColorDialog(QDialog):
    """
    PySide6-native color selection dialog.
    """
    
    color_selected = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_colors = {}
        self.color_buttons = {}
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Color Selection")
        self.setMinimumSize(800, 700)  # Allow resizing
        self.resize(900, 800)  # Much larger default size
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Select colors for atoms, spheres, and bonds")
        title.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            margin: 10px;
            color: #000;
            background-color: #f0f0f0;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
        """)
        layout.addWidget(title)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                background-color: #fff;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #ccc;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #fff;
                border-bottom: 1px solid #fff;
            }
        """)
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_atoms_tab()
        self.create_spheres_tab()
        self.create_bonds_tab()
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #ccc;")
        layout.addWidget(separator)
        
        # Status label
        self.status_label = QLabel("Select colors and click 'Apply Changes'")
        self.status_label.setStyleSheet("""
            color: #333; 
            font-size: 11px; 
            margin: 5px;
            background-color: #f9f9f9;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 3px;
        """)
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)
        
        self.apply_btn = QPushButton("Apply Changes")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.apply_btn.clicked.connect(self.apply_colors)
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.reset_btn = QPushButton("Reset All")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #E65100;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_colors)
        button_layout.addWidget(self.reset_btn)
    
    def create_atoms_tab(self):
        """Create atoms color tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Title
        title = QLabel("Atom Colors")
        title.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            margin: 8px;
            color: #000;
            background-color: #f0f0f0;
            padding: 10px;
            border: 2px solid #333;
            border-radius: 5px;
        """)
        layout.addWidget(title)
        
        # Atom color buttons
        atoms = ["C", "H", "O", "N", "S", "P", "F", "Cl", "Br", "I"]
        
        for atom in atoms:
            atom_layout = QHBoxLayout()
            layout.addLayout(atom_layout)
            
            # Atom label
            atom_label = QLabel(atom)
            atom_label.setMinimumWidth(80)
            atom_label.setStyleSheet("background-color: white; color: black; font-size: 20px; font-weight: bold; padding: 10px; border: 2px solid black;")
            atom_layout.addWidget(atom_label)
            
            # Color preview
            color_preview = QLabel()
            color_preview.setStyleSheet("""
                QLabel {
                    border: 2px solid #333;
                    background-color: white;
                    width: 60px;
                    height: 30px;
                    border-radius: 4px;
                }
            """)
            atom_layout.addWidget(color_preview)
            
            # Color button
            color_btn = QPushButton("Choose Color")
            color_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 5px;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
            color_btn.clicked.connect(lambda checked, a=atom, preview=color_preview: self.choose_atom_color(a, preview))
            atom_layout.addWidget(color_btn)
            
            # Store references
            self.color_buttons[f'atom_{atom.lower()}'] = color_preview
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Atoms")
    
    def create_spheres_tab(self):
        """Create spheres color tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Title
        title = QLabel("Sphere Colors")
        title.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            margin: 8px;
            color: #000;
            background-color: #f0f0f0;
            padding: 10px;
            border: 2px solid #333;
            border-radius: 5px;
        """)
        layout.addWidget(title)
        
        # Sphere color buttons
        spheres = ["default", "com", "centroid", "custom"]
        
        for sphere in spheres:
            sphere_layout = QHBoxLayout()
            layout.addLayout(sphere_layout)
            
            # Sphere label
            sphere_label = QLabel(f"{sphere.capitalize()}:")
            sphere_label.setStyleSheet("""
                font-weight: bold; 
                width: 80px;
                color: #000;
                font-size: 12px;
                background-color: #fff;
                padding: 5px;
                border: 1px solid #333;
                border-radius: 3px;
            """)
            sphere_layout.addWidget(sphere_label)
            
            # Color preview
            color_preview = QLabel()
            color_preview.setStyleSheet("""
                QLabel {
                    border: 2px solid #333;
                    background-color: white;
                    width: 60px;
                    height: 30px;
                    border-radius: 4px;
                }
            """)
            sphere_layout.addWidget(color_preview)
            
            # Color button
            color_btn = QPushButton("Choose Color")
            color_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 5px;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
            color_btn.clicked.connect(lambda checked, s=sphere, preview=color_preview: self.choose_sphere_color(s, preview))
            sphere_layout.addWidget(color_btn)
            
            # Store references
            self.color_buttons[f'sphere_{sphere}'] = color_preview
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Spheres")
    
    def create_bonds_tab(self):
        """Create bonds/sticks color tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Title
        title = QLabel("Bond/Stick Colors")
        title.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            margin: 8px;
            color: #000;
            background-color: #f0f0f0;
            padding: 10px;
            border: 2px solid #333;
            border-radius: 5px;
        """)
        layout.addWidget(title)
        
        # Bond color buttons
        bonds = ["default", "single", "double", "triple", "selected", "highlight"]
        
        for bond in bonds:
            bond_layout = QHBoxLayout()
            layout.addLayout(bond_layout)
            
            # Bond label
            bond_label = QLabel(f"{bond.capitalize()}:")
            bond_label.setStyleSheet("""
                font-weight: bold; 
                width: 80px;
                color: #000;
                font-size: 12px;
                background-color: #fff;
                padding: 5px;
                border: 1px solid #333;
                border-radius: 3px;
            """)
            bond_layout.addWidget(bond_label)
            
            # Color preview
            color_preview = QLabel()
            color_preview.setStyleSheet("""
                QLabel {
                    border: 2px solid #333;
                    background-color: white;
                    width: 60px;
                    height: 30px;
                    border-radius: 4px;
                }
            """)
            bond_layout.addWidget(color_preview)
            
            # Color button
            color_btn = QPushButton("Choose Color")
            color_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 5px;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
            color_btn.clicked.connect(lambda checked, b=bond, preview=color_preview: self.choose_bond_color(b, preview))
            bond_layout.addWidget(color_btn)
            
            # Store references
            self.color_buttons[f'stick_{bond}'] = color_preview
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Sticks")
    
    def choose_atom_color(self, atom: str, preview: QLabel):
        """Choose color for atom."""
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            preview.setStyleSheet(f"""
                QLabel {{
                    border: 1px solid #ccc;
                    background-color: {hex_color};
                    width: 50px;
                    height: 20px;
                }}
            """)
            self.selected_colors[f'atom_{atom.lower()}'] = hex_color
    
    def choose_sphere_color(self, sphere: str, preview: QLabel):
        """Choose color for sphere."""
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            preview.setStyleSheet(f"""
                QLabel {{
                    border: 1px solid #ccc;
                    background-color: {hex_color};
                    width: 50px;
                    height: 20px;
                }}
            """)
            self.selected_colors[f'sphere_{sphere}'] = hex_color
    
    def choose_bond_color(self, bond: str, preview: QLabel):
        """Choose color for bond."""
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            preview.setStyleSheet(f"""
                QLabel {{
                    border: 1px solid #ccc;
                    background-color: {hex_color};
                    width: 50px;
                    height: 20px;
                }}
            """)
            self.selected_colors[f'stick_{bond}'] = hex_color
    
    def apply_colors(self):
        """Apply selected colors."""
        if self.selected_colors:
            self.status_label.setText(f"Applying {len(self.selected_colors)} colors...")
            self.color_selected.emit(self.selected_colors)
            self.accept()
        else:
            self.status_label.setText("No colors selected! Please choose colors first.")
    
    def reset_colors(self):
        """Reset all colors."""
        self.selected_colors = {}
        
        # Reset all color previews to white
        for key, preview in self.color_buttons.items():
            preview.setStyleSheet("""
                QLabel {
                    border: 1px solid #ccc;
                    background-color: white;
                    width: 50px;
                    height: 20px;
                }
            """)
        
        self.status_label.setText("All colors reset to default")


def show_pyside6_color_dialog(parent=None) -> Dict[str, str]:
    """Show PySide6 color dialog and return selected colors."""
    dialog = PySide6ColorDialog(parent)
    result = dialog.exec_()
    
    if result == QDialog.Accepted:
        return dialog.selected_colors
    else:
        return {}


def apply_pyside6_colors(colors: Dict[str, str]):
    """Apply PySide6 selected colors to theme."""
    try:
        from src.shared.ui.theme import COLORS
        print(f"DEBUG: Applying PySide6 colors to theme: {colors}")
        COLORS.update(colors)
        print(f"DEBUG: Successfully applied {len(colors)} PySide6 colors to theme")
    except Exception as e:
        print(f"ERROR applying PySide6 colors to theme: {e}")
        import traceback
        traceback.print_exc()
