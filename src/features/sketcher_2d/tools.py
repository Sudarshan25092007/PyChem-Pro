# -*- coding: utf-8 -*-
# Adapted from ChemCanvas (GPLv3)
from .app_data import App, Settings
from .drawing_parents import Color, Align, PenStyle
from .tool_helpers import draw_objs_recursively
from .molecule import Molecule
from .atom import Atom
from .bond import Bond
from .arrow import Arrow
from .text_label import TextLabel
from . import geometry as geo

toolsettings = {
    'structure': 'C',
    'bond_type': 'single',
    'mode': 'bond', # bond or atom
}

class Tool:
    def __init__(self): pass
    def on_mouse_press(self, x, y): pass
    def on_mouse_release(self, x, y): pass
    def on_mouse_move(self, x, y): pass
    def on_mouse_double_click(self, x, y): pass
    def on_key_press(self, key, text): pass
    def on_right_click(self, x, y): pass
    def clear(self): pass
    def show_status(self, msg): pass

class StructureTool(Tool):
    def __init__(self):
        Tool.__init__(self)
        self.reset()
        self.preview_item = None
        self.atom_with_preview_bond = None

    def reset(self):
        self.atom1 = None
        self.mouse_press_pos = None

    def on_mouse_press(self, x, y):
        self.mouse_press_pos = (x, y)
        self.atom1 = None
        focused_obj = App.paper.focused_obj
        if isinstance(focused_obj, Atom):
            self.atom1 = focused_obj

    def on_mouse_move(self, x, y):
        if not App.paper.dragging:
            focused_obj = App.paper.focused_obj
            if isinstance(focused_obj, Atom):
                if focused_obj is not self.atom_with_preview_bond:
                    self.clear_preview()
                    self.show_preview(focused_obj)
            else:
                self.clear_preview()
            return
        # Dragging to draw bond
        if not self.atom1:
            mol = Molecule()
            App.paper.addObject(mol)
            self.atom1 = mol.new_atom(toolsettings['structure'])
            self.atom1.set_pos(*self.mouse_press_pos)
            self.atom1.draw()
        
        if self.preview_item:
            App.paper.removeItem(self.preview_item)
        self.preview_item = App.paper.addLine(self.atom1.pos + (x, y), style=PenStyle.dashed)

    def on_mouse_release(self, x, y):
        if not App.paper.dragging:
            self.on_mouse_click(x, y)
            return
        
        self.clear_preview()
        if self.atom1:
            atom2 = self.atom1.molecule.new_atom(toolsettings['structure'])
            atom2.set_pos(x, y)
            bond = self.atom1.molecule.new_bond()
            bond.set_type(toolsettings['bond_type'])
            bond.connect_atoms(self.atom1, atom2)
            
            # Check for overlap
            focused_obj = App.paper.focused_obj
            if isinstance(focused_obj, Atom) and focused_obj is not self.atom1:
                focused_obj.eat_atom(atom2)
                atom2 = focused_obj
            
            self.atom1.draw()
            atom2.draw()
            bond.draw()
            App.paper.save_state_to_undo_stack()
        self.reset()

    def on_mouse_click(self, x, y):
        focused_obj = App.paper.focused_obj
        if not focused_obj:
            mol = Molecule()
            App.paper.addObject(mol)
            atom = mol.new_atom(toolsettings['structure'])
            atom.set_pos(x, y)
            atom.draw()
        elif isinstance(focused_obj, Atom):
            # Change symbol or add branch
            if focused_obj.symbol != toolsettings['structure']:
                focused_obj.set_symbol(toolsettings['structure'])
                focused_obj.draw()
            else:
                # Add branch
                bond_length = Settings.bond_length * focused_obj.molecule.scale_val
                nx, ny = focused_obj.molecule.find_place(focused_obj, bond_length)
                atom2 = focused_obj.molecule.new_atom(toolsettings['structure'])
                atom2.set_pos(nx, ny)
                bond = focused_obj.molecule.new_bond()
                bond.set_type(toolsettings['bond_type'])
                bond.connect_atoms(focused_obj, atom2)
                focused_obj.draw()
                atom2.draw()
                bond.draw()
        elif isinstance(focused_obj, Bond):
            # Cycle bond type
            types = ['single', 'double', 'triple']
            if focused_obj.type in types:
                idx = (types.index(focused_obj.type) + 1) % len(types)
                focused_obj.set_type(types[idx])
                focused_obj.draw()
                for a in focused_obj.atoms: a.draw()
        
        App.paper.save_state_to_undo_stack()
        self.reset()

    def show_preview(self, atom):
        bond_length = Settings.bond_length * atom.molecule.scale_val
        nx, ny = atom.molecule.find_place(atom, bond_length)
        self.preview_item = App.paper.addLine(atom.pos + (nx, ny), style=PenStyle.dashed)
        self.atom_with_preview_bond = atom

    def on_key_press(self, key, text):
        focused = App.paper.focused_obj
        if isinstance(focused, Atom):
            mapping = {
                'c': 'C', 'n': 'N', 'o': 'O', 's': 'S', 'p': 'P', 
                'f': 'F', 'l': 'Cl', 'b': 'Br', 'i': 'I', 'h': 'H'
            }
            symbol = mapping.get(text.lower())
            if symbol:
                focused.set_symbol(symbol)
                focused.draw()
                App.paper.save_state_to_undo_stack()
                return True
        return False

    def clear_preview(self):
        if self.preview_item:
            App.paper.removeItem(self.preview_item)
            self.preview_item = None
            self.atom_with_preview_bond = None

