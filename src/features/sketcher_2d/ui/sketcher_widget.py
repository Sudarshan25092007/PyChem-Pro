# -*- coding: utf-8 -*-
from src.shared.qt_compat import *
from ..paper import Paper
from ..tools import StructureTool, EraserTool, toolsettings
from ..app_data import App, Settings

class SketcherWidget(QWidget):
    molecule_imported = Signal(str) # SMILES string

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        App.paper = self.paper # Shared App object
    def _init_ui(self):
        # Main layout: Horizontal (Toolbar on left, Canvas on right)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Toolbar (Vertical)
        self.toolbar = QToolBar()
        self.toolbar.setOrientation(Qt.Orientation.Vertical)
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setMovable(False)
        self.toolbar.setStyleSheet("""
            QToolBar {
                background-color: transparent;
                border-right: 1px solid palette(mid);
                padding: 5px;
            }
            QToolButton {
                margin: 2px;
                padding: 5px;
                border-radius: 4px;
            }
            QToolButton:checked {
                background-color: palette(highlight);
                color: palette(highlighted-text);
            }
        """)
        main_layout.addWidget(self.toolbar)

        # Tool group for exclusive selection
        self.tool_group = QActionGroup(self)

        # Basic Tools
        self.action_bond = QAction("Bond", self)
        self.action_bond.setToolTip("Draw Bonds")
        self.action_bond.setCheckable(True)
        self.tool_group.addAction(self.action_bond)
        self.toolbar.addAction(self.action_bond)

        self.action_eraser = QAction("Eraser", self)
        self.action_eraser.setToolTip("Remove Atoms or Bonds")
        self.action_eraser.setCheckable(True)
        self.tool_group.addAction(self.action_eraser)
        self.toolbar.addAction(self.action_eraser)

        self.action_text = QAction("Text", self)
        self.action_text.setToolTip("Add Text")
        self.action_text.setCheckable(True)
        self.tool_group.addAction(self.action_text)
        self.toolbar.addAction(self.action_text)

        self.action_select = QAction("Select", self)
        self.action_select.setToolTip("Select & Move")
        self.action_select.setCheckable(True)
        self.action_select.setChecked(True)
        self.tool_group.addAction(self.action_select)
        self.toolbar.addAction(self.action_select)

        self.action_rotate = QAction("Rotate", self)
        self.action_rotate.setToolTip("Rotate Molecule")
        self.action_rotate.setCheckable(True)
        self.tool_group.addAction(self.action_rotate)
        self.toolbar.addAction(self.action_rotate)

        self.toolbar.addSeparator()

        # Bond Types
        self.bond_combo = QComboBox()
        self.bond_combo.addItems(["single", "double", "triple", "wedge", "hashed_wedge"])
        self.bond_combo.currentTextChanged.connect(self._on_bond_type_changed)
        self.toolbar.addWidget(self.bond_combo)

        self.toolbar.addSeparator()

        # Rings
        self.toolbar.addWidget(QLabel("Rings"))
        self.action_benzene = QAction("Benzene", self)
        self.action_benzene.setCheckable(True)
        self.tool_group.addAction(self.action_benzene)
        self.toolbar.addAction(self.action_benzene)

        self.action_cyclohexane = QAction("Hexane", self)
        self.action_cyclohexane.setCheckable(True)
        self.tool_group.addAction(self.action_cyclohexane)
        self.toolbar.addAction(self.action_cyclohexane)

        self.action_cyclopentane = QAction("Pentane", self)
        self.action_cyclopentane.setCheckable(True)
        self.tool_group.addAction(self.action_cyclopentane)
        self.toolbar.addAction(self.action_cyclopentane)


        self.toolbar.addSeparator()
        self.toolbar.addWidget(QLabel("Arrows"))
        self.action_arrow = QAction("Reaction", self)
        self.action_arrow.setCheckable(True)
        self.tool_group.addAction(self.action_arrow)
        self.toolbar.addAction(self.action_arrow)

        self.action_equilibrium = QAction("Equil.", self)
        self.action_equilibrium.setCheckable(True)
        self.tool_group.addAction(self.action_equilibrium)
        self.toolbar.addAction(self.action_equilibrium)

        self.action_reversible = QAction("Revers.", self)
        self.action_reversible.setCheckable(True)
        self.tool_group.addAction(self.action_reversible)
        self.toolbar.addAction(self.action_reversible)

        self.action_curly = QAction("Curly CCW", self)
        self.action_curly.setCheckable(True)
        self.tool_group.addAction(self.action_curly)
        self.toolbar.addAction(self.action_curly)

        self.action_curly_cw = QAction("Curly CW", self)
        self.action_curly_cw.setCheckable(True)
        self.tool_group.addAction(self.action_curly_cw)
        self.toolbar.addAction(self.action_curly_cw)

        self.action_fish_up = QAction("Fish Up", self)
        self.action_fish_up.setCheckable(True)
        self.tool_group.addAction(self.action_fish_up)
        self.toolbar.addAction(self.action_fish_up)

        self.action_fish_down = QAction("Fish Down", self)
        self.action_fish_down.setCheckable(True)
        self.tool_group.addAction(self.action_fish_down)
        self.toolbar.addAction(self.action_fish_down)

        self.toolbar.addSeparator()


        # Right side: Canvas and Right Toolbar
        self.view = QGraphicsView()
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.view.setBackgroundBrush(QBrush(QColor(255, 255, 255)))
        self.view.setStyleSheet("QGraphicsView { border: 1px solid palette(mid); border-radius: 4px; }")
        main_layout.addWidget(self.view, 1)

        # Right Toolbar (Vertical)
        self.right_toolbar = QToolBar()
        self.right_toolbar.setOrientation(Qt.Orientation.Vertical)
        self.right_toolbar.setIconSize(QSize(24, 24))
        self.right_toolbar.setMovable(False)
        self.right_toolbar.setStyleSheet(self.toolbar.styleSheet())
        main_layout.addWidget(self.right_toolbar)

        # Zoom Controls (Right Toolbar)
        self.action_zoom_in = QAction("Zoom In", self)
        self.action_zoom_in.triggered.connect(lambda: self._zoom(1.2))
        self.right_toolbar.addAction(self.action_zoom_in)

        self.action_zoom_out = QAction("Zoom Out", self)
        self.action_zoom_out.triggered.connect(lambda: self._zoom(0.8))
        self.right_toolbar.addAction(self.action_zoom_out)

        self.action_zoom_reset = QAction("Reset", self)
        self.action_zoom_reset.triggered.connect(self._zoom_reset)
        self.right_toolbar.addAction(self.action_zoom_reset)

        self.right_toolbar.addSeparator()

        # Undo/Redo/Clear (Right Toolbar)
        self.action_undo = QAction("Undo", self)
        self.action_undo.setShortcut(QKeySequence.Undo)
        self.action_undo.triggered.connect(self._on_undo)
        self.right_toolbar.addAction(self.action_undo)

        self.action_redo = QAction("Redo", self)
        self.action_redo.setShortcut(QKeySequence.Redo)
        self.action_redo.triggered.connect(self._on_redo)
        self.right_toolbar.addAction(self.action_redo)

        self.right_toolbar.addSeparator()

        # Copy/Paste (Right Toolbar)
        self.action_copy = QAction("Copy", self)
        self.action_copy.setShortcut(QKeySequence.Copy)
        self.action_copy.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.action_copy.triggered.connect(self._on_copy)
        self.right_toolbar.addAction(self.action_copy)
        self.addAction(self.action_copy)

        self.action_paste = QAction("Paste", self)
        self.action_paste.setShortcut(QKeySequence.Paste)
        self.action_paste.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.action_paste.triggered.connect(self._on_paste)
        self.right_toolbar.addAction(self.action_paste)
        self.addAction(self.action_paste)

        self.right_toolbar.addSeparator()
        
        self.action_smiles = QAction("SMILES", self)
        self.action_smiles.setToolTip("SMILES to 2D")
        self.action_smiles.triggered.connect(self._on_smiles_to_2d)
        self.right_toolbar.addAction(self.action_smiles)

        self.right_toolbar.addSeparator()

        self.action_clear = QAction("Clear", self)
        self.action_clear.triggered.connect(self._on_clear)
        self.right_toolbar.addAction(self.action_clear)

        # Spacer for Right Toolbar
        right_spacer = QWidget()
        right_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.right_toolbar.addWidget(right_spacer)
        
        self.action_import = QAction("Import", self)
        self.action_import.setToolTip("Import to 3D View (Ctrl+I)")
        self.action_import.setShortcut(QKeySequence("Ctrl+I"))
        self.action_import.triggered.connect(self._on_import)
        self.right_toolbar.addAction(self.action_import)
        
        # Style the button specifically to make it visible
        import_btn = self.right_toolbar.widgetForAction(self.action_import)
        if import_btn:
            import_btn.setStyleSheet("font-weight: bold; color: palette(highlight);")

        self.paper = Paper(self.view)
        self.view.setScene(self.paper)
        self.paper.setSize(2000, 2000)
        self.view.centerOn(0, 0)
        
        from ..tools import TemplateTool, ArrowTool, SelectTool, TextTool, RotateTool
        self.tools = {
            "bond": StructureTool(),
            "eraser": EraserTool(),
            "text": TextTool(),
            "select": SelectTool(),
            "rotate": RotateTool(),
            "benzene": TemplateTool("benzene"),
            "cyclohexane": TemplateTool("cyclohexane"),
            "cyclopentane": TemplateTool("cyclopentane"),
            "pyridine": TemplateTool("pyridine"),
            "furan": TemplateTool("furan"),
            "pyrrole": TemplateTool("pyrrole"),
            "arrow": ArrowTool("reaction", curvature=0.0),
            "equilibrium": ArrowTool("equilibrium", curvature=0.0),
            "reversible": ArrowTool("reversible", curvature=0.0),
            "curly": ArrowTool("curly", curvature=1.0),
            "curly_cw": ArrowTool("curly", curvature=-1.0),
            "fish_up": ArrowTool("fish_up", curvature=1.0),
            "fish_down": ArrowTool("fish_down", curvature=-1.0)
        }
        self.current_tool = self.tools["select"]
        App.tool = self.current_tool

        self.tool_group.triggered.connect(self._on_tool_changed)
        self.paper.text_editing_finished.connect(self._on_text_editing_finished)

    def _on_text_editing_finished(self):
        # ChemDraw style: after text is finished, switch back to select tool
        from ..tools import TextTool
        if isinstance(self.current_tool, TextTool):
            self.action_select.setChecked(True)
            self._on_tool_changed(self.action_select)

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        factor = 1.1 if angle > 0 else 0.9
        self._zoom(factor)
        super().wheelEvent(event)

    def keyPressEvent(self, event):
        if App.tool and hasattr(App.tool, 'on_key_press'):
            if App.tool.on_key_press(event.key(), event.text()):
                return

        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            from ..tools import SelectTool
            if isinstance(self.current_tool, SelectTool):
                for obj in self.current_tool.objs[:]:  # Copy list to avoid modification during iteration
                    if hasattr(obj, 'delete_from_paper'):
                        obj.delete_from_paper()
                    elif hasattr(obj, 'atoms'):
                        # It's a molecule
                        self.paper.removeObject(obj)
                    elif hasattr(obj, 'molecule'):
                        # It's an atom or bond
                        obj.delete_from_paper()
                    else:
                        # TextLabel or other drawable object
                        self.paper.removeObject(obj)
                self.current_tool.objs = []
                for o in self.paper.objects:
                    if hasattr(o, 'set_selected'):
                        o.set_selected(False)
                self.paper.save_state_to_undo_stack()
        super().keyPressEvent(event)

    def _zoom(self, factor):
        self.view.scale(factor, factor)

    def _zoom_reset(self):
        self.view.resetTransform()

    def showEvent(self, event):
        App.paper = self.paper
        App.tool = self.current_tool
        super().showEvent(event)

    def _on_tool_changed(self, action):
        if action == self.action_bond:
            self.current_tool = self.tools["bond"]
        elif action == self.action_eraser:
            self.current_tool = self.tools["eraser"]
        elif action == self.action_text:
            self.current_tool = self.tools["text"]
        elif action == self.action_select:
            self.current_tool = self.tools["select"]
        elif action == self.action_rotate:
            self.current_tool = self.tools["rotate"]
        elif action == self.action_benzene:
            self.current_tool = self.tools["benzene"]
        elif action == self.action_cyclohexane:
            self.current_tool = self.tools["cyclohexane"]
        elif action == self.action_cyclopentane:
            self.current_tool = self.tools["cyclopentane"]
        elif action == self.action_arrow:
            self.current_tool = self.tools["arrow"]
        elif action == self.action_equilibrium:
            self.current_tool = self.tools["equilibrium"]
        elif action == self.action_reversible:
            self.current_tool = self.tools["reversible"]
        elif action == self.action_curly:
            self.current_tool = self.tools["curly"]
        elif action == self.action_curly_cw:
            self.current_tool = self.tools["curly_cw"]
        elif action == self.action_fish_up:
            self.current_tool = self.tools["fish_up"]
        elif action == self.action_fish_down:
            self.current_tool = self.tools["fish_down"]
        App.tool = self.current_tool

    def _on_bond_type_changed(self, text):
        toolsettings['bond_type'] = text

    def _on_element_changed(self, text):
        toolsettings['structure'] = text

    def _on_clear(self):
        self.paper.clear()
        self.paper.save_state_to_undo_stack()

    def _on_import(self):
        from ..fileformat_smiles import Smiles
        mols = [obj for obj in self.paper.objects if obj.class_name == "Molecule"]
        if not mols: return
        gen = Smiles()
        try:
            smiles = gen.generate(mols[-1])
            if smiles:
                self.molecule_imported.emit(smiles)
        except Exception as e:
            print(f"Error generating SMILES: {e}")
            # Try to import anyway with a fallback
            try:
                # Try without marking aromatic bonds
                smiles = gen._oasa.get_smiles(mols[-1])
                if smiles:
                    self.molecule_imported.emit(smiles)
            except:
                print("Could not generate SMILES for this molecule structure")

    def _on_undo(self):
        self.paper.undo()

    def _on_redo(self):
        self.paper.redo()

    def _on_copy(self):
        from ..tools import SelectTool
        if isinstance(self.current_tool, SelectTool):
            App.clipboard = []
            for obj in self.current_tool.objs:
                if hasattr(obj, 'clone'):
                    App.clipboard.append(obj.clone())
            print(f"Copied {len(App.clipboard)} objects to clipboard")

    def _on_paste(self):
        if not App.clipboard:
            return
        
        new_objs = []
        offset = 20
        for obj in App.clipboard:
            new_obj = obj.clone()
            if hasattr(new_obj, 'move_by'):
                new_obj.move_by(offset, offset)
            elif hasattr(new_obj, 'atoms'):
                # Molecule
                for a in new_obj.atoms:
                    a.move_by(offset, offset)
            
            self.paper.addObject(new_obj)
            new_obj.draw()
            new_objs.append(new_obj)
        
        # Select the newly pasted objects
        from ..tools import SelectTool
        if isinstance(self.current_tool, SelectTool):
            self.current_tool.objs = new_objs
            for o in self.paper.objects:
                if hasattr(o, 'set_selected'):
                    o.set_selected(o in new_objs)
        
        self.paper.save_state_to_undo_stack("Paste")
        
        # Shift clipboard for consecutive pastes
        for obj in App.clipboard:
            if hasattr(obj, 'move_by'):
                obj.move_by(offset, offset)
            elif hasattr(obj, 'atoms'):
                for a in obj.atoms:
                    a.move_by(offset, offset)

    def _on_smiles_to_2d(self):
        text, ok = QInputDialog.getText(self, "SMILES to 2D", "Enter SMILES string:")
        if not ok or not text.strip():
            return
            
        try:
            from src.features.smiles_parser.services.parser import parse_smiles
            from src.features.smiles_parser.rules.aromaticity import kekulize
            from src.features.layout_2d.generators.coordgen2d_smiles_pure_oasa import CoordinateGenerator2DSMILES
            from ..molecule import Molecule
            from ..atom import Atom
            from ..bond import Bond
            from src.core.domain.models.bond import BondType
            
            mol_domain = parse_smiles(text.strip())
            # Force kekulization to show double bonds in rings
            kekulize(mol_domain)
            
            gen = CoordinateGenerator2DSMILES(mol_domain)
            coords = gen.generate()
            
            # Place at center of view
            view_rect = self.view.mapToScene(self.view.viewport().rect()).boundingRect()
            cx, cy = view_rect.center().x(), view_rect.center().y()
            
            new_mol = Molecule()
            self.paper.addObject(new_mol)
            
            atom_map = {}
            scale = 40 # Increased scale for better visibility
            
            for atom in mol_domain.atoms:
                new_atom = Atom(atom.symbol)
                new_atom.charge = atom.formal_charge
                if atom.index in coords:
                    new_atom.x = cx + coords[atom.index][0] * scale
                    new_atom.y = cy + coords[atom.index][1] * scale
                else:
                    new_atom.x, new_atom.y = cx, cy
                new_mol.add_atom(new_atom)
                atom_map[atom.index] = new_atom
            
            for bond in mol_domain.bonds:
                new_bond = Bond()
                btype = "single"
                if bond.bond_type == BondType.DOUBLE: btype = "double"
                elif bond.bond_type == BondType.TRIPLE: btype = "triple"
                elif bond.bond_type == BondType.AROMATIC: 
                    # For aromatic, we let oasa or simple alternating logic handle it later, 
                    # but for now just use alternating pattern or single.
                    # Actually OASA kekulizes aromatic bonds during text_to_mol.
                    # Since we use parse_smiles, we should check if it's already kekulized.
                    btype = "single" 
                
                new_bond.set_type(btype)
                new_bond.connect_atoms(atom_map[bond.begin_atom_idx], atom_map[bond.end_atom_idx])
                new_mol.add_bond(new_bond)
            
            # Handle aromatic bonds specifically if any
            # For simplicity, if we have aromatic bonds, we can try to kekulize them
            # but sketcher Bond class prefers "single"/"double".
            
            new_mol.draw()
            self.paper.save_state_to_undo_stack("Import SMILES")
            self.view.centerOn(cx, cy)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Could not convert SMILES: {str(e)}")
