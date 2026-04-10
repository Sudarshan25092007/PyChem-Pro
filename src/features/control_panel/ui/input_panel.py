"""
Input Panel — SMILES input, conversion controls, and molecule info display.
"""

from src.shared.qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QProgressBar, QTextEdit,
    QComboBox, QCheckBox, QFrame, QSizePolicy, QSpinBox,
    QScrollArea, QSlider, Qt, Signal, QFont
)
from src.shared.ui.theme import COLORS


class InputPanel(QWidget):
    """
    Left panel with SMILES input, controls, and molecule information.
    """

    convert_requested = Signal(str)
    export_sdf_requested = Signal()
    export_mol2_requested = Signal()
    export_image_requested = Signal(int, bool)  # (dpi, white_bg) — white_bg always True now
    sphere_scale_changed = Signal(float)
    stick_scale_changed = Signal(float)
    line_scale_changed = Signal(float)
    show_sidechains_changed = Signal(bool)
    show_sasa_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(320)
        self._init_ui()

    def _init_ui(self):
        # Use a scroll area so the panel works on small screens
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        # ── Title ──
        title = QLabel("SMILES to 3D")
        title.setObjectName("labelTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Molecular Structure Converter")
        subtitle.setObjectName("labelSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(4)

        # ── SMILES Input ──
        input_group = QGroupBox("SMILES Input")
        input_layout = QVBoxLayout(input_group)
        input_layout.setSpacing(8)

        self.smiles_input = QTextEdit()
        self.smiles_input.setPlaceholderText("Enter SMILES notation here...\n\nExamples:\nc1ccccc1  (Benzene)\nCCO  (Ethanol)\nCC(=O)O  (Acetic acid)")
        self.smiles_input.setMinimumHeight(90)
        self.smiles_input.setMaximumHeight(110)
        self.smiles_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_widget']};
                font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
                font-size: 14px;
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
            }}
            QTextEdit:focus {{
                border-color: {COLORS['border_focus']};
            }}
        """)
        input_layout.addWidget(self.smiles_input)

        layout.addWidget(input_group)

        # ── Convert Button ──
        self.convert_btn = QPushButton("Convert to 3D")
        self.convert_btn.setFixedHeight(42)
        self.convert_btn.setObjectName("btnSuccess")
        font = self.convert_btn.font()
        font.setPointSize(13)
        font.setBold(True)
        self.convert_btn.setFont(font)
        self.convert_btn.clicked.connect(self._on_convert)
        layout.addWidget(self.convert_btn)

        # ── Progress ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # ── View Options ──
        view_group = QGroupBox("View Options")
        view_layout = QVBoxLayout(view_group)
        view_layout.setSpacing(6)

        checkbox_style = f"""
            QCheckBox {{
                color: {COLORS['text_primary']};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                border-radius: 4px;
                border: 2px solid {COLORS['border']};
                background-color: {COLORS['bg_widget']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['accent']};
                border-color: {COLORS['accent']};
            }}
        """

        self.show_h_check = QCheckBox("Show Hydrogens")
        self.show_h_check.setChecked(False)  # BKChem-style: hide H by default
        self.show_h_check.setStyleSheet(checkbox_style)
        view_layout.addWidget(self.show_h_check)

        self.show_labels_check = QCheckBox("Show Labels")
        self.show_labels_check.setChecked(False)
        self.show_labels_check.setStyleSheet(checkbox_style)
        view_layout.addWidget(self.show_labels_check)

        self.show_sidechains_check = QCheckBox("Show Side Chains")
        self.show_sidechains_check.setChecked(False)
        self.show_sidechains_check.setStyleSheet(checkbox_style)
        view_layout.addWidget(self.show_sidechains_check)

        self.show_sasa_check = QCheckBox("Show SASA Surface")
        self.show_sasa_check.setChecked(False)
        self.show_sasa_check.setStyleSheet(checkbox_style)
        view_layout.addWidget(self.show_sasa_check)

        self.sasa_selected_only_check = QCheckBox("SASA Selection Only")
        self.sasa_selected_only_check.setChecked(False)
        self.sasa_selected_only_check.setStyleSheet(checkbox_style)
        view_layout.addWidget(self.sasa_selected_only_check)

        render_row = QHBoxLayout()
        render_label = QLabel("Style:")
        render_row.addWidget(render_label)
        self.render_combo = QComboBox()
        self.render_combo.addItems(["Ball & Stick", "Space Fill", "Wireframe", "Cartoon", "Ribbon", "Backbone"])
        render_row.addWidget(self.render_combo, 1)
        view_layout.addLayout(render_row)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet(f"background-color: {COLORS['border']}; max-height: 1px;")
        view_layout.addWidget(sep1)

        # Radius sliders
        slider_style = f"""
            QSlider::groove:horizontal {{
                background: {COLORS['bg_widget']};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {COLORS['accent']};
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {COLORS['accent_hover']};
            }}
            QSlider::sub-page:horizontal {{
                background: {COLORS['accent']};
                border-radius: 3px;
            }}
        """

        # Sphere radius
        self.sphere_slider, self.sphere_label = self._make_slider(
            view_layout, "Sphere:", 10, 300, 100, slider_style,
            lambda v: self._on_scale_changed('sphere', v)
        )

        # Stick radius
        self.stick_slider, self.stick_label = self._make_slider(
            view_layout, "Stick:", 10, 300, 100, slider_style,
            lambda v: self._on_scale_changed('stick', v)
        )

        # Line radius
        self.line_slider, self.line_label = self._make_slider(
            view_layout, "Line:", 10, 300, 100, slider_style,
            lambda v: self._on_scale_changed('line', v)
        )

        layout.addWidget(view_group)

        # ── Export ──
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)
        export_layout.setSpacing(8)

        # Structure files row
        struct_row = QHBoxLayout()
        self.sdf_btn = QPushButton("Save SDF")
        self.sdf_btn.setObjectName("btnSecondary")
        self.sdf_btn.clicked.connect(self.export_sdf_requested.emit)
        self.sdf_btn.setEnabled(False)
        struct_row.addWidget(self.sdf_btn)

        self.mol2_btn = QPushButton("Save MOL2")
        self.mol2_btn.setObjectName("btnSecondary")
        self.mol2_btn.clicked.connect(self.export_mol2_requested.emit)
        self.mol2_btn.setEnabled(False)
        struct_row.addWidget(self.mol2_btn)
        export_layout.addLayout(struct_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']}; max-height: 1px;")
        export_layout.addWidget(sep)

        # Image export DPI row
        dpi_row = QHBoxLayout()
        dpi_row.setSpacing(8)
        dpi_label = QLabel("Image DPI:")
        dpi_row.addWidget(dpi_label)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(300)
        self.dpi_spin.setSingleStep(50)
        self.dpi_spin.setFixedWidth(100)
        self.dpi_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {COLORS['bg_widget']};
                border: 2px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px 8px;
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            QSpinBox:focus {{ border-color: {COLORS['border_focus']}; }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 18px;
                border: none;
                background: {COLORS['bg_hover']};
            }}
            QSpinBox::up-button {{ border-top-right-radius: 4px; }}
            QSpinBox::down-button {{ border-bottom-right-radius: 4px; }}
        """)
        dpi_row.addWidget(self.dpi_spin)
        dpi_row.addStretch()
        export_layout.addLayout(dpi_row)

        # White background checkbox removed — exports always use white bg
        # for publication quality (standard in ChemDraw, PyMOL, etc.)

        self.export_img_btn = QPushButton("Export Image")
        self.export_img_btn.setObjectName("btnSecondary")
        self.export_img_btn.clicked.connect(self._on_export_image)
        self.export_img_btn.setEnabled(False)
        export_layout.addWidget(self.export_img_btn)

        layout.addWidget(export_group)

        # ── Molecule Info ──
        info_group = QGroupBox("Molecule Info")
        info_layout = QVBoxLayout(info_group)

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMinimumHeight(100)
        self.info_text.setMaximumHeight(140)
        self.info_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_widget']};
                font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
                font-size: 12px;
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
                padding: 6px;
            }}
        """)
        self.info_text.setPlaceholderText("Molecule info appears here...")
        info_layout.addWidget(self.info_text)

        layout.addWidget(info_group)

        layout.addStretch()

        # ── Footer ──
        footer = QLabel("PyChem molecular viewer v1.0")
        footer.setObjectName("labelMuted")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

    def _on_convert(self):
        smiles = self.smiles_input.toPlainText().strip()
        # Take first line if multi-line
        if '\n' in smiles:
            smiles = smiles.split('\n')[0].strip()
        if smiles:
            self.convert_requested.emit(smiles)

    def set_progress(self, value):
        if value <= 0:
            self.progress_bar.setVisible(False)
        else:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(value)

    def update_molecule_info(self, molecule):
        if not molecule:
            self.info_text.clear()
            return

        info_lines = [
            f"Formula: {molecule.molecular_formula()}",
            f"Weight:  {molecule.molecular_weight():.2f} Da",
            f"Atoms:   {len(molecule.atoms)}",
            f"Bonds:   {len(molecule.bonds)}",
            f"Charge:  {molecule.total_charge()}",
            f"Rings:   {len(molecule.find_rings())}",
        ]

        charges = [a.partial_charge for a in molecule.atoms if a.partial_charge != 0]
        if charges:
            info_lines.append(f"Q range: {min(charges):.3f} to {max(charges):.3f}")

        self.info_text.setPlainText("\n".join(info_lines))

    def enable_tools(self, enabled=True):
        self.sdf_btn.setEnabled(enabled)
        self.mol2_btn.setEnabled(enabled)
        self.export_img_btn.setEnabled(enabled)

    def _on_export_image(self):
        dpi = self.dpi_spin.value()
        self.export_image_requested.emit(dpi, True)  # Always white background

    def _make_slider(self, parent_layout, label_text, min_val, max_val, default, style, callback):
        """Create a labeled slider row. Returns (slider, value_label)."""
        row = QHBoxLayout()
        row.setSpacing(6)

        label = QLabel(label_text)
        label.setFixedWidth(52)
        label.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        row.addWidget(label)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default)
        slider.setStyleSheet(style)
        row.addWidget(slider, 1)

        val_label = QLabel(f"{default}%")
        val_label.setFixedWidth(36)
        val_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        val_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text_muted']};")
        row.addWidget(val_label)

        slider.valueChanged.connect(lambda v: val_label.setText(f"{v}%"))
        slider.valueChanged.connect(callback)

        parent_layout.addLayout(row)
        return slider, val_label

    def _on_scale_changed(self, which, value):
        """Emit scale changed signal."""
        scale = value / 100.0
        if which == 'sphere':
            self.sphere_scale_changed.emit(scale)
        elif which == 'stick':
            self.stick_scale_changed.emit(scale)
        elif which == 'line':
            self.line_scale_changed.emit(scale)