class EraserTool(Tool):
    def on_mouse_press(self, x, y):
        focused = App.paper.focused_obj
        if focused:
            if isinstance(focused, Atom):
                mol = focused.molecule
                # Remove connected bonds first
                for bond in list(focused.bonds):
                    bond.disconnect_atoms()
                    mol.remove_bond(bond)
                    bond.delete_from_paper()
                mol.remove_atom(focused)
                focused.delete_from_paper()
                # Split or delete molecule if empty
                if not mol.atoms:
                    App.paper.removeObject(mol)
                else:
                    mol.split_fragments()
            elif isinstance(focused, Bond):
                mol = focused.molecule
                focused.disconnect_atoms()
                mol.remove_bond(focused)
                focused.delete_from_paper()
                mol.split_fragments()
            elif isinstance(focused, Arrow):
                focused.delete_from_paper()
            elif isinstance(focused, TextLabel):
                focused.delete_from_paper()
            
            App.paper.save_state_to_undo_stack()

class RotateTool(Tool):
    def __init__(self):
        self.mouse_press_pos = None
        self.center = None
        self.molecule = None

    def on_mouse_press(self, x, y):
        self.mouse_press_pos = (x, y)
        focused = App.paper.focused_obj
        if focused:
            if hasattr(focused, 'molecule'):
                self.molecule = focused.molecule
            else:
                self.molecule = focused
            if self.molecule:
                self.center = self.molecule.get_center()

    def on_mouse_move(self, x, y):
        if not App.paper.dragging or not self.molecule: return
        import math
        angle1 = math.atan2(self.mouse_press_pos[1] - self.center[1], self.mouse_press_pos[0] - self.center[0])
        angle2 = math.atan2(y - self.center[1], x - self.center[0])
        angle = angle2 - angle1
        self.molecule.rotate(angle, self.center)
        
        if hasattr(self.molecule, 'atoms'):
            for a in self.molecule.atoms:
                a.on_bond_count_change()
                a.draw()
        if hasattr(self.molecule, 'bonds'):
            for b in self.molecule.bonds:
                b.draw()
        elif hasattr(self.molecule, 'draw'):
            self.molecule.draw()
            
        self.mouse_press_pos = (x, y)

    def on_mouse_release(self, x, y):
        if self.molecule:
            App.paper.save_state_to_undo_stack()
        self.molecule = None

