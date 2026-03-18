"""
Python Console — Interactive Python interpreter widget.

Provides a REPL-like console embedded in the application.
The current molecule is available as `mol` in the console namespace.
"""

import sys
import io
import traceback
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QTextCursor
from src.shared.ui.theme import COLORS


class PythonConsole(QWidget):
    """
    Embedded Python interpreter with output display and command input.

    The molecule object is available as `mol` in the console namespace.
    Numpy is available as `np`.
    """

    command_executed = Signal(str)  # Emitted after each command with output

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(200)
        self.setMinimumHeight(80)

        self._namespace = {}
        self._history = []
        self._history_idx = 0

        self._init_ui()
        self._init_namespace()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header = QWidget()
        header.setFixedHeight(26)
        header.setStyleSheet(f"""
            background-color: {COLORS['bg_tertiary']};
            border-bottom: 1px solid {COLORS['border']};
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 10, 0)
        lbl = QLabel("Python Console")
        lbl.setStyleSheet(f"color: {COLORS['accent2']}; font-size: 11px; font-weight: 600;")
        header_layout.addWidget(lbl)
        header_layout.addStretch()
        help_lbl = QLabel("mol = current molecule | np = numpy")
        help_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        header_layout.addWidget(help_lbl)
        layout.addWidget(header)

        mono_font = QFont('JetBrains Mono', 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        fallbacks = ['Cascadia Code', 'Consolas', 'Courier New']
        for fb in fallbacks:
            mono_font.setFamily(fb)

        # Output area
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(mono_font)
        self.output.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
                border: none;
                padding: 4px 8px;
                selection-background-color: {COLORS['accent']};
            }}
        """)
        self.output.setPlaceholderText("Python console ready. Type commands below.")
        layout.addWidget(self.output, 1)

        # Input line
        input_container = QWidget()
        input_container.setStyleSheet(f"background-color: {COLORS['bg_secondary']}; border-top: 1px solid {COLORS['border']};")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(8, 3, 8, 3)
        input_layout.setSpacing(6)

        prompt = QLabel(">>>")
        prompt.setFont(mono_font)
        prompt.setStyleSheet(f"color: {COLORS['accent2']}; font-weight: bold;")
        input_layout.addWidget(prompt)

        self.input_line = QLineEdit()
        self.input_line.setFont(mono_font)
        self.input_line.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_widget']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['border_focus']};
            }}
        """)
        self.input_line.setPlaceholderText("Enter Python command...")
        self.input_line.returnPressed.connect(self._execute)
        input_layout.addWidget(self.input_line, 1)

        layout.addWidget(input_container)

    def _init_namespace(self):
        """Set up the console namespace with useful imports and helpers."""
        self._viewer_3d = None
        self._viewer_2d = None

        self._namespace = {
            '__builtins__': __builtins__,
            'mol': None,
            'print': self._console_print,
            # Main selection command — takes natural language strings
            'sele': self._sele,
            's': self._sele,           # Short alias
            'clear': self._clear_selection,
            'selected': self._get_selected,
            # Direct functions still available
            'select': self._select_by_element,
            'select_idx': self._select_by_indices,
            # Measurement
            'distance': self._measure_distance,
            'dist': self._measure_distance,
            'angle': self._measure_angle,
            # Fingerprints
            'morgan_fp': self._morgan_fp,
            'topological_fp': self._topological_fp,
            'maccs_keys': self._maccs_keys,
            'similarity': self._similarity,
            # Help
            'help_cmds': self._show_help,
        }
        # Pre-import numpy
        try:
            import numpy as np
            self._namespace['np'] = np
        except ImportError:
            pass

    def set_viewer(self, viewer_3d, viewer_2d=None):
        """Set viewer references for selection commands."""
        self._viewer_3d = viewer_3d
        self._viewer_2d = viewer_2d

    def set_molecule(self, molecule):
        """Update the molecule reference in the console namespace."""
        self._namespace['mol'] = molecule

    # ─── Natural Language Selection Parser ─────────────────────────

    def _sele(self, expr):
        """
        Select atoms using a natural expression string.
        Case-insensitive. Examples:
            sele('C')               - all carbon atoms
            sele('N or O')          - nitrogen or oxygen
            sele('C and ring')      - carbons in rings
            sele('not H')           - everything except H
            sele('ring')            - all ring atoms
            sele('nonring')         - all non-ring atoms
            sele('bonded N')        - atoms bonded to nitrogen
            sele('within 3.0 N')    - atoms within 3A of nitrogen
            sele('C and not ring')  - non-ring carbons
            sele('N or O or S')     - multiple element union
        """
        mol = self._namespace.get('mol')
        if not mol:
            self._append_text("No molecule loaded.", COLORS['warning'])
            return []

        try:
            result = self._parse_selection_expr(expr.strip(), mol)
            self._apply_selection(result)
            self._append_output(f"sele '{expr}': {len(result)} atom(s)")
            return sorted(result)
        except Exception as e:
            self._append_text(f"Selection error: {e}", COLORS['error'])
            return []

    def _parse_selection_expr(self, expr, mol):
        """Parse a selection expression into a set of atom indices."""
        expr = expr.strip()
        if not expr:
            return set()

        # Handle 'or' — split on 'or' (case-insensitive)
        # We split on ' or ' to avoid matching within words like 'fluorine'
        parts_or = self._split_keyword(expr, 'or')
        if len(parts_or) > 1:
            result = set()
            for part in parts_or:
                result |= self._parse_selection_expr(part.strip(), mol)
            return result

        # Handle 'and' — split on 'and'
        parts_and = self._split_keyword(expr, 'and')
        if len(parts_and) > 1:
            result = None
            for part in parts_and:
                part_set = self._parse_selection_expr(part.strip(), mol)
                if result is None:
                    result = part_set
                else:
                    result &= part_set
            return result if result is not None else set()

        # Handle 'not' prefix
        lower = expr.lower().strip()
        if lower.startswith('not '):
            inner = expr[4:].strip()
            inner_set = self._parse_selection_expr(inner, mol)
            all_atoms = set(a.index for a in mol.atoms)
            return all_atoms - inner_set

        # Handle 'within X.X <expr>'
        if lower.startswith('within ') or lower.startswith('near ') or lower.startswith('around '):
            return self._parse_within(expr, mol)

        # Handle 'bonded <expr>'
        if lower.startswith('bonded '):
            inner = expr[7:].strip()
            inner_set = self._parse_selection_expr(inner, mol)
            return self._compute_bonded(inner_set, mol)

        # Atomic terms
        return self._parse_atomic_term(lower, mol)

    def _split_keyword(self, expr, keyword):
        """Split expression on keyword (case-insensitive), respecting word boundaries."""
        lower = expr.lower()
        parts = []
        pattern = f' {keyword} '
        start = 0
        while True:
            idx = lower.find(pattern, start)
            if idx == -1:
                parts.append(expr[start:].strip())
                break
            parts.append(expr[start:idx].strip())
            start = idx + len(pattern)
        return [p for p in parts if p]

    def _parse_within(self, expr, mol):
        """Parse 'within 3.0 N' or 'near 3.0 C'"""
        import math as m
        tokens = expr.split(None, 2)
        if len(tokens) < 3:
            raise ValueError(f"Expected 'within <dist> <expr>', got: {expr}")
        try:
            dist = float(tokens[1])
        except ValueError:
            raise ValueError(f"Invalid distance: {tokens[1]}")
        inner_expr = tokens[2]
        src = self._parse_selection_expr(inner_expr, mol)

        result = set()
        for i in src:
            a1 = mol.atoms[i]
            if not a1.has_coords:
                continue
            for a2 in mol.atoms:
                if a2.index in src:
                    continue
                if not a2.has_coords:
                    continue
                dx = a1.x - a2.x
                dy = a1.y - a2.y
                dz = (a1.z or 0) - (a2.z or 0)
                d = m.sqrt(dx*dx + dy*dy + dz*dz)
                if d <= dist:
                    result.add(a2.index)
        return result | src

    def _compute_bonded(self, src_set, mol):
        """Get atoms bonded to source set."""
        result = set()
        for idx in src_set:
            for nb in mol.get_neighbors(idx):
                result.add(nb)
        return result | src_set

    def _parse_atomic_term(self, term, mol):
        """Parse a single selection term."""
        # Keywords
        if term in ('ring', 'rings'):
            rings = mol.find_rings()
            result = set()
            for r in rings:
                result.update(r)
            return result

        if term in ('nonring', 'non_ring', 'non-ring', 'chain'):
            rings = mol.find_rings()
            ring_set = set()
            for r in rings:
                ring_set.update(r)
            return set(a.index for a in mol.atoms) - ring_set

        if term in ('all', '*', 'everything'):
            return set(a.index for a in mol.atoms)

        if term in ('none', 'nothing'):
            return set()

        if term in ('heavy', 'hetero'):
            return set(a.index for a in mol.atoms if a.symbol != 'H')

        if term == 'h' or term == 'hydrogen':
            return set(a.index for a in mol.atoms if a.symbol == 'H')

        # Element symbol — case-insensitive matching
        # Try exact match first, then capitalize
        symbol = term[0].upper() + term[1:].lower() if len(term) > 1 else term.upper()

        # Common element names
        element_names = {
            'carbon': 'C', 'nitrogen': 'N', 'oxygen': 'O', 'sulfur': 'S',
            'phosphorus': 'P', 'fluorine': 'F', 'chlorine': 'Cl', 'bromine': 'Br',
            'iodine': 'I', 'boron': 'B', 'silicon': 'Si', 'selenium': 'Se',
        }
        if term in element_names:
            symbol = element_names[term]

        indices = [a.index for a in mol.atoms if a.symbol == symbol]
        if indices:
            return set(indices)

        # Try as-is (e.g., 'Cl', 'Br')
        indices = [a.index for a in mol.atoms if a.symbol.lower() == term]
        if indices:
            return set(indices)

        raise ValueError(f"Unknown selection term: '{term}'")

    # ─── Simple Functions ──────────────────────────────────────────

    def _select_by_element(self, element_symbol):
        """select('C') — select by element (backward compatible)."""
        mol = self._namespace.get('mol')
        if not mol:
            self._append_text("No molecule loaded.", COLORS['warning'])
            return []
        indices = [a.index for a in mol.atoms if a.symbol == element_symbol]
        self._apply_selection(indices)
        self._append_output(f"Selected {len(indices)} {element_symbol} atom(s)")
        return indices

    def _select_by_indices(self, indices):
        """select_idx([0,1,2]) — select by index list."""
        self._apply_selection(list(indices))
        self._append_output(f"Selected {len(indices)} atom(s)")
        return list(indices)

    def _clear_selection(self):
        """Clear all atom selections."""
        self._apply_selection([])
        self._append_output("Selection cleared.")

    def _get_selected(self):
        """Return list of currently selected atom indices."""
        if self._viewer_3d:
            return sorted(self._viewer_3d.selected_atoms)
        return []

    # ─── Measurement ───────────────────────────────────────────────

    def _measure_distance(self, idx1, idx2):
        """distance(0, 1) — measure distance between two atoms."""
        import math
        mol = self._namespace.get('mol')
        if not mol:
            return 0.0
        a1, a2 = mol.atoms[idx1], mol.atoms[idx2]
        if a1.has_coords and a2.has_coords:
            dx = a1.x - a2.x
            dy = a1.y - a2.y
            dz = (a1.z or 0) - (a2.z or 0)
            d = math.sqrt(dx*dx + dy*dy + dz*dz)
            self._append_output(
                f"Distance {a1.symbol}{idx1}-{a2.symbol}{idx2}: {d:.3f} A")
            return d
        self._append_text("Atoms have no coordinates.", COLORS['warning'])
        return 0.0

    def _measure_angle(self, idx1, idx2, idx3):
        """angle(0, 1, 2) — measure angle at vertex idx2."""
        import math
        mol = self._namespace.get('mol')
        if not mol:
            return 0.0
        a1, a2, a3 = mol.atoms[idx1], mol.atoms[idx2], mol.atoms[idx3]
        if a1.has_coords and a2.has_coords and a3.has_coords:
            import numpy as np
            v1 = np.array([a1.x - a2.x, a1.y - a2.y, (a1.z or 0) - (a2.z or 0)])
            v2 = np.array([a3.x - a2.x, a3.y - a2.y, (a3.z or 0) - (a2.z or 0)])
            cos_a = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-12)
            ang = math.degrees(math.acos(max(-1, min(1, cos_a))))
            self._append_output(
                f"Angle {a1.symbol}{idx1}-{a2.symbol}{idx2}-{a3.symbol}{idx3}: {ang:.1f} deg")
            return ang
        self._append_text("Atoms have no coordinates.", COLORS['warning'])
        return 0.0

    # ─── Fingerprints ──────────────────────────────────────────────

    def _morgan_fp(self, radius=2, n_bits=2048):
        """morgan_fp(radius=2, n_bits=2048) — compute Morgan fingerprint."""
        from src.features.cheminformatics.topology.fingerprints import get_morgan_fingerprint
        mol = self._namespace.get('mol')
        if not mol:
            self._append_text("No molecule loaded.", COLORS['warning'])
            return None
        fp = get_morgan_fingerprint(mol, radius, n_bits)
        n_set = sum(fp)
        self._append_output(f"Morgan FP (r={radius}, {n_bits} bits) generated with {n_set} bits set.")
        return fp

    def _topological_fp(self, min_path=1, max_path=7, n_bits=2048):
        """topological_fp(max_path=7, n_bits=2048) — compute topological fingerprint."""
        from src.features.cheminformatics.topology.fingerprints import get_topological_fingerprint
        mol = self._namespace.get('mol')
        if not mol:
            self._append_text("No molecule loaded.", COLORS['warning'])
            return None
        fp = get_topological_fingerprint(mol, min_path, max_path, n_bits)
        n_set = sum(fp)
        self._append_output(f"Topological FP (path={min_path}-{max_path}, {n_bits} bits) generated with {n_set} bits set.")
        return fp

    def _maccs_keys(self):
        """maccs_keys() — compute MACCS keys."""
        from src.features.cheminformatics.topology.fingerprints import get_maccs_keys
        mol = self._namespace.get('mol')
        if not mol:
            self._append_text("No molecule loaded.", COLORS['warning'])
            return None
        fp = get_maccs_keys(mol)
        n_set = sum(fp)
        self._append_output(f"MACCS Keys (166 bits) generated with {n_set} bits set.")
        return fp

    def _similarity(self, fp1, fp2):
        """similarity(fp1, fp2) — compute Tanimoto similarity."""
        from src.features.cheminformatics.topology.fingerprints import tanimoto_similarity
        if not fp1 or not fp2:
            self._append_text("Invalid fingerprints provided.", COLORS['warning'])
            return 0.0
        try:
            sim = tanimoto_similarity(fp1, fp2)
            self._append_output(f"Tanimoto Similarity: {sim:.4f}")
            return sim
        except Exception as e:
            self._append_text(f"Error computing similarity: {e}", COLORS['warning'])
            return 0.0

    # ─── Internals ─────────────────────────────────────────────────

    def _apply_selection(self, indices):
        """Apply selection to viewers."""
        idx_set = set(indices)
        if self._viewer_3d:
            self._viewer_3d.set_selected(idx_set)
        if self._viewer_2d:
            self._viewer_2d.set_selected(idx_set)

    def _show_help(self):
        """Show available console commands."""
        help_text = (
            "=== Selection (natural syntax) ===\n"
            "  sele('C')              Select carbons\n"
            "  sele('N or O')         Nitrogen or oxygen\n"
            "  sele('C and ring')     Carbons in rings\n"
            "  sele('not H')          All except H\n"
            "  sele('ring')           All ring atoms\n"
            "  sele('nonring')        Non-ring atoms\n"
            "  sele('bonded N')       Bonded to nitrogen\n"
            "  sele('within 3.0 N')   Within 3A of nitrogen\n"
            "  sele('C and not ring') Non-ring carbons\n"
            "  sele('heavy')          Non-hydrogen atoms\n"
            "  s('N or O or S')       s() = short for sele()\n"
            "  clear()                Clear selection\n"
            "  selected()             Get selected indices\n"
            "=== Measurement ===\n"
            "  distance(0, 1)         Distance in Angstroms\n"
            "  angle(0, 1, 2)         Angle in degrees\n"
            "=== Fingerprints ===\n"
            "  fp = morgan_fp(r=2)    Morgan (ECFP) fingerprint\n"
            "  fp = topological_fp()  Daylight-like topological\n"
            "  fp = maccs_keys()      MACCS structural keys (subset)\n"
            "  similarity(fp1, fp2)   Tanimoto similarity\n"
            "=== Molecule ===\n"
            "  mol.atoms / bonds      Atom/bond lists\n"
            "  mol.molecular_formula()\n"
            "  np                     NumPy module"
        )
        self._append_text(help_text, COLORS['accent2'])

    def _console_print(self, *args, **kwargs):
        """Custom print that outputs to the console widget."""
        output = io.StringIO()
        kwargs['file'] = output
        print(*args, **kwargs)
        self._append_output(output.getvalue().rstrip('\n'))

    def _execute(self):
        """Execute the current input line."""
        cmd = self.input_line.text().strip()
        if not cmd:
            return

        # Show command
        self._append_text(f">>> {cmd}", COLORS['accent2'])

        # Add to history
        self._history.append(cmd)
        self._history_idx = len(self._history)
        self.input_line.clear()

        # Execute
        try:
            # Try eval first (expression)
            try:
                result = eval(cmd, self._namespace)
                if result is not None:
                    self._append_output(repr(result))
            except SyntaxError:
                # Fall back to exec (statement)
                exec(cmd, self._namespace)
        except Exception:
            tb = traceback.format_exc()
            # Show only the last few lines
            lines = tb.strip().split('\n')
            if len(lines) > 4:
                lines = lines[-3:]
            self._append_text('\n'.join(lines), COLORS['error'])

        self.command_executed.emit(cmd)

    def _append_output(self, text):
        """Append normal output."""
        self._append_text(text, COLORS['text_primary'])

    def _append_text(self, text, color):
        """Append colored text to output."""
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = cursor.charFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(text + '\n')

        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def keyPressEvent(self, event):
        """Handle history navigation."""
        if event.key() == Qt.Key.Key_Up and self._history:
            self._history_idx = max(0, self._history_idx - 1)
            self.input_line.setText(self._history[self._history_idx])
        elif event.key() == Qt.Key.Key_Down and self._history:
            self._history_idx = min(len(self._history), self._history_idx + 1)
            if self._history_idx < len(self._history):
                self.input_line.setText(self._history[self._history_idx])
            else:
                self.input_line.clear()
        else:
            super().keyPressEvent(event)