class TemplateTool(Tool):
    def __init__(self, template_name):
        self.template_name = template_name

    def on_mouse_press(self, x, y):
        focused = App.paper.focused_obj
        if isinstance(focused, Bond):
            self._fuse_to_bond(focused, x, y)
        else:
            self._place_at(x, y)
        App.paper.save_state_to_undo_stack()

    def _place_at(self, x, y):
        mol = Molecule()
        App.paper.addObject(mol)
        self._generate_ring(mol, x, y, 30, 0)

    def _fuse_to_bond(self, bond, x, y):
        mol = bond.molecule
        a1, a2 = bond.atoms
        # Calculate angle and length of the bond
        from math import atan2, sqrt, pi, cos, sin
        angle = atan2(a2.y - a1.y, a2.x - a1.x)
        length = sqrt((a2.x - a1.x)**2 + (a2.y - a1.y)**2)
        
        n = {"benzene": 6, "cyclohexane": 6, "cyclopentane": 5, "pyridine": 6, "furan": 5, "pyrrole": 5}.get(self.template_name, 6)
        ext_angle = 2 * pi / n
        
        # Determine side based on click position
        # Cross product of (a2-a1) and (click-a1)
        # In Qt coords (Y down), a positive cross product means one side, negative the other.
        side = (a2.x - a1.x) * (y - a1.y) - (a2.y - a1.y) * (x - a1.x)
        if side > 0:
            ext_angle = -ext_angle
        
        # We start from a2 and go around. The first bond is a2->a1 (already exists)
        # So we need to add n-2 new atoms.
        curr_angle = angle + pi - ext_angle
        curr_atom = a1
        
        atoms = [a2, a1]
        for i in range(n - 2):
            nx = curr_atom.x + length * cos(curr_angle)
            ny = curr_atom.y + length * sin(curr_angle)
            
            # Check if an atom already exists at this position
            new_atom = mol.new_atom("C")
            new_atom.set_pos(nx, ny)
            atoms.append(new_atom)
            
            new_bond = mol.new_bond()
            new_bond.set_type("single")
            new_bond.connect_atoms(curr_atom, new_atom)
            
            curr_atom = new_atom
            curr_angle -= ext_angle
            
        # Close the ring
        final_bond = mol.new_bond()
        final_bond.connect_atoms(curr_atom, a2)
        
        # If it's benzene, we need to fix double bond pattern and side
        if self.template_name == "benzene":
            # Naphthalene-like pattern: shared bond can be double or single.
            # Let's make the new ring alternate starting from a2-curr_atom as double.
            # And set second_line_side to point inwards.
            
            # Calculate center of new ring for second_line_side
            new_center_x = sum(a.x for a in atoms) / n
            new_center_y = sum(a.y for a in atoms) / n
            
            # Bonds in order: [a2-a1, a1-new1, new1-new2, new2-new3, new3-new4, new4-a2]
            shared_bond = bond
            # List of bonds for the new ring
            ring_bonds = [shared_bond]
            for i in range(2, len(atoms)):
                ring_bonds.append(mol.get_bond_between_atoms(atoms[i-1], atoms[i]))
            ring_bonds.append(final_bond)

            # Check if shared atoms already have double bonds elsewhere
            a1_has_double = any(bo.type == "double" for bo in a1.neighbor_edges if bo != bond)
            a2_has_double = any(bo.type == "double" for bo in a2.neighbor_edges if bo != bond)
            
            # Count total double bonds on shared atoms (including the shared bond)
            a1_double_count = sum(1 for bo in a1.neighbor_edges if bo.type == "double")
            a2_double_count = sum(1 for bo in a2.neighbor_edges if bo.type == "double")
            
            for i, b in enumerate(ring_bonds):
                if not b or i == 0: continue # Don't force change the shared bond
                
                # Extended logic to support up to 10 rings fusion
                # Check if adding a double bond would exceed valency (max 4 for carbon)
                # Each atom can have at most 2 double bonds (since each double bond counts as 2)
                can_add_double = True
                if b.atoms[0] in (a1, a2):
                    atom = b.atoms[0]
                    if atom == a1 and a1_double_count >= 2:
                        can_add_double = False
                    elif atom == a2 and a2_double_count >= 2:
                        can_add_double = False
                if b.atoms[1] in (a1, a2):
                    atom = b.atoms[1]
                    if atom == a1 and a1_double_count >= 2:
                        can_add_double = False
                    elif atom == a2 and a2_double_count >= 2:
                        can_add_double = False
                
                # If neither atom has a double bond (and shared isn't double), we can add 3 double bonds (i=1,3,5)
                # If they do have double bonds but still have capacity, we can still add double bonds
                # For extensive ring systems, prefer single bonds when valency is tight
                if not a1_has_double and not a2_has_double and bond.type != "double":
                    new_type = "double" if (i % 2 == 1) else "single"
                elif can_add_double:
                    # Allow double bond placement based on alternating pattern
                    new_type = "double" if (i % 2 == 0) else "single"
                else:
                    # Must use single bond to avoid exceeding valency
                    new_type = "single"
                
                b.set_type(new_type)
                
                if new_type == "double":
                    # Point double bond line towards the new ring center using native geometry logic
                    b.auto_second_line_side = False
                    v1 = b.atoms[0]
                    v2 = b.atoms[1]
                    from . import geometry as geo
                    b.second_line_side = geo.line_get_side_of_point([v1.x, v1.y, v2.x, v2.y], (new_center_x, new_center_y))
        else:
            final_bond.set_type("single")
        
        mol.handle_overlap()
        for a in mol.atoms: a.draw()
        for b in mol.bonds: b.draw()

    def _generate_ring(self, mol, x, y, radius, start_angle):
        from math import cos, sin, pi
        n = {"benzene": 6, "cyclohexane": 6, "cyclopentane": 5}[self.template_name]
        points = []
        for i in range(n):
            angle = start_angle + i * (2 * pi / n)
            points.append((x + radius * cos(angle), y + radius * sin(angle)))
        
        atoms = []
        for p in points:
            a = mol.new_atom("C")
            a.set_pos(*p)
            atoms.append(a)
        
        for i in range(n):
            b = mol.new_bond()
            is_double = (self.template_name == "benzene" and i % 2 == 0)
            b.set_type("double" if is_double else "single")
            b.connect_atoms(atoms[i], atoms[(i+1)%n])
        
        for a in mol.atoms: a.draw()
        for b in mol.bonds: b.draw()

class ArrowTool(Tool):
    def __init__(self, arrow_type="reaction", curvature=1.0):
        self.arrow_type = arrow_type
        self.curvature = curvature
        self.p1 = None
        self.preview_item = None

    def on_mouse_press(self, x, y):
        self.p1 = (x, y)

    def on_mouse_move(self, x, y):
        if not App.paper.dragging or not self.p1: return
        if self.preview_item:
            App.paper.removeItem(self.preview_item)
        self.preview_item = App.paper.addLine(self.p1 + (x, y), style=PenStyle.dashed)

    def on_mouse_release(self, x, y):
        if self.p1:
            if self.preview_item:
                App.paper.removeItem(self.preview_item)
                self.preview_item = None
            
            from .arrow import Arrow
            arrow = Arrow(self.p1, (x, y), type=self.arrow_type, curvature=self.curvature)
            App.paper.addObject(arrow)
            arrow.draw()
            App.paper.save_state_to_undo_stack()
        self.p1 = None

class TextTool(Tool):
    def __init__(self):
        self.current_text = None

    def on_mouse_press(self, x, y):
        focused = App.paper.focused_obj
        if isinstance(focused, TextLabel):
            self.current_text = focused
        else:
            # Create new text with empty string
            text = TextLabel(x, y, "")
            App.paper.addObject(text)
            text.draw()
            self.current_text = text
        App.paper.save_state_to_undo_stack()

    def on_key_press(self, key, text):
        if self.current_text:
            if key == 16777219:  # Backspace
                if self.current_text.text:
                    self.current_text.text = self.current_text.text[:-1]
                    self.current_text.draw()
                    App.paper.save_state_to_undo_stack()
            elif key == 16777220:  # Enter
                self.current_text = None
            elif text and text.isprintable():
                self.current_text.text += text
                self.current_text.draw()
                App.paper.save_state_to_undo_stack()
            return True
        return False

class SelectTool(Tool):
    def __init__(self):
        self.mouse_press_pos = None
        self.objs = []
        self.dragging_curvature = None
        self.selection_rect_item = None
        self.selection_start_pos = None
        self.mode = "move"  # "move" or "select"
        self.lasso_points = []
        self.lasso_item = None
        self.rotating = False
        self.right_click_press = None

    def on_mouse_press(self, x, y):
        self.mouse_press_pos = (x, y)
        self.selection_start_pos = (x, y)
        self.lasso_points = [(x, y)]
        focused = App.paper.focused_obj
        if focused:
            self.mode = "move"
            # Get the top-level object (molecule, arrow, text, etc.)
            if hasattr(focused, 'molecule') and focused.molecule:
                obj = focused.molecule
            elif hasattr(focused, 'parent') and focused.parent:
                obj = focused.parent
            else:
                obj = focused
            
            self.objs = [obj]
            
            # Update selection visuals
            for o in App.paper.objects:
                if hasattr(o, 'set_selected'):
                    o.set_selected(o in self.objs)
            
            # Check for curvature dragging (if clicked near p2 of an arrow)
            if isinstance(focused, Arrow):
                from math import sqrt
                dist_to_tip = sqrt((x - focused.p2[0])**2 + (y - focused.p2[1])**2)
                if dist_to_tip < 15:
                    self.dragging_curvature = focused
        else:
            self.mode = "select"
            self.objs = []
            for o in App.paper.objects:
                if hasattr(o, 'set_selected'):
                    o.set_selected(False)

    def on_right_click(self, x, y):
        self.right_click_press = (x, y)
        focused = App.paper.focused_obj
        if focused:
            # Get the top-level object (molecule, arrow, text, etc.)
            if hasattr(focused, 'molecule') and focused.molecule:
                obj = focused.molecule
            elif hasattr(focused, 'parent') and focused.parent:
                obj = focused.parent
            else:
                obj = focused
            
            if obj not in self.objs:
                self.objs = [obj]
            
            for o in App.paper.objects:
                if hasattr(o, 'set_selected'):
                    o.set_selected(o in self.objs)
            
            self.rotating = True

    def on_mouse_move(self, x, y):
        if not App.paper.dragging: return
        
        if self.rotating and self.right_click_press:
            # Rotate selected objects with right click
            if not self.objs: return
            obj = self.objs[0]
            if not hasattr(obj, 'get_center'): return
            
            center = obj.get_center()
            import math
            angle1 = math.atan2(self.right_click_press[1] - center[1], self.right_click_press[0] - center[0])
            angle2 = math.atan2(y - center[1], x - center[0])
            angle = (angle2 - angle1) * 0.4 # Reduced sensitivity
            
            obj.rotate(angle, center)
            if hasattr(obj, 'atoms'):
                for a in obj.atoms:
                    a.on_bond_count_change()
                    a.draw()
                for b in obj.bonds:
                    b.draw()
            else:
                obj.draw()
            
            self.right_click_press = (x, y)
            return
        
        if self.dragging_curvature:
            arrow = self.dragging_curvature
            # Calculate curvature based on perpendicular distance from line p1-p2
            import math
            p1, p2 = arrow.p1, arrow.p2
            dist_12 = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            if dist_12 < 1: return
            
            # Perpendicular distance using cross product
            # (p2-p1) cross (p_mouse-p1) / dist_12
            side_dist = ((p2[0] - p1[0]) * (y - p1[1]) - (p2[1] - p1[1]) * (x - p1[0])) / dist_12
            
            # Normalize curvature (dist * 0.3 * curvature = side_dist => curvature = side_dist / (dist * 0.3))
            arrow.curvature = side_dist / (dist_12 * 0.3)
            arrow.draw()
            return

        if self.mode == "select":
            # Draw selection rectangle (for now, rectangular selection)
            # Could be extended to lasso by tracking points
            if self.selection_rect_item:
                App.paper.removeItem(self.selection_rect_item)
            
            x1, y1 = self.selection_start_pos
            x2, y2 = x, y
            rect = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
            self.selection_rect_item = App.paper.addRect(rect, color=(100, 100, 255), width=1, fill=(100, 100, 255, 50))
            return

        if not self.objs: return
        
        # Move selected objects
        dx = x - self.mouse_press_pos[0]
        dy = y - self.mouse_press_pos[1]
        
        for obj in self.objs:
            if hasattr(obj, 'move_by'):
                obj.move_by(dx, dy)
            elif hasattr(obj, 'atoms'):
                # It's a molecule
                for a in obj.atoms:
                    a.move_by(dx, dy)
                    a.draw()
                for b in obj.bonds:
                    b.draw()
            elif hasattr(obj, 'draw'):
                obj.draw()
        
        self.mouse_press_pos = (x, y)

    def on_mouse_release(self, x, y):
        if self.rotating:
            self.rotating = False
            self.right_click_press = None
            if self.objs:
                App.paper.save_state_to_undo_stack()
            return
        
        if self.selection_rect_item:
            App.paper.removeItem(self.selection_rect_item)
            self.selection_rect_item = None
            
            # Select objects within the rectangle
            x1, y1 = self.selection_start_pos
            x2, y2 = x, y
            rect = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
            
            # Get objects in the selection rectangle
            selected = App.paper.objectsInRect(rect)
            self.objs = []
            for obj in selected:
                if hasattr(obj, 'molecule') and obj.molecule:
                    if obj.molecule not in self.objs:
                        self.objs.append(obj.molecule)
                else:
                    if obj not in self.objs:
                        self.objs.append(obj)
            
            # Update selection visuals
            for o in App.paper.objects:
                if hasattr(o, 'set_selected'):
                    o.set_selected(o in self.objs)
        
        if self.objs or self.dragging_curvature:
            App.paper.save_state_to_undo_stack()
        self.dragging_curvature = None
        self.mode = "move"

    def on_key_press(self, key, text):
        focused = App.paper.focused_obj
        if isinstance(focused, Atom):
            mapping = {
                'c': 'C', 'n': 'N', 'o': 'O', 's': 'S', 'p': 'P', 
                'f': 'F', 'l': 'Cl', 'b': 'Br', 'i': 'I', 'h': 'H'
            }
            symbol = mapping.get(text.lower())
            if symbol:
                focused.set_symbol(symbol)
                focused.draw()
                App.paper.save_state_to_undo_stack()
                return True
        elif isinstance(focused, Arrow):
            if text in ('+', '='):
                focused.curvature += 0.2
                focused.draw()
                App.paper.save_state_to_undo_stack()
                return True
            elif text in ('-', '_'):
                focused.curvature -= 0.2
                focused.draw()
                App.paper.save_state_to_undo_stack()
                return True
        elif isinstance(focused, TextLabel):
            if key == 16777219:  # Backspace
                if focused.text:
                    focused.text = focused.text[:-1]
                    focused.draw()
                    App.paper.save_state_to_undo_stack()
            elif text and text.isprintable():
                focused.text += text
                focused.draw()
                App.paper.save_state_to_undo_stack()
            return True
        return False
